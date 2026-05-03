"""Pydantic models for chart symbol-comparison CRUD endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SeriesType = Literal["line", "candlestick"]

_SYMBOL = Field(..., min_length=1, max_length=64)
_PROVIDER = Field(..., min_length=1, max_length=32)
_COLOR = Field(..., min_length=1, max_length=16)


class ComparisonCreateRequest(BaseModel):
    main_symbol: str = _SYMBOL
    comparison_symbol: str = _SYMBOL
    provider: str = _PROVIDER
    color: str = _COLOR
    series_type: SeriesType = "line"


class ComparisonUpdateRequest(BaseModel):
    color: str | None = Field(None, min_length=1, max_length=16)
    series_type: SeriesType | None = None


class ComparisonInfo(BaseModel):
    id: str
    main_symbol: str
    comparison_symbol: str
    provider: str
    color: str
    series_type: SeriesType
    position: int
    created_at: str


class ComparisonListResponse(BaseModel):
    comparisons: list[ComparisonInfo]
