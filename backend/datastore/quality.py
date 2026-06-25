"""Ingest-time quality checks.

Returns clean rows, quarantined rows (with a ``reason`` column), and gap
warnings. Failed bars are never silently dropped — they are surfaced for the
caller to report. Gaps cannot be quarantined (the rows are missing), so they
are returned as warnings.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from backend.datastore.schema import BARS_SCHEMA

_JUMP_THRESHOLD = 0.50


@dataclass
class QualityResult:
    clean: pl.DataFrame
    quarantined: pl.DataFrame  # BARS_SCHEMA + "reason"
    gap_warnings: list[str]


def check_bars(
    bars: pl.DataFrame, actions: pl.DataFrame, *, max_gap_days: int = 5
) -> QualityResult:
    bars = bars.sort("timestamp")
    reasons: list[str | None] = [None] * bars.height
    rows = list(bars.iter_rows(named=True))

    seen: set = set()
    action_dates = set(actions["ex_date"].to_list()) if actions.height else set()

    prev_close: float | None = None
    for i, r in enumerate(rows):
        reason: str | None = None
        ts = r["timestamp"]
        if ts in seen:
            reason = "duplicate_timestamp"
        elif min(r["open"], r["high"], r["low"], r["close"]) <= 0:
            reason = "non_positive_price"
        elif r["volume"] < 0:
            reason = "negative_volume"
        elif (
            r["high"] < r["low"]
            or r["high"] < r["open"]
            or r["high"] < r["close"]
            or r["low"] > r["open"]
            or r["low"] > r["close"]
        ):
            reason = "ohlc_inconsistent"
        elif (
            prev_close is not None
            and prev_close > 0
            and abs(r["close"] / prev_close - 1.0) > _JUMP_THRESHOLD
            and ts not in action_dates
        ):
            reason = "jump_without_action"

        seen.add(ts)
        reasons[i] = reason
        if reason is None:
            prev_close = r["close"]

    reason_s = pl.Series("reason", reasons, dtype=pl.Utf8)
    tagged = bars.with_columns(reason_s)
    clean = tagged.filter(pl.col("reason").is_null()).drop("reason")
    quarantined = tagged.filter(pl.col("reason").is_not_null())

    return QualityResult(
        clean=clean.select(BARS_SCHEMA.keys()),
        quarantined=quarantined,
        gap_warnings=_gap_warnings(clean, max_gap_days),
    )


def _gap_warnings(clean: pl.DataFrame, max_gap_days: int) -> list[str]:
    if clean.height < 2:
        return []
    ts = clean.sort("timestamp")["timestamp"].to_list()
    out: list[str] = []
    for a, b in zip(ts, ts[1:]):
        if (b - a).days > max_gap_days:
            out.append(
                f"gap {a.date().isoformat()} -> {b.date().isoformat()} ({(b - a).days}d)"
            )
    return out
