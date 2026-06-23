"""Semantic version of the backtesting engine.

Bump ONLY on a change that can alter results (cost-model default, fill-logic
fix, metric definition). Bumping flags older snapshots as stale; it never
recomputes them. Record each bump below.

Changelog:
  1.0.0 — initial versioned engine (reproducibility foundation).
"""

from __future__ import annotations

ENGINE_VERSION = "1.0.0"
