"""HistoricalStore: the read API the engine/route uses.

Reads raw bars from Parquet, applies read-time back-adjustment (adjusted series
for signals + raw_* retained for fills), exposes corporate actions and resolves
survivorship-correct universes. Read-only: a missing symbol raises
``DataNotFound`` (the caller tells the user to ingest).
"""

from __future__ import annotations

from datetime import datetime

import polars as pl

from backend.backtesting.multi.universe import Universe
from backend.datastore.actions import read_actions
from backend.datastore.adjust import back_adjust
from backend.datastore.errors import DataNotFound
from backend.datastore.layout import StoreLayout
from backend.datastore.manifest import load_manifest
from backend.datastore.membership import resolve_universe


class HistoricalStore:
    def __init__(self, layout: StoreLayout, *, provider_name: str) -> None:
        self._layout = layout
        self._provider = provider_name

    def read_raw(self, symbol: str) -> pl.DataFrame:
        path = self._layout.bars(self._provider, symbol)
        if not path.exists():
            raise DataNotFound(f"no bars for {symbol!r}; run ingest")
        return pl.read_parquet(path)

    def get_actions(self, symbol: str) -> pl.DataFrame:
        return read_actions(self._layout, self._provider, symbol)

    def read_frames(
        self, symbols: list[str], *, adjusted: bool = True
    ) -> dict[str, pl.DataFrame]:
        out: dict[str, pl.DataFrame] = {}
        for symbol in symbols:
            raw = self.read_raw(symbol)
            out[symbol] = (
                back_adjust(raw, self.get_actions(symbol)) if adjusted else raw
            )
        return out

    def resolve_universe(self, index: str, start: datetime, end: datetime) -> Universe:
        return resolve_universe(self._layout, index, start, end)

    def head_version(self) -> str | None:
        return load_manifest(self._layout).get("head")
