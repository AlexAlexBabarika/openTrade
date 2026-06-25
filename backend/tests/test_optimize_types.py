# backend/tests/test_optimize_types.py
"""Sweep value types and objective-metric extraction."""

from __future__ import annotations

import math

from backend.backtesting.optimize.types import metric_value


def test_metric_value_reads_a_named_field() -> None:
    assert metric_value({"sharpe": 1.4, "calmar": 0.9}, "sharpe") == 1.4


def test_missing_or_none_metric_is_negative_infinity_for_maximization() -> None:
    assert metric_value({"sharpe": None}, "sharpe") == -math.inf
    assert metric_value({}, "sharpe") == -math.inf
