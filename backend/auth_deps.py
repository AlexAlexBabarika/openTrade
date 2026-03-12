"""
FastAPI dependency for JWT verification via Supabase.

Usage in protected routes:

    from backend.auth_deps import get_current_user, optional_current_user
    from backend.auth_models import AuthUserInfo

    @app.get("/protected")
    def protected(user: AuthUserInfo = Depends(get_current_user)):
        return {"hello": user.email}

    @app.get("/optional")
    def maybe_authed(user: AuthUserInfo | None = Depends(optional_current_user)):
        if user:
            return {"hello": user.email}
        return {"hello": "anonymous"}
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.auth_models import AuthUserInfo
from backend.supabase_client import get_supabase_client

_bearer_scheme = HTTPBearer(auto_error=False)


def _user_from_token(token: str) -> AuthUserInfo:
    """
    Verify a Supabase JWT and return the user.
    Raises HTTPException 401 on any failure.
    """
    supabase = get_supabase_client()
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth is not configured on this server",
        )
    try:
        response = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = getattr(response, "user", None) if response else None
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AuthUserInfo(id=str(user.id), email=getattr(user, "email", None))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthUserInfo:
    """
    FastAPI dependency: require a valid Bearer token.
    Returns the authenticated user or raises 401.
    """
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
    """
    FastAPI dependency: return the user if a valid token is present, else None.
    Does not raise on missing or invalid tokens.
    """
    if not credentials:
        return None
    try:
        return _user_from_token(credentials.credentials)
    except HTTPException:
        return None
