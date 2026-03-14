"""
Secure API-key CRUD endpoints.

All mutations encrypt the key before writing and never return the raw key.
Reads return metadata only (provider, prefix, timestamps).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api_key_models import (
    ApiKeyAuditEntry,
    ApiKeyAuditResponse,
    ApiKeyCreateRequest,
    ApiKeyInfo,
    ApiKeyListResponse,
    ApiKeyProvider,
    ApiKeyUpdateRequest,
)
from backend.auth_deps import get_current_user
from backend.auth_models import AuthUserInfo
from backend.encryption import encrypt_api_key, make_key_prefix
from backend.supabase_client import require_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user/api-keys", tags=["api-keys"])


def _row_to_info(row: dict) -> ApiKeyInfo:
    return ApiKeyInfo(
        id=str(row["id"]),
        provider=row["provider"],
        key_prefix=row.get("key_prefix"),
        created_at=str(row["created_at"]) if row.get("created_at") else None,
        updated_at=str(row["updated_at"]) if row.get("updated_at") else None,
    )


@router.get("", response_model=ApiKeyListResponse)
def list_api_keys(user: AuthUserInfo = Depends(get_current_user)):
    supabase = require_supabase_client()
    resp = (
        supabase.table("api_keys")
        .select("id, provider, key_prefix, created_at, updated_at")
        .eq("user_id", user.id)
        .order("created_at")
        .execute()
    )
    rows = resp.data or []
    return ApiKeyListResponse(keys=[_row_to_info(r) for r in rows])


@router.post("", response_model=ApiKeyInfo, status_code=status.HTTP_201_CREATED)
def create_api_key(
    body: ApiKeyCreateRequest,
    user: AuthUserInfo = Depends(get_current_user),
):
    supabase = require_supabase_client()

    existing = (
        supabase.table("api_keys")
        .select("id")
        .eq("user_id", user.id)
        .eq("provider", body.provider.value)
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"API key for {body.provider.value} already exists. Use PUT to update.",
        )

    encrypted = encrypt_api_key(body.api_key)
    prefix = make_key_prefix(body.api_key)

    resp = (
        supabase.table("api_keys")
        .insert(
            {
                "user_id": user.id,
                "provider": body.provider.value,
                "encrypted_key": _bytes_to_pg_hex(encrypted),
                "key_prefix": prefix,
            }
        )
        .execute()
    )
    row = resp.data[0] if resp.data else None
    if not row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store API key",
        )
    return _row_to_info(row)


@router.put("/{provider}", response_model=ApiKeyInfo)
def update_api_key(
    provider: ApiKeyProvider,
    body: ApiKeyUpdateRequest,
    user: AuthUserInfo = Depends(get_current_user),
):
    supabase = require_supabase_client()

    existing = (
        supabase.table("api_keys")
        .select("id")
        .eq("user_id", user.id)
        .eq("provider", provider.value)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No API key for {provider.value}",
        )

    encrypted = encrypt_api_key(body.api_key)
    prefix = make_key_prefix(body.api_key)

    resp = (
        supabase.table("api_keys")
        .update(
            {
                "encrypted_key": _bytes_to_pg_hex(encrypted),
                "key_prefix": prefix,
            }
        )
        .eq("user_id", user.id)
        .eq("provider", provider.value)
        .execute()
    )
    row = resp.data[0] if resp.data else None
    if not row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API key",
        )
    return _row_to_info(row)


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    provider: ApiKeyProvider,
    user: AuthUserInfo = Depends(get_current_user),
):
    supabase = require_supabase_client()

    existing = (
        supabase.table("api_keys")
        .select("id")
        .eq("user_id", user.id)
        .eq("provider", provider.value)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No API key for {provider.value}",
        )

    supabase.table("api_keys").delete().eq("user_id", user.id).eq(
        "provider", provider.value
    ).execute()


@router.get("/audit", response_model=ApiKeyAuditResponse)
def list_audit_log(
    limit: int = 50,
    user: AuthUserInfo = Depends(get_current_user),
):
    supabase = require_supabase_client()
    clamped_limit = min(max(limit, 1), 200)
    resp = (
        supabase.table("api_key_audit_log")
        .select("id, provider, action, created_at")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(clamped_limit)
        .execute()
    )
    rows = resp.data or []
    entries = [
        ApiKeyAuditEntry(
            id=str(r["id"]),
            provider=r.get("provider"),
            action=r["action"],
            created_at=str(r["created_at"]) if r.get("created_at") else None,
        )
        for r in rows
    ]
    return ApiKeyAuditResponse(entries=entries)


def _bytes_to_pg_hex(b: bytes) -> str:
    """Encode bytes as Postgres hex-format bytea literal: \\x deadbeef..."""
    return "\\x" + b.hex()
