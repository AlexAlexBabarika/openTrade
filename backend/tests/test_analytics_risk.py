"""Unit tests for backend.market.analytics.risk."""

from __future__ import annotations

import numpy as np
import pytest

from backend.market.analytics import (
    ANNUAL_FACTOR,
    compute_max_drawdown,
    compute_sharpe,
    compute_sortino,
    compute_var,
)

from ._analytics_helpers import make_candles


def test_sharpe_steady_uptrend():
    # closes give returns [1, 2, 3]: mean=2, stdev(ddof=1)=1
    closes = [1.0, float(np.exp(1.0)), float(np.exp(3.0)), float(np.exp(6.0))]
    assert compute_sharpe(make_candles(closes), rf=0.0) == pytest.approx(
        2.0 * ANNUAL_FACTOR
    )


def test_sharpe_subtracts_per_period_rf():
    closes = [1.0, float(np.exp(1.0)), float(np.exp(3.0)), float(np.exp(6.0))]
    # (mean - rf) / stdev * factor = (2 - 0.5) / 1 * sqrt(252)
    assert compute_sharpe(make_candles(closes), rf=0.5) == pytest.approx(
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
    assert compute_sortino(make_candles(closes), rf=0.0) == pytest.approx(
        np.sqrt(126.0)
    )


def test_sortino_no_downside_raises():
    # returns [1, 2, 3]: no negatives → undefined
    closes = [1.0, float(np.exp(1.0)), float(np.exp(3.0)), float(np.exp(6.0))]
    with pytest.raises(ValueError, match="downside"):
        compute_sortino(make_candles(closes), rf=0.0)


def test_max_drawdown_classic_peak_trough():
    # closes [100, 110, 90, 95]: peak=110, trough=90 → MDD = -2/11
    result = compute_max_drawdown(make_candles([100.0, 110.0, 90.0, 95.0]))
    assert result.max_drawdown == pytest.approx(-2.0 / 11.0)
    assert len(result.series) == 4
    assert result.series[0].value == pytest.approx(0.0)
    assert result.series[2].value == pytest.approx(-2.0 / 11.0)


def test_var_historical_at_95_and_99():
    # 21 returns spaced -10..10: np.quantile linear gives -9 and -9.8
    n = 21
    cum = np.concatenate(([0.0], np.cumsum(np.linspace(-10.0, 10.0, n))))
    closes = [float(np.exp(c + 20.0)) for c in cum]  # +20 to keep > 0
    result = compute_var(make_candles(closes))
    assert result.var_95 == pytest.approx(-9.0)
    assert result.var_99 == pytest.approx(-9.8)
    assert result.n == n
