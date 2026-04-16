"""
Technical indicator calculations for OHLCV data.

All heavy computation is delegated to numpy for vectorised performance.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from backend.market.models import OHLCVCandle


def _close_array(candles: list[OHLCVCandle]) -> NDArray[np.float64]:
    return np.array([c.close for c in candles], dtype=np.float64)


def _rolling_mean(arr: NDArray[np.float64], period: int) -> NDArray[np.float64]:
    """Vectorised rolling mean via cumulative sum. Length = len(arr) - period + 1."""
    cs = np.cumsum(arr)
    cs[period:] -= cs[:-period]
    return cs[period - 1 :] / period


def calculate_sma(candles: list[OHLCVCandle], period: int) -> list[dict]:
    """Calculate Simple Moving Average from close prices.

    Returns list of {"timestamp": datetime, "value": float} for each point
    where enough data exists (i.e. starting from index period-1).
    """
    if period < 1:
        raise ValueError("Period must be at least 1")
    if len(candles) < period:
        return []

    closes = _close_array(candles)
    sma = _rolling_mean(closes, period)

    return [
        {"timestamp": candles[period - 1 + i].timestamp, "value": round(float(v), 6)}
        for i, v in enumerate(sma)
    ]


def calculate_bollinger_bands(
    candles: list[OHLCVCandle], period: int, num_std: float = 2.0
) -> list[dict]:
    """Calculate Bollinger Bands from close prices.

    Returns list of {"timestamp": datetime, "upper": float, "middle": float, "lower": float}
    for each point where enough data exists (starting from index period-1).
    """
    if period < 1:
        raise ValueError("Period must be at least 1")
    if num_std <= 0:
        raise ValueError("Standard deviation multiplier must be positive")
    if len(candles) < period:
        return []

    closes = _close_array(candles)
    sma = _rolling_mean(closes, period)

    sq_cs = np.cumsum(closes**2)
    sq_cs[period:] -= sq_cs[:-period]
    mean_sq = sq_cs[period - 1 :] / period
    std = np.sqrt(np.maximum(mean_sq - sma**2, 0.0))

    band = num_std * std
    upper = sma + band
    lower = sma - band

    return [
        {
            "timestamp": candles[period - 1 + i].timestamp,
            "upper": round(float(upper[i]), 6),
            "middle": round(float(sma[i]), 6),
            "lower": round(float(lower[i]), 6),
        }
        for i in range(len(sma))
    ]


def calculate_ema(candles: list[OHLCVCandle], period: int) -> list[dict]:
    """Calculate Exponential Moving Average from close prices.

    Uses SMA of the first `period` values as the initial EMA seed.
    Returns list of {"timestamp": datetime, "value": float}.
    """
    if period < 1:
        raise ValueError("Period must be at least 1")
    if len(candles) < period:
        return []

    closes = _close_array(candles)
    multiplier = 2.0 / (period + 1)

    ema = np.empty(len(closes) - period + 1, dtype=np.float64)
    ema[0] = closes[:period].mean()
    for i in range(1, len(ema)):
        ema[i] = (closes[period - 1 + i] - ema[i - 1]) * multiplier + ema[i - 1]

    return [
        {"timestamp": candles[period - 1 + i].timestamp, "value": round(float(v), 6)}
        for i, v in enumerate(ema)
    ]
