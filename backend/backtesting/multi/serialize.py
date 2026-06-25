"""Canonical serialization of a ``PortfolioBacktestResult``.

``portfolio_result_to_dict`` is the single source of truth for the on-the-wire
shape of a portfolio run: a fully JSON-serializable dict. It reuses the
single-run dicts for orders/fills/trades (which carry ``symbol``) and adds the
portfolio-only blocks: per-symbol bars, weighted equity points, the constraint
binding log, and the portfolio metrics (with the nested single-run taxonomy
under ``metrics.portfolio``). The dashboard is a pure reader of this output.
"""

from __future__ import annotations

import dataclasses

from backend.backtesting.multi.engine import PortfolioBacktestResult
from backend.backtesting.serialize import (
    _bar_dict,
    _fill_dict,
    _order_dict,
    _trade_dict,
)


def portfolio_result_to_dict(result: PortfolioBacktestResult) -> dict:
    """The canonical, fully JSON-serializable blob for a portfolio run."""
    meta = dataclasses.asdict(result.meta)
    meta["started_at"] = result.meta.started_at.isoformat()
    meta["finished_at"] = result.meta.finished_at.isoformat()

    bars: dict[str, list[dict]] = {}
    for event in result.events:
        for symbol, bar in event.bars.items():
            bars.setdefault(symbol, []).append(_bar_dict(bar))

    metrics = result.metrics
    return {
        "meta": meta,
        "symbols": sorted(bars),
        "bars": bars,
        "orders": [_order_dict(o) for o in result.orders],
        "fills": [_fill_dict(f) for f in result.fills],
        "equity": [
            {
                "t": int(p.time.timestamp()),
                "value": p.equity,
                "cash": p.cash,
                "holdings": p.holdings,
                "weights": p.weights,
            }
            for p in result.equity_curve
        ],
        "trades": [_trade_dict(t) for t in result.trades],
        "constraint_events": [
            {
                "t": int(e.time.timestamp()),
                "constraint": e.constraint,
                "symbol": e.symbol,
                "requested": e.requested,
                "applied": e.applied,
                "detail": e.detail,
            }
            for e in result.constraint_events
        ],
        "metrics": {
            "portfolio": dataclasses.asdict(metrics.portfolio),
            "symbol_sharpes": metrics.symbol_sharpes,
            "avg_hhi": metrics.avg_hhi,
            "max_hhi": metrics.max_hhi,
            "avg_top5_weight": metrics.avg_top5_weight,
            "max_top5_weight": metrics.max_top5_weight,
            "max_single_name_weight": metrics.max_single_name_weight,
            "correlation_symbols": metrics.correlation_symbols,
            "correlation_matrix": metrics.correlation_matrix,
            "sector_exposure": [
                {"t": int(p.time.timestamp()), "exposures": p.exposures}
                for p in metrics.sector_exposure
            ],
            "turnover_annualized": metrics.turnover_annualized,
            "turnover_per_event": [
                {"index": index, "turnover": value}
                for index, value in sorted(metrics.turnover_per_event.items())
            ],
            "attribution_by_symbol": metrics.attribution_by_symbol,
            "attribution_by_sector": metrics.attribution_by_sector,
        },
    }
