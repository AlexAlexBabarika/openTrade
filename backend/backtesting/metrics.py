"""The metrics taxonomy for a backtest run.

Each public function is pure and computes one group (or one number) from the
equity curve, the matched trades, or the bars, so each is independently testable.
``compute_metrics`` assembles them into a ``Metrics``.

Conventions: returns are simple period-over-period equity returns; annualization
uses ``periods_per_year`` (inferred from bar spacing, default daily = 252);
risk-free rate defaults to 0. Calendar quantities (CAGR, monthly/yearly grouping)
use the equity point timestamps.
"""

from __future__ import annotations

import statistics
from datetime import datetime

from backend.backtesting.types import Bar, Drawdown, EquityPoint, Metrics, Trade

_SECONDS_PER_YEAR = 365.25 * 24 * 3600
_HOLDINGS_EPS = 1e-9


# ---------------------------------------------------------------------------
# Return metrics (Task 3)
# ---------------------------------------------------------------------------


def returns(curve: list[EquityPoint]) -> list[float]:
    """Period-over-period simple returns of the equity curve."""
    out: list[float] = []
    for prev, cur in zip(curve, curve[1:]):
        out.append(cur.equity / prev.equity - 1 if prev.equity else 0.0)
    return out


def total_return(curve: list[EquityPoint]) -> float:
    if len(curve) < 2 or curve[0].equity == 0:
        return 0.0
    return curve[-1].equity / curve[0].equity - 1


def cagr(curve: list[EquityPoint]) -> float:
    if len(curve) < 2 or curve[0].equity <= 0:
        return 0.0
    years = (curve[-1].time - curve[0].time).total_seconds() / _SECONDS_PER_YEAR
    if years <= 0:
        return 0.0
    return (curve[-1].equity / curve[0].equity) ** (1 / years) - 1


def _period_returns(curve: list[EquityPoint], keyfn) -> list[float]:
    """Returns per calendar period, keyed by ``keyfn(time)``.

    The end-of-period equity is the last point in that period; the first period's
    base is the first point's own equity, and each subsequent period's base is the
    prior period's end."""
    if not curve:
        return []
    ends: list[float] = []
    last_key = None
    for p in curve:
        k = keyfn(p.time)
        if k == last_key:
            ends[-1] = p.equity
        else:
            ends.append(p.equity)
            last_key = k
    out: list[float] = []
    prev = curve[0].equity
    for eq in ends:
        out.append(eq / prev - 1 if prev else 0.0)
        prev = eq
    return out


def monthly_returns(curve: list[EquityPoint]) -> list[float]:
    return _period_returns(curve, lambda t: (t.year, t.month))


def yearly_returns(curve: list[EquityPoint]) -> list[float]:
    return _period_returns(curve, lambda t: t.year)


def pct_positive(period_rets: list[float]) -> float | None:
    if not period_rets:
        return None
    return sum(1 for r in period_rets if r > 0) / len(period_rets)


def infer_periods_per_year(times: list[datetime]) -> float:
    """Annualization factor from median bar spacing.

    Maps common bar sizes to their standard trading-period counts; falls back to
    a calendar estimate for unusual spacings."""
    if len(times) < 3:
        return 252.0
    deltas = sorted((b - a).total_seconds() for a, b in zip(times, times[1:]))
    median = deltas[len(deltas) // 2]
    if median <= 0:
        return 252.0
    days = median / 86400
    if days <= 1.5:
        return 252.0  # daily
    if days <= 9:
        return 52.0  # weekly
    if days <= 45:
        return 12.0  # monthly
    return _SECONDS_PER_YEAR / median


# ---------------------------------------------------------------------------
# Risk-adjusted metrics (Task 4)
# ---------------------------------------------------------------------------


def _sample_std(xs: list[float]) -> float:
    return statistics.stdev(xs) if len(xs) >= 2 else 0.0


def sharpe(
    period_returns: list[float], *, risk_free_rate: float, periods_per_year: float
) -> float:
    if not period_returns:
        return 0.0
    rf = risk_free_rate / periods_per_year
    excess = [r - rf for r in period_returns]
    sd = _sample_std(excess)
    if sd == 0:
        return 0.0
    return statistics.fmean(excess) / sd * (periods_per_year**0.5)


def sortino(
    period_returns: list[float], *, risk_free_rate: float, periods_per_year: float
) -> float:
    if not period_returns:
        return 0.0
    rf = risk_free_rate / periods_per_year
    excess = [r - rf for r in period_returns]
    downside = [min(0.0, e) for e in excess]
    dd = (sum(d * d for d in downside) / len(excess)) ** 0.5
    if dd == 0:
        return 0.0
    return statistics.fmean(excess) / dd * (periods_per_year**0.5)


def calmar(*, cagr_value: float, max_drawdown: float) -> float:
    if max_drawdown == 0:
        return 0.0
    return cagr_value / abs(max_drawdown)


def information_ratio(
    period_returns: list[float],
    benchmark_returns: list[float],
    *,
    periods_per_year: float,
) -> float:
    n = min(len(period_returns), len(benchmark_returns))
    if n == 0:
        return 0.0
    active = [period_returns[i] - benchmark_returns[i] for i in range(n)]
    sd = _sample_std(active)
    if sd == 0:
        return 0.0
    return statistics.fmean(active) / sd * (periods_per_year**0.5)


# ---------------------------------------------------------------------------
# Drawdown metrics (Task 5)
# ---------------------------------------------------------------------------


def compute_drawdowns(curve: list[EquityPoint]) -> list[Drawdown]:
    """Every peak-to-recovery drawdown episode, in time order."""
    if not curve:
        return []
    episodes: list[Drawdown] = []
    peak = curve[0].equity
    peak_time = curve[0].time
    peak_index = 0
    in_dd = False
    trough = peak
    trough_time = peak_time
    for i, p in enumerate(curve):
        if p.equity >= peak:
            if in_dd:
                episodes.append(
                    Drawdown(
                        start=peak_time,
                        trough=trough_time,
                        recovery=p.time,
                        depth=trough / peak - 1,
                        length=i - peak_index,
                    )
                )
                in_dd = False
            peak = p.equity
            peak_time = p.time
            peak_index = i
        else:
            if not in_dd:
                in_dd = True
                trough = p.equity
                trough_time = p.time
            elif p.equity < trough:
                trough = p.equity
                trough_time = p.time
    if in_dd:
        episodes.append(
            Drawdown(
                start=peak_time,
                trough=trough_time,
                recovery=None,
                depth=trough / peak - 1,
                length=(len(curve) - 1) - peak_index,
            )
        )
    return episodes


def max_drawdown(episodes: list[Drawdown]) -> float:
    return min((d.depth for d in episodes), default=0.0)


def max_drawdown_length(episodes: list[Drawdown]) -> int:
    """Length of the *deepest* drawdown episode (the length paired with the max
    drawdown depth), not the longest episode on the curve."""
    if not episodes:
        return 0
    return min(episodes, key=lambda d: d.depth).length


def avg_drawdown(episodes: list[Drawdown]) -> float:
    if not episodes:
        return 0.0
    return statistics.fmean(d.depth for d in episodes)


def time_underwater(curve: list[EquityPoint]) -> float:
    if not curve:
        return 0.0
    peak = curve[0].equity
    under = 0
    for p in curve:
        peak = max(peak, p.equity)
        if p.equity < peak:
            under += 1
    return under / len(curve)


# ---------------------------------------------------------------------------
# Trade-quality metrics (Task 6)
# ---------------------------------------------------------------------------


def _max_run(trades: list[Trade], predicate) -> int:
    best = run = 0
    for t in trades:
        if predicate(t.pnl):
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def trade_quality(trades: list[Trade]) -> dict:
    """Win rate, averages, ratios, expectancy, consecutive runs, and bars held.

    Returned as a dict so ``compute_metrics`` can splat it into ``Metrics`` and
    each key is independently asserted in tests. ``None`` where undefined."""
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]
    gross_win = sum(t.pnl for t in wins)
    gross_loss = sum(t.pnl for t in losses)  # <= 0

    avg_win = statistics.fmean(t.pnl for t in wins) if wins else None
    avg_loss = statistics.fmean(t.pnl for t in losses) if losses else None
    win_loss_ratio = (
        avg_win / abs(avg_loss)
        if avg_win is not None and avg_loss not in (None, 0)
        else None
    )
    profit_factor = gross_win / abs(gross_loss) if gross_loss != 0 else None

    return {
        "win_rate": len(wins) / len(trades) if trades else None,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "win_loss_ratio": win_loss_ratio,
        "profit_factor": profit_factor,
        "expectancy": statistics.fmean(t.pnl for t in trades) if trades else None,
        "max_consecutive_wins": _max_run(trades, lambda p: p > 0),
        "max_consecutive_losses": _max_run(trades, lambda p: p < 0),
        "avg_bars_held_winners": (
            statistics.fmean(t.bars_held for t in wins) if wins else None
        ),
        "avg_bars_held_losers": (
            statistics.fmean(t.bars_held for t in losses) if losses else None
        ),
    }


# ---------------------------------------------------------------------------
# Exposure metrics (Task 7)
# ---------------------------------------------------------------------------


def exposure(curve: list[EquityPoint]) -> dict:
    """Time-in-market, average position size, and peak leverage, as fractions of
    equity. Returned as a dict for splatting into ``Metrics``."""
    if not curve:
        return {"pct_time_in_market": 0.0, "avg_position_pct": 0.0, "max_leverage": 0.0}
    in_market = 0
    ratios: list[float] = []
    for p in curve:
        if abs(p.holdings) > _HOLDINGS_EPS:
            in_market += 1
        ratios.append(abs(p.holdings) / p.equity if p.equity else 0.0)
    return {
        "pct_time_in_market": in_market / len(curve),
        "avg_position_pct": statistics.fmean(ratios),
        "max_leverage": max(ratios),
    }


# ---------------------------------------------------------------------------
# Orchestrator (Task 8)
# ---------------------------------------------------------------------------


def _benchmark_returns(bars: list[Bar]) -> list[float]:
    """Buy-and-hold returns from bar closes (the dashboard's default benchmark)."""
    out: list[float] = []
    for prev, cur in zip(bars, bars[1:]):
        out.append(cur.close / prev.close - 1 if prev.close else 0.0)
    return out


def compute_metrics(
    curve: list[EquityPoint],
    trades: list[Trade],
    bars: list[Bar],
    *,
    risk_free_rate: float = 0.0,
    periods_per_year: float | None = None,
) -> Metrics:
    times = [p.time for p in curve]
    ppy = (
        periods_per_year
        if periods_per_year is not None
        else infer_periods_per_year(times)
    )
    rets = returns(curve)
    bench = _benchmark_returns(bars)
    months = monthly_returns(curve)
    years = yearly_returns(curve)
    episodes = compute_drawdowns(curve)
    mdd = max_drawdown(episodes)
    tr = total_return(curve)
    cg = cagr(curve)
    q = trade_quality(trades)
    ex = exposure(curve)

    return Metrics(
        total_return=tr,
        cagr=cg,
        # Arithmetic mean of calendar-year returns; deliberately distinct from
        # the geometric ``cagr`` above (the spec lists both as separate metrics).
        avg_annual_return=statistics.fmean(years) if years else 0.0,
        best_month=max(months) if months else None,
        worst_month=min(months) if months else None,
        best_year=max(years) if years else None,
        worst_year=min(years) if years else None,
        pct_positive_months=pct_positive(months),
        pct_positive_years=pct_positive(years),
        sharpe=sharpe(rets, risk_free_rate=risk_free_rate, periods_per_year=ppy),
        sortino=sortino(rets, risk_free_rate=risk_free_rate, periods_per_year=ppy),
        calmar=calmar(cagr_value=cg, max_drawdown=mdd),
        information_ratio=information_ratio(rets, bench, periods_per_year=ppy),
        max_drawdown=mdd,
        max_drawdown_length=max_drawdown_length(episodes),
        avg_drawdown=avg_drawdown(episodes),
        time_underwater=time_underwater(curve),
        recovery_factor=tr / abs(mdd) if mdd != 0 else 0.0,
        win_rate=q["win_rate"],
        avg_win=q["avg_win"],
        avg_loss=q["avg_loss"],
        win_loss_ratio=q["win_loss_ratio"],
        profit_factor=q["profit_factor"],
        expectancy=q["expectancy"],
        max_consecutive_wins=q["max_consecutive_wins"],
        max_consecutive_losses=q["max_consecutive_losses"],
        avg_bars_held_winners=q["avg_bars_held_winners"],
        avg_bars_held_losers=q["avg_bars_held_losers"],
        pct_time_in_market=ex["pct_time_in_market"],
        avg_position_pct=ex["avg_position_pct"],
        max_leverage=ex["max_leverage"],
    )
