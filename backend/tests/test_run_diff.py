from backend.backtesting.run_diff import diff_runs


def _blob(n, total_return, equity, trades):
    return {
        "meta": {
            "engine_version": "1.0.0",
            "data_version": "v1",
            "ast_hash": "h",
            "seed": 0,
        },
        "params": {"n": n},
        "config": {"starting_cash": 1e5},
        "metrics": {"total_return": total_return, "sharpe": 1.0},
        "equity": equity,
        "trades": trades,
    }


def _eq(t, v):
    return {"t": t, "value": v}


def _trade(sym, entry_t, direction, pnl):
    return {
        "symbol": sym,
        "entry_time": entry_t,
        "direction": direction,
        "exit_time": "x",
        "exit_price": 1.0,
        "pnl": pnl,
    }


def test_inputs_diff_shows_only_changed_param():
    a = _blob(10, 0.1, [], [])
    b = _blob(20, 0.1, [], [])
    diff = diff_runs(a, b)
    paths = {row["path"]: (row["a"], row["b"]) for row in diff["inputs_diff"]}
    assert paths == {"params.n": (10, 20)}


def test_metrics_diff_sorted_by_abs_delta():
    a = _blob(10, 0.10, [], [])
    b = _blob(10, 0.40, [], [])
    diff = diff_runs(a, b)
    top = diff["metrics_diff"][0]
    assert top["metric"] == "total_return"
    assert round(top["delta"], 2) == 0.30


def test_equity_overlay_aligns_and_residuals():
    a = _blob(10, 0.1, [_eq(1, 100.0), _eq(2, 110.0)], [])
    b = _blob(10, 0.1, [_eq(1, 100.0), _eq(2, 120.0)], [])
    overlay = diff_runs(a, b)["equity_overlay"]
    assert overlay["residual"] == [{"t": 1, "value": 0.0}, {"t": 2, "value": 10.0}]


def test_trades_diff_classifies():
    a = _blob(
        10,
        0.1,
        [],
        [_trade("AAPL", "t1", "buy", 5.0), _trade("MSFT", "t2", "buy", 1.0)],
    )
    b = _blob(
        10,
        0.1,
        [],
        [_trade("AAPL", "t1", "buy", 7.0), _trade("GOOG", "t3", "buy", 2.0)],
    )
    td = diff_runs(a, b)["trades_diff"]
    assert [c["key"] for c in td["changed"]] == [["AAPL", "t1", "buy"]]
    assert [c["key"] for c in td["only_in_a"]] == [["MSFT", "t2", "buy"]]
    assert [c["key"] for c in td["only_in_b"]] == [["GOOG", "t3", "buy"]]
