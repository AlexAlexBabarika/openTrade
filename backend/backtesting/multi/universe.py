"""Universe definition: which symbols exist for the strategy, and when.

Membership is interval-based — start inclusive, end exclusive, either side
open — so the engine can answer "was this symbol tradable at bar t" exactly,
track join/leave events, and support a symbol leaving and rejoining. A static
list is the degenerate case of one open interval per symbol.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from backend.backtesting.errors import UniverseError


@dataclass(frozen=True, slots=True)
class Membership:
    """One interval of a symbol's universe membership.

    ``start`` is inclusive, ``end`` exclusive; ``None`` on either side means
    unbounded in that direction."""

    symbol: str
    start: datetime | None = None
    end: datetime | None = None

    def contains(self, time: datetime) -> bool:
        if self.start is not None and time < self.start:
            return False
        if self.end is not None and time >= self.end:
            return False
        return True


class Universe:
    """The set of membership intervals, validated and queryable by time."""

    def __init__(self, memberships: Iterable[Membership]) -> None:
        intervals: dict[str, list[Membership]] = {}
        for m in memberships:
            if m.start is not None and m.end is not None and m.start >= m.end:
                raise UniverseError(
                    f"membership for {m.symbol!r} has start >= end "
                    f"({m.start.isoformat()} >= {m.end.isoformat()})"
                )
            intervals.setdefault(m.symbol, []).append(m)
        if not intervals:
            raise UniverseError("universe has no symbols")

        for symbol, ms in intervals.items():
            ms.sort(key=lambda m: (m.start is not None, m.start))
            for prev, cur in zip(ms, ms[1:]):
                if prev.end is None or cur.start is None or cur.start < prev.end:
                    raise UniverseError(
                        f"overlapping membership intervals for {symbol!r}"
                    )

        self._intervals = {s: tuple(ms) for s, ms in sorted(intervals.items())}

    @classmethod
    def static(cls, symbols: Iterable[str]) -> "Universe":
        """A universe whose symbols are members for the whole backtest."""
        return cls(Membership(symbol) for symbol in symbols)

    @property
    def symbols(self) -> tuple[str, ...]:
        """Every symbol that is ever a member, sorted."""
        return tuple(self._intervals)

    def is_active(self, symbol: str, time: datetime) -> bool:
        return any(m.contains(time) for m in self._intervals.get(symbol, ()))

    def memberships(self) -> list["Membership"]:
        """Flattened membership intervals (sorted by symbol, then start)."""
        return [m for ms in self._intervals.values() for m in ms]

    def active(self, time: datetime) -> tuple[str, ...]:
        """Symbols that are members at ``time``, sorted."""
        return tuple(s for s in self._intervals if self.is_active(s, time))
