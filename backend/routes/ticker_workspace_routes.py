"""
GET/PUT for per-user ticker groups and sidebar filters (public.ticker_workspaces).
User scoping is enforced in Python; PostgREST uses the service role client.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends

from backend.core.auth_deps import get_current_user
from backend.core.supabase_client import get_service_postgrest
from backend.models.auth_models import AuthUserInfo
from backend.models.ticker_workspace_models import (
    TickerWorkspaceBody,
    TickerWorkspaceResponse,
    default_ticker_workspace,
)
from backend.routes.db_error_handlers.ticker_workspace_db_error_handler import (
    TickerWorkspaceDBErrorHandler,
)

logger: logging.Logger = logging.getLogger(__name__)
tickerWorkspaceDBErrorHandler: TickerWorkspaceDBErrorHandler = (
    TickerWorkspaceDBErrorHandler(logger)
)
router = APIRouter(prefix="/user", tags=["user"])


def _parse_workspace_payload(raw: object) -> TickerWorkspaceBody | None:
    if not isinstance(raw, dict):
        return None
    try:
        return TickerWorkspaceBody.model_validate(raw)
    except Exception:
        return None


@router.get("/ticker-workspace", response_model=TickerWorkspaceResponse)
def get_ticker_workspace(
    user: AuthUserInfo = Depends(get_current_user),
):
    db = get_service_postgrest()
    try:
        resp = (
            db.from_("ticker_workspaces")
            .select("data, updated_at")
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
    except Exception as e:
        raise tickerWorkspaceDBErrorHandler.handle_db_error(
            e, "read ticker workspace"
        ) from e

    rows = resp.data or []
    if not rows:
        w = default_ticker_workspace()
        return TickerWorkspaceResponse(
            workspace=w, from_database=False, updated_at=None
        )

    row = rows[0]
    raw = row.get("data")
    parsed = _parse_workspace_payload(raw)
    if parsed is None:
        logger.warning(
            "Invalid ticker_workspaces.data for user %s; returning defaults from DB",
            user.id,
        )
        w = default_ticker_workspace()
    else:
        w = parsed

    updated: datetime | str | None = row.get("updated_at")
    updated_s = None
    if updated is not None:
        if isinstance(updated, datetime):
            updated_s = updated.isoformat()
        else:
            updated_s = str(updated)

    return TickerWorkspaceResponse(
        workspace=w, from_database=True, updated_at=updated_s
    )


@router.put("/ticker-workspace", response_model=TickerWorkspaceResponse)
def put_ticker_workspace(
    body: TickerWorkspaceBody,
    user: AuthUserInfo = Depends(get_current_user),
):
    db = get_service_postgrest()
    payload = body.model_dump(mode="json", by_alias=True)
    try:
        (
            db.from_("ticker_workspaces")
            .upsert(
                {
                    "user_id": user.id,
                    "data": payload,
                },
                on_conflict="user_id",
            )
            .execute()
        )
    except Exception as e:
        raise tickerWorkspaceDBErrorHandler.handle_db_error(
            e, "save ticker workspace"
        ) from e

    try:
        reread = (
            db.from_("ticker_workspaces")
            .select("data, updated_at")
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
    except Exception as e:
        raise tickerWorkspaceDBErrorHandler.handle_db_error(
            e, "read ticker workspace after save"
        ) from e
    reread_rows = reread.data or []
    if not reread_rows:
        return TickerWorkspaceResponse(
            workspace=body, from_database=True, updated_at=None
        )
    row = reread_rows[0]
    raw = row.get("data")
    parsed = _parse_workspace_payload(raw)
    w = parsed if parsed is not None else body
    updated: datetime | str | None = row.get("updated_at")
    updated_s = None
    if updated is not None:
        if isinstance(updated, datetime):
            updated_s = updated.isoformat()
        else:
            updated_s = str(updated)
    return TickerWorkspaceResponse(
        workspace=w, from_database=True, updated_at=updated_s
    )
