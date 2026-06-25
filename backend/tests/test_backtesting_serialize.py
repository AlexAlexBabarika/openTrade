"""Canonical serialization: in-memory dict, on-disk JSON + Parquet bars."""

from __future__ import annotations

from backend.backtesting.engine import run_backtest
from backend.backtesting.serialize import read_result, result_to_dict, write_result
from backend.backtesting.strategy import Strategy
from backend.tests._backtesting_fixtures import BuyAndHold, canonical_frame


class _ShortThenCover(Strategy):
    """Open a short on the first bar, cover later -> one completed SELL trade."""

    def on_bar(self, ctx) -> None:
        if ctx.bars.index == 0:
            ctx.sell(5.0)
        elif ctx.bars.index == 5:
            ctx.buy(5.0)


def _result():
    return run_backtest(
        frame=canonical_frame(),
        strategy=BuyAndHold(),
        starting_cash=10_000.0,
        seed=0,
        strategy_id="buy_and_hold",
    )


def test_result_to_dict_has_canonical_shape():
    d = result_to_dict(_result())

    assert set(d) == {"meta", "bars", "orders", "fills", "equity", "trades", "metrics"}
    assert d["meta"]["strategy_id"] == "buy_and_hold"
    assert isinstance(d["meta"]["started_at"], str)  # ISO string
    assert len(d["equity"]) == len(d["bars"])
    sample = d["equity"][0]
    assert set(sample) == {"t", "value", "cash", "holdings"}
    assert d["metrics"]["total_return"] is not None


def test_result_to_dict_is_json_serializable():
    import json

    json.dumps(result_to_dict(_result()))  # must not raise


def test_write_then_read_round_trips(tmp_path):
    result = _result()
    out_dir = write_result(result, tmp_path)

    assert (out_dir / "run.json").exists()
    assert (out_dir / "bars.parquet").exists()

    loaded = read_result(out_dir)
    assert loaded["meta"]["run_id"] == result.meta.run_id
    assert len(loaded["bars"]) == len(result.bars)
    assert loaded["bars"][0]["close"] == result.bars[0].close
    # bar timestamps survive as unix ints (guards against a Parquet type regression)
    assert loaded["bars"][0]["t"] == int(result.bars[0].time.timestamp())
    assert isinstance(loaded["bars"][0]["t"], int)
    # equity survives the round trip
    assert len(loaded["equity"]) == len(result.equity_curve)


def test_short_trade_round_trips_through_serializer(tmp_path):
    import json

    result = run_backtest(
        frame=canonical_frame(),
        strategy=_ShortThenCover(),
        starting_cash=10_000.0,
        seed=0,
    )
    d = result_to_dict(result)
    assert len(d["trades"]) == 1
    assert d["trades"][0]["direction"] == "sell"  # Side.SELL via .value
    json.dumps(d)  # SELL enum + ISO trade datetimes serialize cleanly

    loaded = read_result(write_result(result, tmp_path))
    assert loaded["trades"][0]["direction"] == "sell"
