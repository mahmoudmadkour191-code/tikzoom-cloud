import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from handlers import bot_profile_cache


@pytest.mark.asyncio
async def test_get_bot_avatar_thumbnail_serializes_concurrent_cold_cache_calls(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(bot_profile_cache, "_bot_username", "downloader_bot")
    monkeypatch.setattr(bot_profile_cache, "_bot_id", 777)
    monkeypatch.setattr(bot_profile_cache, "_bot_avatar_path", None)
    monkeypatch.setattr(bot_profile_cache, "_bot_avatar_lock", asyncio.Lock())
    monkeypatch.setattr(
        bot_profile_cache, "_AUDIO_THUMB_PATH", tmp_path / "bot_audio_thumbnail.jpg"
    )
    photos = SimpleNamespace(
        total_count=1,
        photos=[
            [
                SimpleNamespace(
                    file_id="small", width=160, height=160, file_size=32_000
                )
            ]
        ],
    )

    async def fake_download(_file_id, destination):
        await asyncio.sleep(0)
        destination.write(b"image-bytes")

    def fake_normalize(source_path: Path, output_path: Path) -> bool:
        output_path.write_bytes(source_path.read_bytes())
        return True

    bot = SimpleNamespace(
        get_user_profile_photos=AsyncMock(return_value=photos),
        download=AsyncMock(side_effect=fake_download),
    )
    monkeypatch.setattr(
        bot_profile_cache, "_normalize_audio_thumbnail_file", fake_normalize
    )

    first, second = await asyncio.gather(
        bot_profile_cache.get_bot_avatar_thumbnail(bot),
        bot_profile_cache.get_bot_avatar_thumbnail(bot),
    )

    assert first is not None and second is not None
    assert first.path == second.path == str(tmp_path / "bot_audio_thumbnail.jpg")
    assert (tmp_path / "bot_audio_thumbnail.jpg").read_bytes() == b"image-bytes"
    # Only one cold-cache caller may download; the other must reuse the result.
    assert bot.download.await_count == 1
    assert bot.get_user_profile_photos.await_count == 1
