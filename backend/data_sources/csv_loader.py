"""
CSV loader using pandas. Auto-detects column names and normalizes to unified schema.
"""

from pathlib import Path
from typing import Any

import pandas as pd
from backend.models import OHLCVCandle
from backend.normalizer import normalize_rows


def _detect_time_column(df: pd.DataFrame) -> str | None:
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
    Load OHLCV from CSV using pandas.
    Column names are auto-detected (Date, Open, o, etc.) and normalized.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    df = pd.read_csv(path, parse_dates=True)
    if df.empty:
        return []
    time_col = _detect_time_column(df)
    if time_col is None:
        raise ValueError(
            "CSV must have a date/time column (Date, Datetime, time, timestamp, dt, t)"
        )
    # Validate timestamps before normalization: polars/try_parse_dates coerces
    # unparseable values to null, which would fail later with a confusing error.
    null_mask = df[time_col].is_null()
    if null_mask.any():
        bad_rows = [i for i, v in enumerate(null_mask.to_list()) if v]
        sample = bad_rows[:5]
        raise ValueError(
            f"CSV has unparseable timestamps in {time_col} at row(s) {sample}{'...' if len(bad_rows) > 5 else ''}. "
            f"Total invalid rows: {len(bad_rows)}. "
            "Check date format (e.g. YYYY-MM-DD, DD/MM/YYYY) or ensure no empty/invalid cells."
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
    df = pd.read_csv(path, parse_dates=True, nrows=max_rows + 10)
    columns = list(df.columns)
    rows = df.head(max_rows).to_dict(orient="records")
    return columns, rows
