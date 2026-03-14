"""
Pydantic models for auth API requests and responses.
"""

from pydantic import BaseModel, EmailStr, Field


class AuthSignupRequest(BaseModel):
    """Request body for POST /auth/signup."""

    email: EmailStr
    password: str = Field(..., min_length=6)


class AuthLoginRequest(BaseModel):
    """Request body for POST /auth/login."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class AuthUserInfo(BaseModel):
    """User info returned in session/token responses."""

    id: str
    email: str | None = None


class AuthSessionResponse(BaseModel):
    """Response for login/signup: tokens and user."""

    access_token: str
    refresh_token: str
    expires_at: int | None = None
    user: AuthUserInfo


class AuthSignupPendingResponse(BaseModel):
    """Response when signup succeeds but email confirmation is required (202)."""

    message: str


class AuthSessionUserResponse(BaseModel):
    """Response for GET /auth/session: current user info."""

    user: AuthUserInfo
