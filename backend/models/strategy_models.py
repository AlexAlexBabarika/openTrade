"""Pydantic models for saved backtest-strategy CRUD endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

_NAME_FIELD = Field(..., min_length=1, max_length=120)
_CODE_FIELD = Field(..., min_length=1, max_length=200_000)


class StrategyCreateRequest(BaseModel):
    name: str = _NAME_FIELD
    code: str = _CODE_FIELD


class StrategyUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    code: str | None = Field(None, min_length=1, max_length=200_000)


class StrategyInfo(BaseModel):
    id: str
    name: str
    code: str
    created_at: str
    updated_at: str


class StrategyListResponse(BaseModel):
    strategies: list[StrategyInfo]
