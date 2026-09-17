import asyncio
import re

import aiohttp

from services.logger import logger as logging
from services.platforms.tiktok_common import (
    SHORT_HOSTS,
    URL_EXPAND_CACHE_MAXSIZE,
    URL_EXPAND_TIMEOUT,
    strip_tiktok_tracking,
)

logging = logging.bind(service="tiktok_media")


class TikTokUrlResolverMixin:
    def _get_expanded_tiktok_url_inflight(self) -> dict[str, "asyncio.Future[str]"]:
        inflight = getattr(self, "_expanded_tiktok_url_inflight", None)
        if inflight is None:
            inflight = {}
            self._expanded_tiktok_url_inflight = inflight
        return inflight

    async def _expand_tiktok_url_cached_async(self, url: str) -> str:
        cached = self._expanded_tiktok_url_cache.get(url)
        if cached is not None:
            self._expanded_tiktok_url_cache.move_to_end(url)
            return cached

        # Hold the lock only to check the cache and claim a per-URL in-flight
        # future; the HEAD request itself runs outside the lock so different
        # URLs expand concurrently while duplicate URLs coalesce.
        inflight = self._get_expanded_tiktok_url_inflight()
        async with self._expanded_tiktok_url_lock:
            cached = self._expanded_tiktok_url_cache.get(url)
            if cached is not None:
                self._expanded_tiktok_url_cache.move_to_end(url)
                return cached
            existing = inflight.get(url)
            if existing is not None and not existing.done():
                future = existing
                is_leader = False
            else:
                future = asyncio.get_running_loop().create_future()
                inflight[url] = future
                is_leader = True

        if not is_leader:
            return await asyncio.shield(future)

        try:
            session = await self._get_http_session()
            headers = {"User-Agent": self._get_user_agent()}
            async with session.head(
                url,
                allow_redirects=True,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=URL_EXPAND_TIMEOUT),
            ) as response:
                expanded = str(response.url) or url

            async with self._expanded_tiktok_url_lock:
                self._expanded_tiktok_url_cache[url] = expanded
                self._expanded_tiktok_url_cache.move_to_end(url)
                if len(self._expanded_tiktok_url_cache) > URL_EXPAND_CACHE_MAXSIZE:
                    self._expanded_tiktok_url_cache.popitem(last=False)
            if not future.done():
                future.set_result(expanded)
            return expanded
        except Exception as exc:
            if not future.done():
                future.set_exception(exc)
                # Mark the exception as retrieved so an abandoned future does
                # not emit "exception was never retrieved" warnings.
                future.exception()
            raise
        finally:
            if inflight.get(url) is future:
                inflight.pop(url, None)
            if not future.done():
                future.cancel()

    async def process_tiktok_url_async(self, text: str) -> str:
        def extract_tiktok_url(input_text: str) -> str:
            match = re.search(r"(https?://(?:www\.|vm\.|vt\.|vn\.)?tiktok\.com/\S+)", input_text)
            return match.group(0) if match else input_text

        url = strip_tiktok_tracking(extract_tiktok_url(text))
        logging.debug("TikTok URL extracted: raw=%s extracted=%s", text, url)

        try:
            parsed = aiohttp.helpers.URL(url)
            host = parsed.host or ""
            if host.lower() in SHORT_HOSTS:
                expanded = await self._expand_tiktok_url_cached_async(url)
                logging.debug("TikTok short URL expanded: raw=%s expanded=%s", url, expanded)
                return strip_tiktok_tracking(expanded)
            return strip_tiktok_tracking(url)
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logging.error("Error expanding TikTok URL: url=%s error=%s", url, exc)
            return strip_tiktok_tracking(url)
