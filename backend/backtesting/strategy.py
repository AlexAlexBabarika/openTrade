"""The strategy authoring contract.

Strategy code subclasses ``Strategy`` and implements ``on_bar``. The engine owns
the loop and calls ``on_bar`` once per revealed bar with the context; this is
what keeps the clock — and therefore look-ahead prevention — in the engine's
hands rather than the strategy's.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.backtesting.context import Context


class Strategy:
    def on_bar(self, ctx: "Context") -> None:
        """Called once per bar. Override to place orders via ctx."""
        raise NotImplementedError
