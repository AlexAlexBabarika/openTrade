# backend/tests/test_optimize_search.py
"""Deterministic enumeration of the parameter space."""

from __future__ import annotations

from backend.backtesting.optimize.search import grid, grid_size, random_search
from backend.backtesting.optimize.space import Choice, Int


def test_grid_is_the_cartesian_product_in_sorted_key_order() -> None:
    space = {"b": Int(1, 2), "a": Choice(["x", "y"])}
    combos = list(grid(space))
    # keys sorted -> ("a", "b"); product iterates last key fastest
    assert combos == [
        {"a": "x", "b": 1},
        {"a": "x", "b": 2},
        {"a": "y", "b": 1},
        {"a": "y", "b": 2},
    ]


def test_grid_size_matches_enumeration() -> None:
    space = {"a": Int(1, 10), "b": Int(1, 10)}
    assert grid_size(space) == 100
    assert grid_size(space) == len(list(grid(space)))


def test_random_search_is_deterministic_for_a_seed() -> None:
    space = {"a": Int(0, 100), "b": Int(0, 100)}
    a = list(random_search(space, n=20, seed=42))
    b = list(random_search(space, n=20, seed=42))
    assert a == b
    assert len(a) == 20
    assert all(set(c) == {"a", "b"} for c in a)


def test_random_search_changes_with_seed() -> None:
    space = {"a": Int(0, 100)}
    assert list(random_search(space, n=10, seed=1)) != list(
        random_search(space, n=10, seed=2)
    )
