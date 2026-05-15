"""Unit tests for backend.market.analytics.distribution."""

from __future__ import annotations

import numpy as np
import pytest

from backend.market.analytics import (
    compute_kurtosis,
    compute_return_distribution,
    compute_skewness,
    compute_stdev,
    compute_variance,
)

from ._analytics_helpers import make_candles

# Closes whose log-returns are exactly [-2, -1, 0, 1, 2].
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
    assert compute_variance(make_candles(_SYMMETRIC_CLOSES)) == pytest.approx(2.5)


def test_stdev_is_sqrt_of_variance():
    assert compute_stdev(make_candles(_SYMMETRIC_CLOSES)) == pytest.approx(np.sqrt(2.5))


def test_skewness_of_symmetric_returns_is_zero():
    assert compute_skewness(make_candles(_SYMMETRIC_CLOSES)) == pytest.approx(
        0.0, abs=1e-12
    )


def test_excess_kurtosis_of_symmetric_returns():
    # population excess kurtosis of [-2,-1,0,1,2]:
    #   σ_pop² = 2, Σz⁴/n = 8.5/5 = 1.7, − 3 = −1.3
    assert compute_kurtosis(make_candles(_SYMMETRIC_CLOSES)) == pytest.approx(-1.3)


def test_moment_funcs_raise_on_too_few_returns():
    # Need ≥ 2 returns (i.e. ≥ 3 candles).
    too_few = make_candles([100.0, 110.0])
    for fn in (compute_variance, compute_stdev, compute_skewness, compute_kurtosis):
        with pytest.raises(ValueError):
            fn(too_few)


def test_return_distribution_histogram_counts():
    # Returns 0..10 (11 points) with 5 bins → counts [2, 2, 2, 2, 3]
    cum = np.concatenate(([0.0], np.cumsum(np.arange(11, dtype=float))))
    closes = [float(np.exp(c)) for c in cum]
    result = compute_return_distribution(make_candles(closes), bins=5)
    counts = [b.count for b in result.bins]
    assert counts == [2, 2, 2, 2, 3]
    assert len(result.bins) == 5
    assert result.bins[0].left == pytest.approx(0.0)
    assert result.bins[-1].right == pytest.approx(10.0)
