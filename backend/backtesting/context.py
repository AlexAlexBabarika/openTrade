"""The strategy-facing context (``ctx``) and its look-ahead guard.

``BarSeries`` is a cursor over the full ordered bar list. The engine calls
``advance()`` once per consumed BAR event to reveal the next bar; strategy code
only ever sees ``ctx.bars``, which bounds every read against the revealed
cursor. Reading at or past the next index is, by definition, look-ahead and
raises ``LookAheadError`` — there is no path to a silent future read.
"""

from __future__ import annotations

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


class Context:
    """What user strategy code receives each bar as ``ctx``."""

    def __init__(
        self,
        bars: BarSeries,
        broker: "Broker | None" = None,
        portfolio: "Portfolio | None" = None,
    ) -> None:
        self._bars = bars
        self._broker = broker
        self._portfolio = portfolio

    @property
    def bars(self) -> BarSeries:
        return self._bars

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
