from typing import NamedTuple, Optional

from services.logger import logger as logging

logging = logging.bind(service="cobalt_media")


def classify_cobalt_media_type(
    media_url: str,
    *,
    audio_only: bool = False,
    declared_type: Optional[str] = None,
    filename: Optional[str] = None,
    mime_type: Optional[str] = None,
) -> str:
    if audio_only:
        return "audio"

    if declared_type:
        normalized_type = declared_type.lower()
        if normalized_type in {"video", "gif", "merge", "mute", "remux"}:
            return "video"
        if normalized_type == "photo":
            return "photo"
        if normalized_type == "audio":
            return "audio"

    if mime_type:
        normalized_mime = mime_type.lower()
        if normalized_mime.startswith("video/"):
            return "video"
        if normalized_mime.startswith("image/"):
            return "photo"
        if normalized_mime.startswith("audio/"):
            return "audio"

    probe = f"{media_url} {filename or ''}".lower()
    if any(ext in probe for ext in (".mp3", ".m4a", ".aac", ".ogg", ".wav", ".opus")):
        return "audio"
    if any(ext in probe for ext in (".jpg", ".jpeg", ".png", ".webp", ".avif")):
        return "photo"
    return "video"


def extract_cobalt_thumb(source: dict) -> Optional[str]:
    for key in ("thumb", "thumbnail", "poster", "preview", "cover"):
        value = source.get(key)
        if isinstance(value, str) and value:
            return value
    return None


class CobaltParsedMedia(NamedTuple):
    """Resolved response status plus (url, media_type, thumb) tuples."""

    status: str
    items: list[tuple[str, str, Optional[str]]]


def parse_cobalt_media_response(
    data: dict,
    *,
    audio_only: bool = False,
    allow_multi_tunnel: bool = False,
    source: str = "cobalt",
) -> Optional[CobaltParsedMedia]:
    """Parse the Cobalt status machine into (url, type, thumb) media tuples.

    Handles the tunnel/redirect, picker, local-processing and error statuses,
    inferring a missing status from the payload shape. Returns None when the
    response is an error, unsupported, or yields no media items.
    """
    if not isinstance(data, dict):
        return None

    status = data.get("status")
    if not status:
        if "url" in data:
            status = "tunnel"
        elif "picker" in data:
            status = "picker"

    items: list[tuple[str, str, Optional[str]]] = []

    if status in {"tunnel", "redirect"}:
        media_url = data.get("url")
        if isinstance(media_url, str) and media_url:
            items.append(
                (
                    media_url,
                    classify_cobalt_media_type(
                        media_url,
                        audio_only=audio_only,
                        filename=data.get("filename"),
                    ),
                    extract_cobalt_thumb(data),
                )
            )
    elif status == "picker":
        picker_audio_url = data.get("audio")
        if audio_only and isinstance(picker_audio_url, str) and picker_audio_url:
            items.append((picker_audio_url, "audio", None))
        else:
            for item in data.get("picker") or []:
                if not isinstance(item, dict):
                    continue
                media_url = item.get("url")
                if not isinstance(media_url, str) or not media_url:
                    continue
                items.append(
                    (
                        media_url,
                        classify_cobalt_media_type(
                            media_url,
                            audio_only=audio_only,
                            declared_type=item.get("type"),
                        ),
                        extract_cobalt_thumb(item),
                    )
                )
    elif status == "local-processing":
        tunnel_urls = data.get("tunnel") or []
        output = data.get("output") if isinstance(data.get("output"), dict) else {}
        if not isinstance(tunnel_urls, list) or not tunnel_urls:
            logging.error(
                "Cobalt local-processing response has no tunnels: source=%s payload=%s",
                source,
                data,
            )
            return None
        if not allow_multi_tunnel and not audio_only and len(tunnel_urls) > 1:
            logging.error(
                "Unsupported Cobalt local-processing payload: source=%s type=%s tunnel_count=%s",
                source,
                data.get("type"),
                len(tunnel_urls),
            )
            return None
        for media_url in tunnel_urls:
            if not isinstance(media_url, str) or not media_url:
                continue
            items.append(
                (
                    media_url,
                    classify_cobalt_media_type(
                        media_url,
                        audio_only=audio_only,
                        declared_type=data.get("type"),
                        filename=output.get("filename"),
                        mime_type=output.get("type"),
                    ),
                    extract_cobalt_thumb(data) or extract_cobalt_thumb(output),
                )
            )
    elif status == "error":
        error_obj = data.get("error") or {}
        logging.error(
            "Cobalt API returned error: source=%s code=%s context=%s",
            source,
            error_obj.get("code") if isinstance(error_obj, dict) else None,
            error_obj.get("context") if isinstance(error_obj, dict) else None,
        )
        return None
    else:
        logging.error(
            "Unsupported Cobalt response status: source=%s status=%s payload=%s",
            source,
            status,
            data,
        )
        return None

    if not items:
        logging.error(
            "Cobalt response has no media items: source=%s status=%s payload=%s",
            source,
            status,
            data,
        )
        return None

    return CobaltParsedMedia(status=status, items=items)
