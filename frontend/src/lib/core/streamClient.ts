import type { OHLCVCandle } from './types';
import { wsLiveUrl } from './config';
import type { MarketDataProviderValue } from '$lib/features/market/marketDataProviders';

export type StreamConnectionState = 'connecting' | 'connected' | 'closed';

export interface CandleSubscription {
  provider: MarketDataProviderValue;
  symbol: string;
  interval: string;
}

export interface SnapshotMsg {
  type: 'snapshot';
  provider: MarketDataProviderValue;
  symbol: string;
  interval: string;
  candles: OHLCVCandle[];
}

export interface CandleMsg {
  type: 'candle';
  provider: MarketDataProviderValue;
  symbol: string;
  interval: string;
  candle: OHLCVCandle;
  is_final: boolean;
}

export interface StatusMsg {
  type: 'status';
  provider: MarketDataProviderValue;
  symbol: string;
  interval: string;
  state: 'connected' | 'reconnecting' | 'closed';
}

export interface ErrorMsg {
  type: 'error';
  code: string;
  message: string;
}

type ServerMsg =
  | SnapshotMsg
  | CandleMsg
  | StatusMsg
  | ErrorMsg
  | { type: 'pong' }
  | {
      type: 'quote';
      provider: string;
      symbol: string;
      price: number;
      ts: string;
    };

export interface CandleHandlers {
  onSnapshot?: (msg: SnapshotMsg) => void;
  onCandle?: (msg: CandleMsg) => void;
  onStatus?: (msg: StatusMsg) => void;
  onConnectionChange?: (state: StreamConnectionState) => void;
}

function candleKey(s: CandleSubscription): string {
  return `c:${s.provider}:${s.symbol}:${s.interval}`;
}

interface CandleEntry {
  sub: CandleSubscription;
  handlers: Set<CandleHandlers>;
  /** Initial `since` from the first subscriber (REST history end). */
  initialSince?: string;
  /** Most recent candle timestamp seen on the wire — used for gap-fill on reconnect. */
  lastSeenTs?: string;
}

export class StreamClient {
  #ws: WebSocket | null = null;
  #candleSubs = new Map<string, CandleEntry>();
  #reconnectAttempts = 0;
  #reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  #intentionalClose = false;
  #pendingSends: string[] = [];

  readonly reconnectDelayMs = 1000;
  readonly maxReconnectDelayMs = 30000;
  readonly maxReconnectAttempts = 10;

  subscribeCandles(
    sub: CandleSubscription,
    handlers: CandleHandlers,
    opts: { since?: string } = {},
  ): () => void {
    const key = candleKey(sub);
    let entry = this.#candleSubs.get(key);
    const isFirst = !entry;
    if (!entry) {
      entry = { sub, handlers: new Set(), initialSince: opts.since };
      this.#candleSubs.set(key, entry);
    }
    entry.handlers.add(handlers);

    this.#ensureConnected();
    if (isFirst) {
      this.#sendJson({
        type: 'subscribe',
        provider: sub.provider,
        symbol: sub.symbol,
        interval: sub.interval,
        since: entry.lastSeenTs ?? entry.initialSince,
      });
    }

    return () => {
      const e = this.#candleSubs.get(key);
      if (!e) return;
      e.handlers.delete(handlers);
      if (e.handlers.size === 0) {
        this.#candleSubs.delete(key);
        this.#sendJson({
          type: 'unsubscribe',
          provider: sub.provider,
          symbol: sub.symbol,
          interval: sub.interval,
        });
        if (this.#candleSubs.size === 0) {
          this.#disconnect();
        }
      }
    };
  }

  #ensureConnected(): void {
    if (
      this.#ws &&
      (this.#ws.readyState === WebSocket.OPEN ||
        this.#ws.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }
    this.#connect();
  }

  #connect(): void {
    this.#intentionalClose = false;
    this.#emitConnectionState('connecting');
    const ws = new WebSocket(wsLiveUrl());
    this.#ws = ws;

    ws.onopen = () => {
      this.#reconnectAttempts = 0;
      this.#emitConnectionState('connected');
      // Re-subscribe everything (covers reconnect; on first connect sends queued subs).
      for (const entry of this.#candleSubs.values()) {
        this.#sendJsonRaw({
          type: 'subscribe',
          provider: entry.sub.provider,
          symbol: entry.sub.symbol,
          interval: entry.sub.interval,
          since: entry.lastSeenTs ?? entry.initialSince,
        });
      }
      // Flush anything queued before open (typically subsumed by re-sub above, but safe).
      const queued = this.#pendingSends;
      this.#pendingSends = [];
      for (const m of queued) ws.send(m);
    };

    ws.onmessage = ev => {
      let msg: ServerMsg;
      try {
        msg = JSON.parse(ev.data as string) as ServerMsg;
      } catch {
        return;
      }
      this.#dispatch(msg);
    };

    ws.onclose = () => {
      this.#ws = null;
      this.#emitConnectionState('closed');
      if (this.#intentionalClose) return;
      if (this.#candleSubs.size === 0) return;
      if (this.#reconnectAttempts >= this.maxReconnectAttempts) return;
      const delay = this.#nextReconnectDelay();
      this.#reconnectTimer = setTimeout(() => {
        this.#reconnectAttempts += 1;
        this.#connect();
      }, delay);
    };

    ws.onerror = () => {
      // close handler will run; nothing extra to do.
    };
  }

  #disconnect(): void {
    this.#intentionalClose = true;
    if (this.#reconnectTimer) {
      clearTimeout(this.#reconnectTimer);
      this.#reconnectTimer = null;
    }
    if (this.#ws) {
      this.#ws.close();
      this.#ws = null;
    }
    this.#pendingSends = [];
  }

  #nextReconnectDelay(): number {
    const exp = this.reconnectDelayMs * 2 ** this.#reconnectAttempts;
    const capped = Math.min(exp, this.maxReconnectDelayMs);
    return Math.random() * capped;
  }

  #sendJson(payload: unknown): void {
    if (this.#ws && this.#ws.readyState === WebSocket.OPEN) {
      this.#ws.send(JSON.stringify(payload));
    } else {
      this.#pendingSends.push(JSON.stringify(payload));
    }
  }

  #sendJsonRaw(payload: unknown): void {
    this.#ws?.send(JSON.stringify(payload));
  }

  #emitConnectionState(state: StreamConnectionState): void {
    for (const entry of this.#candleSubs.values()) {
      for (const h of entry.handlers) h.onConnectionChange?.(state);
    }
  }

  #dispatch(msg: ServerMsg): void {
    if (
      msg.type === 'snapshot' ||
      msg.type === 'candle' ||
      msg.type === 'status'
    ) {
      const key = candleKey({
        provider: msg.provider as MarketDataProviderValue,
        symbol: msg.symbol,
        interval: msg.interval,
      });
      const entry = this.#candleSubs.get(key);
      if (!entry) return;
      if (msg.type === 'snapshot') {
        const last = msg.candles[msg.candles.length - 1];
        if (last) entry.lastSeenTs = maxIso(entry.lastSeenTs, last.timestamp);
      } else if (msg.type === 'candle') {
        entry.lastSeenTs = maxIso(entry.lastSeenTs, msg.candle.timestamp);
      }
      for (const h of entry.handlers) {
        if (msg.type === 'snapshot') h.onSnapshot?.(msg);
        else if (msg.type === 'candle') h.onCandle?.(msg);
        else h.onStatus?.(msg);
      }
    }
  }
}

function maxIso(a: string | undefined, b: string): string {
  if (!a) return b;
  return Date.parse(b) > Date.parse(a) ? b : a;
}

let _instance: StreamClient | null = null;

export function getStreamClient(): StreamClient {
  if (!_instance) _instance = new StreamClient();
  return _instance;
}
