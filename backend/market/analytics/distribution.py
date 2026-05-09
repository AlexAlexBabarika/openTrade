"""Distribution-shape descriptors of log-returns.

The four classical moments (variance, stdev, skewness, kurtosis) plus the
empirical histogram — every quantity here describes the shape of the return
distribution itself, not its dependence structure or risk-adjusted scaling.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.market.models import OHLCVCandle

from ._common import require_returns


@dataclass(frozen=True)
class DistributionBin:
    left: float
    right: float
    count: int


@dataclass(frozen=True)
class ReturnDistributionResult:
    bins: list[DistributionBin]


def compute_variance(candles: list[OHLCVCandle]) -> float:
    """Sample variance (ddof=1) of log-returns."""
    r = require_returns(candles, min_n=2)
    return float(np.var(r, ddof=1))


def compute_stdev(candles: list[OHLCVCandle]) -> float:
    """Sample standard deviation (ddof=1) of log-returns."""
    r = require_returns(candles, min_n=2)
    return float(np.std(r, ddof=1))


def compute_skewness(candles: list[OHLCVCandle]) -> float:
    """Fisher-Pearson skewness of log-returns (population estimator)."""
    r = require_returns(candles, min_n=2)
    sigma = float(np.std(r, ddof=0))
    if sigma == 0.0:
        raise ValueError("Skewness undefined: zero variance in returns.")
    z = (r - r.mean()) / sigma
    return float(np.mean(z**3))


def compute_kurtosis(candles: list[OHLCVCandle]) -> float:
    """Excess kurtosis of log-returns (population estimator, normal → 0)."""
    r = require_returns(candles, min_n=2)
    sigma = float(np.std(r, ddof=0))
    if sigma == 0.0:
        raise ValueError("Kurtosis undefined: zero variance in returns.")
    z = (r - r.mean()) / sigma
    return float(np.mean(z**4) - 3.0)


def compute_return_distribution(
    candles: list[OHLCVCandle], bins: int = 50
) -> ReturnDistributionResult:
    """Empirical histogram of log-returns."""
    if bins < 1:
        raise ValueError("bins must be ≥ 1.")
    r = require_returns(candles, min_n=2)
    counts, edges = np.histogram(r, bins=bins)
    out = [
        DistributionBin(
            left=float(edges[i]), right=float(edges[i + 1]), count=int(counts[i])
        )
        for i in range(bins)
    ]
    return ReturnDistributionResult(bins=out)
