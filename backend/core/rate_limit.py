"""
Simple in-memory sliding-window rate limiting (per client IP).

**Limitations** (by design for a small single-node app):

- **Per process**: each Uvicorn/Gunicorn worker has its own counters; effective
  budget is roughly ``limit × number of workers``.
- **Key = client IP** from ``request.client.host``; clients behind the same NAT
  share one bucket. For production behind a proxy, consider reading
  ``X-Forwarded-For`` (carefully, to avoid spoofing) — not implemented here.
- **429 + Retry-After**: callers get ``Retry-After`` set to the full window
  length in seconds (conservative hint, not exact time-until-slot).
"""

from __future__ import annotations

import os
import threading
from collections import defaultdict, deque
from time import monotonic

_lock = threading.Lock()
_windows: dict[str, deque[float]] = defaultdict(deque)

# Defaults; override via env for ops tuning
_MAX = int(os.environ.get("MARKET_RATE_LIMIT_MAX", "120"))
_WINDOW_SEC = float(os.environ.get("MARKET_RATE_LIMIT_WINDOW_SEC", "60"))


def retry_after_seconds() -> int:
    """Seconds to advertise on 429 ``Retry-After`` (whole window, conservative)."""
    return max(1, int(_WINDOW_SEC))


def allow(key: str) -> bool:
    """Return True if request is allowed; False if over limit."""
    now = monotonic()
    with _lock:
        q = _windows[key]
        while q and now - q[0] > _WINDOW_SEC:
            q.popleft()
        if len(q) >= _MAX:
            return False
        q.append(now)
        return True


def client_key(host: str | None) -> str:
    return host or "unknown"
