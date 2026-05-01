"""
Normalizes raw OHLCV data into the unified schema.
Maps various column names (Date, Open, o, etc.) to canonical: timestamp, open, high, low, close, volume.
Ensures UTC ISO8601 timestamps.
"""

import math
from datetime import date, datetime, timezone
from typing import Any

from backend.market.models import OHLCVCandle

COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "timestamp": ("date", "datetime", "time", "timestamp", "dt", "t"),
    "open": ("open", "o"),
    "high": ("high", "h"),
    "low": ("low", "l"),
    "close": ("close", "c"),
    "volume": ("volume", "v", "vol"),
}

_TIMESTAMP_FORMATS = (
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
)


def normalize_column_name(name: str) -> str | None:
    """Map a column name to its canonical key, or None if not OHLCV-related."""
    if not name or not isinstance(name, str):
        return None
    key = name.strip().lower()
    for canonical, aliases in COLUMN_ALIASES.items():
        if key in aliases:
            return canonical
    return None


def _is_null(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return True
    return False


def parse_timestamp(value: Any) -> datetime:
    """Parse an arbitrary value to a naive-UTC datetime."""
    if _is_null(value):
        raise ValueError(
            "Invalid timestamp: null/NaT. "
            "Check date format (e.g. YYYY-MM-DD) or ensure no empty cells in the date column."
        )
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    elif isinstance(value, (int, float)):
        if value > 1e12:
            value = value / 1000.0
        dt = datetime.fromtimestamp(value, tz=timezone.utc)
    elif isinstance(value, str):
        for fmt in _TIMESTAMP_FORMATS:
            try:
                dt = datetime.strptime(value.strip(), fmt)
                break
            except ValueError:
                continue
        else:
            from dateutil import parser as date_parser

            dt = date_parser.parse(value)
    else:
        raise ValueError(f"Cannot parse timestamp: {value!r}")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def to_float(value: Any) -> float:
    """Coerce to float. NaN/inf/empty become 0.0."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return 0.0
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).strip().replace(",", ""))


def normalize_row(row: dict[str, Any], symbol: str) -> OHLCVCandle:
    """Convert a single row (dict with arbitrary keys) to OHLCVCandle."""
    mapped: dict[str, Any] = {}
    for raw_key, raw_value in row.items():
        canon = normalize_column_name(raw_key)
        if canon is None:
            continue
        mapped[canon] = (
            parse_timestamp(raw_value) if canon == "timestamp" else to_float(raw_value)
        )

    if "timestamp" not in mapped:
        raise ValueError("Row missing timestamp")

    for key in ("open", "high", "low", "close", "volume"):
        mapped.setdefault(key, 0.0)

    if mapped["open"] <= 0 and mapped["close"] > 0:
        mapped["open"] = mapped["close"]
    elif mapped["close"] <= 0 and mapped["open"] > 0:
        mapped["close"] = mapped["open"]
    elif mapped["open"] <= 0 and mapped["close"] <= 0:
        mapped["open"] = mapped["close"] = 0.01

    mapped["symbol"] = symbol
    return OHLCVCandle(**mapped)


def normalize_rows(rows: list[dict[str, Any]], symbol: str) -> list[OHLCVCandle]:
    """Convert multiple rows to list of OHLCVCandles."""
    return [normalize_row(r, symbol) for r in rows]
