"""Shared NumPy helpers for extracting fields from OHLCV candle lists."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from backend.market.models import OHLCVCandle


def open_array(candles: list[OHLCVCandle]) -> NDArray[np.float64]:
    """Extract open prices as a contiguous float64 array."""
    return np.array([c.open for c in candles], dtype=np.float64)


def high_array(candles: list[OHLCVCandle]) -> NDArray[np.float64]:
    """Extract high prices as a contiguous float64 array."""
    return np.array([c.high for c in candles], dtype=np.float64)


def low_array(candles: list[OHLCVCandle]) -> NDArray[np.float64]:
    """Extract low prices as a contiguous float64 array."""
    return np.array([c.low for c in candles], dtype=np.float64)


def close_array(candles: list[OHLCVCandle]) -> NDArray[np.float64]:
    """Extract close prices as a contiguous float64 array."""
    return np.array([c.close for c in candles], dtype=np.float64)


def volume_array(candles: list[OHLCVCandle]) -> NDArray[np.float64]:
    """Extract volumes as a contiguous float64 array."""
    return np.array([c.volume for c in candles], dtype=np.float64)
