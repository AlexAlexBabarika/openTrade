"""
Pydantic models for unified OHLCV data and API contracts.
All timestamps are UTC, ISO8601.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class OHLCVCandle(BaseModel):
    """Unified OHLCV candle. All consumers use this schema."""

    symbol: str = Field(..., min_length=1, description="Instrument symbol")
    timestamp: datetime = Field(..., description="Candle time, UTC ISO8601")
    open: float = Field(..., gt=0, description="Open price")
    high: float = Field(..., ge=0, description="High price")
    low: float = Field(..., ge=0, description="Low price")
    close: float = Field(..., gt=0, description="Close price")
    volume: float = Field(..., ge=0, description="Volume")

    class Config:
        json_encoders = {datetime: lambda v: v.strftime("%Y-%m-%dT%H:%M:%SZ")}


class OHLCVCandleList(BaseModel):
    """List of OHLCV candles for REST responses."""

    symbol: str
    candles: list[OHLCVCandle]


class CSVUploadResponse(BaseModel):
    """Response after CSV upload: symbol and count."""

    symbol: str
    count: int
    preview_columns: list[str]


SourceType = Literal["yfinance", "csv"]
