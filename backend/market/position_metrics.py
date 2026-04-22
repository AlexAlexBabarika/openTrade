"""
Pure position / risk-reward metrics for long and short trade planning.

Used by POST /data/position-metrics; kept free of FastAPI imports for unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Side = Literal["long", "short"]


class PositionMetricsError(ValueError):
    """Invalid price levels for the given side."""


@dataclass(frozen=True)
class PositionMetricsResult:
    risk_price_distance: float
    reward_price_distance: float
    risk_reward_ratio: float | None
    quantity: float | None
    profit_at_target: float | None
    loss_at_stop: float | None
    quantity_capped_by_leverage: bool


def _validate_levels(side: Side, entry: float, stop: float, target: float) -> None:
    if side == "long":
        if not (stop < entry < target):
            raise PositionMetricsError(
                "long position requires stop_price < entry_price < target_price"
            )
    else:
        if not (target < entry < stop):
            raise PositionMetricsError(
                "short position requires target_price < entry_price < stop_price"
            )


def _risk_reward_per_unit(
    side: Side, entry: float, stop: float, target: float
) -> tuple[float, float]:
    if side == "long":
        risk = entry - stop
        reward = target - entry
    else:
        risk = stop - entry
        reward = entry - target
    return risk, reward


def compute_position_metrics(
    side: Side,
    entry_price: float,
    stop_price: float,
    target_price: float,
    *,
    account_balance: float | None = None,
    risk_percent: float | None = None,
    risk_amount: float | None = None,
    quantity: float | None = None,
    leverage: float = 1.0,
) -> PositionMetricsResult:
    """
    risk_percent: portion of account (0–100) used when risk_amount is not set.
    quantity: if set, skips risk-based sizing; leverage cap still applies when account_balance is set.
    leverage: max notional = account_balance * leverage (when account_balance is set).
    """
    if entry_price <= 0:
        raise PositionMetricsError("entry_price must be positive")
    if leverage <= 0:
        raise PositionMetricsError("leverage must be positive")
    if risk_percent is not None and (risk_percent < 0 or risk_percent > 100):
        raise PositionMetricsError("risk_percent must be between 0 and 100")

    _validate_levels(side, entry_price, stop_price, target_price)
    risk_pu, reward_pu = _risk_reward_per_unit(
        side, entry_price, stop_price, target_price
    )
    if risk_pu <= 0 or reward_pu <= 0:
        raise PositionMetricsError("invalid risk or reward distance")

    rr: float | None = None
    if risk_pu > 0:
        rr = reward_pu / risk_pu

    qty: float | None = None
    capped = False

    if quantity is not None:
        if quantity <= 0:
            raise PositionMetricsError("quantity must be positive when set")
        qty = quantity
    else:
        ra: float | None = risk_amount
        if ra is None and account_balance is not None and risk_percent is not None:
            ra = account_balance * (risk_percent / 100.0)
        if ra is not None:
            if ra <= 0:
                raise PositionMetricsError("computed risk_amount must be positive")
            qty = ra / risk_pu

    if qty is not None and account_balance is not None:
        max_notional = account_balance * leverage
        max_qty = max_notional / entry_price
        if qty > max_qty:
            qty = max_qty
            capped = True

    profit: float | None = None
    loss: float | None = None
    if qty is not None:
        profit = qty * reward_pu
        loss = qty * risk_pu

    return PositionMetricsResult(
        risk_price_distance=risk_pu,
        reward_price_distance=reward_pu,
        risk_reward_ratio=rr,
        quantity=qty,
        profit_at_target=profit,
        loss_at_stop=loss,
        quantity_capped_by_leverage=capped,
    )
