"""Rebalance policies: *when* to trade toward targets.

``ctx.rebalance()`` decides what to trade; a policy decides whether this bar
is a trading moment. Each policy is a small object whose
``should_rebalance(ctx)`` reads only public context state (``time``,
``weights``, ``targets``), so policies compose with any sizer and are usable
from sandboxed strategy code.

Periodic boundaries are detected causally — a period's *first* bar triggers,
because the last bar of a period is unknowable until after it has passed.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from backend.backtesting.multi.context import PortfolioContext


_PERIOD_KEYS: dict[str, Callable[[datetime], tuple]] = {
    "daily": lambda t: (t.year, t.month, t.day),
    "weekly": lambda t: tuple(t.isocalendar()[:2]),
    "monthly": lambda t: (t.year, t.month),
}


class PeriodicRebalance:
    """Fires on the first bar of each new calendar period (and on the very
    first bar seen, establishing the initial allocation)."""

    def __init__(self, period: str = "monthly") -> None:
        if period not in _PERIOD_KEYS:
            raise ValueError(
                f"unknown period {period!r}; expected one of {sorted(_PERIOD_KEYS)}"
            )
        self._key = _PERIOD_KEYS[period]
        self._last: tuple | None = None

    def should_rebalance(self, ctx: "PortfolioContext") -> bool:
        key = self._key(ctx.time)
        if key != self._last:
            self._last = key
            return True
        return False


class ThresholdRebalance:
    """Fires when any *targeted* symbol's actual weight drifts more than
    ``max_drift`` from its target. Held symbols without a target are
    unmanaged — rebalance would not touch them, so they never trigger one."""

    def __init__(self, max_drift: float) -> None:
        self._max_drift = max_drift

    def drift(self, ctx: "PortfolioContext") -> float:
        weights = ctx.weights
        return max(
            (
                abs(weights.get(symbol, 0.0) - target)
                for symbol, target in ctx.targets.items()
            ),
            default=0.0,
        )

    def should_rebalance(self, ctx: "PortfolioContext") -> bool:
        return self.drift(ctx) > self._max_drift


class SignalRebalance:
    """Fires whenever the declared targets change from the last bar seen."""

    def __init__(self) -> None:
        self._last: dict[str, float] = {}

    def should_rebalance(self, ctx: "PortfolioContext") -> bool:
        targets = ctx.targets
        changed = targets != self._last
        self._last = targets
        return changed
