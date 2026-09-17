from __future__ import annotations

import json
import sys
from dataclasses import asdict

from services.logger import disable_log_sinks
from utils.download_manager import DownloadConfig, ResilientDownloader


def _read_payload() -> dict:
    raw = sys.stdin.buffer.read()
    if not raw:
        raise ValueError("No payload provided to download worker.")
    return json.loads(raw.decode("utf-8"))


def _build_config(raw: dict) -> DownloadConfig:
    config_data = dict(raw or {})
    stream_timeout = config_data.get("stream_timeout")
    if isinstance(stream_timeout, list):
        config_data["stream_timeout"] = tuple(stream_timeout)
    return DownloadConfig(**config_data)


def main() -> int:
    # The parent process raises this worker's entire stderr as the download
    # error message and shares its log files, so drop every log sink first:
    # stderr must carry only the final exception text, and a second process
    # must not write/rotate the parent's rotating log files.
    disable_log_sinks()
    try:
        payload = _read_payload()
        config = _build_config(payload.get("config") or {})
        downloader = ResilientDownloader(
            output_dir=payload["output_dir"],
            config=config,
            source=payload.get("source", "worker"),
        )
        metrics = downloader._download_sync(
            payload["url"],
            payload["filename"],
            payload.get("headers") or {},
            bool(payload.get("skip_if_exists", False)),
            None,
            int(payload.get("max_size_bytes") or 0) or None,
        )
        sys.stdout.write(json.dumps(asdict(metrics)))
        sys.stdout.flush()
        return 0
    except Exception as exc:
        sys.stderr.write(str(exc))
        sys.stderr.flush()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
