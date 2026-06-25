# backend/tests/test_optimize_space.py
"""Parameter schema: enumeration (grid), sampling (random), and round-trip."""

from __future__ import annotations

import random

import pytest

from backend.backtesting.optimize.space import Choice, Float, Int, parse_schema


def test_int_values_are_inclusive_and_stepped() -> None:
    assert Int(5, 20, step=5).values() == [5, 10, 15, 20]


def test_float_values_are_inclusive_and_rounded() -> None:
    # 0.5 -> 2.0 step 0.5 stays exact under rounding to the step's decimals.
    assert Float(0.5, 2.0, step=0.5).values() == [0.5, 1.0, 1.5, 2.0]


def test_float_values_handle_scientific_notation_steps() -> None:
    # repr(1e-05) is "1e-05"; the grid must not collapse to a single 0.0.
    assert Float(0.0, 0.0003, step=1e-05).values()[:4] == [0.0, 1e-05, 2e-05, 3e-05]


def test_choice_values_preserve_declared_order() -> None:
    assert Choice(["trend", "meanrev"]).values() == ["trend", "meanrev"]


def test_sample_is_deterministic_for_a_seed() -> None:
    p = Int(0, 100, step=1)
    a = [p.sample(random.Random(7)) for _ in range(1)]
    b = [p.sample(random.Random(7)) for _ in range(1)]
    assert a == b
    assert 0 <= a[0] <= 100


def test_parse_schema_reads_a_params_declaration() -> None:
    ns = {"params": {"fast": Int(5, 50, step=5), "regime": Choice(["a", "b"])}}
    schema = parse_schema(ns)
    assert set(schema) == {"fast", "regime"}
    assert schema["fast"].values()[0] == 5


def test_parse_schema_rejects_a_non_param_value() -> None:
    with pytest.raises(ValueError, match="not a parameter"):
        parse_schema({"params": {"fast": 5}})


def test_to_dict_round_trips() -> None:
    for p in (Int(5, 50, step=5), Float(0.5, 5.0, step=0.5), Choice([1, 2, 3])):
        from backend.backtesting.optimize.space import param_from_dict

        assert param_from_dict(p.to_dict()).values() == p.values()
