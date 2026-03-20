"""Upper bounds for OHLCV payloads (abuse / memory)."""

from __future__ import annotations

import os

# Truncate to the most recent N candles if a provider returns more.
MAX_OHLCV_CANDLES = max(100, int(os.environ.get("MAX_MARKET_OHLCV_CANDLES", "8000")))


def cap_candles[T](candles: list[T]) -> list[T]:
    """Keep at most ``MAX_OHLCV_CANDLES`` (most recent)."""
    if len(candles) <= MAX_OHLCV_CANDLES:
        return candles
    return candles[-MAX_OHLCV_CANDLES:]
