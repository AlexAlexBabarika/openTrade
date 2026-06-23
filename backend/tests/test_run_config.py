# backend/tests/test_run_config.py
from datetime import datetime, timezone

from backend.backtesting.multi.universe import Membership, Universe
from backend.backtesting.run_config import RunInputs, config_to_dict


def _t(day: int) -> datetime:
    return datetime(2020, 1, day, tzinfo=timezone.utc)


def test_default_costs_are_recorded_when_none():
    cfg = config_to_dict(
        RunInputs(code="x", params={}, data_version="v", seed=0, starting_cash=1e5)
    )
    assert cfg["costs"]["slippage"] == {"model": "FixedBpsSlippage", "bps": 5.0}
    assert cfg["costs"]["commission"] == {"model": "BpsCommission", "bps": 1.0}
    assert cfg["starting_cash"] == 1e5
    assert cfg["universe"] is None
    assert cfg["constraints"] is None


def test_universe_records_memberships_and_active_sets():
    uni = Universe([Membership("AAPL"), Membership("MSFT", start=_t(2))])
    cfg = config_to_dict(
        RunInputs(
            code="x",
            params={},
            data_version="v",
            seed=0,
            starting_cash=1e5,
            universe=uni,
        ),
        event_times=[_t(1), _t(2)],
    )
    assert {m["symbol"] for m in cfg["universe"]["memberships"]} == {"AAPL", "MSFT"}
    active_by_t = {row["t"]: row["active"] for row in cfg["universe"]["active"]}
    assert active_by_t[int(_t(1).timestamp())] == ["AAPL"]
    assert active_by_t[int(_t(2).timestamp())] == ["AAPL", "MSFT"]


def test_config_is_json_serializable():
    import json

    json.dumps(
        config_to_dict(
            RunInputs(
                code="x", params={"n": 5}, data_version="v", seed=1, starting_cash=1e5
            )
        )
    )
