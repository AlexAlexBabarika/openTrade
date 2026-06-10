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
    """A submitted order. ``id`` and ``submitted_index`` are set by the broker.

    ``symbol`` is ``None`` in single-symbol runs (the run's one instrument is
    implicit) and required by the multi-asset broker."""

    side: Side
    quantity: float
    type: OrderType = OrderType.MARKET
    limit: float | None = None
    stop: float | None = None
    id: int | None = None
    submitted_index: int | None = None
    triggered: bool = False  # set once a stop/stop-limit's stop has been hit
    symbol: str | None = None


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
    symbol: str | None = None


@dataclass(frozen=True, slots=True)
class Position:
    """A signed position: positive is long, negative short. ``avg_price`` is the
    average entry price of the currently open quantity (0 when flat)."""

    quantity: float = 0.0
    avg_price: float = 0.0


@dataclass(frozen=True, slots=True)
class Trade:
    """A matched round trip: position leaves flat, then returns to flat.

    ``direction`` is the entry side (``BUY`` = long, ``SELL`` = short).
    ``quantity`` is the total quantity entered. ``entry_price``/``exit_price`` are
    quantity-weighted. ``pnl`` is realized currency P&L net of commissions, and
    reconciles with the portfolio's realized P&L. ``pnl_pct`` is ``pnl`` over the
    entry notional. ``bars_held`` is ``exit_index - entry_index`` in bars.
    """

    direction: Side
    quantity: float
    entry_time: datetime
    exit_time: datetime
    entry_index: int
    exit_index: int
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    bars_held: int


@dataclass(frozen=True, slots=True)
class EquityPoint:
    """One sample of the equity curve, marked to a bar's close.

    ``equity == cash + holdings``. ``holdings`` is the signed marked value of the
    open position (negative when short)."""

    time: datetime
    equity: float
    cash: float
    holdings: float


@dataclass(frozen=True, slots=True)
class Drawdown:
    """A peak-to-recovery drawdown episode. ``depth`` is a negative fraction;
    ``length`` is in bars from the prior peak to recovery (or to the end if the
    episode never recovered, in which case ``recovery`` is ``None``)."""

    start: datetime
    trough: datetime
    recovery: datetime | None
    depth: float
    length: int


@dataclass(frozen=True, slots=True)
class RunMeta:
    """Identity and provenance of a single run. ``run_id`` is a fresh UUID hex.
    ``started_at``/``finished_at`` are wall-clock and do not affect determinism."""

    run_id: str
    seed: int
    starting_cash: float
    started_at: datetime
    finished_at: datetime
    strategy_id: str | None = None
    params: dict | None = None
    data_version: str | None = None


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """The complete canonical record produced by a run."""

    meta: RunMeta
    bars: list[Bar]
    orders: list[Order]
    fills: list[Fill]
    equity_curve: list[EquityPoint]
    trades: list[Trade]
    metrics: Metrics


@dataclass(frozen=True, slots=True)
class Metrics:
    """The full metrics taxonomy, pre-computed for the dashboard.

    Fields that are undefined for a run (e.g. trade stats when there are no
    trades) are ``None``."""

    # Return
    total_return: float
    cagr: float
    avg_annual_return: float
    best_month: float | None
    worst_month: float | None
    best_year: float | None
    worst_year: float | None
    pct_positive_months: float | None
    pct_positive_years: float | None
    # Risk-adjusted
    sharpe: float
    sortino: float
    calmar: float
    information_ratio: float
    # Drawdown
    max_drawdown: float
    max_drawdown_length: int
    avg_drawdown: float
    time_underwater: float
    recovery_factor: float
    # Trade quality
    win_rate: float | None
    avg_win: float | None
    avg_loss: float | None
    win_loss_ratio: float | None
    profit_factor: float | None
    expectancy: float | None
    max_consecutive_wins: int
    max_consecutive_losses: int
    avg_bars_held_winners: float | None
    avg_bars_held_losers: float | None
    # Exposure
    pct_time_in_market: float
    avg_position_pct: float
    max_leverage: float
