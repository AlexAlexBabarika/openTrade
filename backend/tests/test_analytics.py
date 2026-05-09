"""Unit tests for backend.market.analytics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np

from backend.market.analytics import _log_returns
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
