"""Build dashboard JSON snapshot from config watchlist (no Telegram bot).

Author: Shijie Zheng (Kerry Zheng) — https://github.com/Formyselfonly
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiohttp

from app.core.config import get_config_path, load_config
from app.providers.binance_rest import BinanceRestClient, to_binance_symbol
from app.providers.yfinance_poll import YahooFinancePoller, _fetch_live_price
from app.schemas.config import AppConfig, SymbolConfig
from app.schemas.market import DataSource, Kline
from app.services.engine import (
    calculate_indicators,
    supports_cluster,
    supports_touch,
)
from app.services.status_format import WATCH_PCT, build_metrics

logger = logging.getLogger(__name__)

_EQUITY_SOURCES = frozenset({DataSource.YFINANCE, DataSource.NASDAQ})

BINANCE_TICKER_URLS = {
    "spot": "https://api.binance.com/api/v3/ticker/price",
    "futures": "https://fapi.binance.com/fapi/v1/ticker/price",
}


@dataclass(frozen=True)
class IntervalSnapshot:
    interval: str
    label: str
    cluster_pct: float | None
    cluster_alert: bool
    cluster_near: bool
    ma200_pct: float | None
    ma200_side: str | None
    ma200_alert: bool
    ma200_near: bool
    ma200_value: float | None
    status: str


@dataclass(frozen=True)
class SymbolSnapshot:
    symbol: str
    source: str
    price: float | None
    intervals: list[IntervalSnapshot]
    data_feed: str | None = None
    error: str | None = None


def _to_yf_crypto_ticker(symbol: str) -> str:
    normalized = symbol.upper().replace("/", "")
    if normalized.endswith("USDT"):
        return f"{normalized[:-4]}-USD"
    return symbol


async def _fetch_yf_klines(
    yf_ticker: str,
    display_symbol: str,
    interval: str,
) -> list[Kline]:
    poller = YahooFinancePoller(
        symbol=display_symbol,
        yf_ticker=yf_ticker,
        interval=interval,
        poll_seconds=300,
        on_update=_noop_update,
    )
    return await asyncio.to_thread(poller.fetch_history, 250)


async def _fetch_binance_klines_with_fallback(
    rest: BinanceRestClient,
    symbol_cfg: SymbolConfig,
    interval: str,
) -> tuple[list[Kline], str]:
    """Try Binance futures/spot; fall back to Yahoo on geo-block (451)."""
    markets: list[str] = []
    for m in (symbol_cfg.market, "spot", "futures"):
        if m not in markets:
            markets.append(m)

    last_error: Exception | None = None
    for market in markets:
        try:
            klines = await rest.fetch_klines(
                symbol_cfg.symbol,
                interval,
                market=market,
            )
            if klines:
                return klines, f"binance_{market}"
        except aiohttp.ClientResponseError as exc:
            last_error = exc
            if exc.status in {451, 403, 418}:
                logger.warning(
                    "Binance %s geo-blocked for %s %s (%s), retrying",
                    market,
                    symbol_cfg.symbol,
                    interval,
                    exc.status,
                )
                continue
            raise

    yf_ticker = _to_yf_crypto_ticker(symbol_cfg.symbol)
    try:
        klines = await _fetch_yf_klines(
            yf_ticker,
            symbol_cfg.symbol,
            interval,
        )
        if klines:
            logger.info(
                "Using Yahoo fallback for %s %s (%s)",
                symbol_cfg.symbol,
                interval,
                yf_ticker,
            )
            return klines, "yahoo_crypto"
    except Exception as exc:
        last_error = exc
        logger.exception(
            "Yahoo crypto fallback failed for %s",
            symbol_cfg.symbol,
        )

    if last_error is not None:
        raise last_error
    msg = f"No klines for {symbol_cfg.symbol} {interval}"
    raise RuntimeError(msg)


def _cluster_flags(
    pct: float | None,
    threshold_pct: float,
) -> tuple[bool, bool]:
    if pct is None or pct != pct or pct == float("inf"):
        return False, False
    return pct <= threshold_pct, pct <= WATCH_PCT


def _touch_flags(pct: float | None, threshold_pct: float) -> tuple[bool, bool]:
    if pct is None or pct != pct or pct == float("inf"):
        return False, False
    return pct <= threshold_pct, pct <= WATCH_PCT


async def _fetch_binance_price(
    session: aiohttp.ClientSession,
    symbol: str,
    market: str,
) -> float | None:
    url = BINANCE_TICKER_URLS.get(market, BINANCE_TICKER_URLS["futures"])
    params = {"symbol": to_binance_symbol(symbol)}
    try:
        async with session.get(url, params=params) as resp:
            if resp.status in {451, 403, 418}:
                return None
            resp.raise_for_status()
            data = await resp.json()
            price = float(data["price"])
            return price if price > 0 else None
    except aiohttp.ClientResponseError:
        return None
    except Exception:
        logger.exception("Binance price fetch failed for %s", symbol)
        return None


async def _fetch_yf_price(yf_ticker: str, fallback: float) -> float | None:
    import yfinance as yf

    ticker = yf.Ticker(yf_ticker)
    return await asyncio.to_thread(_fetch_live_price, ticker, fallback)


async def _fetch_history(
    rest: BinanceRestClient,
    symbol_cfg: SymbolConfig,
    interval: str,
) -> tuple[list[Kline], str]:
    if symbol_cfg.source == DataSource.BINANCE:
        return await _fetch_binance_klines_with_fallback(
            rest,
            symbol_cfg,
            interval,
        )
    if symbol_cfg.source not in _EQUITY_SOURCES:
        msg = f"Unsupported source: {symbol_cfg.source}"
        raise ValueError(msg)
    klines = await _fetch_yf_klines(
        symbol_cfg.yf_ticker,
        symbol_cfg.symbol,
        interval,
    )
    return klines, "yahoo"


async def _noop_update(*_args: object) -> None:
    return None


async def _resolve_price(
    session: aiohttp.ClientSession,
    symbol_cfg: SymbolConfig,
    klines: list[Kline],
    data_feed: str,
) -> float | None:
    if symbol_cfg.source == DataSource.BINANCE:
        for market in (symbol_cfg.market, "spot", "futures"):
            live = await _fetch_binance_price(
                session,
                symbol_cfg.symbol,
                market,
            )
            if live is not None:
                return live
        if data_feed == "yahoo_crypto" and klines:
            yf_ticker = _to_yf_crypto_ticker(symbol_cfg.symbol)
            return await _fetch_yf_price(yf_ticker, klines[-1].close)
    if symbol_cfg.source in _EQUITY_SOURCES and klines:
        return await _fetch_yf_price(symbol_cfg.yf_ticker, klines[-1].close)
    if klines:
        return klines[-1].close
    return None


def _build_interval_snapshot(
    symbol: str,
    interval: str,
    klines: list[Kline],
    price: float,
    cluster_threshold_pct: float,
    touch_threshold_pct: float,
) -> IntervalSnapshot:
    label_map = {"4h": "4H", "1d": "1D", "1wk": "1W", "1w": "1W"}
    label = label_map.get(interval.lower(), interval.upper())

    if len(klines) < 200:
        return IntervalSnapshot(
            interval=interval,
            label=label,
            cluster_pct=None,
            cluster_alert=False,
            cluster_near=False,
            ma200_pct=None,
            ma200_side=None,
            ma200_alert=False,
            ma200_near=False,
            ma200_value=None,
            status="skipped",
        )

    indicators = calculate_indicators(klines)
    if indicators is None or price <= 0:
        return IntervalSnapshot(
            interval=interval,
            label=label,
            cluster_pct=None,
            cluster_alert=False,
            cluster_near=False,
            ma200_pct=None,
            ma200_side=None,
            ma200_alert=False,
            ma200_near=False,
            ma200_value=None,
            status="skipped",
        )

    metrics = build_metrics(symbol, interval, indicators, price)
    cluster_alert, cluster_near = _cluster_flags(
        metrics.cluster_pct,
        cluster_threshold_pct,
    )
    ma200_pct = metrics.touch_ma_pct if supports_touch(interval) else None
    ma200_side = metrics.touch_ma_side if supports_touch(interval) else None
    ma200_alert, ma200_near = _touch_flags(ma200_pct, touch_threshold_pct)

    return IntervalSnapshot(
        interval=interval,
        label=label,
        cluster_pct=(
            metrics.cluster_pct if supports_cluster(interval) else None
        ),
        cluster_alert=cluster_alert,
        cluster_near=cluster_near,
        ma200_pct=ma200_pct,
        ma200_side=ma200_side,
        ma200_alert=ma200_alert,
        ma200_near=ma200_near,
        ma200_value=indicators.ma_200 if supports_touch(interval) else None,
        status="ok",
    )


async def build_dashboard_payload(config: AppConfig) -> dict[str, Any]:
    cluster_threshold_pct = config.thresholds.cluster * 100
    touch_threshold_pct = config.thresholds.touch * 100
    refresh_seconds = config.polling.yfinance_interval_seconds

    symbols_out: list[dict[str, Any]] = []
    skipped: list[str] = []

    async with aiohttp.ClientSession() as session:
        rest = BinanceRestClient(session)
        for symbol_cfg in config.symbols:
            interval_snaps: list[IntervalSnapshot] = []
            symbol_price: float | None = None
            symbol_error: str | None = None
            data_feed: str | None = None

            for interval in symbol_cfg.intervals:
                label = f"{symbol_cfg.symbol} {interval}"
                try:
                    klines, feed = await _fetch_history(
                        rest,
                        symbol_cfg,
                        interval,
                    )
                    if data_feed is None:
                        data_feed = feed
                    if symbol_price is None:
                        symbol_price = await _resolve_price(
                            session,
                            symbol_cfg,
                            klines,
                            feed,
                        )
                    price = symbol_price or (
                        klines[-1].close if klines else 0.0
                    )
                    snap = _build_interval_snapshot(
                        symbol_cfg.symbol,
                        interval,
                        klines,
                        price,
                        cluster_threshold_pct,
                        touch_threshold_pct,
                    )
                    interval_snaps.append(snap)
                    if snap.status == "skipped":
                        skipped.append(label)
                except Exception as exc:
                    logger.exception("Dashboard export failed: %s", label)
                    skipped.append(label)
                    interval_snaps.append(
                        IntervalSnapshot(
                            interval=interval,
                            label=interval,
                            cluster_pct=None,
                            cluster_alert=False,
                            cluster_near=False,
                            ma200_pct=None,
                            ma200_side=None,
                            ma200_alert=False,
                            ma200_near=False,
                            ma200_value=None,
                            status="error",
                        ),
                    )
                    symbol_error = str(exc)[:120]

            symbols_out.append(
                {
                    **asdict(
                        SymbolSnapshot(
                            symbol=symbol_cfg.symbol,
                            source=str(symbol_cfg.source),
                            price=symbol_price,
                            intervals=interval_snaps,
                            data_feed=data_feed,
                            error=symbol_error,
                        ),
                    ),
                    "intervals": [asdict(iv) for iv in interval_snaps],
                },
            )

    return {
        "updated_at": datetime.now(tz=UTC).isoformat(),
        "refresh_seconds": refresh_seconds,
        "cluster_threshold_pct": cluster_threshold_pct,
        "touch_threshold_pct": touch_threshold_pct,
        "watch_pct": WATCH_PCT,
        "symbol_count": len(symbols_out),
        "skipped": skipped,
        "symbols": symbols_out,
    }


async def export_dashboard_json(
    output: Path,
    config_path: Path | None = None,
) -> dict[str, Any]:
    path = config_path or get_config_path()
    config = load_config(path)
    payload = await build_dashboard_payload(config)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(
        "Dashboard JSON written: %s (%s symbols)",
        output,
        payload["symbol_count"],
    )
    return payload
