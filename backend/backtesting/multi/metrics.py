"""Portfolio-level metrics.

The portfolio equity curve gets the full single-run taxonomy (Sharpe,
drawdowns, trade quality, ...) by reusing ``compute_metrics``; this module
adds what only exists at the portfolio level:

- concentration: Herfindahl index, top-5 weight, max single-name weight,
  summarized over the run (absolute weights, so shorts concentrate too)
- sector exposure over time (from the user-supplied sector map)
- pairwise correlation of position-contribution returns, where a symbol's
  contribution at t is its lagged weight times its price return — zero while
  unheld, so the matrix reflects the portfolio as traded, not raw prices
- turnover (annualized + per-event distribution)
- P&L attribution by symbol (fill cash flows plus final marked value — exact,
  costs included) and by sector

Attribution by signal bucket needs signal tagging that does not exist yet and
is deliberately left out.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from backend.backtesting.errors import EngineError
from backend.backtesting.metrics import (
    Metrics,
    compute_metrics,
    infer_periods_per_year,
    sharpe,
)
from backend.backtesting.multi.book import PortfolioEquityPoint
from backend.backtesting.multi.timeline import MultiBarEvent
from backend.backtesting.multi.turnover import annualized_turnover, per_event_turnover
from backend.backtesting.types import EquityPoint, Fill, Side, Trade


@dataclass(frozen=True, slots=True)
class SectorExposurePoint:
    """Summed signed weight per sector at one equity point."""

    time: datetime
    exposures: dict[str, float]


@dataclass(frozen=True, slots=True)
class PortfolioMetrics:
    """Everything the portfolio dashboard reads, pre-computed."""

    portfolio: Metrics
    symbol_sharpes: dict[str, float]
    avg_hhi: float
    max_hhi: float
    avg_top5_weight: float
    max_top5_weight: float
    max_single_name_weight: float
    correlation_symbols: list[str]
    correlation_matrix: list[list[float]]
    sector_exposure: list[SectorExposurePoint]
    turnover_annualized: float
    turnover_per_event: dict[int, float]
    attribution_by_symbol: dict[str, float]
    attribution_by_sector: dict[str, float]


def concentration(curve: list[PortfolioEquityPoint]) -> dict[str, float]:
    """HHI / top-5 / single-name concentration over the run, on |weights|."""
    if not curve:
        return {
            "avg_hhi": 0.0,
            "max_hhi": 0.0,
            "avg_top5_weight": 0.0,
            "max_top5_weight": 0.0,
            "max_single_name_weight": 0.0,
        }
    hhis: list[float] = []
    top5s: list[float] = []
    singles: list[float] = []
    for point in curve:
        abs_weights = sorted((abs(w) for w in point.weights.values()), reverse=True)
        hhis.append(sum(w * w for w in abs_weights))
        top5s.append(sum(abs_weights[:5]))
        singles.append(abs_weights[0] if abs_weights else 0.0)
    return {
        "avg_hhi": statistics.fmean(hhis),
        "max_hhi": max(hhis),
        "avg_top5_weight": statistics.fmean(top5s),
        "max_top5_weight": max(top5s),
        "max_single_name_weight": max(singles),
    }


def contribution_series(
    events: list[MultiBarEvent], curve: list[PortfolioEquityPoint]
) -> dict[str, list[float]]:
    """Per-symbol position-contribution returns, aligned to events 1..n-1.

    A symbol's contribution at event t is its weight at t-1 times its price
    return into t (zero when unheld or when the symbol has no bar at t).
    Only symbols ever held appear."""
    held = sorted({s for p in curve for s in p.weights})
    series: dict[str, list[float]] = {s: [] for s in held}
    marks: dict[str, float] = {}
    for index, event in enumerate(events):
        if index > 0:
            prev_weights = curve[index - 1].weights
            for symbol in held:
                bar = event.bars.get(symbol)
                prev_mark = marks.get(symbol)
                if bar is None or not prev_mark:
                    series[symbol].append(0.0)
                else:
                    price_return = bar.close / prev_mark - 1.0
                    series[symbol].append(prev_weights.get(symbol, 0.0) * price_return)
        for symbol, bar in event.bars.items():
            marks[symbol] = bar.close
    return series


def pairwise_correlation(
    series: Mapping[str, list[float]],
) -> tuple[list[str], list[list[float]]]:
    """Pearson correlation matrix over the contribution series.

    A zero-variance series (never held, or held flat) correlates 0 with
    everything; the diagonal is 1 by definition."""
    symbols = sorted(series)
    means = {s: statistics.fmean(series[s]) if series[s] else 0.0 for s in symbols}
    stds = {
        s: statistics.pstdev(series[s]) if len(series[s]) >= 2 else 0.0 for s in symbols
    }
    matrix: list[list[float]] = []
    for a in symbols:
        row: list[float] = []
        for b in symbols:
            if a == b:
                row.append(1.0)
                continue
            if stds[a] == 0.0 or stds[b] == 0.0:
                row.append(0.0)
                continue
            n = min(len(series[a]), len(series[b]))
            cov = (
                sum(
                    (series[a][i] - means[a]) * (series[b][i] - means[b])
                    for i in range(n)
                )
                / n
            )
            row.append(cov / (stds[a] * stds[b]))
        matrix.append(row)
    return symbols, matrix


def sector_exposure_over_time(
    curve: list[PortfolioEquityPoint], sectors: Mapping[str, str] | None
) -> list[SectorExposurePoint]:
    """Signed sector weights per equity point; empty without a sector map.
    Symbols missing from the map are excluded (they have no sector)."""
    if not sectors:
        return []
    out: list[SectorExposurePoint] = []
    for point in curve:
        exposures: dict[str, float] = {}
        for symbol in sorted(point.weights):
            sector = sectors.get(symbol)
            if sector is not None:
                exposures[sector] = exposures.get(sector, 0.0) + point.weights[symbol]
        out.append(SectorExposurePoint(time=point.time, exposures=exposures))
    return out


def attribution_by_symbol(
    fills: list[Fill], final_marks: Mapping[str, float]
) -> dict[str, float]:
    """Exact per-symbol P&L: fill cash flows (costs included — the fill price
    already carries slippage/spread, commission is explicit) plus the final
    marked value of whatever is still open."""
    cash_flow: dict[str, float] = {}
    quantity: dict[str, float] = {}
    for fill in fills:
        if fill.symbol is None:
            continue
        signed = fill.quantity if fill.side == Side.BUY else -fill.quantity
        cash_flow[fill.symbol] = (
            cash_flow.get(fill.symbol, 0.0) - signed * fill.price - fill.commission
        )
        quantity[fill.symbol] = quantity.get(fill.symbol, 0.0) + signed
    return {
        symbol: cash_flow[symbol] + quantity[symbol] * final_marks.get(symbol, 0.0)
        for symbol in sorted(cash_flow)
    }


def attribution_by_sector(
    by_symbol: Mapping[str, float], sectors: Mapping[str, str] | None
) -> dict[str, float]:
    """Symbol attribution grouped by sector; unmapped symbols fall into
    ``"unclassified"``. Empty without a sector map."""
    if not sectors:
        return {}
    out: dict[str, float] = {}
    for symbol in sorted(by_symbol):
        sector = sectors.get(symbol, "unclassified")
        out[sector] = out.get(sector, 0.0) + by_symbol[symbol]
    return out


def symbol_sharpes(events: list[MultiBarEvent]) -> dict[str, float]:
    """Annualized Sharpe of each symbol's own close-to-close returns — the
    per-name baseline reported alongside the portfolio Sharpe."""
    closes: dict[str, list[float]] = {}
    times: dict[str, list[datetime]] = {}
    for event in events:
        for symbol, bar in event.bars.items():
            closes.setdefault(symbol, []).append(bar.close)
            times.setdefault(symbol, []).append(bar.time)
    out: dict[str, float] = {}
    for symbol in sorted(closes):
        cs = closes[symbol]
        rets = [b / a - 1.0 for a, b in zip(cs, cs[1:]) if a != 0.0]
        out[symbol] = sharpe(
            rets,
            risk_free_rate=0.0,
            periods_per_year=infer_periods_per_year(times[symbol]),
        )
    return out


def compute_portfolio_metrics(
    *,
    events: list[MultiBarEvent],
    fills: list[Fill],
    equity_curve: list[PortfolioEquityPoint],
    trades: list[Trade],
    sectors: Mapping[str, str] | None = None,
) -> PortfolioMetrics:
    """Assemble the full portfolio metrics block from a run's raw record."""
    for p in equity_curve:
        if not math.isfinite(p.equity):
            raise EngineError(
                f"portfolio equity became non-finite at {p.time.isoformat()} "
                "— likely runaway leverage; check costs and strategy sizing"
            )
    eq_points = [
        EquityPoint(time=p.time, equity=p.equity, cash=p.cash, holdings=p.holdings)
        for p in equity_curve
    ]
    conc = concentration(equity_curve)
    contributions = contribution_series(events, equity_curve)
    correlation_syms, correlation = pairwise_correlation(contributions)
    final_marks: dict[str, float] = {}
    for event in events:
        for symbol, bar in event.bars.items():
            final_marks[symbol] = bar.close
    by_symbol = attribution_by_symbol(fills, final_marks)

    return PortfolioMetrics(
        portfolio=compute_metrics(eq_points, trades, bars=[]),
        symbol_sharpes=symbol_sharpes(events),
        avg_hhi=conc["avg_hhi"],
        max_hhi=conc["max_hhi"],
        avg_top5_weight=conc["avg_top5_weight"],
        max_top5_weight=conc["max_top5_weight"],
        max_single_name_weight=conc["max_single_name_weight"],
        correlation_symbols=correlation_syms,
        correlation_matrix=correlation,
        sector_exposure=sector_exposure_over_time(equity_curve, sectors),
        turnover_annualized=annualized_turnover(fills, equity_curve),
        turnover_per_event=per_event_turnover(fills, equity_curve),
        attribution_by_symbol=by_symbol,
        attribution_by_sector=attribution_by_sector(by_symbol, sectors),
    )
