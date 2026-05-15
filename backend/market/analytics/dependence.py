"""Dependence and memory measures of log-returns.

- ``compute_correlation`` — cross-sectional Pearson vs benchmarks.
- ``compute_volatility_clustering`` — Ljung-Box autocorrelation of squared
  returns (serial dependence in volatility).
- ``compute_hurst`` — long-memory exponent via rescaled-range.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.stats import chi2

from backend.market.models import OHLCVCandle

from ._common import log_returns, require_returns


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


def compute_correlation(
    candles: list[OHLCVCandle],
    benchmarks: dict[str, list[OHLCVCandle]],
) -> CorrelationResult:
    """Pearson correlation of log-returns vs each benchmark.

    Series are right-aligned to the shortest length so the most recent
    overlapping window is used.
    """
    base = require_returns(candles, min_n=2)
    rows: list[CorrelationRow] = []
    for name, bench_candles in benchmarks.items():
        bench = log_returns(bench_candles)
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
    r = require_returns(candles, min_n=lag + 1)
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
    r = require_returns(candles, min_n=100)
    n = int(r.size)
    sizes = np.unique(np.logspace(np.log10(10), np.log10(n // 2), num=20).astype(int))
    sizes = sizes[sizes >= 10]
    if sizes.size < 4:
        raise ValueError("Not enough distinct window sizes; need more data.")

    rs_vals = []
    for w in sizes:
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
