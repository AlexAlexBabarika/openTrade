"""Quantitative analytics suite, organised by domain.

Submodules:
- ``_common``      — log-returns, sample-size guard, ANNUAL_FACTOR.
- ``distribution`` — shape of the return distribution: variance, stdev,
                     skewness, kurtosis, empirical histogram.
- ``risk``         — risk metrics: Sharpe, Sortino, max drawdown, VaR.
- ``dependence``   — dependence and memory: correlation, volatility
                     clustering, Hurst exponent.

Public symbols are re-exported here so callers can ``from
backend.market.analytics import compute_sharpe`` without caring which
submodule owns it.
"""

from ._common import ANNUAL_FACTOR, log_returns, require_returns
from .dependence import (
    CorrelationResult,
    CorrelationRow,
    VolatilityClusteringResult,
    compute_correlation,
    compute_hurst,
    compute_volatility_clustering,
)
from .distribution import (
    DistributionBin,
    ReturnDistributionResult,
    compute_kurtosis,
    compute_return_distribution,
    compute_skewness,
    compute_stdev,
    compute_variance,
)
from .risk import (
    DrawdownPoint,
    MaxDrawdownResult,
    VaRResult,
    compute_max_drawdown,
    compute_sharpe,
    compute_sortino,
    compute_var,
)

__all__ = [
    "ANNUAL_FACTOR",
    "log_returns",
    "require_returns",
    # distribution
    "DistributionBin",
    "ReturnDistributionResult",
    "compute_variance",
    "compute_stdev",
    "compute_skewness",
    "compute_kurtosis",
    "compute_return_distribution",
    # risk
    "DrawdownPoint",
    "MaxDrawdownResult",
    "VaRResult",
    "compute_sharpe",
    "compute_sortino",
    "compute_max_drawdown",
    "compute_var",
    # dependence
    "CorrelationRow",
    "CorrelationResult",
    "VolatilityClusteringResult",
    "compute_correlation",
    "compute_volatility_clustering",
    "compute_hurst",
]
