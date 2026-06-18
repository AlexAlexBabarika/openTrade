"""Index membership: seed CSV -> Parquet -> Universe.

The seed CSV carries historical constituent intervals (start inclusive, end
exclusive; blank = unbounded). ``resolve_universe`` returns the engine's
``Universe`` built from the membership intervals overlapping a date window, so a
backtest sees a survivorship-correct, point-in-time-correct symbol set.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import polars as pl

from backend.backtesting.multi.universe import Membership, Universe
from backend.datastore.errors import DataNotFound
from backend.datastore.layout import StoreLayout
from backend.datastore.schema import MEMBERSHIP_SCHEMA

SEED_DIR = Path(__file__).resolve().parent / "seeds"


def load_seed(csv_path: Path) -> pl.DataFrame:
    raw = pl.read_csv(csv_path)
    return raw.select(
        pl.col("index").cast(pl.Utf8),
        pl.col("symbol").cast(pl.Utf8),
        _parse_date("start"),
        _parse_date("end"),
    )


def _parse_date(col: str) -> pl.Expr:
    return (
        pl.col(col)
        .cast(pl.Utf8)
        .str.strptime(pl.Datetime("us"), "%Y-%m-%d", strict=False)
        .dt.replace_time_zone("UTC")
        .alias(col)
    )


def write_membership(layout: StoreLayout, index: str, frame: pl.DataFrame) -> None:
    rows = frame.filter(pl.col("index") == index).select(MEMBERSHIP_SCHEMA.keys())
    path = layout.membership(index)
    layout.ensure_parent(path)
    rows.write_parquet(path)


def read_membership(layout: StoreLayout, index: str) -> pl.DataFrame:
    path = layout.membership(index)
    if not path.exists():
        raise DataNotFound(f"no membership for index {index!r}; run ingest")
    return pl.read_parquet(path)


def resolve_universe(
    layout: StoreLayout, index: str, start: datetime, end: datetime
) -> Universe:
    frame = read_membership(layout, index)
    memberships: list[Membership] = []
    for r in frame.iter_rows(named=True):
        m_start, m_end = r["start"], r["end"]
        # keep intervals that overlap [start, end)
        if m_end is not None and m_end <= start:
            continue
        if m_start is not None and m_start >= end:
            continue
        memberships.append(Membership(symbol=r["symbol"], start=m_start, end=m_end))
    if not memberships:
        raise DataNotFound(f"index {index!r} has no members in window")
    return Universe(memberships)
