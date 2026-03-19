"""
CSV data loader using pandas. Auto-detects column names and normalizes to unified schema.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from backend.market.models import OHLCVCandle
from backend.market.normalizer import normalize_column_name, normalize_rows
from backend.market.data_sources.marketdataprovider import MarketDataProvider


def _detect_time_column(df: pd.DataFrame) -> str | None:
    """Return first column that normalizes to 'timestamp'."""
    for c in df.columns:
        if normalize_column_name(c) == "timestamp":
            return c
    return None


class CsvLoader(MarketDataProvider):
    """Loads OHLCV data from a CSV file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def name(self) -> str:
        return "csv"

    @property
    def requires_api_key(self) -> bool:
        return False

    def get_ohlcv(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> list[OHLCVCandle]:
        if not self._path.exists():
            raise FileNotFoundError(str(self._path))
        df = pd.read_csv(self._path)
        if df.empty:
            return []

        time_col = _detect_time_column(df)
        if time_col is None:
            raise ValueError(
                "CSV must have a date/time column (Date, Datetime, time, timestamp, dt, t)"
            )

        df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
        null_mask = df[time_col].isnull()
        if null_mask.any():
            bad_rows = [i for i, v in enumerate(null_mask.tolist()) if v]
            sample = bad_rows[:5]
            raise ValueError(
                f"CSV has unparseable timestamps in {time_col} at row(s) {sample}"
                f"{'...' if len(bad_rows) > 5 else ''}. "
                f"Total invalid rows: {len(bad_rows)}. "
                "Check date format (e.g. YYYY-MM-DD, DD/MM/YYYY) or ensure no empty/invalid cells."
            )

        rows: list[dict[str, Any]] = df.to_dict(orient="records")
        return normalize_rows(rows, symbol)


def load_csv(path: str | Path, symbol: str) -> list[OHLCVCandle]:
    """Load CSV: return list of OHLCVCandle."""
    return CsvLoader(path).get_ohlcv(symbol)


def csv_preview(
    path: str | Path, max_rows: int = 5
) -> tuple[list[str], list[dict[str, Any]]]:
    """Preview CSV: return column names and first max_rows as list of dicts."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    df = pd.read_csv(path, nrows=max_rows + 10)
    time_col = _detect_time_column(df)
    if time_col is not None:
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
    columns = list(df.columns)
    rows = df.head(max_rows).to_dict(orient="records")
    return columns, rows
