"""Core value types for the backtesting engine.

Foundational, immutable building blocks the event loop consumes. Order, fill,
and position types are defined alongside the tasks that exercise them so every
field traces to a behaviour under test.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    MOO = "moo"  # market-on-open
    MOC = "moc"  # market-on-close


@dataclass(frozen=True, slots=True)
class Bar:
    """A single closed OHLCV bar. ``time`` is the bar's close timestamp (UTC)."""

    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class BarEvent:
    """A ``BAR`` event: a newly closed bar entering the event loop."""

    bar: Bar

    @property
    def time(self) -> datetime:
        return self.bar.time


@dataclass(slots=True)
class Order:
    """A submitted order. ``id`` and ``submitted_index`` are set by the broker."""

    side: Side
    quantity: float
    type: OrderType = OrderType.MARKET
    limit: float | None = None
    stop: float | None = None
    id: int | None = None
    submitted_index: int | None = None


@dataclass(frozen=True, slots=True)
class Fill:
    """A completed fill.

    ``price`` is the effective fill price (it already includes slippage and
    half-spread); ``reference_price`` is the pre-cost close-to-close price. The
    cost fields are currency totals for reporting and cash accounting.
    """

    order_id: int
    side: Side
    quantity: float
    price: float
    reference_price: float
    slippage: float
    spread_cost: float
    commission: float
    submitted_index: int
    fill_index: int
    reason: str


@dataclass(frozen=True, slots=True)
class Position:
    """A signed position: positive is long, negative short. ``avg_price`` is the
    average entry price of the currently open quantity (0 when flat)."""

    quantity: float = 0.0
    avg_price: float = 0.0


@dataclass(frozen=True, slots=True)
class EquityPoint:
    """One sample of the equity curve, marked to a bar's close."""

    time: datetime
    equity: float


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """The complete record produced by a run."""

    orders: list[Order]
    fills: list[Fill]
    equity_curve: list[EquityPoint]
