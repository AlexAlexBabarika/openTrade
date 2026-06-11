"""Engine error hierarchy.

A single ``EngineError`` base so strategy authors and the runner can catch
"the engine rejected this" distinctly from arbitrary Python errors.
"""

from __future__ import annotations


class EngineError(Exception):
    """Base class for all backtesting-engine errors."""


class LookAheadError(EngineError):
    """Raised when strategy code tries to read a bar in the future."""


class UniverseError(EngineError):
    """Raised when a universe definition is invalid or a symbol is read
    outside its membership window."""


class ConstraintError(EngineError):
    """Raised when an order directly violates a hard portfolio constraint."""
