"""Pluggable position sizers: signals in, target weights out.

Sizing is deliberately separate from signal generation — a strategy decides
*what* to hold (signals), a sizer decides *how much* (weights), and the two
compose via ``ctx.target_weight`` + ``ctx.rebalance()``. Every sizer here is a
pure function with sorted-symbol determinism, so swapping sizers never changes
signal logic and identical inputs always allocate identically. A custom sizer
is simply any user function that returns a ``{symbol: weight}`` dict.

``signals`` map symbols to a signed strength; only the sign is used (zero
means "no position"). Weights are signed fractions of equity.
"""

from __future__ import annotations

import statistics
from typing import Iterable, Mapping, Sequence

from backend.backtesting.types import Bar


def _signs(signals: Mapping[str, float] | Iterable[str]) -> dict[str, float]:
    """Normalize signals to ``{symbol: +1.0 | -1.0}``, dropping zero signals."""
    if isinstance(signals, Mapping):
        return {
            symbol: 1.0 if signals[symbol] > 0 else -1.0
            for symbol in sorted(signals)
            if signals[symbol] != 0.0
        }
    return {symbol: 1.0 for symbol in sorted(signals)}


def equal_weight(
    signals: Mapping[str, float] | Iterable[str], *, gross: float = 1.0
) -> dict[str, float]:
    """1/N: split ``gross`` exposure equally across the active signals,
    keeping each signal's sign. A plain iterable of symbols means all long."""
    signs = _signs(signals)
    if not signs:
        return {}
    per_name = gross / len(signs)
    return {symbol: sign * per_name for symbol, sign in signs.items()}


def inverse_volatility(
    vols: Mapping[str, float],
    *,
    signals: Mapping[str, float] | None = None,
    gross: float = 1.0,
) -> dict[str, float]:
    """Size inversely to recent volatility so each name contributes roughly
    equal risk: ``|w_i| = gross * (1/vol_i) / sum(1/vol_j)``.

    Symbols with a non-positive volatility are dropped (no honest size
    exists). Signs come from ``signals`` when given (zero signal drops the
    symbol); otherwise all long."""
    eligible = {s: v for s, v in vols.items() if v > 0.0}
    signs = _signs(signals if signals is not None else list(eligible))
    eligible = {s: v for s, v in sorted(eligible.items()) if s in signs}
    if not eligible:
        return {}
    total_inverse = sum(1.0 / v for v in eligible.values())
    return {
        symbol: signs[symbol] * gross * (1.0 / vol) / total_inverse
        for symbol, vol in eligible.items()
    }


def kelly_weight(*, edge: float, variance: float, fraction: float = 1.0) -> float:
    """Fractional Kelly for one name: ``fraction * edge / variance``.

    ``edge`` is the expected period return, ``variance`` its variance. A
    non-positive variance makes the criterion undefined — stay flat."""
    if variance <= 0.0:
        return 0.0
    return fraction * edge / variance


def kelly_weights(
    *,
    edges: Mapping[str, float],
    variances: Mapping[str, float],
    fraction: float = 1.0,
) -> dict[str, float]:
    """Per-symbol fractional Kelly. A symbol missing a variance (or with a
    non-positive one) is dropped rather than sized on a guess."""
    out: dict[str, float] = {}
    for symbol in sorted(edges):
        variance = variances.get(symbol, 0.0)
        if variance > 0.0:
            out[symbol] = kelly_weight(
                edge=edges[symbol], variance=variance, fraction=fraction
            )
    return out


def trailing_volatility(bars: Sequence[Bar], lookback: int) -> float | None:
    """Sample standard deviation of the last ``lookback`` close-to-close
    returns, or ``None`` when fewer than two returns exist.

    Accepts any bar sequence, including the look-ahead-guarded ``ctx.bars``
    views (only revealed history is ever read)."""
    n = len(bars)
    window = min(n, lookback + 1)
    closes = [bars[i].close for i in range(n - window, n)]
    rets = [b / a - 1.0 for a, b in zip(closes, closes[1:]) if a != 0.0]
    if len(rets) < 2:
        return None
    return statistics.stdev(rets)
