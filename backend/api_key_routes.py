"""
Secure API-key CRUD endpoints.

All mutations encrypt the key before writing and never return the raw key.
Reads return metadata only (provider, prefix, timestamps).
Uses service_role for PostgREST; user scoping is enforced in Python via validated user_id.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from postgrest.exceptions import APIError

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
from backend.supabase_client import get_service_postgrest

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


def _handle_api_key_error(exc: Exception, operation: str) -> HTTPException:
    """
    Map PostgREST/encryption errors to HTTPException with actionable detail.
    Logs full error for debugging.
    """
    if isinstance(exc, APIError):
        code = getattr(exc, "code", None) or "unknown"
        msg = getattr(exc, "message", None) or str(exc)
        hint = getattr(exc, "hint", None)
        details = getattr(exc, "details", None)
        logger.exception(
            "API key %s failed: code=%s message=%r hint=%r details=%r",
            operation,
            code,
            msg,
            hint,
            details,
        )
        # Map known Postgres/PostgREST codes to user-facing messages (include code for debugging)
        code_suffix = f" [code {code}]" if code else ""
        if code == "42501":
            detail = f"Permission denied: {msg}. Ensure your session is valid and try again.{code_suffix}"
        elif code == "23503":
            detail = f"Referenced user or resource not found.{code_suffix}"
        elif code == "23505":
            detail = f"Duplicate entry: {msg}{code_suffix}"
        elif code == "42P01":
            detail = f"Database schema issue. Contact support.{code_suffix}"
        elif str(code).startswith("PGRST"):
            detail = f"Request error: {msg}{code_suffix}"
        else:
            detail = f"{msg}" + (f" ({hint})" if hint else "") + code_suffix
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
    if isinstance(exc, RuntimeError) and "API_KEYS_ENCRYPTION_KEY" in str(exc):
        logger.exception("API key %s failed: encryption not configured", operation)
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key storage is not configured. Contact support.",
        )
    logger.exception("API key %s failed: %s", operation, exc)
    # Never expose internal exception details to the client.
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to {operation}. Please try again or contact support.",
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
        raise _handle_api_key_error(e, "list API keys")
    rows = resp.data or []
    return ApiKeyListResponse(keys=[_row_to_info(r) for r in rows])


@router.post("", response_model=ApiKeyInfo, status_code=status.HTTP_201_CREATED)
def create_api_key(
    body: ApiKeyCreateRequest,
    user: AuthUserInfo = Depends(get_current_user),
):
    db = get_service_postgrest()
    try:
        existing = (
            db.from_("api_keys")
            .select("id")
            .eq("user_id", user.id)
            .eq("provider", body.provider.value)
            .limit(1)
            .execute()
        )
    except Exception as e:
        raise _handle_api_key_error(e, "check existing API key")
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"API key for {body.provider.value} already exists. Use PUT to update.",
        )

    try:
        encrypted = encrypt_api_key(body.api_key)
        prefix = make_key_prefix(body.api_key)
    except Exception as e:
        raise _handle_api_key_error(e, "encrypt API key")

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
    except Exception as e:
        raise _handle_api_key_error(e, "create API key")
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
        raise _handle_api_key_error(e, "check existing API key for update")
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No API key for {provider.value}",
        )

    try:
        encrypted = encrypt_api_key(body.api_key)
        prefix = make_key_prefix(body.api_key)
    except Exception as e:
        raise _handle_api_key_error(e, "encrypt API key")

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
        raise _handle_api_key_error(e, "update API key")
    row = resp.data[0] if resp.data else None
    if not row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API key (no response)",
        )
    return _row_to_info(row)


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    provider: ApiKeyProvider,
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
        raise _handle_api_key_error(e, "check existing API key for delete")
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No API key for {provider.value}",
        )

    try:
        db.from_("api_keys").delete().eq("user_id", user.id).eq(
            "provider", provider.value
        ).execute()
    except Exception as e:
        raise _handle_api_key_error(e, "delete API key")


@router.get("/audit", response_model=ApiKeyAuditResponse)
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
        raise _handle_api_key_error(e, "list audit log")
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
