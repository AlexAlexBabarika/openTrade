"""Shared helpers and constants for the analytics suite.

Centralises the single definition of log-returns and the annualisation
factor so every domain module agrees on the inputs.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from backend.market.candle_utils import close_array
from backend.market.models import OHLCVCandle

# Daily-bar annualisation factor. Per the plan, fixed for v1; an interval-aware
# factor can be threaded through later if needed.
ANNUAL_FACTOR: float = float(np.sqrt(252.0))


def log_returns(candles: list[OHLCVCandle]) -> NDArray[np.float64]:
    """Log-returns of close prices: r_t = ln(c_t / c_{t-1}).

    Returns an array of length max(0, len(candles) - 1). All downstream
    metrics consume this single definition so log-return semantics are
    consistent across the analytics suite.
    """
    if len(candles) < 2:
        return np.empty(0, dtype=np.float64)
    closes = close_array(candles)
    return np.log(closes[1:] / closes[:-1])


def require_returns(candles: list[OHLCVCandle], min_n: int = 2) -> NDArray[np.float64]:
    """Compute log-returns and assert sufficient sample size."""
    r = log_returns(candles)
    if r.size < min_n:
        raise ValueError(
            f"Need at least {min_n + 1} candles ({min_n} returns); got {len(candles)}."
        )
    return r
