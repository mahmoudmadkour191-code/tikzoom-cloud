"""Export dashboard status.json for GitHub Pages (no Telegram required).

Author: Shijie Zheng (Kerry Zheng) — https://github.com/Formyselfonly
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from app.services.dashboard_export import export_dashboard_json

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT = Path("docs/data/status.json")


def _ensure_telegram_env() -> None:
    """config.yaml expands ${TELEGRAM_*}; placeholders for export-only runs."""
    os.environ.setdefault("TELEGRAM_BOT_TOKEN", "export-placeholder")
    os.environ.setdefault("TELEGRAM_CHAT_ID", "0")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export MA dashboard JSON for static site",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help=f"Output path (default: {_DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        help="config.yaml path",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    _ensure_telegram_env()

    try:
        payload = asyncio.run(
            export_dashboard_json(args.output, args.config),
        )
    except Exception:
        logger.exception("Dashboard export failed")
        sys.exit(1)

    active = sum(
        1
        for sym in payload["symbols"]
        for iv in sym["intervals"]
        if iv["status"] == "ok"
    )
    print(f"OK → {args.output} ({active} active interval rows)")


if __name__ == "__main__":
    main()
