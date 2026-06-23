from backend.backtesting.run_id import run_key, run_status
from backend.backtesting.version import ENGINE_VERSION


def _kwargs(**over):
    base = dict(
        engine_version="1.0.0",
        ast_hash="abc",
        params={"n": 10},
        data_version="v1",
        seed=0,
        config={"starting_cash": 1e5},
    )
    base.update(over)
    return base


def test_identical_inputs_collide():
    assert run_key(**_kwargs()) == run_key(**_kwargs())


def test_param_change_changes_id():
    assert run_key(**_kwargs()) != run_key(**_kwargs(params={"n": 20}))


def test_key_is_order_independent_for_params():
    a = run_key(**_kwargs(params={"a": 1, "b": 2}))
    b = run_key(**_kwargs(params={"b": 2, "a": 1}))
    assert a == b


def test_status_flags_stale_engine():
    fresh = run_status({"engine_version": ENGINE_VERSION})
    stale = run_status({"engine_version": "0.9.0"})
    assert fresh == {
        "stale": False,
        "recorded": ENGINE_VERSION,
        "current": ENGINE_VERSION,
    }
    assert stale["stale"] is True and stale["recorded"] == "0.9.0"
