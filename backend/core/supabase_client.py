"""
Supabase client for auth and user data.
Uses SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from environment.
"""

import logging
import os
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

if TYPE_CHECKING:
    from postgrest import SyncPostgrestClient
    from supabase import Client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

_client: "Client | None" = None
_service_postgrest: "SyncPostgrestClient | None" = None


def get_supabase_client() -> "Client | None":
    """
    Return the Supabase client, or None if credentials are not configured.
    Creates the client lazily on first call.
    """
    global _client
    if _client is not None:
        return _client
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return None
    try:
        from supabase import create_client

        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        return _client
    except Exception as e:
        logger.warning("Failed to create Supabase client: %s", e)
        return None


def require_supabase_client() -> "Client":
    """
    Return the Supabase client, or raise HTTP 503 if not configured.
    Use for auth endpoints that must have Supabase available.
    """
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth is not configured on this server. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
        )
    return client


def get_service_postgrest() -> "SyncPostgrestClient":
    """Return a PostgREST client that always authenticates as service_role.

    The shared Supabase client's .table() method is unsafe for data operations
    because auth events (login, signup, token refresh) overwrite its Authorization
    header with the user's JWT.  This dedicated client is immune to that.
    """
    global _service_postgrest
    if _service_postgrest is not None:
        return _service_postgrest

    client = require_supabase_client()

    from postgrest import SyncPostgrestClient

    _service_postgrest = SyncPostgrestClient(
        str(client.rest_url),
        headers={
            "apiKey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    )
    return _service_postgrest


def is_supabase_configured() -> bool:
    """Return True if Supabase credentials are present."""
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)
