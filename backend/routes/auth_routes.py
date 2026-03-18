"""
Auth endpoints: signup, login, logout, session, refresh.
All auth is proxied through the backend to Supabase.

Token strategy:
  - refresh_token → HttpOnly cookie (never exposed to JS)
  - access_token  → returned in JSON body, held in-memory on the frontend
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials

from backend.core.auth_deps import _bearer_scheme, get_current_user
from backend.models.auth_models import (
    AuthLoginRequest,
    AuthSessionResponse,
    AuthSessionUserResponse,
    AuthSignupPendingResponse,
    AuthSignupRequest,
    AuthUserInfo,
)
from backend.core.supabase_client import get_supabase_client, require_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "opentrade_refresh_token"
REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/auth",
        max_age=REFRESH_COOKIE_MAX_AGE,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/auth",
    )


def _build_session_response(sb_response) -> AuthSessionResponse:
    """Build AuthSessionResponse from Supabase AuthResponse."""
    session = sb_response.session
    user = sb_response.user
    if not session or not user:
        raise HTTPException(
            status_code=500, detail="Invalid auth response from Supabase"
        )
    return AuthSessionResponse(
        access_token=session.access_token,
        expires_at=getattr(session, "expires_at", None),
        user=AuthUserInfo(id=str(user.id), email=getattr(user, "email", None)),
    )


@router.post(
    "/signup",
    response_model=AuthSessionResponse,
    responses={
        202: {
            "model": AuthSignupPendingResponse,
            "description": "Email confirmation required. Check your email to confirm your account, then log in.",
        },
    },
)
def signup(body: AuthSignupRequest, response: Response):
    """
    Create a new user account. On success without email confirmation:
    returns 200 with access_token (refresh_token set as HttpOnly cookie).
    If email confirmation is required: returns 202 Accepted with a message.
    """
    supabase = require_supabase_client()
    try:
        sb_response = supabase.auth.sign_up(
            {"email": body.email, "password": body.password}
        )
    except Exception as exc:
        logger.error("Supabase sign_up failed: %s", exc)
        raise HTTPException(status_code=400, detail="Signup failed")
    if sb_response.session and sb_response.user:
        _set_refresh_cookie(response, sb_response.session.refresh_token)
        return _build_session_response(sb_response)
    if sb_response.user:
        pending = AuthSignupPendingResponse(
            message="Check your email to confirm your account, then log in."
        )
        return JSONResponse(status_code=202, content=pending.model_dump())
    raise HTTPException(status_code=400, detail="Signup failed")


@router.post("/login", response_model=AuthSessionResponse)
def login(body: AuthLoginRequest, response: Response):
    """
    Sign in with email and password. Returns access_token in the body;
    refresh_token is set as an HttpOnly cookie.
    """
    supabase = require_supabase_client()
    try:
        sb_response = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as exc:
        logger.warning("Supabase sign_in_with_password failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not sb_response.session or not sb_response.user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    _set_refresh_cookie(response, sb_response.session.refresh_token)
    return _build_session_response(sb_response)


@router.post("/refresh", response_model=AuthSessionResponse)
def refresh(request: Request, response: Response):
    """
    Exchange the refresh_token cookie for a new access_token.
    Also rotates the refresh_token cookie.
    """
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    supabase = require_supabase_client()
    try:
        sb_response = supabase.auth.refresh_session(token)
    except Exception as exc:
        logger.warning("Supabase refresh_session failed: %s", exc)
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    if not sb_response.session or not sb_response.user:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    _set_refresh_cookie(response, sb_response.session.refresh_token)
    return _build_session_response(sb_response)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
):
    """
    Revoke the current session in Supabase, clear the refresh_token cookie,
    and instruct the client to discard the in-memory access token.
    """
    if credentials:
        supabase = get_supabase_client()
        if supabase:
            try:
                supabase.auth.admin.sign_out(credentials.credentials)
            except Exception as exc:
                logger.warning("Supabase sign-out failed: %s", exc)
    _clear_refresh_cookie(response)
    return {"message": "Logged out"}


@router.get("/session", response_model=AuthSessionUserResponse)
def get_session(user: AuthUserInfo = Depends(get_current_user)):
    """
    Return the current user if the Bearer token is valid.
    Requires Authorization: Bearer <access_token>.
    """
    return AuthSessionUserResponse(user=user)
