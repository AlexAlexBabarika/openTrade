"""Saved backtest-strategy CRUD endpoints.

Mirrors the user-scripts resource (`script_routes`) over a dedicated
``user_strategies`` table. Execution is NOT here: a strategy runs through
``POST /backtests/run`` (single run) or ``POST /sweeps`` (optimization).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.auth_deps import get_current_user
from backend.core.supabase_client import get_service_postgrest
from backend.models.auth_models import AuthUserInfo
from backend.models.strategy_models import (
    StrategyCreateRequest,
    StrategyInfo,
    StrategyListResponse,
    StrategyUpdateRequest,
)
from backend.routes.db_error_handlers.strategy_db_error_handler import (
    StrategyDBErrorHandler,
)

logger: logging.Logger = logging.getLogger(__name__)
strategyDBErrorHandler: StrategyDBErrorHandler = StrategyDBErrorHandler(logger)
router = APIRouter(prefix="/strategies", tags=["strategies"])

_TABLE = "user_strategies"


def _row_to_info(row: dict) -> StrategyInfo:
    return StrategyInfo(
        id=str(row["id"]),
        name=row["name"],
        code=row["code"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


@router.get("", response_model=StrategyListResponse)
def list_strategies(
    user: AuthUserInfo = Depends(get_current_user),
) -> StrategyListResponse:
    db = get_service_postgrest()
    try:
        resp = (
            db.from_(_TABLE)
            .select("id, name, code, created_at, updated_at")
            .eq("user_id", user.id)
            .order("updated_at", desc=True)
            .execute()
        )
    except Exception as e:
        raise strategyDBErrorHandler.handle_db_error(e, "list strategies") from e
    return StrategyListResponse(strategies=[_row_to_info(r) for r in resp.data or []])


@router.post("", response_model=StrategyInfo, status_code=status.HTTP_201_CREATED)
def create_strategy(
    body: StrategyCreateRequest,
    user: AuthUserInfo = Depends(get_current_user),
) -> StrategyInfo:
    db = get_service_postgrest()
    try:
        resp = (
            db.from_(_TABLE)
            .insert(
                {
                    "user_id": user.id,
                    "name": body.name,
                    "code": body.code,
                }
            )
            .execute()
        )
    except Exception as e:
        raise strategyDBErrorHandler.handle_db_error(e, "create strategy") from e
    row = resp.data[0] if resp.data else None
    if not row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store strategy (no response).",
        )
    return _row_to_info(row)


@router.get("/{strategy_id}", response_model=StrategyInfo)
def get_strategy(
    strategy_id: str,
    user: AuthUserInfo = Depends(get_current_user),
) -> StrategyInfo:
    db = get_service_postgrest()
    try:
        resp = (
            db.from_(_TABLE)
            .select("id, name, code, created_at, updated_at")
            .eq("user_id", user.id)
            .eq("id", strategy_id)
            .limit(1)
            .execute()
        )
    except Exception as e:
        raise strategyDBErrorHandler.handle_db_error(e, "read strategy") from e
    rows = resp.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )
    return _row_to_info(rows[0])


@router.put("/{strategy_id}", response_model=StrategyInfo)
def update_strategy(
    strategy_id: str,
    body: StrategyUpdateRequest,
    user: AuthUserInfo = Depends(get_current_user),
) -> StrategyInfo:
    patch: dict[str, str] = {}
    if body.name is not None:
        patch["name"] = body.name
    if body.code is not None:
        patch["code"] = body.code
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'name' or 'code' must be provided.",
        )

    db = get_service_postgrest()
    try:
        resp = (
            db.from_(_TABLE)
            .update(patch)
            .eq("user_id", user.id)
            .eq("id", strategy_id)
            .execute()
        )
    except Exception as e:
        raise strategyDBErrorHandler.handle_db_error(e, "update strategy") from e
    rows = resp.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )
    return _row_to_info(rows[0])


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_strategy(
    strategy_id: str,
    user: AuthUserInfo = Depends(get_current_user),
) -> None:
    db = get_service_postgrest()
    try:
        resp = (
            db.from_(_TABLE)
            .delete()
            .eq("user_id", user.id)
            .eq("id", strategy_id)
            .execute()
        )
    except Exception as e:
        raise strategyDBErrorHandler.handle_db_error(e, "delete strategy") from e
    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )
