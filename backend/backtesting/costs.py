"""Pluggable cost models: slippage, commission, spread.

Slippage and half-spread move the effective fill price adverse to the trade
(a buy fills above the reference, a sell below); commission is a separate
currency charge that does not move the price. Each category is a Protocol so
richer variants (ATR-scaled slippage, tiered commission, bid/ask-estimated
spread) can be dropped in later; the fixed/per-share concretes here are the
conservative defaults. Frictionless results require an explicit opt-in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.backtesting.types import Bar, Side


class SlippageModel(Protocol):
    def slippage(self, reference_price: float, side: Side, bar: Bar) -> float:
        """Adverse price impact per share (>= 0, in price units)."""
        ...


class CommissionModel(Protocol):
    def commission(self, price: float, quantity: float) -> float:
        """Commission charged for a fill (>= 0, in currency)."""
        ...


class SpreadModel(Protocol):
    def half_spread(self, reference_price: float, bar: Bar) -> float:
        """Half the bid/ask spread per share (>= 0, in price units)."""
        ...


@dataclass(frozen=True, slots=True)
class FixedBpsSlippage:
    bps: float

    def slippage(self, reference_price: float, side: Side, bar: Bar) -> float:
        return reference_price * self.bps / 1e4


@dataclass(frozen=True, slots=True)
class PerShareCommission:
    per_share: float

    def commission(self, price: float, quantity: float) -> float:
        return self.per_share * abs(quantity)


@dataclass(frozen=True, slots=True)
class BpsCommission:
    bps: float

    def commission(self, price: float, quantity: float) -> float:
        return abs(price * quantity) * self.bps / 1e4


@dataclass(frozen=True, slots=True)
class FixedBpsHalfSpread:
    bps: float

    def half_spread(self, reference_price: float, bar: Bar) -> float:
        return reference_price * self.bps / 1e4


@dataclass(frozen=True, slots=True)
class Costs:
    """Bundle of the three cost models applied to every fill."""

    slippage: SlippageModel
    commission: CommissionModel
    spread: SpreadModel

    @classmethod
    def default(cls) -> "Costs":
        """Conservative, non-zero defaults (5 bps slippage, 2 bps half-spread,
        1 bps commission).

        Commission is notional-based (bps) rather than per-share so that every
        cost is scale-invariant: back-adjusted history can drive prices to a
        fraction of a cent (and share counts into the billions), where a
        per-share commission would dwarf the position value and bankrupt the
        book on a single fill."""
        return cls(
            slippage=FixedBpsSlippage(5.0),
            commission=BpsCommission(1.0),
            spread=FixedBpsHalfSpread(2.0),
        )

    @classmethod
    def frictionless(cls) -> "Costs":
        return cls(
            slippage=FixedBpsSlippage(0.0),
            commission=PerShareCommission(0.0),
            spread=FixedBpsHalfSpread(0.0),
        )

    def apply(
        self,
        *,
        reference_price: float,
        side: Side,
        quantity: float,
        bar: Bar,
    ) -> tuple[float, float, float, float]:
        """Return ``(fill_price, slippage_cost, spread_cost, commission)``.

        ``fill_price`` already includes slippage and half-spread; the cost
        figures are currency totals for reporting/accounting.
        """
        slip_per_share = self.slippage.slippage(reference_price, side, bar)
        half_per_share = self.spread.half_spread(reference_price, bar)
        direction = 1.0 if side == Side.BUY else -1.0
        fill_price = reference_price + direction * (slip_per_share + half_per_share)
        commission = self.commission.commission(fill_price, quantity)
        return (
            fill_price,
            slip_per_share * abs(quantity),
            half_per_share * abs(quantity),
            commission,
        )
