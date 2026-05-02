"""
Secure API-key CRUD endpoints.

All mutations encrypt the key before writing and never return the raw key.
Reads return metadata only (provider, prefix, timestamps).
Uses service_role for PostgREST; user scoping is enforced in Python via validated user_id.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from postgrest.exceptions import APIError

from backend.models.api_key_models import (
    ApiKeyAuditEntry,
    ApiKeyAuditResponse,
    ApiKeyCreateRequest,
    ApiKeyInfo,
    ApiKeyListResponse,
    ApiKeyProvider,
    ApiKeyUpdateRequest,
)
from backend.core.auth_deps import get_current_user
from backend.models.auth_models import AuthUserInfo
from backend.core.encryption import encrypt_api_key, make_key_prefix
from backend.core.supabase_client import get_service_postgrest
from backend.routes.db_error_handlers.api_key_db_error_handler import (
    ApiKeyDBErrorHandler,
)

apiKeyDBErrorHandler: ApiKeyDBErrorHandler = ApiKeyDBErrorHandler(
    logging.getLogger(__name__)
)
router = APIRouter(prefix="/user/api-keys", tags=["api-keys"])


def _row_to_info(row: dict) -> ApiKeyInfo:
    return ApiKeyInfo(
        id=str(row["id"]),
        provider=row["provider"],
        key_prefix=row["key_prefix"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


@router.get("", response_model=ApiKeyListResponse)
def list_api_keys(
    user: AuthUserInfo = Depends(get_current_user),
):
    db = get_service_postgrest()
    try:
        resp = (
            db.from_("api_keys")
            .select("id, provider, key_prefix, created_at, updated_at")
            .eq("user_id", user.id)
            .order("created_at")
            .execute()
        )
    except Exception as e:
        raise apiKeyDBErrorHandler.handle_db_error(e, "list API keys")
    rows = resp.data or []
    return ApiKeyListResponse(keys=[_row_to_info(r) for r in rows])


@router.post("", response_model=ApiKeyInfo, status_code=status.HTTP_201_CREATED)
def create_api_key(
    body: ApiKeyCreateRequest,
    user: AuthUserInfo = Depends(get_current_user),
):
    db = get_service_postgrest()

    try:
        encrypted = encrypt_api_key(body.api_key)
        prefix = make_key_prefix(body.api_key)
    except Exception as e:
        raise apiKeyDBErrorHandler.handle_db_error(e, "encrypt API key")

    try:
        resp = (
            db.from_("api_keys")
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
    except APIError as e:
        if e.code == "23505":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"API key for {body.provider.value} already exists. Use PUT to update.",
            ) from e
        raise apiKeyDBErrorHandler.handle_db_error(e, "create API key")
    except Exception as e:
        raise apiKeyDBErrorHandler.handle_db_error(e, "create API key")

    row = resp.data[0] if resp.data else None
    if not row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store API key (no response)",
        )
    return _row_to_info(row)


@router.put("/{provider}", response_model=ApiKeyInfo)
def update_api_key(
    provider: ApiKeyProvider,
    body: ApiKeyUpdateRequest,
    user: AuthUserInfo = Depends(get_current_user),
):
    db = get_service_postgrest()
    try:
        existing = (
            db.from_("api_keys")
            .select("id")
            .eq("user_id", user.id)
            .eq("provider", provider.value)
            .limit(1)
            .execute()
        )
    except Exception as e:
        raise apiKeyDBErrorHandler.handle_db_error(
            e, "check existing API key for update"
        )
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No API key for {provider.value}",
        )

    try:
        encrypted = encrypt_api_key(body.api_key)
        prefix = make_key_prefix(body.api_key)
    except Exception as e:
        raise apiKeyDBErrorHandler.handle_db_error(e, "encrypt API key")

    try:
        resp = (
            db.from_("api_keys")
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
    except Exception as e:
        raise apiKeyDBErrorHandler.handle_db_error(e, "update API key")
    row = resp.data[0] if resp.data else None
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No API key for {provider.value}",
        )
    return _row_to_info(row)


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    provider: ApiKeyProvider,
    user: AuthUserInfo = Depends(get_current_user),
):
    db = get_service_postgrest()
    try:
        resp = (
            db.from_("api_keys")
            .delete()
            .eq("user_id", user.id)
            .eq("provider", provider.value)
            .select("id")
            .execute()
        )
    except Exception as e:
        raise apiKeyDBErrorHandler.handle_db_error(e, "delete API key")
    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No API key for {provider.value}",
        )


@router.get("/audit/logs", response_model=ApiKeyAuditResponse)
def list_audit_log(
    limit: int = 50,
    user: AuthUserInfo = Depends(get_current_user),
):
    db = get_service_postgrest()
    clamped_limit = min(max(limit, 1), 200)
    try:
        resp = (
            db.from_("api_key_audit_log")
            .select("id, provider, action, created_at")
            .eq("user_id", user.id)
            .order("created_at", desc=True)
            .limit(clamped_limit)
            .execute()
        )
    except Exception as e:
        raise apiKeyDBErrorHandler.handle_db_error(e, "list audit log")
    rows = resp.data or []
    entries = [
        ApiKeyAuditEntry(
            id=str(r["id"]),
            provider=r["provider"],
            action=r["action"],
            created_at=str(r["created_at"]),
        )
        for r in rows
    ]
    return ApiKeyAuditResponse(entries=entries)


def _bytes_to_pg_hex(b: bytes) -> str:
    """Encode bytes as Postgres hex-format bytea literal: \\x deadbeef..."""
    return "\\x" + b.hex()
