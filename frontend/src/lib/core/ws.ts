import type { OHLCVCandle } from './types';
import { wsStreamUrl } from './config';
import type { MarketDataProviderValue } from '$lib/features/market/marketDataProviders';

export type ConnectionStatus =
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'error';

export interface WSClientOptions {
  provider: MarketDataProviderValue;
  symbol: string;
  onCandle: (c: OHLCVCandle) => void;
  onStatus?: (status: ConnectionStatus) => void;
  /** Base delay for exponential backoff; doubled each attempt up to maxReconnectDelayMs. */
  reconnectDelayMs?: number;
  /** Cap for the exponential backoff. */
  maxReconnectDelayMs?: number;
  maxReconnectAttempts?: number;
}

export class WSClient {
  private ws: WebSocket | null = null;
  private provider: MarketDataProviderValue;
  private symbol: string;
  private onCandle: (c: OHLCVCandle) => void;
  private onStatus?: (status: ConnectionStatus) => void;
  private reconnectDelayMs: number;
  private maxReconnectDelayMs: number;
  private maxReconnectAttempts: number;
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private intentionalClose = false;

  constructor(options: WSClientOptions) {
    this.provider = options.provider;
    this.symbol = options.symbol;
    this.onCandle = options.onCandle;
    this.onStatus = options.onStatus;
    this.reconnectDelayMs = options.reconnectDelayMs ?? 1000;
    this.maxReconnectDelayMs = options.maxReconnectDelayMs ?? 30000;
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? 10;
  }

  connect(): void {
    this.intentionalClose = false;
    this.reconnectAttempts = 0;
    this.doConnect();
  }

  private doConnect(): void {
    this.onStatus?.('connecting');
    const url = wsStreamUrl(this.provider, this.symbol);
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.onStatus?.('connected');
    };

    this.ws.onmessage = event => {
      try {
        const data = JSON.parse(event.data as string) as Record<
          string,
          unknown
        >;
        if (data.error) {
          this.onStatus?.('error');
          return;
        }
        if (
          typeof data.symbol === 'string' &&
          typeof data.timestamp === 'string' &&
          typeof data.open === 'number' &&
          typeof data.close === 'number'
        ) {
          this.onCandle(data as unknown as OHLCVCandle);
        }
      } catch {
        // ignore parse errors
      }
    };

    this.ws.onclose = () => {
      this.ws = null;
      this.onStatus?.('disconnected');
      if (
        !this.intentionalClose &&
        this.reconnectAttempts < this.maxReconnectAttempts
      ) {
        this.reconnectTimer = setTimeout(() => {
          this.reconnectAttempts++;
          this.doConnect();
        }, this.nextReconnectDelay());
      }
    };

    this.ws.onerror = () => {
      this.onStatus?.('error');
    };
  }

  /** Exponential backoff with full jitter to desync multiple clients. */
  private nextReconnectDelay(): number {
    const exp = this.reconnectDelayMs * 2 ** this.reconnectAttempts;
    const capped = Math.min(exp, this.maxReconnectDelayMs);
    return Math.random() * capped;
  }

  disconnect(): void {
    this.intentionalClose = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.onStatus?.('disconnected');
  }
}
