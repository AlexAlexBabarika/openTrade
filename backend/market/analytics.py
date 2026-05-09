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


def _require_returns(candles: list[OHLCVCandle], min_n: int = 2) -> NDArray[np.float64]:
    """Compute log-returns and assert sufficient sample size."""
    r = _log_returns(candles)
    if r.size < min_n:
        raise ValueError(
            f"Need at least {min_n + 1} candles ({min_n} returns); got {len(candles)}."
        )
    return r


def compute_variance(candles: list[OHLCVCandle]) -> float:
    """Sample variance (ddof=1) of log-returns."""
    r = _require_returns(candles, min_n=2)
    return float(np.var(r, ddof=1))


def compute_stdev(candles: list[OHLCVCandle]) -> float:
    """Sample standard deviation (ddof=1) of log-returns."""
    r = _require_returns(candles, min_n=2)
    return float(np.std(r, ddof=1))


def compute_skewness(candles: list[OHLCVCandle]) -> float:
    """Fisher-Pearson skewness of log-returns (population estimator)."""
    r = _require_returns(candles, min_n=2)
    sigma = float(np.std(r, ddof=0))
    if sigma == 0.0:
        raise ValueError("Skewness undefined: zero variance in returns.")
    z = (r - r.mean()) / sigma
    return float(np.mean(z**3))


def compute_kurtosis(candles: list[OHLCVCandle]) -> float:
    """Excess kurtosis of log-returns (population estimator, normal → 0)."""
    r = _require_returns(candles, min_n=2)
    sigma = float(np.std(r, ddof=0))
    if sigma == 0.0:
        raise ValueError("Kurtosis undefined: zero variance in returns.")
    z = (r - r.mean()) / sigma
    return float(np.mean(z**4) - 3.0)
