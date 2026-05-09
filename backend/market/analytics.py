"""
Quantitative analytics calculations for OHLCV data.

All heavy computation is delegated to numpy for vectorised performance.
Mirrors the style of backend.market.indicators.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
from numpy.typing import NDArray

from backend.market.candle_utils import close_array
from backend.market.models import OHLCVCandle

# Daily-bar annualisation factor. Per the plan, fixed for v1; an interval-aware
# factor can be threaded through later if needed.
ANNUAL_FACTOR: float = float(np.sqrt(252.0))


@dataclass(frozen=True)
class DrawdownPoint:
    timestamp: datetime
    value: float


@dataclass(frozen=True)
class MaxDrawdownResult:
    max_drawdown: float
    series: list[DrawdownPoint]


@dataclass(frozen=True)
class VaRResult:
    var_95: float
    var_99: float
    n: int


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


def compute_sharpe(candles: list[OHLCVCandle], rf: float = 0.0) -> float:
    """Annualised Sharpe ratio of log-returns.

    rf is per-period (matches the bar interval); subtracted from each return
    before computing mean / sample-stdev. Annualised by sqrt(252).
    """
    r = _require_returns(candles, min_n=2)
    excess = r - rf
    sigma = float(np.std(excess, ddof=1))
    if sigma == 0.0:
        raise ValueError("Sharpe undefined: zero stdev in excess returns.")
    return float(excess.mean() / sigma * ANNUAL_FACTOR)


def compute_sortino(candles: list[OHLCVCandle], rf: float = 0.0) -> float:
    """Annualised Sortino ratio of log-returns.

    Downside deviation = sqrt(mean(min(r - rf, 0)^2)) over all returns
    (positives count as zero in the sum). Annualised by sqrt(252).
    """
    r = _require_returns(candles, min_n=2)
    excess = r - rf
    downside = np.minimum(excess, 0.0)
    dd = float(np.sqrt(np.mean(downside**2)))
    if dd == 0.0:
        raise ValueError("Sortino undefined: no downside returns.")
    return float(excess.mean() / dd * ANNUAL_FACTOR)


def compute_max_drawdown(candles: list[OHLCVCandle]) -> MaxDrawdownResult:
    """Maximum drawdown computed on the close-price wealth curve.

    Drawdown_i = (close_i - running_max_i) / running_max_i, ≤ 0.
    Returns the most-negative value plus the full timestamped series.
    """
    if len(candles) < 2:
        raise ValueError("Need at least 2 candles for drawdown.")
    closes = close_array(candles)
    peaks = np.maximum.accumulate(closes)
    dd = (closes - peaks) / peaks
    series = [
        DrawdownPoint(timestamp=candles[i].timestamp, value=float(dd[i]))
        for i in range(len(candles))
    ]
    return MaxDrawdownResult(max_drawdown=float(dd.min()), series=series)


def compute_var(candles: list[OHLCVCandle]) -> VaRResult:
    """Historical VaR at 95% and 99% from log-returns.

    Returns the signed return at each percentile (negative = loss).
    """
    r = _require_returns(candles, min_n=2)
    return VaRResult(
        var_95=float(np.quantile(r, 0.05)),
        var_99=float(np.quantile(r, 0.01)),
        n=int(r.size),
    )
