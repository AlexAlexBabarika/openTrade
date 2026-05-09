"""Unit tests for backend.market.analytics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from backend.market.analytics import (
    ANNUAL_FACTOR,
    _log_returns,
    compute_kurtosis,
    compute_max_drawdown,
    compute_sharpe,
    compute_skewness,
    compute_sortino,
    compute_stdev,
    compute_var,
    compute_variance,
)
from backend.market.models import OHLCVCandle


def _candles(closes: list[float]) -> list[OHLCVCandle]:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        OHLCVCandle(
            symbol="TEST",
            timestamp=base + timedelta(days=i),
            open=c,
            high=c,
            low=c,
            close=c,
            volume=0.0,
        )
        for i, c in enumerate(closes)
    ]


def test_log_returns_known_values():
    # closes: [100, 110, 99, 108.9]
    # expected: ln(1.1), ln(0.9), ln(1.1)
    out = _log_returns(_candles([100.0, 110.0, 99.0, 108.9]))
    assert out.dtype == np.float64
    expected = np.array([np.log(1.1), np.log(0.9), np.log(1.1)])
    np.testing.assert_allclose(out, expected, rtol=1e-12)


def test_log_returns_too_few_candles_returns_empty():
    assert _log_returns(_candles([100.0])).size == 0
    assert _log_returns([]).size == 0


# Closes whose log-returns are exactly [-2, -1, 0, 1, 2].
# c_{i+1} = c_i * exp(r_i); start at exp(3) so all closes stay > 0.
_SYMMETRIC_CLOSES = [
    float(np.exp(3.0)),
    float(np.exp(1.0)),
    float(np.exp(0.0)),
    float(np.exp(0.0)),
    float(np.exp(1.0)),
    float(np.exp(3.0)),
]


def test_variance_sample_of_symmetric_returns():
    # returns=[-2,-1,0,1,2] → sample variance (ddof=1) = 10/4 = 2.5
    assert compute_variance(_candles(_SYMMETRIC_CLOSES)) == pytest.approx(2.5)


def test_stdev_is_sqrt_of_variance():
    candles = _candles(_SYMMETRIC_CLOSES)
    assert compute_stdev(candles) == pytest.approx(np.sqrt(2.5))


def test_skewness_of_symmetric_returns_is_zero():
    assert compute_skewness(_candles(_SYMMETRIC_CLOSES)) == pytest.approx(
        0.0, abs=1e-12
    )


def test_excess_kurtosis_of_symmetric_returns():
    # population excess kurtosis of [-2,-1,0,1,2]:
    #   σ_pop² = 2, Σz⁴/n = 8.5/5 = 1.7, − 3 = −1.3
    assert compute_kurtosis(_candles(_SYMMETRIC_CLOSES)) == pytest.approx(-1.3)


def test_sharpe_steady_uptrend():
    # closes give returns [1, 2, 3]: mean=2, stdev(ddof=1)=1
    closes = [1.0, float(np.exp(1.0)), float(np.exp(3.0)), float(np.exp(6.0))]
    assert compute_sharpe(_candles(closes), rf=0.0) == pytest.approx(
        2.0 * ANNUAL_FACTOR
    )


def test_sharpe_subtracts_per_period_rf():
    closes = [1.0, float(np.exp(1.0)), float(np.exp(3.0)), float(np.exp(6.0))]
    # (mean - rf) / stdev * factor = (2 - 0.5) / 1 * sqrt(252)
    assert compute_sharpe(_candles(closes), rf=0.5) == pytest.approx(
        1.5 * ANNUAL_FACTOR
    )


def test_sortino_known_value():
    # returns [-1, 2, -1, 2]: mean=0.5
    # downside dev (target=0) = sqrt((1+0+1+0)/4) = sqrt(0.5)
    # sortino = 0.5 / sqrt(0.5) * sqrt(252) = sqrt(126)
    closes = [
        1.0,
        float(np.exp(-1.0)),
        float(np.exp(1.0)),
        1.0,
        float(np.exp(2.0)),
    ]
    assert compute_sortino(_candles(closes), rf=0.0) == pytest.approx(np.sqrt(126.0))


def test_sortino_no_downside_raises():
    # returns [1, 2, 3]: no negatives → undefined
    closes = [1.0, float(np.exp(1.0)), float(np.exp(3.0)), float(np.exp(6.0))]
    with pytest.raises(ValueError, match="downside"):
        compute_sortino(_candles(closes), rf=0.0)


def test_max_drawdown_classic_peak_trough():
    # closes [100, 110, 90, 95]: peak=110, trough=90 → MDD = -2/11
    result = compute_max_drawdown(_candles([100.0, 110.0, 90.0, 95.0]))
    assert result.max_drawdown == pytest.approx(-2.0 / 11.0)
    # series length matches candles; first point has 0 drawdown.
    assert len(result.series) == 4
    assert result.series[0].value == pytest.approx(0.0)
    assert result.series[2].value == pytest.approx(-2.0 / 11.0)


def test_var_historical_at_95_and_99():
    # 21 returns spaced -10..10: np.quantile linear gives -9 and -9.8
    n = 21
    cum = np.concatenate(([0.0], np.cumsum(np.linspace(-10.0, 10.0, n))))
    closes = [float(np.exp(c + 20.0)) for c in cum]  # +20 to keep > 0
    candles = _candles(closes)
    result = compute_var(candles)
    assert result.var_95 == pytest.approx(-9.0)
    assert result.var_99 == pytest.approx(-9.8)
    assert result.n == n


def test_stat_funcs_raise_on_too_few_returns():
    # Need ≥ 2 returns (i.e. ≥ 3 candles) for sample variance/stdev.
    with pytest.raises(ValueError):
        compute_variance(_candles([100.0, 110.0]))
    with pytest.raises(ValueError):
        compute_stdev(_candles([100.0, 110.0]))
    # Skew/kurtosis need ≥ 2 returns and non-zero stdev.
    with pytest.raises(ValueError):
        compute_skewness(_candles([100.0, 110.0]))
    with pytest.raises(ValueError):
        compute_kurtosis(_candles([100.0, 110.0]))
