from datetime import datetime, timezone

import polars as pl

from backend.datastore.quality import check_bars
from backend.datastore.schema import ACTIONS_SCHEMA, BARS_SCHEMA, empty_frame


def _utc(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc)


def _bar(t, o=10.0, h=11.0, low=9.0, c=10.5, v=100.0):
    return {"timestamp": t, "open": o, "high": h, "low": low, "close": c, "volume": v}


def _bars(rows):
    return pl.DataFrame(rows, schema=BARS_SCHEMA)


def test_clean_bars_pass():
    res = check_bars(
        _bars([_bar(_utc(2021, 1, 4)), _bar(_utc(2021, 1, 5))]),
        empty_frame(ACTIONS_SCHEMA),
    )
    assert res.clean.height == 2
    assert res.quarantined.height == 0


def test_duplicate_timestamp_quarantined():
    res = check_bars(
        _bars([_bar(_utc(2021, 1, 4)), _bar(_utc(2021, 1, 4))]),
        empty_frame(ACTIONS_SCHEMA),
    )
    assert res.quarantined.height == 1
    assert "duplicate_timestamp" in set(res.quarantined["reason"].to_list())


def test_negative_and_ohlc_inconsistent_quarantined():
    rows = [
        _bar(_utc(2021, 1, 4), v=-1.0),  # negative volume
        _bar(_utc(2021, 1, 5), o=10, h=8, low=9, c=10),  # high < low
        _bar(_utc(2021, 1, 6), o=-5, h=11, low=9, c=10),  # negative price
    ]
    res = check_bars(_bars(rows), empty_frame(ACTIONS_SCHEMA))
    reasons = set(res.quarantined["reason"].to_list())
    assert {"negative_volume", "ohlc_inconsistent", "non_positive_price"} <= reasons
    assert res.clean.height == 0


def test_price_jump_without_action_quarantined():
    rows = [
        _bar(_utc(2021, 1, 4), o=100, h=101, low=99, c=100.0),
        _bar(_utc(2021, 1, 5), o=20, h=21, low=19, c=20.0),
    ]
    res = check_bars(_bars(rows), empty_frame(ACTIONS_SCHEMA))
    assert "jump_without_action" in set(res.quarantined["reason"].to_list())


def test_price_jump_with_matching_action_is_clean():
    rows = [
        _bar(_utc(2021, 1, 4), o=100, h=101, low=99, c=100.0),
        _bar(_utc(2021, 1, 5), o=20, h=21, low=19, c=20.0),
    ]
    actions = pl.DataFrame(
        [{"symbol": "X", "ex_date": _utc(2021, 1, 5), "kind": "split", "value": 5.0}],
        schema=ACTIONS_SCHEMA,
    )
    res = check_bars(_bars(rows), actions)
    assert res.quarantined.height == 0


def test_gap_warning_emitted():
    rows = [_bar(_utc(2021, 1, 4)), _bar(_utc(2021, 2, 1))]  # ~28-day gap
    res = check_bars(_bars(rows), empty_frame(ACTIONS_SCHEMA), max_gap_days=5)
    assert res.gap_warnings
    assert "2021-01-04" in res.gap_warnings[0]
