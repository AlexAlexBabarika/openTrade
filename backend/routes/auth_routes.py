"""Local email/password authentication with rotating refresh sessions."""

import hashlib
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials

from backend.core.auth_deps import (
    JWT_ALGORITHM,
    _bearer_scheme,
    _secret,
    get_current_user,
)
from backend.core.database import DatabaseError, connection
from backend.models.auth_models import (
    AuthLoginRequest,
    AuthSessionResponse,
    AuthSessionUserResponse,
    AuthSignupRequest,
    AuthUserInfo,
)

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_COOKIE_NAME = "opentrade_refresh_token"
REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30
ACCESS_TOKEN_MAX_AGE = 60 * 15
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
_passwords = PasswordHasher()


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/auth",
        max_age=REFRESH_COOKIE_MAX_AGE,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/auth",
    )


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _new_session(cur, user_id: str) -> str:
    token = secrets.token_urlsafe(48)
    cur.execute(
        "INSERT INTO refresh_sessions (token_hash, user_id, expires_at) VALUES (%s, %s, %s)",
        (
            _token_hash(token),
            user_id,
            datetime.now(timezone.utc) + timedelta(seconds=REFRESH_COOKIE_MAX_AGE),
        ),
    )
    return token


def _response(user: AuthUserInfo) -> AuthSessionResponse:
    expires_at = int(time.time()) + ACCESS_TOKEN_MAX_AGE
    token = jwt.encode(
        {
            "sub": user.id,
            "email": user.email,
            "type": "access",
            "iat": int(time.time()),
            "exp": expires_at,
        },
        _secret(),
        algorithm=JWT_ALGORITHM,
    )
    return AuthSessionResponse(access_token=token, expires_at=expires_at, user=user)


@router.post(
    "/signup", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED
)
def signup(body: AuthSignupRequest, response: Response) -> AuthSessionResponse:
    email = str(body.email).strip().lower()
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id, email",
                (email, _passwords.hash(body.password)),
            )
            row = cur.fetchone()
            refresh_token = _new_session(cur, str(row["id"]))
    except DatabaseError:
        raise
    except Exception as exc:
        if getattr(exc, "sqlstate", None) == "23505":
            raise HTTPException(
                status_code=409, detail="An account with this email already exists"
            ) from exc
        raise HTTPException(status_code=500, detail="Signup failed") from exc
    user = AuthUserInfo(id=str(row["id"]), email=row["email"])
    _set_refresh_cookie(response, refresh_token)
    return _response(user)


@router.post("/login", response_model=AuthSessionResponse)
def login(body: AuthLoginRequest, response: Response) -> AuthSessionResponse:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, password_hash FROM users WHERE email = %s",
            (str(body.email).strip().lower(),),
        )
        row = cur.fetchone()
        try:
            if not row:
                raise VerifyMismatchError()
            _passwords.verify(row["password_hash"], body.password)
        except VerifyMismatchError as exc:
            raise HTTPException(
                status_code=401, detail="Invalid email or password"
            ) from exc
        refresh_token = _new_session(cur, str(row["id"]))
    user = AuthUserInfo(id=str(row["id"]), email=row["email"])
    _set_refresh_cookie(response, refresh_token)
    return _response(user)


@router.post("/refresh", response_model=AuthSessionResponse)
def refresh(request: Request, response: Response) -> AuthSessionResponse:
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM refresh_sessions s USING users u WHERE s.token_hash = %s AND s.user_id = u.id AND s.expires_at > now() RETURNING u.id, u.email",
            (_token_hash(token),),
        )
        row = cur.fetchone()
        if not row:
            _clear_refresh_cookie(response)
            raise HTTPException(
                status_code=401, detail="Invalid or expired refresh token"
            )
        refresh_token = _new_session(cur, str(row["id"]))
    user = AuthUserInfo(id=str(row["id"]), email=row["email"])
    _set_refresh_cookie(response, refresh_token)
    return _response(user)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
):
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if token:
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM refresh_sessions WHERE token_hash = %s",
                (_token_hash(token),),
            )
    _clear_refresh_cookie(response)
    return {"message": "Logged out"}


@router.get("/session", response_model=AuthSessionUserResponse)
def get_session(user: AuthUserInfo = Depends(get_current_user)):
    return AuthSessionUserResponse(user=user)
