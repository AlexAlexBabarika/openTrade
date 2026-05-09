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
from scipy.stats import chi2

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


@dataclass(frozen=True)
class CorrelationRow:
    benchmark: str
    value: float


@dataclass(frozen=True)
class CorrelationResult:
    rows: list[CorrelationRow]


@dataclass(frozen=True)
class VolatilityClusteringResult:
    lag: int
    q: float
    p_value: float


@dataclass(frozen=True)
class DistributionBin:
    left: float
    right: float
    count: int


@dataclass(frozen=True)
class ReturnDistributionResult:
    bins: list[DistributionBin]


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


def compute_correlation(
    candles: list[OHLCVCandle],
    benchmarks: dict[str, list[OHLCVCandle]],
) -> CorrelationResult:
    """Pearson correlation of log-returns vs each benchmark.

    Series are right-aligned to the shortest length so the most recent
    overlapping window is used.
    """
    base = _require_returns(candles, min_n=2)
    rows: list[CorrelationRow] = []
    for name, bench_candles in benchmarks.items():
        bench = _log_returns(bench_candles)
        n = min(base.size, bench.size)
        if n < 2:
            raise ValueError(f"Benchmark '{name}' has too few returns ({n}).")
        a = base[-n:]
        b = bench[-n:]
        if np.std(a, ddof=0) == 0.0 or np.std(b, ddof=0) == 0.0:
            raise ValueError(f"Correlation undefined for '{name}': zero variance.")
        rho = float(np.corrcoef(a, b)[0, 1])
        rows.append(CorrelationRow(benchmark=name, value=rho))
    return CorrelationResult(rows=rows)


def _autocorrelation(x: NDArray[np.float64], lag: int) -> float:
    """Autocorrelation of x at the given lag (population estimator)."""
    centered = x - x.mean()
    denom = float(np.sum(centered**2))
    if denom == 0.0:
        return 0.0
    num = float(np.sum(centered[:-lag] * centered[lag:]))
    return num / denom


def compute_volatility_clustering(
    candles: list[OHLCVCandle], lag: int = 10
) -> VolatilityClusteringResult:
    """Ljung-Box Q-statistic on squared log-returns at the given lag.

    Q = n(n+2) Σ_{k=1..h} ρ_k² / (n - k); under H₀ (no autocorrelation up to
    lag h) Q ~ χ²(h). Significant Q ⇒ volatility clustering.
    """
    if lag < 1:
        raise ValueError("lag must be ≥ 1.")
    r = _require_returns(candles, min_n=lag + 1)
    s = r**2
    n = int(s.size)
    q = 0.0
    for k in range(1, lag + 1):
        rho_k = _autocorrelation(s, k)
        q += rho_k * rho_k / (n - k)
    q *= n * (n + 2)
    p_value = float(chi2.sf(q, df=lag))
    return VolatilityClusteringResult(lag=lag, q=float(q), p_value=p_value)


def compute_hurst(candles: list[OHLCVCandle]) -> float:
    """Hurst exponent via rescaled-range (R/S) over log-spaced windows.

    H ≈ 0.5 → random walk; > 0.5 → trending; < 0.5 → mean-reverting.
    Requires ≥ 100 returns.
    """
    r = _require_returns(candles, min_n=100)
    n = int(r.size)
    # Log-spaced window sizes from 10 to n/2.
    sizes = np.unique(np.logspace(np.log10(10), np.log10(n // 2), num=20).astype(int))
    sizes = sizes[sizes >= 10]
    if sizes.size < 4:
        raise ValueError("Not enough distinct window sizes; need more data.")

    rs_vals = []
    for w in sizes:
        # Average R/S across non-overlapping windows of size w.
        n_windows = n // w
        if n_windows < 1:
            continue
        rs_window = []
        for i in range(n_windows):
            seg = r[i * w : (i + 1) * w]
            mean = seg.mean()
            dev = np.cumsum(seg - mean)
            rng = float(dev.max() - dev.min())
            sd = float(np.std(seg, ddof=0))
            if sd == 0.0:
                continue
            rs_window.append(rng / sd)
        if rs_window:
            rs_vals.append((w, np.mean(rs_window)))

    if len(rs_vals) < 4:
        raise ValueError("Hurst regression needs ≥ 4 valid window sizes.")
    log_w = np.log([w for w, _ in rs_vals])
    log_rs = np.log([rs for _, rs in rs_vals])
    slope, _ = np.polyfit(log_w, log_rs, 1)
    return float(slope)


def compute_return_distribution(
    candles: list[OHLCVCandle], bins: int = 50
) -> ReturnDistributionResult:
    """Histogram of log-returns."""
    if bins < 1:
        raise ValueError("bins must be ≥ 1.")
    r = _require_returns(candles, min_n=2)
    counts, edges = np.histogram(r, bins=bins)
    out = [
        DistributionBin(
            left=float(edges[i]), right=float(edges[i + 1]), count=int(counts[i])
        )
        for i in range(bins)
    ]
    return ReturnDistributionResult(bins=out)
