"""CRUD for per-user chart symbol comparisons (public.symbol_comparisons)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.auth_deps import get_current_user
from backend.core.supabase_client import get_service_postgrest
from backend.models.auth_models import AuthUserInfo
from backend.models.comparison_models import (
    ComparisonCreateRequest,
    ComparisonInfo,
    ComparisonListResponse,
    ComparisonUpdateRequest,
)
from backend.routes.db_error_handlers.comparison_db_error_handler import (
    ComparisonDBErrorHandler,
)

logger: logging.Logger = logging.getLogger(__name__)
comparisonDBErrorHandler: ComparisonDBErrorHandler = ComparisonDBErrorHandler(logger)
router = APIRouter(prefix="/user/comparisons", tags=["comparisons"])

MAX_COMPARISONS_PER_MAIN_SYMBOL = 4

_SELECT_COLS = "id, main_symbol, comparison_symbol, provider, color, series_type, position, created_at"


def _row_to_info(row: dict) -> ComparisonInfo:
    return ComparisonInfo(
        id=str(row["id"]),
        main_symbol=row["main_symbol"],
        comparison_symbol=row["comparison_symbol"],
        provider=row["provider"],
        color=row["color"],
        series_type=row["series_type"],
        position=int(row.get("position") or 0),
        created_at=str(row["created_at"]),
    )


@router.get("", response_model=ComparisonListResponse)
def list_comparisons(
    main_symbol: str = Query(..., min_length=1, max_length=64),
    user: AuthUserInfo = Depends(get_current_user),
) -> ComparisonListResponse:
    db = get_service_postgrest()
    try:
        resp = (
            db.from_("symbol_comparisons")
            .select(_SELECT_COLS)
            .eq("user_id", user.id)
            .eq("main_symbol", main_symbol)
            .order("position", desc=False)
            .order("created_at", desc=False)
            .execute()
        )
    except Exception as e:
        raise comparisonDBErrorHandler.handle_db_error(e, "list comparisons") from e
    return ComparisonListResponse(
        comparisons=[_row_to_info(r) for r in resp.data or []]
    )


@router.post("", response_model=ComparisonInfo, status_code=status.HTTP_201_CREATED)
def create_comparison(
    body: ComparisonCreateRequest,
    user: AuthUserInfo = Depends(get_current_user),
) -> ComparisonInfo:
    if body.comparison_symbol.strip().upper() == body.main_symbol.strip().upper():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comparison symbol must differ from the main symbol.",
        )

    db = get_service_postgrest()
    try:
        existing = (
            db.from_("symbol_comparisons")
            .select("id, position")
            .eq("user_id", user.id)
            .eq("main_symbol", body.main_symbol)
            .order("position", desc=True)
            .execute()
        )
    except Exception as e:
        raise comparisonDBErrorHandler.handle_db_error(e, "count comparisons") from e

    rows = existing.data or []
    if len(rows) >= MAX_COMPARISONS_PER_MAIN_SYMBOL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Maximum {MAX_COMPARISONS_PER_MAIN_SYMBOL} comparisons per symbol.",
        )
    next_position = (rows[0]["position"] + 1) if rows else 0

    try:
        resp = (
            db.from_("symbol_comparisons")
            .insert(
                {
                    "user_id": user.id,
                    "main_symbol": body.main_symbol,
                    "comparison_symbol": body.comparison_symbol,
                    "provider": body.provider,
                    "color": body.color,
                    "series_type": body.series_type,
                    "position": next_position,
                }
            )
            .execute()
        )
    except Exception as e:
        raise comparisonDBErrorHandler.handle_db_error(e, "create comparison") from e

    row = resp.data[0] if resp.data else None
    if not row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store comparison (no response).",
        )
    return _row_to_info(row)


@router.patch("/{comparison_id}", response_model=ComparisonInfo)
def update_comparison(
    comparison_id: str,
    body: ComparisonUpdateRequest,
    user: AuthUserInfo = Depends(get_current_user),
) -> ComparisonInfo:
    patch: dict[str, object] = {}
    if body.color is not None:
        patch["color"] = body.color
    if body.series_type is not None:
        patch["series_type"] = body.series_type
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'color' or 'series_type' must be provided.",
        )

    db = get_service_postgrest()
    try:
        resp = (
            db.from_("symbol_comparisons")
            .update(patch)
            .eq("user_id", user.id)
            .eq("id", comparison_id)
            .execute()
        )
    except Exception as e:
        raise comparisonDBErrorHandler.handle_db_error(e, "update comparison") from e
    rows = resp.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comparison {comparison_id} not found",
        )
    return _row_to_info(rows[0])


@router.delete("/{comparison_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comparison(
    comparison_id: str,
    user: AuthUserInfo = Depends(get_current_user),
) -> None:
    db = get_service_postgrest()
    try:
        resp = (
            db.from_("symbol_comparisons")
            .delete()
            .eq("user_id", user.id)
            .eq("id", comparison_id)
            .execute()
        )
    except Exception as e:
        raise comparisonDBErrorHandler.handle_db_error(e, "delete comparison") from e
    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comparison {comparison_id} not found",
        )
