"""
StreamHub: refcounted fan-out from upstream provider streams to browser clients.

Skeleton only — interfaces, data structures, and lifecycle hooks. Provider
wiring (Binance, Twelve Data) and the `/ws/live` FastAPI endpoint land in
later steps.

Shape:
    (provider, symbol, interval) → SubscriptionGroup
        ├── one upstream task pulling provider.stream_ohlcv(...)
        ├── set[ClientSession] of subscribers
        └── ring buffer of last N events (snapshot for late joiners)

Refcount: when the last client unsubscribes, the upstream task is cancelled.
A single StreamHub instance lives per process; start/stop run in FastAPI's
lifespan.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from backend.models.market_data_models import MarketDataProviderEnum
from backend.streaming.protocol import ServerMessage, StreamEvent

SubscriptionKey = tuple[
    MarketDataProviderEnum, str, str
]  # (provider, symbol, interval)

# Bounded ring buffer of recent events per subscription, replayed on join.
SNAPSHOT_BUFFER_SIZE = 128


SendFn = Callable[[ServerMessage], Awaitable[None]]


@dataclass
class ClientSession:
    """One browser tab. Owns its own send coroutine and tracked subscriptions."""

    client_id: str
    send: SendFn
    subscriptions: set[SubscriptionKey] = field(default_factory=set)


@dataclass
class SubscriptionGroup:
    """All clients sharing one upstream (provider, symbol, interval) stream."""

    key: SubscriptionKey
    clients: set[ClientSession] = field(default_factory=set)
    recent: deque[StreamEvent] = field(
        default_factory=lambda: deque(maxlen=SNAPSHOT_BUFFER_SIZE)
    )
    upstream_task: asyncio.Task[None] | None = None


class StreamHub:
    """Per-process singleton. Not thread-safe; assumes single asyncio loop."""

    def __init__(self) -> None:
        self._groups: dict[SubscriptionKey, SubscriptionGroup] = {}
        self._lock = asyncio.Lock()

    # -- lifecycle ---------------------------------------------------------

    async def start(self) -> None:
        """Called from FastAPI lifespan startup. No-op for the skeleton."""
        return None

    async def stop(self) -> None:
        """Cancel all upstream tasks and drop all groups."""
        async with self._lock:
            for group in self._groups.values():
                if group.upstream_task is not None:
                    group.upstream_task.cancel()
            self._groups.clear()

    # -- subscription management ------------------------------------------

    async def subscribe(
        self, client: ClientSession, key: SubscriptionKey
    ) -> SubscriptionGroup:
        """Attach `client` to the group for `key`, spawning upstream if new."""
        async with self._lock:
            group = self._groups.get(key)
            if group is None:
                group = SubscriptionGroup(key=key)
                self._groups[key] = group
                group.upstream_task = asyncio.create_task(self._run_upstream(group))
            group.clients.add(client)
            client.subscriptions.add(key)
            return group

    async def unsubscribe(self, client: ClientSession, key: SubscriptionKey) -> None:
        """Detach `client`; cancel upstream if no clients remain."""
        async with self._lock:
            group = self._groups.get(key)
            if group is None:
                return
            group.clients.discard(client)
            client.subscriptions.discard(key)
            if not group.clients:
                if group.upstream_task is not None:
                    group.upstream_task.cancel()
                del self._groups[key]

    async def disconnect(self, client: ClientSession) -> None:
        """Drop all of a client's subscriptions (e.g. on socket close)."""
        for key in list(client.subscriptions):
            await self.unsubscribe(client, key)

    # -- internals (provider wiring lands later) ---------------------------

    async def _run_upstream(self, group: SubscriptionGroup) -> None:
        """Pull events from the provider and fan out to subscribers.

        Provider wiring is intentionally absent in this skeleton. The real
        implementation will:
          1. Resolve the provider, call `provider.stream_ohlcv(symbol, interval)`.
          2. For each StreamEvent: append to `group.recent`, translate to a
             ServerMessage, and `await client.send(...)` for each subscriber.
          3. On upstream error: emit a `status: reconnecting` to all clients
             and reconnect with backoff.
        """
        raise NotImplementedError("Provider wiring lands in a later step")


_hub: StreamHub | None = None


def get_hub() -> StreamHub:
    """Process-wide singleton accessor."""
    global _hub
    if _hub is None:
        _hub = StreamHub()
    return _hub
