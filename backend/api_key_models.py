"""
Pydantic models for API key endpoints.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ApiKeyProvider(str, Enum):
    twelvedata = "twelvedata"
    alphavantage = "alphavantage"
    massive = "massive"


class ApiKeyCreateRequest(BaseModel):
    provider: ApiKeyProvider
    api_key: str = Field(..., min_length=1, max_length=512)


class ApiKeyUpdateRequest(BaseModel):
    api_key: str = Field(..., min_length=1, max_length=512)


class ApiKeyInfo(BaseModel):
    id: str
    provider: ApiKeyProvider
    key_prefix: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ApiKeyListResponse(BaseModel):
    keys: list[ApiKeyInfo]


class ApiKeyAuditEntry(BaseModel):
    id: str
    provider: str | None = None
    action: str
    created_at: str | None = None


class ApiKeyAuditResponse(BaseModel):
    entries: list[ApiKeyAuditEntry]
