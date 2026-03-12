"""
Auth endpoints: signup, login, logout, session.
All auth is proxied through the backend to Supabase.
"""

from fastapi import APIRouter, HTTPException, Request

from backend.auth_models import (
    AuthLoginRequest,
    AuthSessionResponse,
    AuthSessionUserResponse,
    AuthSignupRequest,
    AuthUserInfo,
)
from backend.supabase_client import require_supabase_client

router = APIRouter(prefix="/auth", tags=["auth"])


def _extract_bearer_token(request: Request) -> str | None:
    """Extract Bearer token from Authorization header."""
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


def _auth_response_from_supabase(response) -> AuthSessionResponse:
    """Build AuthSessionResponse from Supabase AuthResponse."""
    session = response.session
    user = response.user
    if not session or not user:
        raise HTTPException(
            status_code=500, detail="Invalid auth response from Supabase"
        )
    return AuthSessionResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_at=getattr(session, "expires_at", None),
        user=AuthUserInfo(id=str(user.id), email=getattr(user, "email", None)),
    )


@router.post("/signup", response_model=AuthSessionResponse)
def signup(body: AuthSignupRequest):
    """
    Create a new user account. Returns access_token and refresh_token.
    If email confirmation is required, returns 200 with a message to check email.
    """
    supabase = require_supabase_client()
    try:
        response = supabase.auth.sign_up(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if response.session and response.user:
        return _auth_response_from_supabase(response)
    # Signup succeeded but no session (e.g. email confirmation required)
    if response.user:
        raise HTTPException(
            status_code=202,
            detail="Check your email to confirm your account, then log in.",
        )
    raise HTTPException(status_code=400, detail="Signup failed")


@router.post("/login", response_model=AuthSessionResponse)
def login(body: AuthLoginRequest):
    """
    Sign in with email and password. Returns access_token and refresh_token.
    """
    supabase = require_supabase_client()
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not response.session or not response.user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _auth_response_from_supabase(response)


@router.post("/logout")
def logout():
    """
    Log out. Client should discard stored tokens.
    Server-side session invalidation is optional; JWT remains valid until expiry.
    """
    return {"message": "Logged out"}


@router.get("/session", response_model=AuthSessionUserResponse)
def get_session(request: Request):
    """
    Return the current user if the Bearer token is valid.
    Requires Authorization: Bearer <access_token>.
    """
    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )
    supabase = require_supabase_client()
    try:
        response = supabase.auth.get_user(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = getattr(response, "user", response) if response else None
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return AuthSessionUserResponse(
        user=AuthUserInfo(id=str(user.id), email=getattr(user, "email", None))
    )
