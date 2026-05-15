"""Unit tests for backend.market.candle_utils."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from backend.market.candle_utils import (
    close_array,
    high_array,
    low_array,
    open_array,
    volume_array,
)
from backend.market.models import OHLCVCandle


def _candle(o: float, h: float, low: float, c: float, v: float) -> OHLCVCandle:
    return OHLCVCandle(
        symbol="TEST",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=o,
        high=h,
        low=low,
        close=c,
        volume=v,
    )


def test_field_arrays_extract_correct_fields():
    candles = [
        _candle(1.0, 1.5, 0.5, 1.2, 100.0),
        _candle(2.0, 2.5, 1.5, 2.2, 200.0),
        _candle(3.0, 3.5, 2.5, 3.2, 300.0),
    ]
    assert open_array(candles).tolist() == [1.0, 2.0, 3.0]
    assert high_array(candles).tolist() == [1.5, 2.5, 3.5]
    assert low_array(candles).tolist() == [0.5, 1.5, 2.5]
    assert close_array(candles).tolist() == [1.2, 2.2, 3.2]
    assert volume_array(candles).tolist() == [100.0, 200.0, 300.0]


def test_field_arrays_are_float64():
    candles = [_candle(1.0, 1.5, 0.5, 1.2, 100.0)]
    for fn in (open_array, high_array, low_array, close_array, volume_array):
        assert fn(candles).dtype == np.float64


def test_field_arrays_empty():
    for fn in (open_array, high_array, low_array, close_array, volume_array):
        arr = fn([])
        assert arr.dtype == np.float64
        assert arr.size == 0
