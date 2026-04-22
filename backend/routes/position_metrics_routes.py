"""
Position risk/reward metrics (TradingView-style planning).
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.market.position_metrics import (
    PositionMetricsError,
    compute_position_metrics,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data/position-metrics", tags=["position-metrics"])


class PositionMetricsRequest(BaseModel):
    side: Literal["long", "short"]
    entry_price: float = Field(..., alias="entryPrice", gt=0)
    stop_price: float = Field(..., alias="stopPrice")
    target_price: float = Field(..., alias="targetPrice")
    account_balance: float | None = Field(None, alias="accountBalance", gt=0)
    risk_percent: float | None = Field(None, alias="riskPercent", ge=0, le=100)
    risk_amount: float | None = Field(None, alias="riskAmount", gt=0)
    quantity: float | None = Field(None, alias="quantity", gt=0)
    leverage: float = Field(1.0, gt=0, le=1000)

    class Config:
        populate_by_name = True


class PositionMetricsResponse(BaseModel):
    risk_price_distance: float = Field(..., alias="riskPriceDistance")
    reward_price_distance: float = Field(..., alias="rewardPriceDistance")
    risk_reward_ratio: float | None = Field(None, alias="riskRewardRatio")
    quantity: float | None = Field(None, alias="quantity")
    profit_at_target: float | None = Field(None, alias="profitAtTarget")
    loss_at_stop: float | None = Field(None, alias="lossAtStop")
    quantity_capped_by_leverage: bool = Field(..., alias="quantityCappedByLeverage")

    class Config:
        populate_by_name = True


@router.post(
    "",
    response_model=PositionMetricsResponse,
    response_model_by_alias=True,
)
def post_position_metrics(body: PositionMetricsRequest) -> PositionMetricsResponse:
    try:
        r = compute_position_metrics(
            body.side,
            body.entry_price,
            body.stop_price,
            body.target_price,
            account_balance=body.account_balance,
            risk_percent=body.risk_percent,
            risk_amount=body.risk_amount,
            quantity=body.quantity,
            leverage=body.leverage,
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

    return PositionMetricsResponse(
        risk_price_distance=r.risk_price_distance,
        reward_price_distance=r.reward_price_distance,
        risk_reward_ratio=r.risk_reward_ratio,
        quantity=r.quantity,
        profit_at_target=r.profit_at_target,
        loss_at_stop=r.loss_at_stop,
        quantity_capped_by_leverage=r.quantity_capped_by_leverage,
    )
