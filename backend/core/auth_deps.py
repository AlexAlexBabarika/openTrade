"""FastAPI dependencies for locally issued access tokens."""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.models.auth_models import AuthUserInfo
from backend.core.runtime_secrets import runtime_secret

_bearer_scheme = HTTPBearer(auto_error=False)
JWT_ALGORITHM = "HS256"


def _secret() -> str:
    return runtime_secret("JWT_SECRET")


def _user_from_token(token: str) -> AuthUserInfo:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access" or not payload.get("sub"):
            raise jwt.InvalidTokenError("not an access token")
        return AuthUserInfo(id=str(payload["sub"]), email=payload.get("email"))
    except HTTPException:
        raise
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthUserInfo:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _user_from_token(credentials.credentials)


def optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthUserInfo | None:
    if not credentials:
        return None
    try:
        return _user_from_token(credentials.credentials)
    except HTTPException as exc:
        if exc.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
            return None
        raise
