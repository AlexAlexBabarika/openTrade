"""The portfolio strategy context (``ctx``) with universe-gated visibility.

Mirrors the single-symbol ``Context`` API but every data read and order is
keyed by symbol, and both are gated on current universe membership: a symbol
outside its membership window at the current bar cannot be read or traded
(``UniverseError``), which is what keeps join/leave honest. Per-symbol bar
reads go through the same look-ahead-guarded views as single-symbol runs.

The engine advances the context each event via the underscore ``_set_event``
method; strategy code cannot reach it (the AST guard rejects underscore
attribute access).
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import TYPE_CHECKING, Iterator, NoReturn

from backend.backtesting.context import BarsView
from backend.backtesting.errors import ConstraintError, EngineError, UniverseError
from backend.backtesting.multi.constraints import (
    ConstraintEvent,
    Constraints,
    apply_constraints,
)
from backend.backtesting.types import Order, OrderType, Position, Side

if TYPE_CHECKING:
    from backend.backtesting.multi.book import PortfolioBook
    from backend.backtesting.multi.broker import MultiBroker
    from backend.backtesting.multi.timeline import MultiBarEvent, MultiBarSeries


# Value drifts below this (in currency) are float dust, never worth an order.
_VALUE_EPS = 1e-9


class UniverseBarsView:
    """``ctx.bars``: per-symbol bar history, readable only while the symbol is
    in the universe. Iteration yields the currently active symbols."""

    def __init__(self, series: "MultiBarSeries") -> None:
        self._series = series
        self._active: tuple[str, ...] = ()

    def _set_active(self, active: tuple[str, ...]) -> None:
        self._active = active

    def __getitem__(self, symbol: str) -> BarsView:
        if symbol not in self._active:
            raise UniverseError(f"{symbol!r} is not in the universe at the current bar")
        return self._series[symbol]

    def __contains__(self, symbol: str) -> bool:
        return symbol in self._active

    def __iter__(self) -> Iterator[str]:
        return iter(self._active)

    def __len__(self) -> int:
        return len(self._active)


class PositionLookup:
    """``ctx.position``: callable per-symbol position accessor.

    Misuse guard: single-symbol strategies read ``ctx.position.quantity``.
    A portfolio holds one position per symbol, so attribute access here
    raises a guided ``EngineError`` instead of the opaque AttributeError
    Python would otherwise produce (method attribute lookup falls through to
    the underlying function, yielding "'function' object has no attribute").
    """

    def __init__(self, book: "PortfolioBook") -> None:
        self._book = book

    def __call__(self, symbol: str) -> Position:
        return self._book.position(symbol)

    def __getattr__(self, name: str) -> "NoReturn":
        raise EngineError(
            f"ctx.position has no attribute {name!r}: portfolio strategies "
            "hold one position per symbol — use ctx.position(symbol)."
            f"{name}, e.g. ctx.position('AAPL').quantity"
        )


class PortfolioContext:
    """What portfolio strategy code receives each bar as ``ctx``."""

    def __init__(
        self,
        series: "MultiBarSeries",
        *,
        broker: "MultiBroker",
        book: "PortfolioBook",
        marks: dict[str, float],
        rng: random.Random | None = None,
        params: dict | None = None,
        constraints: Constraints | None = None,
    ) -> None:
        self._broker = broker
        self._book = book
        self._marks = marks
        self._constraints = constraints
        self._constraint_log: list[ConstraintEvent] = []
        self._rng = rng
        self._params = dict(params) if params else {}
        self._bars_view = UniverseBarsView(series)
        self._position_lookup = PositionLookup(book)
        self._event: "MultiBarEvent | None" = None
        self._index = -1
        self._active: tuple[str, ...] = ()
        self._targets: dict[str, float] = {}
        self.state: dict = {}
        """Free-form per-run scratch space for strategy state across bars."""

    def _set_event(
        self, event: "MultiBarEvent", index: int, active: tuple[str, ...]
    ) -> None:
        self._event = event
        self._index = index
        self._active = active
        self._bars_view._set_active(active)

    def _require_event(self) -> "MultiBarEvent":
        if self._event is None:
            raise EngineError("no bar has been consumed yet")
        return self._event

    def _drop_target(self, symbol: str) -> None:
        """Engine hook: a symbol leaving the universe clears its target."""
        self._targets.pop(symbol, None)

    @property
    def params(self) -> dict:
        """The concrete parameter values for this run (empty if unparameterized)."""
        return self._params

    @property
    def random(self) -> random.Random:
        """The run's seeded RNG. Strategy code must use this, never the global
        ``random`` module, so runs stay deterministic."""
        if self._rng is None:
            raise EngineError("no rng bound to this context")
        return self._rng

    @property
    def time(self) -> datetime:
        return self._require_event().time

    @property
    def universe(self) -> tuple[str, ...]:
        """Symbols that are members of the universe at the current bar, sorted."""
        return self._active

    @property
    def bars(self) -> UniverseBarsView:
        return self._bars_view

    @property
    def cash(self) -> float:
        return self._book.cash

    @property
    def equity(self) -> float:
        return self._book.equity(self._marks)

    @property
    def positions(self) -> dict[str, Position]:
        """Non-flat positions keyed by symbol, in sorted symbol order."""
        return self._book.open_positions

    @property
    def position(self) -> PositionLookup:
        """Per-symbol position accessor: ``ctx.position('AAPL').quantity``."""
        return self._position_lookup

    @property
    def weights(self) -> dict[str, float]:
        """Current signed weight of each open position as a fraction of equity."""
        return self._book.weights(self._marks)

    @property
    def targets(self) -> dict[str, float]:
        """The declared target weights (a copy; set via ``target_weight``)."""
        return dict(self._targets)

    @property
    def constraints(self) -> Constraints | None:
        """The run's hard constraints, if any (declared at backtest config)."""
        return self._constraints

    @property
    def constraint_log(self) -> list[ConstraintEvent]:
        """Every constraint binding so far, in occurrence order (a copy)."""
        return list(self._constraint_log)

    def target_weight(self, symbol: str, weight: float) -> None:
        """Declare the intended signed weight of ``symbol`` as a fraction of
        equity. Takes effect when ``rebalance()`` is called; persists across
        bars until overwritten or the symbol leaves the universe."""
        if symbol not in self._active:
            raise UniverseError(
                f"cannot target {symbol!r}: not in the universe at the current bar"
            )
        self._targets[symbol] = float(weight)

    def rebalance(self, *, min_trade_value: float = 0.0) -> list[Order]:
        """Submit market orders moving the book toward the declared targets.

        Each targeted symbol's drift (target value minus current marked value)
        becomes one market order, sized at the symbol's last known close and
        filled next bar through the normal cost-paying path. Drifts smaller
        than ``min_trade_value`` (in currency) are skipped to avoid fee bleed,
        and a targeted symbol with no revealed bar yet is deferred — it is
        sized on a later rebalance once a mark exists. Returns the submitted
        orders.

        When the run declares hard constraints, the effective targets are
        clamped through them first (the declared targets are never rewritten)
        and every binding — including min-trade-size skips — is recorded in
        ``constraint_log``."""
        equity = self._book.equity(self._marks)
        effective = {
            symbol: weight
            for symbol, weight in sorted(self._targets.items())
            if symbol in self._active
        }
        if self._constraints is not None:
            effective, events = apply_constraints(
                effective,
                constraints=self._constraints,
                equity=equity,
                time=self.time,
            )
            self._constraint_log.extend(events)
            min_trade_value = max(min_trade_value, self._constraints.min_trade_value)

        orders: list[Order] = []
        for symbol in sorted(effective):
            mark = self._marks.get(symbol)
            if mark is None or mark <= 0.0:
                continue  # no revealed bar to size against yet
            target_value = effective[symbol] * equity
            current_value = self._book.position(symbol).quantity * mark
            delta = target_value - current_value
            if abs(delta) < _VALUE_EPS:
                continue
            if abs(delta) < min_trade_value:
                self._constraint_log.append(
                    ConstraintEvent(
                        time=self.time,
                        constraint="min_trade_value",
                        symbol=symbol,
                        requested=delta,
                        applied=None,
                        detail=(
                            f"{symbol} drift of {delta:+.2f} below the "
                            f"{min_trade_value:.2f} minimum trade size; skipped"
                        ),
                    )
                )
                continue
            side = Side.BUY if delta > 0 else Side.SELL
            orders.append(
                self._submit(
                    symbol, side, abs(delta) / mark, OrderType.MARKET, None, None
                )
            )
        return orders

    def buy(
        self,
        symbol: str,
        quantity: float | None = None,
        *,
        type: OrderType = OrderType.MARKET,
        limit: float | None = None,
        stop: float | None = None,
    ) -> Order:
        if quantity is None:
            raise EngineError(
                "portfolio orders are per-symbol: ctx.buy('AAPL', quantity) "
                f"— got ctx.buy({symbol!r})"
            )
        return self._submit(symbol, Side.BUY, quantity, type, limit, stop)

    def sell(
        self,
        symbol: str,
        quantity: float | None = None,
        *,
        type: OrderType = OrderType.MARKET,
        limit: float | None = None,
        stop: float | None = None,
    ) -> Order:
        if quantity is None:
            raise EngineError(
                "portfolio orders are per-symbol: ctx.sell('AAPL', quantity) "
                f"— got ctx.sell({symbol!r})"
            )
        return self._submit(symbol, Side.SELL, quantity, type, limit, stop)

    def _submit(
        self,
        symbol: str,
        side: Side,
        quantity: float,
        type: OrderType,
        limit: float | None,
        stop: float | None,
    ) -> Order:
        if not isinstance(symbol, str):
            raise EngineError(
                "portfolio orders are per-symbol: the first argument must be "
                f"a symbol string, e.g. ctx.buy('AAPL', quantity) — got {symbol!r}"
            )
        if symbol not in self._active:
            raise UniverseError(
                f"cannot trade {symbol!r}: not in the universe at the current bar"
            )
        if self._constraints is not None and symbol in self._constraints.no_trade:
            raise ConstraintError(f"{symbol!r} is on the no-trade list")
        order = Order(
            side=side,
            quantity=quantity,
            type=type,
            limit=limit,
            stop=stop,
            symbol=symbol,
        )
        return self._broker.submit(order, event_index=self._index)
