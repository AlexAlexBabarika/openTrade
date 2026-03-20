"""
Load market period / interval options from repo ``shared/*.json``.

Single source of truth with the frontend (Vite imports the same files).
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

from dateutil.relativedelta import relativedelta

_SHARED_DIR = Path(__file__).resolve().parents[2] / "shared"


def _load_json(filename: str) -> dict[str, Any]:
    path = _SHARED_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Shared config missing: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _build_period_to_delta(
    periods_data: dict[str, Any],
) -> dict[str, timedelta | relativedelta]:
    out: dict[str, timedelta | relativedelta] = {}
    for opt in periods_data["options"]:
        value = opt["value"]
        spec = opt["delta"]
        kind = spec["kind"]
        n = int(spec["n"])
        if kind == "days":
            out[value] = timedelta(days=n)
        elif kind == "weeks":
            out[value] = timedelta(weeks=n)
        elif kind == "months":
            out[value] = relativedelta(months=n)
        elif kind == "years":
            out[value] = relativedelta(years=n)
        else:
            raise ValueError(f"Unknown period delta kind: {kind!r}")
    return out


_PERIODS = _load_json("market_periods.json")
_INTERVALS = _load_json("market_intervals.json")

PERIOD_TO_DELTA: dict[str, timedelta | relativedelta] = _build_period_to_delta(_PERIODS)
ALLOWED_PERIODS: frozenset[str] = frozenset(PERIOD_TO_DELTA)
ALLOWED_INTERVALS: frozenset[str] = frozenset(o["value"] for o in _INTERVALS["options"])
TWELVEDATA_INTERVAL_MAP: dict[str, str] = dict(_INTERVALS["twelvedata"])
TWELVEDATA_NATIVE_INTERVALS: frozenset[str] = frozenset(_INTERVALS["twelvedataNative"])


def resolve_twelvedata_interval(interval: str) -> str:
    """Map app interval (e.g. 1d) to Twelve Data API string (e.g. 1day)."""
    if interval in TWELVEDATA_NATIVE_INTERVALS:
        return interval
    mapped = TWELVEDATA_INTERVAL_MAP.get(interval)
    if mapped is not None:
        return mapped
    allowed = sorted(ALLOWED_INTERVALS | TWELVEDATA_NATIVE_INTERVALS)
    raise ValueError(
        f"Unsupported interval '{interval}' for Twelve Data. "
        f"Use one of: {', '.join(allowed)}"
    )


def validate_period(period: str) -> None:
    if period not in ALLOWED_PERIODS:
        raise ValueError(
            f"Invalid period '{period}'. Use one of: {', '.join(sorted(ALLOWED_PERIODS))}"
        )


def validate_interval(interval: str) -> None:
    if (
        interval not in ALLOWED_INTERVALS
        and interval not in TWELVEDATA_NATIVE_INTERVALS
    ):
        raise ValueError(
            f"Invalid interval '{interval}'. Use one of: "
            f"{', '.join(sorted(ALLOWED_INTERVALS | TWELVEDATA_NATIVE_INTERVALS))}"
        )
