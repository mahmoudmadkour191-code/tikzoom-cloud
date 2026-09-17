from __future__ import annotations

import asyncio
import atexit
import json
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Optional


_STATE_FILE = Path(__file__).resolve().parents[2] / ".runtime_state.json"
_STATE_LOCK = RLock()
_state: dict[str, Any] = {}
_state_path: Optional[Path] = None
_state_dirty = False
_flush_task: Optional[asyncio.Task] = None


def _load_state_unlocked() -> dict[str, Any]:
    if not _STATE_FILE.exists():
        return {}

    try:
        return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _ensure_state_cached_unlocked() -> dict[str, Any]:
    global _state, _state_path, _state_dirty
    if _state_path != _STATE_FILE:
        _state = _load_state_unlocked()
        _state_path = _STATE_FILE
        _state_dirty = False
    return _state


def _write_state_unlocked(state: dict[str, Any]) -> None:
    if not state:
        if _STATE_FILE.exists():
            _STATE_FILE.unlink()
        return

    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_path = _STATE_FILE.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(state, ensure_ascii=True, separators=(",", ":")),
        encoding="utf-8",
    )
    temp_path.replace(_STATE_FILE)


def _flush_state() -> None:
    global _state_dirty
    with _STATE_LOCK:
        if not _state_dirty:
            return
        _state_dirty = False
        if _state_path != _STATE_FILE:
            return
        _write_state_unlocked(_state)


async def _flush_state_async() -> None:
    global _flush_task
    try:
        while True:
            await asyncio.to_thread(_flush_state)
            with _STATE_LOCK:
                if not _state_dirty:
                    return
    finally:
        _flush_task = None


def _schedule_flush() -> None:
    global _flush_task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        _flush_state()
        return

    if _flush_task is None or _flush_task.done():
        _flush_task = loop.create_task(_flush_state_async())


def load_bucket(name: str, default_factory: Callable[[], Any]) -> Any:
    with _STATE_LOCK:
        state = _ensure_state_cached_unlocked()
        value = state.get(name)
        if value is None:
            return default_factory()
        return value


def save_bucket(name: str, value: Any) -> None:
    global _state_dirty
    with _STATE_LOCK:
        state = _ensure_state_cached_unlocked()
        if value:
            state[name] = value
        else:
            state.pop(name, None)
        _state_dirty = True
    _schedule_flush()


atexit.register(_flush_state)
