"""Risk metrics: Sharpe, Sortino, Maximum Drawdown, Value at Risk."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from backend.market.candle_utils import close_array
from backend.market.models import OHLCVCandle

from ._common import ANNUAL_FACTOR, require_returns


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


def compute_sharpe(candles: list[OHLCVCandle], rf: float = 0.0) -> float:
    """Annualised Sharpe ratio of log-returns.

    rf is per-period (matches the bar interval); subtracted from each return
    before computing mean / sample-stdev. Annualised by sqrt(252).
    """
    r = require_returns(candles, min_n=2)
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
    r = require_returns(candles, min_n=2)
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
    r = require_returns(candles, min_n=2)
    return VaRResult(
        var_95=float(np.quantile(r, 0.05)),
        var_99=float(np.quantile(r, 0.01)),
        n=int(r.size),
    )
