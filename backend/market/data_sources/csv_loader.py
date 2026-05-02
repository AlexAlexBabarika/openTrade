"""
CSV data loader using polars. Auto-detects column names and normalizes to unified schema.
"""

from pathlib import Path
from typing import Any

import polars as pl

from backend.market.models import OHLCVCandle
from backend.market.normalizer import normalize_column_name, normalize_row
from backend.market.data_sources.marketdataprovider import MarketDataProvider


def _detect_time_column(df: pl.DataFrame) -> str | None:
    """Return first column that normalizes to 'timestamp'."""
    for c in df.columns:
        if normalize_column_name(c) == "timestamp":
            return c
    return None


def _normalize_with_row_index(
    rows: list[dict[str, Any]], symbol: str
) -> list[OHLCVCandle]:
    out: list[OHLCVCandle] = []
    for i, row in enumerate(rows):
        try:
            out.append(normalize_row(row, symbol))
        except ValueError as e:
            raise ValueError(f"CSV row {i}: {e}") from e
    return out


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
        df = pl.read_csv(self._path, try_parse_dates=True)
        if df.is_empty():
            return []

        time_col = _detect_time_column(df)
        if time_col is None:
            raise ValueError(
                "CSV must have a date/time column (Date, Datetime, time, timestamp, dt, t)"
            )

        rows: list[dict[str, Any]] = df.to_dicts()
        return _normalize_with_row_index(rows, symbol)


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
    df = pl.read_csv(path, n_rows=max_rows + 10, try_parse_dates=True)
    columns = list(df.columns)
    rows = df.head(max_rows).to_dicts()
    return columns, rows
