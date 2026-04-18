"""API models for unified market data endpoints."""

from enum import Enum

from pydantic import BaseModel


class MarketDataProviderEnum(str, Enum):
    """Supported OHLCV data providers for GET /data/market."""

    yfinance = "yfinance"
    twelvedata = "twelvedata"
    binance = "binance"


class AssetType(str, Enum):
    """Mirrors the Postgres asset_type enum (20260311123025_asset_type.sql)."""

    stock = "stock"
    option = "option"
    crypto = "crypto"
    forex = "forex"
    commodity = "commodity"
    index = "index"
    bond = "bond"
    etf = "etf"
    mutual_fund = "mutual_fund"
    other = "other"


class SymbolRecord(BaseModel):
    """Canonical symbol entry produced by a provider's list_symbols()."""

    symbol: str
    name: str
    asset_type: AssetType | None = None
    exchange: str | None = None


class SymbolProviders(BaseModel):
    twelvedata: bool
    yfinance: bool
    binance: bool


class SymbolSearchResult(BaseModel):
    symbol: str
    name: str
    asset_type: AssetType | None = None
    exchange: str | None = None
    providers: SymbolProviders


class MarkYFinanceRequest(BaseModel):
    symbol: str
