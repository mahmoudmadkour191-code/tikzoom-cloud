from pathlib import Path

import pytest

from services.platforms import CobaltMediaService, strip_url_query
from services.platforms.ytdlp_helpers import (
    mp3_extract_postprocessors,
    resolve_downloaded_path,
    run_ytdlp_download,
)
from tests.conftest import FakeYoutubeDL
from utils.cobalt_media import extract_cobalt_thumb, parse_cobalt_media_response
from utils.download_manager import (
    DownloadError,
    DownloadMetrics,
    DownloadRateLimitError,
)


def test_strip_url_query_drops_query_and_fragment():
    url = "https://example.com/p/abc/?utm_source=share#frag"
    assert strip_url_query(url) == "https://example.com/p/abc/"
    assert strip_url_query("not a url") == "not a url"


def test_extract_cobalt_thumb_prefers_known_keys():
    assert extract_cobalt_thumb({"thumb": "https://cdn.example.com/t.jpg"}) == "https://cdn.example.com/t.jpg"
    assert extract_cobalt_thumb({"cover": "https://cdn.example.com/c.jpg"}) == "https://cdn.example.com/c.jpg"
    assert extract_cobalt_thumb({"thumb": "", "other": "x"}) is None


def test_parse_cobalt_media_response_tunnel():
    payload = {"status": "tunnel", "url": "https://cdn.example.com/video.mp4"}

    parsed = parse_cobalt_media_response(payload)

    assert parsed is not None
    assert parsed.status == "tunnel"
    assert parsed.items == [("https://cdn.example.com/video.mp4", "video", None)]


def test_parse_cobalt_media_response_infers_status_from_payload_shape():
    parsed = parse_cobalt_media_response({"url": "https://cdn.example.com/photo.jpg"})

    assert parsed is not None
    assert parsed.status == "tunnel"
    assert parsed.items == [("https://cdn.example.com/photo.jpg", "photo", None)]


def test_parse_cobalt_media_response_picker():
    payload = {
        "status": "picker",
        "picker": [
            {"type": "photo", "url": "https://cdn.example.com/1.jpg", "thumb": "https://cdn.example.com/1t.jpg"},
            {"type": "video", "url": "https://cdn.example.com/2.mp4"},
            "junk",
            {"type": "photo"},
        ],
    }

    parsed = parse_cobalt_media_response(payload)

    assert parsed is not None
    assert parsed.items == [
        ("https://cdn.example.com/1.jpg", "photo", "https://cdn.example.com/1t.jpg"),
        ("https://cdn.example.com/2.mp4", "video", None),
    ]


def test_parse_cobalt_media_response_audio_only_uses_picker_audio():
    payload = {
        "status": "picker",
        "audio": "https://cdn.example.com/track.mp3",
        "picker": [{"type": "photo", "url": "https://cdn.example.com/1.jpg"}],
    }

    parsed = parse_cobalt_media_response(payload, audio_only=True)

    assert parsed is not None
    assert parsed.items == [("https://cdn.example.com/track.mp3", "audio", None)]


def test_parse_cobalt_media_response_local_processing_single_tunnel():
    payload = {
        "status": "local-processing",
        "type": "merge",
        "tunnel": ["https://cdn.example.com/tunnel-1"],
        "output": {"filename": "clip.mp4", "type": "video/mp4"},
    }

    parsed = parse_cobalt_media_response(payload)

    assert parsed is not None
    assert parsed.items == [("https://cdn.example.com/tunnel-1", "video", None)]


def test_parse_cobalt_media_response_rejects_multi_tunnel_by_default():
    payload = {
        "status": "local-processing",
        "type": "merge",
        "tunnel": ["https://cdn.example.com/t1", "https://cdn.example.com/t2"],
        "output": {"filename": "clip.mp4", "type": "video/mp4"},
    }

    assert parse_cobalt_media_response(payload) is None

    parsed = parse_cobalt_media_response(payload, allow_multi_tunnel=True)
    assert parsed is not None
    assert [item[0] for item in parsed.items] == [
        "https://cdn.example.com/t1",
        "https://cdn.example.com/t2",
    ]


def test_parse_cobalt_media_response_returns_none_on_error_and_unsupported():
    assert parse_cobalt_media_response({"status": "error", "error": {"code": "x"}}) is None
    assert parse_cobalt_media_response({"status": "mystery"}) is None
    assert parse_cobalt_media_response({"status": "tunnel"}) is None
    assert parse_cobalt_media_response({"status": "local-processing", "tunnel": []}) is None
    assert parse_cobalt_media_response("not a dict") is None


def _make_cobalt_service(tmp_path: Path, *, fetch_cobalt_data_func=None, download_headers=None) -> CobaltMediaService:
    async def passthrough_retry(operation, **_kwargs):
        return await operation()

    class _Logger:
        def __init__(self):
            self.calls = []

        def error(self, message, *args):
            self.calls.append((message, args))

    service = CobaltMediaService(
        str(tmp_path),
        source="testsource",
        retry_async_operation_func=passthrough_retry,
        logger=_Logger(),
        download_error_message="Error downloading test media: url=%s error=%s",
        cobalt_api_url="https://cobalt.test",
        cobalt_api_key="key",
        fetch_cobalt_data_func=fetch_cobalt_data_func,
        download_headers=download_headers,
    )
    return service


@pytest.mark.asyncio
async def test_cobalt_media_service_fetch_cobalt_json_passes_source_and_defaults(tmp_path):
    captured = {}

    async def fake_fetch(base_url, api_key, payload, **kwargs):
        captured["base_url"] = base_url
        captured["api_key"] = api_key
        captured["payload"] = payload
        captured["kwargs"] = kwargs
        return {"status": "tunnel"}

    service = _make_cobalt_service(tmp_path, fetch_cobalt_data_func=fake_fetch)

    data = await service._fetch_cobalt_json({"url": "https://example.com/post"})

    assert data == {"status": "tunnel"}
    assert captured["base_url"] == "https://cobalt.test"
    assert captured["api_key"] == "key"
    assert captured["kwargs"] == {"source": "testsource", "timeout": 15, "attempts": 3}


@pytest.mark.asyncio
async def test_cobalt_media_service_download_media_success_passes_headers(tmp_path, monkeypatch):
    headers = {"Referer": "https://example.com/"}
    service = _make_cobalt_service(tmp_path, download_headers=headers)
    captured = {}

    async def fake_download(url, filename, **kwargs):
        captured["url"] = url
        captured["filename"] = filename
        captured["kwargs"] = kwargs
        path = tmp_path / filename
        path.write_bytes(b"data")
        return DownloadMetrics(
            url=url,
            path=str(path),
            size=4,
            elapsed=0.01,
            used_multipart=False,
            resumed=False,
        )

    monkeypatch.setattr(service._downloader, "download", fake_download)

    metrics = await service.download_media("https://cdn.example.com/v.mp4", "v.mp4", user_id=7)

    assert metrics is not None
    assert captured["kwargs"]["headers"] == headers
    assert captured["kwargs"]["user_id"] == 7


@pytest.mark.asyncio
async def test_cobalt_media_service_download_media_logs_and_returns_none_on_download_error(tmp_path, monkeypatch):
    service = _make_cobalt_service(tmp_path)

    async def fake_download(*_args, **_kwargs):
        raise DownloadError("boom")

    monkeypatch.setattr(service._downloader, "download", fake_download)

    assert await service.download_media("https://cdn.example.com/v.mp4", "v.mp4") is None
    assert len(service._logger.calls) == 1
    message, args = service._logger.calls[0]
    assert message == "Error downloading test media: url=%s error=%s"
    assert args[0] == "https://cdn.example.com/v.mp4"
    assert isinstance(args[1], DownloadError)


@pytest.mark.asyncio
async def test_cobalt_media_service_download_media_reraises_backpressure(tmp_path, monkeypatch):
    service = _make_cobalt_service(tmp_path)

    async def fake_download(*_args, **_kwargs):
        raise DownloadRateLimitError(retry_after=5)

    monkeypatch.setattr(service._downloader, "download", fake_download)

    with pytest.raises(DownloadRateLimitError):
        await service.download_media("https://cdn.example.com/v.mp4", "v.mp4")


def test_resolve_downloaded_path_returns_exact_or_sibling_match(tmp_path):
    exact = tmp_path / "video.mp4"
    exact.write_bytes(b"x")
    assert resolve_downloaded_path(str(exact)) == str(exact)

    expected = tmp_path / "clip.mp4"
    actual = tmp_path / "clip.mkv"
    actual.write_bytes(b"x")
    assert resolve_downloaded_path(str(expected)) == str(actual)


def test_resolve_downloaded_path_raises_when_output_missing(tmp_path):
    with pytest.raises(DownloadError):
        resolve_downloaded_path(str(tmp_path / "missing.mp4"))


def test_run_ytdlp_download_uses_factory_and_downloads_url(tmp_path):
    created = {}

    def factory(options):
        ydl = FakeYoutubeDL(options, ext="mp4", payload=b"bytes")
        created["ydl"] = ydl
        return ydl

    output_path = tmp_path / "video.mp4"
    run_ytdlp_download(factory, "https://example.com/watch", {"outtmpl": str(output_path)})

    assert created["ydl"].urls == ["https://example.com/watch"]
    assert output_path.read_bytes() == b"bytes"


def test_mp3_extract_postprocessors_returns_fresh_copies():
    first = mp3_extract_postprocessors()
    second = mp3_extract_postprocessors()

    assert first == [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
    assert first is not second
    first[0]["preferredquality"] = "64"
    assert mp3_extract_postprocessors()[0]["preferredquality"] == "192"
