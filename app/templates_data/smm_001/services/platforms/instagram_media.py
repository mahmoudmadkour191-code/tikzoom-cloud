import hashlib
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from services.logger import logger as logging
from services.platforms import CobaltMediaService, strip_url_query
from utils.cobalt_media import parse_cobalt_media_response
from utils.download_manager import (
    DownloadError as DownloadError,  # noqa: F401  (re-exported for handlers)
    DownloadMetrics,
)

logging = logging.bind(service="instagram_media")

strip_instagram_url = strip_url_query


@dataclass
class InstagramMedia:
    url: str
    type: str
    thumb: Optional[str] = None


@dataclass
class InstagramVideo:
    id: str
    description: str
    author: str
    media_list: list[InstagramMedia]


def get_instagram_preview_url(media: Optional[InstagramMedia]) -> Optional[str]:
    if not media:
        return None
    if media.type == "photo":
        return media.url
    return media.thumb or None


def _extract_cobalt_description(data: dict, fallback_url: str) -> str:
    metadata = data.get("metadata") or data.get("output", {}).get("metadata") or {}
    if isinstance(metadata, dict):
        fields = ("description", "caption", "title", "text")
        for field_name in fields:
            val = metadata.get(field_name)
            if isinstance(val, str) and val.strip():
                return val.strip()
    if isinstance(data.get("filename"), str) and data["filename"].strip():
        return data["filename"].strip()
    return ""


def _extract_cobalt_author(data: dict, filename: str) -> str:
    metadata = data.get("metadata") or data.get("output", {}).get("metadata") or {}
    if isinstance(metadata, dict):
        fields = ("author", "uploader", "username", "creator", "channel")
        for field_name in fields:
            val = metadata.get(field_name)
            if isinstance(val, str) and val.strip():
                return val.strip()
    if filename:
        parts = filename.replace("\\", "/").split("/")
        for part in parts:
            part = part.strip()
            if part and not part.startswith(".") and "_" in part:
                maybe = part.split("_")[0]
                if maybe and len(maybe) >= 2:
                    return maybe
    return ""


def _extract_instagram_post_id(url: str) -> str:
    import re
    match = re.search(r"instagram\.com/(?:p|reels|reel)/([^/?#&]+)", url)
    if match:
        return match.group(1)
    return ""


class InstagramMediaService(CobaltMediaService):
    def __init__(
        self,
        output_dir: str,
        *,
        cobalt_api_url: str,
        cobalt_api_key: str,
        fetch_cobalt_data_func: Callable[..., Awaitable[dict | None]],
        retry_async_operation_func: Callable[..., Awaitable[DownloadMetrics | None]],
    ) -> None:
        super().__init__(
            output_dir,
            source="instagram",
            cobalt_api_url=cobalt_api_url,
            cobalt_api_key=cobalt_api_key,
            fetch_cobalt_data_func=fetch_cobalt_data_func,
            retry_async_operation_func=retry_async_operation_func,
            logger=logging,
            download_error_message="Error downloading Instagram media: url=%s error=%s",
        )

    async def fetch_data(self, url: str, audio_only: bool = False) -> Optional[InstagramVideo]:
        payload = {
            "url": url,
            "videoQuality": "720",
            "downloadMode": "audio" if audio_only else "auto",
            "alwaysProxy": True,
            "localProcessing": "disabled",
        }
        data = await self._fetch_cobalt_json(payload)
        if not data:
            return None

        parsed = parse_cobalt_media_response(data, audio_only=audio_only, source="instagram")
        if not parsed:
            return None

        media_list = [
            InstagramMedia(url=media_url, type=media_type, thumb=thumb)
            for media_url, media_type, thumb in parsed.items
        ]

        description = ""
        author = ""
        if parsed.status in {"tunnel", "redirect"}:
            filename = data.get("filename", "")
            if isinstance(filename, str):
                description = _extract_cobalt_description(data, fallback_url=url)
            author = _extract_cobalt_author(data, filename)
        elif parsed.status == "picker":
            description = _extract_cobalt_description(data, fallback_url=url)
            author = _extract_cobalt_author(data, "")
        elif parsed.status == "local-processing":
            output = data.get("output") or {}
            description = _extract_cobalt_description(data, fallback_url=url)
            author = _extract_cobalt_author(data, output.get("filename", "") if isinstance(output, dict) else "")

        post_id = _extract_instagram_post_id(url) or hashlib.blake2s(
            url.encode("utf-8"), digest_size=8
        ).hexdigest()
        return InstagramVideo(
            id=post_id,
            description=description,
            author=author or "instagram_user",
            media_list=media_list,
        )
