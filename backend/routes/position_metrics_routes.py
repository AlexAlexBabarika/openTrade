"""
Position risk/reward metrics (TradingView-style planning).
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from backend.market.position_metrics import (
    PositionMetricsError,
    compute_risk_reward_ratio,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data/position-metrics", tags=["position-metrics"])


class PositionMetricsRequest(BaseModel):
    side: Literal["long", "short"]
    entry_price: float = Field(..., alias="entryPrice", gt=0)
    stop_price: float = Field(..., alias="stopPrice")
    target_price: float = Field(..., alias="targetPrice")

    model_config = ConfigDict(populate_by_name=True)


class PositionMetricsResponse(BaseModel):
    risk_reward_ratio: float | None = Field(None, alias="riskRewardRatio")

    model_config = ConfigDict(populate_by_name=True)


@router.post(
    "",
    response_model=PositionMetricsResponse,
    response_model_by_alias=True,
)
def post_position_metrics(body: PositionMetricsRequest) -> PositionMetricsResponse:
    try:
        rr = compute_risk_reward_ratio(
            body.side,
            body.entry_price,
            body.stop_price,
            body.target_price,
        )
    except PositionMetricsError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except Exception:
        logger.exception("position metrics failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="position metrics failed",
        ) from None

    return PositionMetricsResponse(riskRewardRatio=rr)
