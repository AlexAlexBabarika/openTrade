"""The strategy-facing context (``ctx``) and its look-ahead guard.

``BarSeries`` is a cursor over the full ordered bar list. The engine calls
``advance()`` once per consumed BAR event to reveal the next bar; strategy code
only ever sees ``ctx.bars``, which bounds every read against the revealed
cursor. Reading at or past the next index is, by definition, look-ahead and
raises ``LookAheadError`` — there is no path to a silent future read.
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import TYPE_CHECKING, Iterator

from backend.backtesting.errors import EngineError, LookAheadError
from backend.backtesting.types import Bar, Order, OrderType, Position, Side

if TYPE_CHECKING:
    from backend.backtesting.orders import Broker
    from backend.backtesting.portfolio import Portfolio


class BarSeries:
    """History of bars revealed so far, addressable like a sequence.

    ``len`` is the number of revealed bars; index ``0`` is the first bar and
    index ``-1`` (or ``len - 1``) is the current bar. Any forward read raises.
    """

    def __init__(self, bars: list[Bar]) -> None:
        self._bars = bars
        self._cursor = -1  # index of the current bar; -1 = nothing revealed

    def advance(self) -> None:
        """Reveal the next bar. Called by the engine per consumed BAR event."""
        self._cursor += 1

    @property
    def current(self) -> Bar:
        if self._cursor < 0:
            raise EngineError("no bar has been consumed yet")
        return self._bars[self._cursor]

    @property
    def index(self) -> int:
        """Index of the current (most recently revealed) bar."""
        return self._cursor

    def __len__(self) -> int:
        return self._cursor + 1

    def __getitem__(self, key: int) -> Bar:
        revealed = self._cursor + 1
        index = key + revealed if key < 0 else key
        if index > self._cursor:
            raise LookAheadError(
                f"bar index {key} is in the future "
                f"(current bar index {self._cursor})"
            )
        if index < 0:
            raise IndexError(f"bar index {key} out of range")
        return self._bars[index]

    def __iter__(self) -> Iterator[Bar]:
        return iter(self._bars[: self._cursor + 1])


class BarsView:
    """Read-only, look-ahead-guarded view of revealed bars given to strategies.

    Delegates reads to the engine's ``BarSeries`` (so the forward-read guard
    still applies) but exposes no cursor control: there is no ``advance`` here,
    and the underscore-named ``_series`` reference is unreachable from strategy
    code because the AST guard rejects underscore attribute access.
    """

    def __init__(self, series: BarSeries) -> None:
        self._series = series

    def __getitem__(self, key: int) -> Bar:
        return self._series[key]

    def __len__(self) -> int:
        return len(self._series)

    def __iter__(self) -> Iterator[Bar]:
        return iter(self._series)

    @property
    def index(self) -> int:
        return self._series.index


class Context:
    """What user strategy code receives each bar as ``ctx``."""

    def __init__(
        self,
        bars: BarSeries,
        broker: "Broker | None" = None,
        portfolio: "Portfolio | None" = None,
        rng: random.Random | None = None,
        params: dict | None = None,
    ) -> None:
        self._bars = bars
        self._broker = broker
        self._portfolio = portfolio
        self._rng = rng
        self._params = dict(params) if params else {}
        self._bars_view = BarsView(bars)
        self.state: dict = {}
        """Free-form per-run scratch space for strategy state across bars."""

    @property
    def params(self) -> dict:
        """The concrete parameter values for this run (empty if unparameterized).
        Strategy code reads ``ctx.params["fast_ma"]`` etc."""
        return self._params

    @property
    def random(self) -> random.Random:
        """The run's seeded RNG. Strategy code must use this, never the global
        ``random`` module, so runs stay deterministic."""
        if self._rng is None:
            raise EngineError("no rng bound to this context")
        return self._rng

    @property
    def bars(self) -> BarsView:
        return self._bars_view

    @property
    def time(self) -> datetime:
        return self._bars.current.time

    @property
    def position(self) -> Position:
        return self._require_portfolio().position

    @property
    def cash(self) -> float:
        return self._require_portfolio().cash

    @property
    def equity(self) -> float:
        return self._require_portfolio().equity(self._bars.current.close)

    def _require_portfolio(self) -> "Portfolio":
        if self._portfolio is None:
            raise EngineError("no portfolio bound to this context")
        return self._portfolio

    def buy(
        self,
        quantity: float,
        *,
        type: OrderType = OrderType.MARKET,
        limit: float | None = None,
        stop: float | None = None,
    ) -> Order:
        return self._submit(Side.BUY, quantity, type, limit, stop)

    def sell(
        self,
        quantity: float,
        *,
        type: OrderType = OrderType.MARKET,
        limit: float | None = None,
        stop: float | None = None,
    ) -> Order:
        return self._submit(Side.SELL, quantity, type, limit, stop)

    def _submit(
        self,
        side: Side,
        quantity: float,
        type: OrderType,
        limit: float | None,
        stop: float | None,
    ) -> Order:
        if self._broker is None:
            raise EngineError("no broker bound to this context")
        order = Order(side=side, quantity=quantity, type=type, limit=limit, stop=stop)
        return self._broker.submit(order, bar_index=self._bars.index)
