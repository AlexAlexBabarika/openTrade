"""
yfinance data loader. Fetches OHLCV and normalizes to unified schema.
"""

from typing import Any

import yfinance as yf

from backend.market.models import OHLCVCandle
from backend.market.normalizer import normalize_rows
from backend.market.data_sources.marketdataprovider import MarketDataProvider


class YFinanceLoader(MarketDataProvider):
    @property
    def name(self) -> str:
        return "yfinance"

    @property
    def requires_api_key(self) -> bool:
        return False

    def get_ohlcv(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> list[OHLCVCandle]:
        """
        Load OHLCV for symbol from Yahoo Finance.
        Returns list of OHLCVCandle in unified schema (UTC ISO8601).
        """
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df is None or df.empty:
            return []
        df = df.reset_index()
        df.columns = [c.strip() for c in df.columns]
        rows: list[dict[str, Any]] = df.to_dict(orient="records")
        return normalize_rows(rows, symbol)


_loader = YFinanceLoader()


def load_yfinance(
    symbol: str, period: str = "1mo", interval: str = "1d"
) -> list[OHLCVCandle]:
    return _loader.get_ohlcv(symbol, period, interval)
