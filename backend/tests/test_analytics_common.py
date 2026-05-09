"""Unit tests for backend.market.analytics._common."""

from __future__ import annotations

import numpy as np

from backend.market.analytics import log_returns

from ._analytics_helpers import make_candles


def test_log_returns_known_values():
    # closes: [100, 110, 99, 108.9] → returns: ln(1.1), ln(0.9), ln(1.1)
    out = log_returns(make_candles([100.0, 110.0, 99.0, 108.9]))
    assert out.dtype == np.float64
    expected = np.array([np.log(1.1), np.log(0.9), np.log(1.1)])
    np.testing.assert_allclose(out, expected, rtol=1e-12)


def test_log_returns_too_few_candles_returns_empty():
    assert log_returns(make_candles([100.0])).size == 0
    assert log_returns([]).size == 0
