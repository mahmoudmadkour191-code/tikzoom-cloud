"""GitHub Actions state persistence for TikZoom.

The platform runs 24/7 on ephemeral GitHub Actions runners. Everything that
must survive a runner restart (the SQLite database + every hosted bot's
project files) is committed back to the repository, encrypted with Fernet
(``STATE_KEY`` secret), so a public repo never leaks bot tokens or user data.

Layout under ``runtime_state/``:
    db.sqlite.enc   — Fernet(sqlite3 backup bytes of data/platform.db)
    files/<sha>.enc — content-addressed encrypted blobs (bots_storage tree)
    manifest.json   — {relative_path: sha256} for the stored blobs

Content addressing means git only stores a blob when a file actually changed,
so the repo history stays small even with a commit every few minutes.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import subprocess  # noqa: S404
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

STATE_DIR_NAME = "runtime_state"
_EXCLUDED_DIRS = {"node_modules", "__pycache__", ".git", ".tikvenv", ".venv", "venv", ".deps"}
_MAX_FILE_BYTES = 90 * 1024 * 1024  # GitHub hard limit is 100MB — stay well below


def repo_root() -> Path:
    """The project root (parent of ``app/``)."""
    return Path(__file__).resolve().parent.parent


def state_dir() -> Path:
    d = repo_root() / STATE_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fernet():
    key = os.environ.get("STATE_KEY", "").strip()
    if not key:
        return None
    from cryptography.fernet import Fernet

    try:
        return Fernet(key.encode())
    except Exception:  # noqa: BLE001
        logger.error("STATE_KEY is not a valid Fernet key — state persistence disabled")
        return None


def _is_git_repo() -> bool:
    return (repo_root() / ".git").is_dir()


# ---------------------------------------------------------------- restore -- #

def restore_state() -> dict:
    """Rebuild data/platform.db and bots_storage/ from the committed state.

    Returns a small summary dict for logging. Never raises.
    """
    summary = {"restored": False, "files": 0, "db": False}
    try:
        f = _fernet()
        if f is None:
            logger.info("STATE_KEY not set — starting with a fresh state")
            return summary
        sdir = state_dir()
        db_enc = sdir / "db.sqlite.enc"
        settings = get_settings()
        if db_enc.is_file():
            try:
                raw = f.decrypt(db_enc.read_bytes())
                db_path = Path(settings.db_path)
                db_path.parent.mkdir(parents=True, exist_ok=True)
                # remove stale WAL/SHM so sqlite opens the restored file clean
                for suffix in ("-wal", "-shm"):
                    p = Path(str(db_path) + suffix)
                    if p.exists():
                        p.unlink()
                db_path.write_bytes(raw)
                summary["db"] = True
                logger.info("restored platform.db (%d bytes)", len(raw))
            except Exception as exc:  # noqa: BLE001
                logger.error("failed to restore db: %s", exc)

        manifest_path = sdir / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                logger.error("manifest unreadable: %s", exc)
                manifest = {}
            files: dict[str, str] = manifest.get("files", {})
            root = repo_root()
            ok = 0
            for rel, sha in files.items():
                blob = sdir / "files" / f"{sha}.enc"
                if not blob.is_file():
                    logger.warning("missing blob for %s (%s)", rel, sha)
                    continue
                try:
                    data = f.decrypt(blob.read_bytes())
                    target = root / rel
                    if not str(target.resolve()).startswith(str(root.resolve())):
                        continue  # path escape guard
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    ok += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning("restore failed for %s: %s", rel, exc)
            summary["files"] = ok
            logger.info("restored %d files from runtime_state", ok)
        summary["restored"] = True
    except Exception:  # noqa: BLE001
        logger.exception("restore_state failed")
    return summary


def get_settings():
    from .config import get_settings as _gs

    return _gs()


# ----------------------------------------------------------------- commit -- #

def _sqlite_backup_bytes(db_path: str) -> bytes | None:
    """Consistent snapshot of the live SQLite db via the backup API."""
    tmp = None
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        src = sqlite3.connect(db_path, timeout=10)
        dst = sqlite3.connect(tmp.name)
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
        data = Path(tmp.name).read_bytes()
        return data
    except Exception as exc:  # noqa: BLE001
        logger.error("sqlite backup failed: %s", exc)
        return None
    finally:
        if tmp:
            Path(tmp.name).unlink(missing_ok=True)


def _iter_project_files() -> list[Path]:
    settings = get_settings()
    bots_root = Path(settings.bots_path)
    if not bots_root.is_dir():
        return []
    out: list[Path] = []
    for p in bots_root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in _EXCLUDED_DIRS for part in p.parts):
            continue
        if p.suffix in {".pyc", ".pyo"}:
            continue
        out.append(p)
    return out


def build_state(f) -> dict:
    """Produce db.sqlite.enc + files/*.enc + manifest.json. Returns manifest."""
    sdir = state_dir()
    files_dir = sdir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    # 1) database
    db_bytes = _sqlite_backup_bytes(settings.db_path)
    if db_bytes is not None:
        enc = f.encrypt(db_bytes)
        tmp = sdir / "db.sqlite.enc.tmp"
        tmp.write_bytes(enc)
        tmp.replace(sdir / "db.sqlite.enc")

    # 2) project files → content-addressed blobs
    files_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, str] = {}
    referenced: set[str] = set()
    bots_root = Path(settings.bots_path).resolve()
    skipped_big = 0
    for p in _iter_project_files():
        try:
            if p.stat().st_size > _MAX_FILE_BYTES:
                skipped_big += 1
                continue
            data = p.read_bytes()
        except OSError:
            continue
        sha = hashlib.sha256(data).hexdigest()
        blob = files_dir / f"{sha}.enc"
        if not blob.is_file():
            try:
                tmp = blob.with_suffix(".tmp")
                tmp.write_bytes(f.encrypt(data))
                tmp.replace(blob)
            except OSError as exc:
                logger.warning("blob write failed for %s: %s", p, exc)
                continue
        rel = str(p.resolve().relative_to(repo_root()))
        manifest[rel] = sha
        referenced.add(sha)
    if skipped_big:
        logger.warning("skipped %d oversized files (>90MB)", skipped_big)

    # 3) garbage-collect unreferenced blobs
    for blob in files_dir.glob("*.enc"):
        if blob.stem not in referenced:
            try:
                blob.unlink()
            except OSError:
                pass

    mpath = sdir / "manifest.json"
    tmpm = mpath.with_suffix(".tmp")
    tmpm.write_text(json.dumps(
        {"version": 1, "updated": dt.datetime.utcnow().isoformat() + "Z", "files": manifest},
        ensure_ascii=False, indent=1,
    ), encoding="utf-8")
    tmpm.replace(mpath)
    return manifest


def _git(*args: str, timeout: float = 120.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(repo_root()), capture_output=True,
            text=True, timeout=timeout,
        )
        return proc.returncode or 0, (proc.stdout + proc.stderr)[-1500:]
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def _git_push(branch: str) -> tuple[bool, str]:
    rc, out = _git("push", "origin", f"HEAD:{branch}", timeout=300)
    if rc == 0:
        return True, out
    logger.warning("push failed (%s) — attempting rebase + retry", out[-300:])
    _git("pull", "--rebase", "origin", branch, timeout=300)
    rc, out = _git("push", "origin", f"HEAD:{branch}", timeout=300)
    return rc == 0, out


def commit_state_sync(*, label: str = "auto") -> bool:
    """Encrypt + commit + push the current state. Safe to call anywhere."""
    f = _fernet()
    if f is None:
        logger.info("STATE_KEY not set — skipping state commit")
        return False
    if not _is_git_repo():
        logger.info("not a git repo — skipping state commit")
        return False
    try:
        save_pending_to_db()
        build_state(f)
        _git("add", "-A", STATE_DIR_NAME)
        rc, diff = _git("diff", "--cached", "--quiet")
        if rc == 0:
            logger.info("state unchanged — no commit needed")
            return True
        ts = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        branch = os.environ.get("GH_BRANCH") or "main"
        _git("commit", "-m", f"state: {label} {ts}", timeout=120)
        ok, out = _git_push(branch)
        if ok:
            logger.info("state committed & pushed (%s)", label)
        else:
            logger.error("state push failed: %s", out[-400:])
        return ok
    except Exception:  # noqa: BLE001
        logger.exception("commit_state failed")
        return False


async def commit_state(*, label: str = "auto") -> bool:
    return await asyncio.to_thread(commit_state_sync, label=label)


# --------------------------------------------------------------- dispatch -- #

async def dispatch_next_run() -> bool:
    """Trigger the next ``run.yml`` cycle via the GitHub API (self-handover)."""
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not repo or not token:
        logger.info("not on GitHub Actions — skipping next-run dispatch")
        return False
    branch = os.environ.get("GH_BRANCH") or "main"
    import httpx

    url = f"https://api.github.com/repos/{repo}/actions/workflows/run.yml/dispatches"
    payload = {"ref": branch}
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code in (200, 201, 202, 204):
                logger.info("next run dispatched on %s", branch)
                return True
            logger.error("dispatch failed: HTTP %s %s", r.status_code, r.text[:300])
    except Exception as exc:  # noqa: BLE001
        logger.error("dispatch error: %s", exc)
    return False


# ------------------------------------------------------- pending flows i/o -- #

async def save_pending_to_db() -> None:
    """Persist in-memory pending flows so uploads survive runner restarts."""
    try:
        from . import bot_handlers as bh
        from .repo import set_setting

        if not bh._pending:
            return
        data = json.dumps({str(k): v for k, v in bh._pending.items()}, ensure_ascii=False)
        await set_setting("gh_pending_json", data[:100000])
    except Exception as exc:  # noqa: BLE001
        logger.debug("save pending failed: %s", exc)


async def load_pending_from_db() -> None:
    try:
        from . import bot_handlers as bh
        from .repo import get_setting

        raw = await get_setting("gh_pending_json", "")
        if not raw:
            return
        data = json.loads(raw)
        for k, v in data.items():
            try:
                bh._pending[int(k)] = v
            except (ValueError, TypeError):
                continue
        if data:
            logger.info("restored %d pending flows", len(data))
    except Exception as exc:  # noqa: BLE001
        logger.debug("load pending failed: %s", exc)
