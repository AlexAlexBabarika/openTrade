from datetime import datetime, timezone

import polars as pl

from backend.datastore.adjust import ADJUST_LOGIC_VERSION, back_adjust
from backend.datastore.schema import ACTIONS_SCHEMA, BARS_SCHEMA, empty_frame


def _utc(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc)


def _bars(rows):
    return pl.DataFrame(rows, schema=BARS_SCHEMA)


def test_split_makes_series_continuous_no_phantom_drop():
    # AAPL-like 4-for-1 split on 2020-08-31: raw close 500 -> 125.
    bars = _bars(
        [
            {
                "timestamp": _utc(2020, 8, 28),
                "open": 500.0,
                "high": 505.0,
                "low": 498.0,
                "close": 500.0,
                "volume": 100.0,
            },
            {
                "timestamp": _utc(2020, 8, 31),
                "open": 125.0,
                "high": 126.0,
                "low": 124.0,
                "close": 125.0,
                "volume": 400.0,
            },
        ]
    )
    actions = pl.DataFrame(
        [
            {
                "symbol": "AAPL",
                "ex_date": _utc(2020, 8, 31),
                "kind": "split",
                "value": 4.0,
            }
        ],
        schema=ACTIONS_SCHEMA,
    )
    out = back_adjust(bars, actions)

    # Raw series has a ~75% drop; adjusted series is continuous.
    raw = out["raw_close"].to_list()
    adj = out["close"].to_list()
    assert raw == [500.0, 125.0]
    assert adj[0] == 125.0 and adj[1] == 125.0  # pre-split divided by ratio
    # Day-over-day adjusted move is ~0, not -75%.
    assert abs(adj[1] / adj[0] - 1.0) < 1e-9
    # Volume back-adjusted up by the ratio on the pre-split bar.
    assert out["volume"].to_list() == [400.0, 400.0]


def test_dividend_back_adjusts_prior_bars():
    # $10 dividend ex 2021-01-04, prior close 100 -> step factor 0.9.
    bars = _bars(
        [
            {
                "timestamp": _utc(2020, 12, 31),
                "open": 100.0,
                "high": 100.0,
                "low": 100.0,
                "close": 100.0,
                "volume": 10.0,
            },
            {
                "timestamp": _utc(2021, 1, 4),
                "open": 90.0,
                "high": 90.0,
                "low": 90.0,
                "close": 90.0,
                "volume": 10.0,
            },
        ]
    )
    actions = pl.DataFrame(
        [
            {
                "symbol": "X",
                "ex_date": _utc(2021, 1, 4),
                "kind": "dividend",
                "value": 10.0,
            }
        ],
        schema=ACTIONS_SCHEMA,
    )
    out = back_adjust(bars, actions)
    assert out["close"].to_list() == [90.0, 90.0]  # prior bar * 0.9
    assert out["raw_close"].to_list() == [100.0, 90.0]


def test_no_actions_is_identity():
    bars = _bars(
        [
            {
                "timestamp": _utc(2021, 1, 4),
                "open": 1.0,
                "high": 2.0,
                "low": 0.5,
                "close": 1.5,
                "volume": 3.0,
            }
        ]
    )
    out = back_adjust(bars, empty_frame(ACTIONS_SCHEMA))
    assert out["close"].to_list() == [1.5]
    assert out["raw_close"].to_list() == [1.5]


def test_logic_version_is_a_string():
    assert isinstance(ADJUST_LOGIC_VERSION, str) and ADJUST_LOGIC_VERSION
