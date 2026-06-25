"""Ingest pipeline: fetch -> quality-check -> write Parquet -> stamp manifest.

The ``provider`` is duck-typed: it must expose ``name``,
``get_raw_ohlcv(symbol, period, interval)`` and ``get_corporate_actions(symbol)``.
Backtests never call this — it is the explicit population step.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone

import polars as pl

from backend.datastore.actions import actions_to_frame, write_actions
from backend.datastore.adjust import ADJUST_LOGIC_VERSION
from backend.datastore.layout import StoreLayout
from backend.datastore.manifest import (
    ManifestEntry,
    compute_version,
    file_checksum,
    write_entry,
)
from backend.datastore.membership import SEED_DIR, load_seed, write_membership
from backend.datastore.quality import check_bars
from backend.datastore.schema import BARS_SCHEMA


@dataclass
class IngestReport:
    data_version: str
    rows_written: dict[str, int] = field(default_factory=dict)
    quarantined: dict[str, int] = field(default_factory=dict)
    gap_warnings: list[str] = field(default_factory=list)


def _candles_to_frame(candles) -> pl.DataFrame:
    if not candles:
        return pl.DataFrame(schema=BARS_SCHEMA)
    return pl.DataFrame(
        {
            "timestamp": [c.timestamp for c in candles],
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
            "volume": [c.volume for c in candles],
        },
        schema=BARS_SCHEMA,
    )


def ingest_symbols(
    layout: StoreLayout,
    provider,
    symbols: list[str],
    *,
    period: str = "max",
    interval: str = "1d",
    indices: Sequence[str] = (),
) -> IngestReport:
    report = IngestReport(data_version="")
    checksums: dict[str, str] = {}
    ranges: dict[str, tuple[str, str]] = {}

    for symbol in sorted(set(symbols)):
        bars = _candles_to_frame(provider.get_raw_ohlcv(symbol, period, interval))
        actions = actions_to_frame(provider.get_corporate_actions(symbol))
        result = check_bars(bars, actions)

        bars_path = layout.bars(provider.name, symbol)
        layout.ensure_parent(bars_path)
        result.clean.write_parquet(bars_path)
        write_actions(layout, provider.name, symbol, actions)

        if result.quarantined.height:
            q_path = layout.quarantine(provider.name, symbol)
            layout.ensure_parent(q_path)
            result.quarantined.write_parquet(q_path)

        report.rows_written[symbol] = result.clean.height
        report.quarantined[symbol] = result.quarantined.height
        report.gap_warnings.extend(result.gap_warnings)

        rel_bars = bars_path.relative_to(layout.root).as_posix()
        checksums[rel_bars] = file_checksum(bars_path)
        if result.clean.height:
            times = result.clean.sort("timestamp")["timestamp"].to_list()
            ranges[symbol] = (times[0].date().isoformat(), times[-1].date().isoformat())

    for index in indices:
        seed = load_seed(SEED_DIR / f"{index.lower()}_membership.csv")
        write_membership(layout, index, seed)
        mpath = layout.membership(index)
        checksums[mpath.relative_to(layout.root).as_posix()] = file_checksum(mpath)

    version = compute_version(checksums, adjust_logic_version=ADJUST_LOGIC_VERSION)
    write_entry(
        layout,
        ManifestEntry(
            data_version=version,
            symbols=sorted(set(symbols)),
            ranges=ranges,
            checksums=checksums,
            adjust_logic_version=ADJUST_LOGIC_VERSION,
            ingested_at=datetime.now(timezone.utc).isoformat(),
        ),
    )
    report.data_version = version
    return report
