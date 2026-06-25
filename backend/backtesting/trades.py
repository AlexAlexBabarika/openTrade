"""Match fills into position-based round-trip trades.

A trade opens when the signed position leaves flat and closes when it returns to
flat. Scale-ins and scale-outs aggregate into a single trade. A fill that crosses
through flat (a flip) is split: the part that closes the current trade finalizes
it, and the remainder opens a new trade in the opposite direction, dated to the
flipping fill. Fills carry bar indices, not timestamps, so ``bar_times`` resolves
each index to a datetime.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.backtesting.types import Fill, Side, Trade


@dataclass
class _Open:
    """Accumulator for the trade currently being built."""

    direction: int  # +1 long, -1 short
    entry_qty: float = 0.0
    entry_notional: float = 0.0
    exit_qty: float = 0.0
    exit_notional: float = 0.0
    commission: float = 0.0
    entry_index: int = 0

    @property
    def open_qty(self) -> float:
        return self.entry_qty - self.exit_qty


def match_trades(fills: list[Fill], bar_times: list[datetime]) -> list[Trade]:
    trades: list[Trade] = []
    current: _Open | None = None

    def finalize(exit_index: int) -> None:
        nonlocal current
        assert current is not None
        direction = Side.BUY if current.direction > 0 else Side.SELL
        gross = current.direction * (current.exit_notional - current.entry_notional)
        pnl = gross - current.commission
        entry_price = current.entry_notional / current.entry_qty
        exit_price = current.exit_notional / current.exit_qty
        trades.append(
            Trade(
                direction=direction,
                quantity=current.entry_qty,
                entry_time=bar_times[current.entry_index],
                exit_time=bar_times[exit_index],
                entry_index=current.entry_index,
                exit_index=exit_index,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl=pnl,
                pnl_pct=pnl / current.entry_notional,
                bars_held=exit_index - current.entry_index,
            )
        )
        current = None

    for f in fills:
        signed = f.quantity if f.side == Side.BUY else -f.quantity
        sign = 1 if signed > 0 else -1
        qty = abs(signed)

        # Open a fresh trade if flat.
        if current is None:
            current = _Open(direction=sign, entry_index=f.fill_index)

        if sign == current.direction:
            # Same direction: scale in (entry leg).
            current.entry_qty += qty
            current.entry_notional += qty * f.price
            current.commission += f.commission
            continue

        # Opposite direction: close (part of) the trade, and maybe flip.
        open_before = current.open_qty
        closing = min(qty, open_before)
        c_close = f.commission * (closing / qty)
        current.exit_qty += closing
        current.exit_notional += closing * f.price
        current.commission += c_close

        if closing < open_before:
            continue  # partial scale-out: the trade stays open

        # The position reached flat: this fill closes the trade.
        finalize(exit_index=f.fill_index)

        leftover = qty - closing
        if leftover > 0:
            # Flip: the remainder opens a new trade dated to this fill.
            current = _Open(direction=sign, entry_index=f.fill_index)
            current.entry_qty += leftover
            current.entry_notional += leftover * f.price
            current.commission += f.commission - c_close

    return trades
