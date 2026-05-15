"""Unit tests for backend.market.analytics.dependence."""

from __future__ import annotations

import numpy as np
import pytest

from backend.market.analytics import (
    compute_correlation,
    compute_hurst,
    compute_volatility_clustering,
)

from ._analytics_helpers import make_candles


def test_correlation_identical_returns_is_one():
    closes = [1.0, float(np.exp(1.0)), float(np.exp(0.0)), float(np.exp(2.0))]
    candles = make_candles(closes)
    result = compute_correlation(candles, {"COPY": candles})
    assert len(result.rows) == 1
    assert result.rows[0].benchmark == "COPY"
    assert result.rows[0].value == pytest.approx(1.0)


def test_correlation_anti_correlated_is_negative_one():
    closes_a = [1.0, float(np.exp(1.0)), float(np.exp(-1.0)), float(np.exp(2.0))]
    closes_b = [1.0, float(np.exp(-1.0)), float(np.exp(1.0)), float(np.exp(-2.0))]
    result = compute_correlation(
        make_candles(closes_a), {"INV": make_candles(closes_b)}
    )
    assert result.rows[0].value == pytest.approx(-1.0)


def test_correlation_aligns_on_min_length():
    # long returns [1, 2, 3], short returns [2, 3]; aligned tail [2, 3] → ρ=1.
    long_closes = [1.0, float(np.exp(1.0)), float(np.exp(3.0)), float(np.exp(6.0))]
    short_closes = [1.0, float(np.exp(2.0)), float(np.exp(5.0))]
    result = compute_correlation(
        make_candles(long_closes), {"SHORT": make_candles(short_closes)}
    )
    assert result.rows[0].value == pytest.approx(1.0)


def test_volatility_clustering_lag1_known_q():
    # returns [1, 2, 1, 2, 1] → r² = [1, 4, 1, 4, 1]
    # ρ_1 = -0.8, Q = 5*7*0.64/4 = 5.6
    closes = [
        1.0,
        float(np.exp(1.0)),
        float(np.exp(3.0)),
        float(np.exp(4.0)),
        float(np.exp(6.0)),
        float(np.exp(7.0)),
    ]
    result = compute_volatility_clustering(make_candles(closes), lag=1)
    assert result.lag == 1
    assert result.q == pytest.approx(5.6)
    assert 0.0 < result.p_value < 1.0


def test_hurst_random_walk_near_half():
    rng = np.random.default_rng(42)
    n = 500
    returns = rng.normal(0.0, 0.01, n)
    closes = [1.0]
    for r in returns:
        closes.append(closes[-1] * float(np.exp(r)))
    h = compute_hurst(make_candles(closes))
    assert 0.4 < h < 0.6


def test_hurst_requires_enough_data():
    with pytest.raises(ValueError, match="100"):
        compute_hurst(make_candles([1.0, 1.1, 1.2]))
