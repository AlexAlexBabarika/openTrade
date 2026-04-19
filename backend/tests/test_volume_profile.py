"""Unit tests for volume-profile math (path A)."""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from backend.market.models import OHLCVCandle
from backend.market.volume_profile import bin_from_candle_distribution


def _candle(o: float, h: float, lo: float, c: float, v: float) -> OHLCVCandle:
    return OHLCVCandle(
        symbol="TEST",
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        open=o,
        high=h,
        low=lo,
        close=c,
        volume=v,
    )


def test_empty_candles_returns_zero_result():
    res = bin_from_candle_distribution([], row_size=1.0, va_pct=0.7)
    assert res.bins == []
    assert res.poc == 0.0


def test_single_candle_volume_is_preserved():
    # H-L span = 4, row_size = 1 -> 4-5 bins; total volume conserved.
    c = _candle(o=10, h=14, lo=10, c=14, v=100)
    res = bin_from_candle_distribution([c], row_size=1.0, va_pct=0.7)
    total = sum(b.up_vol + b.down_vol for b in res.bins)
    assert math.isclose(total, 100.0, rel_tol=1e-9)


def test_up_candle_puts_all_volume_in_up_side():
    c = _candle(o=10, h=12, lo=10, c=12, v=50)
    res = bin_from_candle_distribution([c], row_size=1.0, va_pct=0.7)
    assert sum(b.up_vol for b in res.bins) == pytest.approx(50.0)
    assert sum(b.down_vol for b in res.bins) == 0.0


def test_down_candle_puts_all_volume_in_down_side():
    c = _candle(o=12, h=12, lo=10, c=10, v=40)
    res = bin_from_candle_distribution([c], row_size=1.0, va_pct=0.7)
    assert sum(b.down_vol for b in res.bins) == pytest.approx(40.0)
    assert sum(b.up_vol for b in res.bins) == 0.0


def test_poc_is_heaviest_bin():
    # Two candles overlap at 11; heaviest row should be at 11.
    c1 = _candle(o=10, h=12, lo=10, c=12, v=100)
    c2 = _candle(o=11, h=11, lo=11, c=11, v=1000)  # doji concentrates at 11
    res = bin_from_candle_distribution([c1, c2], row_size=1.0, va_pct=0.7)
    assert res.poc == pytest.approx(11.0)


def test_value_area_contains_poc():
    c = _candle(o=10, h=14, lo=10, c=14, v=100)
    res = bin_from_candle_distribution([c], row_size=1.0, va_pct=0.7)
    assert res.val <= res.poc <= res.vah


def test_row_size_must_be_positive():
    with pytest.raises(ValueError):
        bin_from_candle_distribution([], row_size=0.0, va_pct=0.7)


def test_va_pct_must_be_in_valid_range():
    with pytest.raises(ValueError):
        bin_from_candle_distribution([], row_size=1.0, va_pct=0.0)
    with pytest.raises(ValueError):
        bin_from_candle_distribution([], row_size=1.0, va_pct=1.5)


def test_doji_candle_dropped_into_single_bin():
    c = _candle(o=10, h=10, lo=10, c=10, v=25)
    res = bin_from_candle_distribution([c], row_size=1.0, va_pct=0.7)
    nonzero = [b for b in res.bins if b.up_vol + b.down_vol > 0]
    assert len(nonzero) == 1
    assert nonzero[0].up_vol == pytest.approx(25.0)
