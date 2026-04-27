"""REST gap-fill helper for the live streaming hub.

When a client subscribes (or re-subscribes after a disconnect), it can pass a
``since`` timestamp marking the last candle it has already drawn. The hub
fetches recent REST candles after that timestamp so the snapshot covers the
gap between the client's last-known bar and what the live socket will emit.

Kept deliberately small: one provider lookup, one REST call, one filter.
"""

from __future__ import annotations

from datetime import datetime, timezone

from starlette.concurrency import run_in_threadpool

from backend.market.data_sources.binance_loader import BinanceProvider
from backend.market.data_sources.marketdataprovider import MarketDataProvider
from backend.market.models import OHLCVCandle
from backend.models.market_data_models import MarketDataProviderEnum

# Interval → REST period sized to comfortably cover plausible disconnect
# windows. Picks a window large enough to backfill a long-ish reconnect but
# small enough not to stall the subscribe path.
_BACKFILL_PERIOD: dict[str, str] = {
    "1m": "1d",
    "3m": "1d",
    "5m": "5d",
    "15m": "5d",
    "30m": "5d",
    "1h": "1mo",
    "2h": "1mo",
    "4h": "3mo",
    "6h": "3mo",
    "8h": "3mo",
    "12h": "6mo",
    "1d": "1y",
    "1w": "5y",
    "1M": "max",
}


def _resolve_provider(name: MarketDataProviderEnum) -> MarketDataProvider:
    if name == MarketDataProviderEnum.binance:
        return BinanceProvider()
    raise NotImplementedError(f"Backfill not implemented for provider '{name}'")


async def backfill_candles(
    provider: MarketDataProviderEnum,
    symbol: str,
    interval: str,
    since: datetime,
) -> list[OHLCVCandle]:
    """Return REST OHLCV candles whose timestamp is strictly after ``since``."""
    period = _BACKFILL_PERIOD.get(interval, "1mo")
    p = _resolve_provider(provider)
    candles = await run_in_threadpool(p.get_ohlcv, symbol, period, interval)
    # Candle timestamps are naive UTC; client-supplied `since` is typically
    # aware. Normalize so the comparison doesn't crash.
    if since.tzinfo is not None:
        since = since.astimezone(timezone.utc).replace(tzinfo=None)
    return [c for c in candles if c.timestamp > since]
