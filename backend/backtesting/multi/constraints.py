"""Hard portfolio constraints, enforced at order generation.

``apply_constraints`` clamps a set of target weights so rebalancing can never
submit a violating order, and returns a structured event per binding — the
user's audit trail ("wanted 50% AAPL, capped at 30% by max_position_weight").
The strategy's declared targets are never rewritten; clamping happens on a
copy at each rebalance.

Constraints apply in a fixed, documented order: no-trade, shorting rules,
per-position caps, sector caps, gross leverage, net leverage. Each stage is
an upper bound, so later proportional scalings can only shrink weights
further, never re-violate an earlier cap. Market-neutral is ``max_net=0.0``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping

# Bindings smaller than this are float noise, not user-relevant events.
_EPS = 1e-12


@dataclass(frozen=True, slots=True)
class Constraints:
    """The user-declared hard limits for a portfolio run.

    ``sectors`` maps symbols to sector names for the sector cap; symbols
    without an entry are exempt. ``min_trade_value`` (currency) makes
    rebalancing skip dust trades; the skip is logged."""

    max_position_weight: float | None = None
    max_position_value: float | None = None
    max_sector_weight: float | None = None
    sectors: Mapping[str, str] | None = None
    long_only: bool = False
    no_short: frozenset[str] = field(default_factory=frozenset)
    no_trade: frozenset[str] = field(default_factory=frozenset)
    max_gross: float | None = None
    max_net: float | None = None
    min_trade_value: float = 0.0


@dataclass(frozen=True, slots=True)
class ConstraintEvent:
    """One binding of one constraint.

    ``requested``/``applied`` are weights for per-symbol bindings and
    aggregates (gross/net) for portfolio-wide ones; ``applied`` is ``None``
    when the action was dropped entirely (no-trade target, skipped dust
    trade). ``detail`` is the human-readable line for the log view."""

    time: datetime
    constraint: str
    symbol: str | None
    requested: float
    applied: float | None
    detail: str


def _pct(w: float) -> str:
    return f"{w * 100:.2f}%"


def apply_constraints(
    targets: Mapping[str, float],
    *,
    constraints: Constraints,
    equity: float,
    time: datetime,
) -> tuple[dict[str, float], list[ConstraintEvent]]:
    """Clamp ``targets`` to satisfy ``constraints``; return (clamped, events)."""
    events: list[ConstraintEvent] = []
    out: dict[str, float] = {}

    # 1. No-trade: the target is dropped, leaving any existing position alone.
    for symbol in sorted(targets):
        weight = float(targets[symbol])
        if symbol in constraints.no_trade:
            events.append(
                ConstraintEvent(
                    time=time,
                    constraint="no_trade",
                    symbol=symbol,
                    requested=weight,
                    applied=None,
                    detail=f"target {_pct(weight)} {symbol} ignored: on the no-trade list",
                )
            )
            continue
        out[symbol] = weight

    # 2. Shorting rules.
    for symbol in sorted(out):
        weight = out[symbol]
        if weight >= 0.0:
            continue
        if constraints.long_only or symbol in constraints.no_short:
            name = "long_only" if constraints.long_only else "no_short"
            events.append(
                ConstraintEvent(
                    time=time,
                    constraint=name,
                    symbol=symbol,
                    requested=weight,
                    applied=0.0,
                    detail=f"wanted {_pct(weight)} {symbol}, shorting not allowed ({name})",
                )
            )
            out[symbol] = 0.0

    # 3. Per-position caps (% of equity and currency amount).
    weight_cap = (
        constraints.max_position_weight
        if constraints.max_position_weight is not None
        else math.inf
    )
    value_cap = (
        constraints.max_position_value / equity
        if constraints.max_position_value is not None and equity > 0.0
        else math.inf
    )
    cap = min(weight_cap, value_cap)
    if math.isfinite(cap):
        for symbol in sorted(out):
            weight = out[symbol]
            if abs(weight) > cap + _EPS:
                name = (
                    "max_position_weight"
                    if weight_cap <= value_cap
                    else "max_position_value"
                )
                clamped = math.copysign(cap, weight)
                events.append(
                    ConstraintEvent(
                        time=time,
                        constraint=name,
                        symbol=symbol,
                        requested=weight,
                        applied=clamped,
                        detail=f"wanted {_pct(weight)} {symbol}, capped at {_pct(clamped)} by {name}",
                    )
                )
                out[symbol] = clamped

    # 4. Sector caps: scale every member of an over-cap sector proportionally.
    if constraints.max_sector_weight is not None and constraints.sectors:
        sector_cap = constraints.max_sector_weight
        by_sector: dict[str, list[str]] = {}
        for symbol in sorted(out):
            sector = constraints.sectors.get(symbol)
            if sector is not None:
                by_sector.setdefault(sector, []).append(symbol)
        for sector in sorted(by_sector):
            gross = sum(abs(out[s]) for s in by_sector[sector])
            if gross > sector_cap + _EPS:
                factor = sector_cap / gross
                for symbol in by_sector[sector]:
                    weight = out[symbol]
                    if weight == 0.0:
                        continue
                    clamped = weight * factor
                    events.append(
                        ConstraintEvent(
                            time=time,
                            constraint="max_sector_weight",
                            symbol=symbol,
                            requested=weight,
                            applied=clamped,
                            detail=(
                                f"wanted {_pct(weight)} {symbol}, capped at "
                                f"{_pct(clamped)} by {sector} sector limit"
                            ),
                        )
                    )
                    out[symbol] = clamped

    # 5. Gross leverage: proportional scale, one aggregate event.
    if constraints.max_gross is not None:
        gross = sum(abs(w) for w in out.values())
        if gross > constraints.max_gross + _EPS:
            factor = constraints.max_gross / gross
            for symbol in sorted(out):
                out[symbol] *= factor
            events.append(
                ConstraintEvent(
                    time=time,
                    constraint="max_gross",
                    symbol=None,
                    requested=gross,
                    applied=constraints.max_gross,
                    detail=(
                        f"gross exposure {_pct(gross)} scaled to "
                        f"{_pct(constraints.max_gross)} (max_gross)"
                    ),
                )
            )

    # 6. Net leverage: scale the dominant side down to the cap.
    if constraints.max_net is not None:
        net = sum(out.values())
        if abs(net) > constraints.max_net + _EPS:
            longs = sum(w for w in out.values() if w > 0.0)
            shorts = -sum(w for w in out.values() if w < 0.0)
            if net > 0.0:
                factor = (shorts + constraints.max_net) / longs if longs > 0.0 else 0.0
                for symbol in sorted(out):
                    if out[symbol] > 0.0:
                        out[symbol] *= factor
            else:
                factor = (longs + constraints.max_net) / shorts if shorts > 0.0 else 0.0
                for symbol in sorted(out):
                    if out[symbol] < 0.0:
                        out[symbol] *= factor
            clamped_net = math.copysign(constraints.max_net, net)
            events.append(
                ConstraintEvent(
                    time=time,
                    constraint="max_net",
                    symbol=None,
                    requested=net,
                    applied=clamped_net,
                    detail=(
                        f"net exposure {_pct(net)} scaled to "
                        f"{_pct(clamped_net)} (max_net)"
                    ),
                )
            )

    return out, events
