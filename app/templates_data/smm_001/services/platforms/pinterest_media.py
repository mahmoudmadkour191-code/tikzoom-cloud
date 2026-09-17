import hashlib
import json
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from services.logger import logger as logging
from services.platforms import CobaltMediaService, strip_url_query
from utils.cobalt_media import parse_cobalt_media_response
from utils.download_manager import (
    DownloadError as DownloadError,  # noqa: F401  (re-exported for handlers)
    DownloadMetrics,
)

logging = logging.bind(service="pinterest_media")

strip_pinterest_url = strip_url_query


def _derive_description(data: dict) -> str:
    output = data.get("output")
    if isinstance(output, dict):
        metadata = output.get("metadata")
        if isinstance(metadata, dict):
            title = metadata.get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()
    description = data.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()
    return ""


@dataclass
class PinterestMedia:
    url: str
    type: str
    thumb: Optional[str] = None


@dataclass
class PinterestPost:
    id: str
    description: str
    media_list: list[PinterestMedia]


def get_pinterest_preview_url(media: Optional[PinterestMedia]) -> Optional[str]:
    if not media:
        return None
    if media.type == "photo":
        return media.thumb or media.url
    return media.thumb or None


def parse_pinterest_post(data: dict) -> Optional[PinterestPost]:
    parsed = parse_cobalt_media_response(data, allow_multi_tunnel=True, source="pinterest")
    if not parsed:
        return None

    media_list = [
        PinterestMedia(url=media_url, type=media_type, thumb=thumb)
        for media_url, media_type, thumb in parsed.items
    ]

    return PinterestPost(
        id=hashlib.blake2s(
            json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"),
            digest_size=8,
        ).hexdigest(),
        description=_derive_description(data),
        media_list=media_list,
    )


class PinterestMediaService(CobaltMediaService):
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
            source="pinterest",
            cobalt_api_url=cobalt_api_url,
            cobalt_api_key=cobalt_api_key,
            fetch_cobalt_data_func=fetch_cobalt_data_func,
            retry_async_operation_func=retry_async_operation_func,
            logger=logging,
            download_error_message="Error downloading Pinterest media: url=%s error=%s",
        )

    async def fetch_post(self, url: str) -> Optional[PinterestPost]:
        payload = {
            "url": url,
            "downloadMode": "auto",
            "videoQuality": "1080",
            "alwaysProxy": True,
            "localProcessing": "disabled",
        }
        data = await self._fetch_cobalt_json(payload)
        if not data:
            return None
        return parse_pinterest_post(data)
