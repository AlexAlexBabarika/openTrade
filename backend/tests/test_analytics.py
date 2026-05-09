"""Unit tests for backend.market.analytics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from backend.market.analytics import (
    _log_returns,
    compute_kurtosis,
    compute_skewness,
    compute_stdev,
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
