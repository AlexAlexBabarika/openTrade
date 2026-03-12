"""
Supabase client for auth and user data.
Uses SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from environment.
"""

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

_client: "Client | None" = None


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
    Return the Supabase client, or raise RuntimeError if not configured.
    Use for auth endpoints that must have Supabase available.
    """
    client = get_supabase_client()
    if client is None:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )
    return client


def is_supabase_configured() -> bool:
    """Return True if Supabase credentials are present."""
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)
