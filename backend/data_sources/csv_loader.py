"""
CSV loader using polars. Auto-detects column names and normalizes to unified schema.
"""

from pathlib import Path
from typing import Any

import polars as pl
from backend.models import OHLCVCandle
from backend.normalizer import normalize_rows


def _detect_time_column(df: pl.DataFrame) -> str | None:
    """Return first column that normalizes to 'timestamp'."""
    from backend.normalizer import _normalize_column_name

    for c in df.columns:
        if _normalize_column_name(c) == "timestamp":
            return c
    return None


def load_csv(
    path: str | Path,
    symbol: str,
) -> list[OHLCVCandle]:
    """
    Load OHLCV from CSV using polars.
    Column names are auto-detected (Date, Open, o, etc.) and normalized.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    df = pl.read_csv(path, try_parse_dates=True)
    if df.is_empty():
        return []
    time_col = _detect_time_column(df)
    if time_col is None:
        raise ValueError(
            "CSV must have a date/time column (Date, Datetime, time, timestamp, dt, t)"
        )
    rows: list[dict[str, Any]] = df.to_dicts()
    return normalize_rows(rows, symbol)


def csv_preview(
    path: str | Path, max_rows: int = 5
) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Preview CSV: return column names and first max_rows as list of dicts.
    Useful for CSV preview endpoint.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    df = pl.read_csv(path, try_parse_dates=True, n_rows=max_rows + 10)
    columns = list(df.columns)
    rows = df.head(max_rows).to_dicts()
    return columns, rows
