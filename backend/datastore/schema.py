"""Polars schemas + column contracts for the on-disk store."""

from __future__ import annotations

from typing import Any

import polars as pl

BARS_SCHEMA: dict[str, Any] = {
    "timestamp": pl.Datetime("us", "UTC"),
    "open": pl.Float64,
    "high": pl.Float64,
    "low": pl.Float64,
    "close": pl.Float64,
    "volume": pl.Float64,
}

ACTIONS_SCHEMA: dict[str, Any] = {
    "symbol": pl.Utf8,
    "ex_date": pl.Datetime("us", "UTC"),
    "kind": pl.Utf8,
    "value": pl.Float64,
}

MEMBERSHIP_SCHEMA: dict[str, Any] = {
    "index": pl.Utf8,
    "symbol": pl.Utf8,
    "start": pl.Datetime("us", "UTC"),
    "end": pl.Datetime("us", "UTC"),
}


def empty_frame(schema: dict[str, Any]) -> pl.DataFrame:
    """An empty frame with the exact dtypes of ``schema``."""
    return pl.DataFrame(schema=schema)
