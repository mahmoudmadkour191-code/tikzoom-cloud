from typing import Optional

from aiogram import types

from handlers.deps import HandlerDependencies
from handlers.utils import (
    get_bot_url,
    safe_answer_inline_query,
    safe_edit_inline_media,
    safe_edit_inline_text,
)
from services.logger import logger
from services.inline.send_flow import handle_post_inline_query, send_inline_post_media
from services.platforms.pinterest_media import get_pinterest_preview_url as _get_pinterest_preview_url

logging = logger.bind(service="pinterest_inline")


async def handle_pinterest_inline_query(
    query: types.InlineQuery,
    *,
    deps: HandlerDependencies,
    pinterest_service,
    pinterest_url_regex: str,
    strip_pinterest_url,
    channel_id: Optional[int],
    service_key: str = "pinterest",
    service_name: str = "Pinterest",
    analytics_action: str = "inline_pinterest_video",
    get_preview_url=_get_pinterest_preview_url,
    allow_text_only: bool = False,
    get_bot_url_fn=get_bot_url,
    safe_answer_inline_query_fn=safe_answer_inline_query,
) -> None:
    await handle_post_inline_query(
        query,
        deps=deps,
        service=pinterest_service,
        url_regex=pinterest_url_regex,
        strip_url_fn=strip_pinterest_url,
        channel_id=channel_id,
        service_key=service_key,
        service_name=service_name,
        analytics_action=analytics_action,
        get_preview_url=get_preview_url,
        allow_text_only=allow_text_only,
        get_bot_url_fn=get_bot_url_fn,
        safe_answer_inline_query_fn=safe_answer_inline_query_fn,
        log=logging,
    )


async def send_inline_pinterest_media(
    *,
    token: str,
    inline_message_id: str,
    actor_name: str,
    actor_user_id: int,
    request_event_id: str,
    duplicate_handler: str,
    deps: HandlerDependencies,
    pinterest_service,
    channel_id: Optional[int],
    max_file_size: int,
    service_key: str = "pinterest",
    service_name: str = "Pinterest",
    get_bot_url_fn=get_bot_url,
    safe_edit_inline_media_fn=safe_edit_inline_media,
    safe_edit_inline_text_fn=safe_edit_inline_text,
) -> None:
    await send_inline_post_media(
        token=token,
        inline_message_id=inline_message_id,
        actor_name=actor_name,
        actor_user_id=actor_user_id,
        request_event_id=request_event_id,
        duplicate_handler=duplicate_handler,
        deps=deps,
        service=pinterest_service,
        channel_id=channel_id,
        max_file_size=max_file_size,
        service_key=service_key,
        service_name=service_name,
        get_bot_url_fn=get_bot_url_fn,
        safe_edit_inline_media_fn=safe_edit_inline_media_fn,
        safe_edit_inline_text_fn=safe_edit_inline_text_fn,
        log=logging,
    )
