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
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from backend.market import cache
from backend.market.data_sources.binance_loader import BinanceProvider
from backend.market.data_sources.marketdataprovider import MarketDataProvider
from backend.models.market_data_models import MarketDataProviderEnum
from backend.streaming.protocol import (
    CandleMessage,
    ServerMessage,
    SnapshotMessage,
    StatusMessage,
    StreamEvent,
)

logger = logging.getLogger(__name__)

SubscriptionKey = tuple[
    MarketDataProviderEnum, str, str
]  # (provider, symbol, interval)

# Bounded ring buffer of recent events per subscription, replayed on join.
SNAPSHOT_BUFFER_SIZE = 128


SendFn = Callable[[ServerMessage], Awaitable[None]]


@dataclass(eq=False)
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
        """Attach `client` to the group for `key`, spawning upstream if new.

        If the group already has buffered events, replay the most recent
        candles to the joining client as a snapshot.
        """
        async with self._lock:
            group = self._groups.get(key)
            spawned = False
            if group is None:
                group = SubscriptionGroup(key=key)
                self._groups[key] = group
                group.upstream_task = asyncio.create_task(self._run_upstream(group))
                spawned = True
            group.clients.add(client)
            client.subscriptions.add(key)
            snapshot_candles = [e.candle for e in group.recent if e.candle is not None]
        if not spawned and snapshot_candles:
            provider, symbol, interval = key
            await client.send(
                SnapshotMessage(
                    provider=provider,
                    symbol=symbol,
                    interval=interval,
                    candles=snapshot_candles,
                )
            )
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

    # -- internals --------------------------------------------------------

    async def _run_upstream(self, group: SubscriptionGroup) -> None:
        """Pull events from the provider and fan out to subscribers."""
        provider_enum, symbol, interval = group.key
        provider = _resolve_streaming_provider(provider_enum)
        try:
            async for event in provider.stream_ohlcv(symbol, interval):
                group.recent.append(event)
                if event.kind == "candle_close" and event.candle is not None:
                    # Keep cache consistent with REST/replay paths.
                    existing = cache.get_cached(provider_enum.value, symbol) or []
                    cache.set_cached(
                        provider_enum.value, symbol, [*existing, event.candle]
                    )
                if event.candle is not None:
                    msg: ServerMessage = CandleMessage(
                        provider=provider_enum,
                        symbol=symbol,
                        interval=interval,
                        candle=event.candle,
                        is_final=event.is_final,
                    )
                    await self._broadcast(group, msg)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Upstream stream failed for %s", group.key)
            await self._broadcast(
                group,
                StatusMessage(
                    provider=provider_enum,
                    symbol=symbol,
                    interval=interval,
                    state="closed",
                ),
            )
            # Reconnect/backoff lands in step 6; for the happy path we let the
            # task end and rely on a fresh subscribe to retry.
            raise exc

    @staticmethod
    async def _broadcast(group: SubscriptionGroup, msg: ServerMessage) -> None:
        for client in list(group.clients):
            try:
                await client.send(msg)
            except Exception:
                logger.debug("Send failed; client will be cleaned up on disconnect")


def _resolve_streaming_provider(
    name: MarketDataProviderEnum,
) -> MarketDataProvider:
    """Map provider enum → provider instance for streaming.

    Happy-path scope: Binance only. Twelve Data lands in step 8.
    """
    if name == MarketDataProviderEnum.binance:
        return BinanceProvider()
    raise NotImplementedError(f"Streaming not implemented for provider '{name}'")


_hub: StreamHub | None = None


def get_hub() -> StreamHub:
    """Process-wide singleton accessor."""
    global _hub
    if _hub is None:
        _hub = StreamHub()
    return _hub
