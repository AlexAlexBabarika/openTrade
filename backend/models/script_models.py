"""Pydantic models for saved user-script CRUD endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


_NAME_FIELD = Field(..., min_length=1, max_length=120)
_CODE_FIELD = Field(..., min_length=1, max_length=200_000)


class ScriptCreateRequest(BaseModel):
    name: str = _NAME_FIELD
    code: str = _CODE_FIELD


class ScriptUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    code: str | None = Field(None, min_length=1, max_length=200_000)


class ScriptInfo(BaseModel):
    id: str
    name: str
    code: str
    created_at: str
    updated_at: str


class ScriptListResponse(BaseModel):
    scripts: list[ScriptInfo]
