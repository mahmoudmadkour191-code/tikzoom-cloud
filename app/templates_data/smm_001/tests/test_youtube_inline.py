from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import messages as bm
from handlers.deps import build_handler_dependencies
from handlers.utils import build_queue_busy_text, build_rate_limit_text
from handlers.youtube_inline import send_inline_youtube_music, send_inline_youtube_video
from services.inline.video_requests import (
    create_inline_video_request,
    get_inline_video_request,
)
from utils.download_manager import DownloadQueueBusyError, DownloadRateLimitError

SETTINGS = {
    "captions": "on",
    "delete_message": "off",
    "info_buttons": "on",
    "url_button": "on",
    "audio_button": "on",
}


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _make_deps(db=None):
    return build_handler_dependencies(
        bot=SimpleNamespace(send_video=AsyncMock(), send_audio=AsyncMock()),
        db=db
        or SimpleNamespace(
            get_file_id=AsyncMock(return_value=None),
            add_file=AsyncMock(),
        ),
        send_analytics=AsyncMock(),
    )


async def _run_send_inline_video(download_stream_fn):
    token = create_inline_video_request(
        "youtube",
        "https://www.youtube.com/watch?v=abc123",
        42,
        dict(SETTINGS),
    )
    edit_inline_text = AsyncMock(return_value=True)
    await send_inline_youtube_video(
        token=token,
        inline_message_id="inline-message-1",
        actor_name="Inline User",
        actor_user_id=42,
        request_event_id="evt-1",
        duplicate_handler="chosen",
        deps=_make_deps(),
        channel_id=-1001234,
        max_file_size=2_000_000_000,
        ytdlp_format_720="best",
        get_youtube_video_fn=lambda url: {
            "id": "abc123",
            "title": "Video",
            "webpage_url": url,
            "view_count": 1,
            "like_count": 1,
        },
        get_video_stream_fn=lambda _yt: {
            "url": "https://cdn.example.com/v.mp4",
            "filesize": 1024,
        },
        safe_int_fn=_safe_int,
        is_manifest_stream_fn=lambda _video: False,
        download_stream_fn=download_stream_fn,
        download_with_ytdlp_metrics_fn=AsyncMock(return_value=None),
        get_bot_url_fn=AsyncMock(return_value="https://t.me/maxloadbot"),
        safe_edit_inline_media_fn=AsyncMock(return_value=True),
        safe_edit_inline_text_fn=edit_inline_text,
    )
    return token, edit_inline_text


@pytest.mark.asyncio
async def test_send_inline_youtube_video_rate_limit_resets_request():
    token, edits = await _run_send_inline_video(
        AsyncMock(side_effect=DownloadRateLimitError(retry_after=30.0))
    )

    request = get_inline_video_request(token)
    assert request is not None
    assert request.state == "pending"
    last_call = edits.await_args_list[-1]
    assert last_call.args[2] == build_rate_limit_text(30.0)
    assert last_call.kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_send_inline_youtube_video_queue_busy_resets_request():
    token, edits = await _run_send_inline_video(
        AsyncMock(side_effect=DownloadQueueBusyError(position=3))
    )

    request = get_inline_video_request(token)
    assert request is not None
    assert request.state == "pending"
    last_call = edits.await_args_list[-1]
    assert last_call.args[2] == build_queue_busy_text(3)
    assert last_call.kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_send_inline_youtube_video_generic_error_resets_request():
    token, edits = await _run_send_inline_video(
        AsyncMock(side_effect=RuntimeError("boom"))
    )

    request = get_inline_video_request(token)
    assert request is not None
    assert request.state == "pending"
    last_call = edits.await_args_list[-1]
    assert last_call.args[2] == bm.something_went_wrong()
    assert last_call.kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_send_inline_youtube_music_generic_error_resets_request():
    token = create_inline_video_request(
        "youtube",
        "https://music.youtube.com/watch?v=abc123",
        42,
        dict(SETTINGS),
    )
    deps = _make_deps(
        db=SimpleNamespace(
            get_file_id=AsyncMock(side_effect=RuntimeError("boom")),
            add_file=AsyncMock(),
        )
    )
    edit_inline_text = AsyncMock(return_value=True)

    await send_inline_youtube_music(
        token=token,
        inline_message_id="inline-message-2",
        actor_name="Inline User",
        actor_user_id=42,
        request_event_id="evt-2",
        duplicate_handler="chosen",
        deps=deps,
        channel_id=-1001234,
        max_file_size=2_000_000_000,
        get_youtube_video_fn=lambda url: {
            "id": "abc123",
            "title": "Song",
            "webpage_url": url,
            "duration": 100,
        },
        download_mp3_with_ytdlp_metrics_fn=AsyncMock(return_value=None),
        retry_async_operation_fn=AsyncMock(return_value=None),
        get_bot_avatar_thumbnail_fn=AsyncMock(return_value=None),
        get_bot_url_fn=AsyncMock(return_value="https://t.me/maxloadbot"),
        safe_edit_inline_media_fn=AsyncMock(return_value=True),
        safe_edit_inline_text_fn=edit_inline_text,
    )

    request = get_inline_video_request(token)
    assert request is not None
    assert request.state == "pending"
    last_call = edit_inline_text.await_args_list[-1]
    assert last_call.args[2] == bm.something_went_wrong()
    assert last_call.kwargs["reply_markup"] is not None
