"""
Quantitative analytics calculations for OHLCV data.

All heavy computation is delegated to numpy for vectorised performance.
Mirrors the style of backend.market.indicators.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from backend.market.candle_utils import close_array
from backend.market.models import OHLCVCandle


def _log_returns(candles: list[OHLCVCandle]) -> NDArray[np.float64]:
    """Log-returns of close prices: r_t = ln(c_t / c_{t-1}).

    Returns an array of length max(0, len(candles) - 1). All downstream
    metrics consume this single definition so log-return semantics are
    consistent across the analytics suite.
    """
    if len(candles) < 2:
        return np.empty(0, dtype=np.float64)
    closes = close_array(candles)
    return np.log(closes[1:] / closes[:-1])
