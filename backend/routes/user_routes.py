"""
User profile endpoints backed by Supabase public.profiles.
"""

from fastapi import APIRouter, Depends

from backend.core.auth_deps import get_current_user
from backend.models.auth_models import (
    AuthUserInfo,
    UserProfile,
    UserProfileResponse,
)
from backend.core.supabase_client import require_supabase_client

router = APIRouter(prefix="/user", tags=["user"])


def _to_profile(user: AuthUserInfo, row: dict | None) -> UserProfile:
    if not row:
        return UserProfile(id=user.id, email=user.email)
    return UserProfile(
        id=str(row.get("id", user.id)),
        email=row.get("email", user.email),
        created_at=(
            str(row["created_at"]) if row.get("created_at") is not None else None
        ),
        updated_at=(
            str(row["updated_at"]) if row.get("updated_at") is not None else None
        ),
    )


def _fetch_profile_row(user_id: str) -> dict | None:
    supabase = require_supabase_client()
    response = (
        supabase.table("profiles")
        .select("id,email,created_at,updated_at")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    data = response.data
    if isinstance(data, list):
        return data[0] if data else None
    return data


@router.get("/profile", response_model=UserProfileResponse)
def get_profile(user: AuthUserInfo = Depends(get_current_user)):
    """
    Return the authenticated user's profile.
    """
    row = _fetch_profile_row(user.id)
    if row is None:
        supabase = require_supabase_client()
        supabase.table("profiles").upsert(
            {"id": user.id, "email": user.email}, on_conflict="id"
        ).execute()
        row = _fetch_profile_row(user.id)
    return UserProfileResponse(profile=_to_profile(user, row))
