import polars as pl

from backend.datastore.schema import (
    ACTIONS_SCHEMA,
    BARS_SCHEMA,
    MEMBERSHIP_SCHEMA,
    empty_frame,
)


def test_empty_frame_matches_schema():
    f = empty_frame(BARS_SCHEMA)
    assert f.height == 0
    assert f.schema["timestamp"] == pl.Datetime("us", "UTC")
    assert set(f.columns) == set(BARS_SCHEMA)


def test_actions_and_membership_columns():
    assert set(ACTIONS_SCHEMA) == {"symbol", "ex_date", "kind", "value"}
    assert set(MEMBERSHIP_SCHEMA) == {"index", "symbol", "start", "end"}
