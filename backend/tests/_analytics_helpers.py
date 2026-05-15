"""Shared test helpers for the analytics suite."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.market.models import OHLCVCandle


def make_candles(closes: list[float]) -> list[OHLCVCandle]:
    """Build OHLCV candles with the given closes; OHLV all == close."""
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        OHLCVCandle(
            symbol="TEST",
            timestamp=base + timedelta(days=i),
            open=c,
            high=c,
            low=c,
            close=c,
            volume=0.0,
        )
        for i, c in enumerate(closes)
    ]
