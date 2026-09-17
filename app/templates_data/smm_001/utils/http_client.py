import asyncio
from typing import Optional

import aiohttp

from services.logger import logger as logging

_session: Optional[aiohttp.ClientSession] = None
_session_loop: Optional[asyncio.AbstractEventLoop] = None
_lock = asyncio.Lock()
_lock_loop: Optional[asyncio.AbstractEventLoop] = None

# Slightly higher limits to speed up bursty handler traffic while keeping sockets bounded
_CLIENT_TIMEOUT = aiohttp.ClientTimeout(total=20, connect=5, sock_read=20)
_CONNECTOR_LIMIT = 128


def _get_loop_bound_lock() -> asyncio.Lock:
    """Return the module lock, recreating it when the running loop changes.

    An asyncio.Lock binds to the loop that first awaits it, so reusing the old
    instance after a loop change would raise RuntimeError and permanently break
    the session-recreation path this module implements.
    """
    global _lock, _lock_loop
    loop = asyncio.get_running_loop()
    if _lock_loop is not loop:
        _lock = asyncio.Lock()
        _lock_loop = loop
    return _lock


async def _close_session_from_previous_loop(session: aiohttp.ClientSession) -> None:
    """Best-effort cleanup for a session created on a different event loop.

    Awaiting ``session.close()`` would touch the previous loop's connector, so
    detach the session and close the connector directly instead.
    """
    try:
        connector = session.connector
        session.detach()
        if connector is not None:
            await connector.close()
    except Exception as exc:
        logging.debug("Discarding HTTP session from a previous event loop: error=%s", exc)


async def get_http_session() -> aiohttp.ClientSession:
    """Return a lazily initialised shared aiohttp session."""
    global _session, _session_loop
    loop = asyncio.get_running_loop()
    if _session and not _session.closed and _session_loop is loop:
        return _session

    async with _get_loop_bound_lock():
        if _session and not _session.closed and _session_loop is loop:
            return _session

        previous_session = _session
        connector = aiohttp.TCPConnector(
            limit=_CONNECTOR_LIMIT,
            limit_per_host=32,
            ttl_dns_cache=300,
            enable_cleanup_closed=True,
        )
        _session = aiohttp.ClientSession(timeout=_CLIENT_TIMEOUT, connector=connector)
        _session_loop = loop
        if previous_session and not previous_session.closed:
            # An open previous session here means the loop changed, so awaiting
            # its close() would run on the wrong loop.
            await _close_session_from_previous_loop(previous_session)
    return _session


async def close_http_session() -> None:
    """Close the shared session if it was created."""
    global _session, _session_loop
    async with _get_loop_bound_lock():
        session = _session
        session_loop = _session_loop
        _session = None
        _session_loop = None
    if session and not session.closed:
        if session_loop is asyncio.get_running_loop():
            await session.close()
        else:
            await _close_session_from_previous_loop(session)
