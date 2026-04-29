"""
Pure position risk/reward calculation for long and short trade planning.

Used by POST /data/position-metrics; kept free of FastAPI imports for unit tests.
"""

from __future__ import annotations

from typing import Literal

Side = Literal["long", "short"]


class PositionMetricsError(ValueError):
    """Invalid price levels for the given side."""


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


def compute_risk_reward_ratio(
    side: Side,
    entry_price: float,
    stop_price: float,
    target_price: float,
) -> float:
    if entry_price <= 0:
        raise PositionMetricsError("entry_price must be positive")

    _validate_levels(side, entry_price, stop_price, target_price)

    if side == "long":
        risk = entry_price - stop_price
        reward = target_price - entry_price
    else:
        risk = stop_price - entry_price
        reward = entry_price - target_price

    if risk <= 0 or reward <= 0:
        raise PositionMetricsError("invalid risk or reward distance")

    return reward / risk
