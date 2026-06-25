"""
The portfolio book is multi-asset accounting: one shared cash balance, one
signed position per symbol, realized PnL attributable per symbol, and an
equity curve whose points carry per-symbol weights (for holdings/heatmap
views). Position math must agree exactly with the single-symbol Portfolio.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.backtesting.multi.book import PortfolioBook
from backend.backtesting.types import Fill, Side


def _fill(
    symbol: str, side: Side, qty: float, price: float, commission: float = 0.0
) -> Fill:
    return Fill(
        order_id=0,
        side=side,
        quantity=qty,
        price=price,
        reference_price=price,
        slippage=0.0,
        spread_cost=0.0,
        commission=commission,
        submitted_index=0,
        fill_index=1,
        reason="market",
        symbol=symbol,
    )


def _t(day: int = 1) -> datetime:
    return datetime(2024, 1, day, tzinfo=timezone.utc)


def test_positions_are_tracked_per_symbol_with_shared_cash() -> None:
    book = PortfolioBook(starting_cash=10_000.0)
    book.apply_fill(_fill("AAPL", Side.BUY, 10.0, 100.0))
    book.apply_fill(_fill("MSFT", Side.BUY, 5.0, 200.0))

    assert book.cash == 10_000.0 - 1_000.0 - 1_000.0
    assert book.position("AAPL").quantity == 10.0
    assert book.position("AAPL").avg_price == 100.0
    assert book.position("MSFT").quantity == 5.0
    assert book.position("GOOG").quantity == 0.0  # flat default


def test_realized_pnl_is_attributed_per_symbol() -> None:
    book = PortfolioBook(starting_cash=10_000.0)
    book.apply_fill(_fill("AAPL", Side.BUY, 10.0, 100.0))
    book.apply_fill(_fill("AAPL", Side.SELL, 10.0, 110.0))
    book.apply_fill(_fill("MSFT", Side.SELL, 5.0, 200.0))  # short
    book.apply_fill(_fill("MSFT", Side.BUY, 5.0, 210.0))  # cover at a loss

    assert book.realized_pnl("AAPL") == 100.0
    assert book.realized_pnl("MSFT") == -50.0
    assert book.total_realized_pnl == 50.0
    assert book.cash == 10_000.0 + 100.0 - 50.0


def test_commission_reduces_cash() -> None:
    book = PortfolioBook(starting_cash=1_000.0)
    book.apply_fill(_fill("AAPL", Side.BUY, 1.0, 100.0, commission=2.0))
    assert book.cash == 1_000.0 - 100.0 - 2.0


def test_equity_marks_every_open_position() -> None:
    book = PortfolioBook(starting_cash=10_000.0)
    book.apply_fill(_fill("AAPL", Side.BUY, 10.0, 100.0))
    book.apply_fill(_fill("MSFT", Side.SELL, 5.0, 200.0))

    equity = book.equity({"AAPL": 110.0, "MSFT": 190.0})
    # cash 10_000 - 1_000 + 1_000 = 10_000; AAPL 1_100; MSFT short -950
    assert equity == 10_000.0 + 1_100.0 - 950.0


def test_mark_to_market_records_weights_per_symbol() -> None:
    book = PortfolioBook(starting_cash=10_000.0)
    book.apply_fill(_fill("AAPL", Side.BUY, 10.0, 100.0))
    book.apply_fill(_fill("MSFT", Side.SELL, 5.0, 200.0))

    point = book.mark_to_market(_t(), {"AAPL": 100.0, "MSFT": 200.0})
    assert point.equity == 10_000.0
    assert point.cash == 10_000.0
    assert point.holdings == 1_000.0 - 1_000.0
    assert point.weights == {"AAPL": 0.1, "MSFT": -0.1}
    assert book.equity_curve == [point]


def test_closed_positions_drop_out_of_weights_and_positions() -> None:
    book = PortfolioBook(starting_cash=10_000.0)
    book.apply_fill(_fill("AAPL", Side.BUY, 10.0, 100.0))
    book.apply_fill(_fill("AAPL", Side.SELL, 10.0, 100.0))

    point = book.mark_to_market(_t(), {"AAPL": 100.0})
    assert point.weights == {}
    assert book.open_positions == {}


def test_open_positions_lists_only_nonflat_symbols() -> None:
    book = PortfolioBook(starting_cash=10_000.0)
    book.apply_fill(_fill("MSFT", Side.BUY, 5.0, 200.0))
    book.apply_fill(_fill("AAPL", Side.BUY, 10.0, 100.0))

    assert list(book.open_positions) == ["AAPL", "MSFT"]  # sorted
    assert book.open_positions["MSFT"].quantity == 5.0
