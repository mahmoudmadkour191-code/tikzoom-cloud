"""TikZoom on GitHub Actions — polling entry point.

Replaces the FastAPI/webhook + Podman server with:
  * state restore from the encrypted repo snapshot (gh_state.restore_state)
  * long-polling of the platform bot (no inbound HTTP on runners)
  * hosted bots as supervised subprocesses with per-bot venvs (runner.py)
  * periodic encrypted state commits + self-handover before the 6h job limit
  * a watchdog schedule in .github/workflows/watchdog.yml as the safety net

Usage:  python -m app.gh_main   (repo root, env from workflow secrets)
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone

from .config import get_settings
from .db import init_db
from .repo import (
    decode_bot_env,
    get_setting,
    list_all_bots,
    set_setting,
)
from .runner import get_runner
from .security import decrypt_token
from .telegram_api import TelegramError, TgClient

logger = logging.getLogger("gh_main")

_POLL_TIMEOUT = 25          # seconds (long poll)
_RECONCILE_CONCURRENCY = 3  # parallel bot boots
_HEALTH_INTERVAL = 60       # seconds between health sweeps
_MAX_BOT_RESTARTS = 3       # per cycle, per bot
_RESTART_COOLDOWN = 120     # seconds before a restart is retried


def _soft_limit_seconds() -> float:
    try:
        minutes = float(os.environ.get("TIKZOOM_SOFT_LIMIT_MIN", "325"))
    except ValueError:
        minutes = 325.0
    return max(minutes, 1.0) * 60.0


def _state_interval() -> float:
    try:
        minutes = float(os.environ.get("TIKZOOM_STATE_INTERVAL_MIN", "15"))
    except ValueError:
        minutes = 15.0
    return max(minutes, 3.0) * 60.0


async def _delete_webhook(client: TgClient) -> None:
    """getUpdates conflicts with an active webhook — make sure none is set."""
    try:
        await client.call("deleteWebhook", drop_pending_updates=False)
    except Exception as exc:  # noqa: BLE001
        logger.warning("deleteWebhook failed: %s", exc)


async def _announce_boot(client: TgClient, running_bots: int) -> None:
    s = get_settings()
    targets = s.admin_id_list
    if not targets:
        return
    username = await get_setting("main_bot_username", "")
    text = (
        "🚀 <b>TikZoom Cloud — الدورة بدأت</b>\n\n"
        f"🤖 البوتات المستضافة الشغالة: <b>{running_bots}</b>\n"
        "🔄 إعادة جدولة تلقائية كل ~5.4 ساعة\n"
        "🛡️ الحماية: فحص ثابت + Gemini\n"
        "💾 الحالة: محفوظة مشفرة داخل المستودع"
    )
    if username:
        text += f"\n\n✅ <b>@{username}</b> شغال 24/7"
    for chat_id in targets[:3]:
        with contextlib.suppress(Exception):
            await client.send_message(chat_id, text)


async def reconcile_bots() -> int:
    """Restart every bot whose status is ``running`` in the restored DB."""
    runner = get_runner()
    bots = await list_all_bots()
    to_start = [b for b in bots if b.status == "running"]
    logger.info("reconcile: %d bots to start (of %d total)", len(to_start), len(bots))
    sem = asyncio.Semaphore(_RECONCILE_CONCURRENCY)
    started = 0

    async def _start_one(b) -> None:
        nonlocal started
        async with sem:
            try:
                token = decrypt_token(b.token_encrypted)
            except Exception as exc:  # noqa: BLE001
                logger.error("bot %s token decrypt failed: %s", b.id, exc)
                return
            env = decode_bot_env(b.env_json or "")
            # GitHub runners cannot receive webhooks — always polling.
            result = await runner.start_supervised(
                bot_id=b.id, language=b.language, file_path=b.file_path,
                token=token, port=None, webhook_url=None, cwd=None,
                extra_env=env,
            )
            if result.error:
                logger.error("bot %s (%s) failed to start: %s",
                             b.id, b.name, result.error[:300])
                from .repo import update_bot_status
                await update_bot_status(b.id, status="crashed",
                                        last_error=result.error[:600])
            else:
                started += 1
                logger.info("bot %s (%s) started", b.id, b.name)

    await asyncio.gather(*(_start_one(b) for b in to_start))
    return started


async def health_loop(runner, stop: asyncio.Event) -> None:
    """Sweep hosted bots: restart ones that died mid-cycle (bounded retries)."""
    from .repo import get_bot, update_bot_status

    restarts: dict[int, int] = {}
    last_attempt: dict[int, float] = {}
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=_HEALTH_INTERVAL)
            return
        except asyncio.TimeoutError:
            pass
        try:
            bots = await list_all_bots()
        except Exception as exc:  # noqa: BLE001
            logger.warning("health sweep db error: %s", exc)
            continue
        for b in bots:
            if b.status != "running" or b.id is None:
                continue
            if runner.is_running(b.id):
                continue
            now = time.monotonic()
            if now - last_attempt.get(b.id, 0.0) < _RESTART_COOLDOWN:
                continue
            n = restarts.get(b.id, 0)
            if n >= _MAX_BOT_RESTARTS:
                continue
            fresh = await get_bot(b.id)
            if not fresh or fresh.status != "running":
                continue
            restarts[b.id] = n + 1
            last_attempt[b.id] = now
            logger.warning("bot %s died — restart %d/%d", b.id, n + 1, _MAX_BOT_RESTARTS)
            try:
                token = decrypt_token(fresh.token_encrypted)
                env = decode_bot_env(fresh.env_json or "")
                result = await runner.start_supervised(
                    bot_id=fresh.id, language=fresh.language,
                    file_path=fresh.file_path, token=token,
                    port=None, webhook_url=None, cwd=None, extra_env=env,
                )
                if result.error:
                    await update_bot_status(fresh.id, status="crashed",
                                            last_error=result.error[:600])
            except Exception as exc:  # noqa: BLE001
                logger.error("restart of bot %s failed: %s", b.id, exc)
                await update_bot_status(fresh.id, status="crashed",
                                        last_error=f"restart error: {exc}"[:600])


async def poll_loop(client: TgClient, stop: asyncio.Event) -> None:
    from .bot_handlers import handle_update

    offset = 0
    try:
        raw = await get_setting("gh_updates_offset", "0")
        offset = int(raw or 0)
    except Exception:  # noqa: BLE001
        offset = 0
    logger.info("polling started (offset=%d)", offset)
    while not stop.is_set():
        try:
            updates = await client.call(
                "getUpdates",
                offset=offset,
                timeout=_POLL_TIMEOUT,
                allowed_updates=["message", "callback_query"],
            )
        except TelegramError as exc:
            msg = str(exc)
            if "409" in msg or "Conflict" in msg:
                logger.error("poll conflict (another getUpdates?) — retrying in 10s")
                await asyncio.sleep(10)
            elif "429" in msg or "Too Many Requests" in msg:
                logger.warning("rate limited — sleeping 15s")
                await asyncio.sleep(15)
            else:
                logger.warning("getUpdates error: %s", msg[:200])
                await asyncio.sleep(5)
            continue
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("poll network error: %s", exc)
            await asyncio.sleep(5)
            continue
        for upd in updates or []:
            offset = max(offset, int(upd.get("update_id", 0))) + 1
            await handle_update(client, upd)
        if updates:
            with contextlib.suppress(Exception):
                await set_setting("gh_updates_offset", str(offset))


async def periodic_commit(stop: asyncio.Event) -> None:
    from . import gh_state

    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=_state_interval())
            return
        except asyncio.TimeoutError:
            pass
        logger.info("periodic state commit…")
        await gh_state.commit_state(label="periodic")


async def main() -> int:
    from . import gh_state

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )
    started_at = time.monotonic()
    boot_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    logger.info("=== TikZoom GH runner boot %s (pid %d) ===", boot_ts, os.getpid())

    summary = await asyncio.to_thread(gh_state.restore_state)
    logger.info("state restore: %s", summary)

    await init_db()
    await gh_state.load_pending_from_db()

    s = get_settings()
    if not s.bot_token:
        logger.critical("BOT_TOKEN missing — refusing to start")
        return 2

    client = TgClient(s.bot_token, timeout=45.0)
    me = await client.call("getMe")
    username = me.get("username") or ""
    first = me.get("first_name") or ""
    logger.info("platform bot: @%s (%s)", username, first)
    await set_setting("main_bot_username", username)
    await _delete_webhook(client)

    stop = asyncio.Event()
    runner = get_runner()
    logger.info("runner mode: process (per-bot venv isolation)")

    # Reconcile in background so the bot responds while heavy boots proceed.
    reconcile_task = asyncio.create_task(_reconcile_and_notify(client))
    health_task = asyncio.create_task(health_loop(runner, stop))
    commit_task = asyncio.create_task(periodic_commit(stop))
    poll_task = asyncio.create_task(poll_loop(client, stop))

    loop = asyncio.get_running_loop()
    shutdown_requested = asyncio.Event()

    def _signal(signame: str) -> None:
        logger.warning("received %s — shutting down cleanly", signame)
        shutdown_requested.set()

    for signame in ("SIGTERM", "SIGINT"):
        with contextlib.suppress(NotImplementedError, AttributeError):
            loop.add_signal_handler(getattr(signal, signame), _signal, signame)

    deadline = started_at + _soft_limit_seconds()
    try:
        while not shutdown_requested.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.info("soft limit reached — handing over to the next run")
                break
            try:
                await asyncio.wait_for(shutdown_requested.wait(), timeout=min(remaining, 60))
            except asyncio.TimeoutError:
                pass
    finally:
        stop.set()
        for task in (poll_task, commit_task, health_task, reconcile_task):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        logger.info("committing state before exit…")
        await gh_state.commit_state(label="handover")
        await gh_state.dispatch_next_run()
        with contextlib.suppress(Exception):
            await runner.stop_all()
        with contextlib.suppress(Exception):
            await client.close()
        logger.info("goodbye — next cycle queued")
    return 0


async def _reconcile_and_notify(client: TgClient) -> None:
    try:
        started = await reconcile_bots()
        await _announce_boot(client, started)
    except Exception:  # noqa: BLE001
        logger.exception("reconcile failed")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
