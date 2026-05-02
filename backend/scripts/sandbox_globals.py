"""Globals injected into the user-script namespace inside the child process."""

from __future__ import annotations

import builtins
from typing import Any

import numpy as np
import polars as pl

from backend.scripts import helpers
from backend.scripts.display import DisplayCollector


_SAFE_BUILTIN_NAMES: frozenset[str] = frozenset(
    {
        "abs",
        "all",
        "any",
        "bool",
        "bytes",
        "callable",
        "chr",
        "complex",
        "dict",
        "divmod",
        "enumerate",
        "filter",
        "float",
        "format",
        "frozenset",
        "hash",
        "hex",
        "int",
        "isinstance",
        "issubclass",
        "iter",
        "len",
        "list",
        "map",
        "max",
        "min",
        "next",
        "object",
        "oct",
        "ord",
        "pow",
        "print",
        "range",
        "repr",
        "reversed",
        "round",
        "set",
        "slice",
        "sorted",
        "str",
        "sum",
        "tuple",
        "type",
        "zip",
        # exceptions a user might reasonably catch
        "Exception",
        "ValueError",
        "TypeError",
        "KeyError",
        "IndexError",
        "ZeroDivisionError",
        "RuntimeError",
        "StopIteration",
        "True",
        "False",
        "None",
        # Allow `import` for the AST-whitelisted modules.
        "__import__",
    }
)


_SAFE_BUILTINS: dict[str, Any] = {
    name: getattr(builtins, name)
    for name in _SAFE_BUILTIN_NAMES
    if hasattr(builtins, name)
}


def build_globals(df: pl.DataFrame, collector: DisplayCollector) -> dict[str, Any]:
    """Build the globals dict for `exec(code, globals)`.

    `df` is expected to be a polars DataFrame with columns
    `timestamp/open/high/low/close/volume` (timestamp UTC).
    """
    return {
        "__builtins__": _SAFE_BUILTINS,
        # data
        "df": df,
        "time": df["timestamp"],
        "open": df["open"],
        "high": df["high"],
        "low": df["low"],
        "close": df["close"],
        "price": df["close"],
        "volume": df["volume"],
        # libs
        "pl": pl,
        "np": np,
        # helpers
        "display": collector,
        "crossover": helpers.crossover,
        "crossunder": helpers.crossunder,
        "compute_rsi": helpers.rsi,
        "compute_macd": helpers.macd,
        "compute_bbands": helpers.bbands,
        "compute_atr": helpers.atr,
    }
