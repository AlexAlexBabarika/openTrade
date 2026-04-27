import { onDestroy } from 'svelte';
import { apiFetch, readErrorMessage } from '$lib/core/api';
import { WSClient, type ConnectionStatus } from '$lib/core/ws';
import type { OHLCVCandle } from '$lib/core/types';
import { fetchMarketOHLCV } from '$lib/features/market/marketData';
import { DEFAULT_MARKET_INTERVAL } from '$lib/features/market/marketIntervals';
import { DEFAULT_MARKET_PERIOD } from '$lib/features/market/marketPeriods';
import {
  providerSupportsWs,
  type MarketDataProviderValue,
} from '$lib/features/market/marketDataProviders';
import {
  subscribeMarketStream,
  type StreamStatus,
} from '$lib/features/market/streaming';

export type ChartApiLike = { appendCandle: (c: OHLCVCandle) => void };

export interface ChartControllerOptions {
  initialSymbol?: string;
  initialSource?: MarketDataProviderValue;
  onSymbolFetched?: (
    symbol: string,
    source: MarketDataProviderValue,
    candleCount: number,
  ) => void;
}

export class ChartController {
  symbol = $state('AAPL');
  loadedSymbol = $state('');
  period = $state<string>(DEFAULT_MARKET_PERIOD);
  interval = $state<string>(DEFAULT_MARKET_INTERVAL);
  source = $state<MarketDataProviderValue>('yfinance');
  autoRefresh = $state(false);

  errorMessage = $state<string | null>(null);
  connectionStatus = $state<ConnectionStatus>('disconnected');
  candles = $state.raw<OHLCVCandle[]>([]);
  chartApi = $state<ChartApiLike | null>(null);
  isLoading = $state(false);
  marketDataVersion = $state(0);
  initialLoadDone = $state(false);

  #wsClient: WSClient | null = null;
  #liveUnsubscribe: (() => void) | null = null;
  #refreshIntervalId: ReturnType<typeof setInterval> | null = null;
  #onSymbolFetched?: ChartControllerOptions['onSymbolFetched'];

  constructor(opts: ChartControllerOptions = {}) {
    if (opts.initialSymbol !== undefined) this.symbol = opts.initialSymbol;
    if (opts.initialSource !== undefined) this.source = opts.initialSource;
    this.#onSymbolFetched = opts.onSymbolFetched;

    $effect(() => {
      if (this.#refreshIntervalId) {
        clearInterval(this.#refreshIntervalId);
        this.#refreshIntervalId = null;
      }
      if (this.autoRefresh) {
        this.#refreshIntervalId = setInterval(() => {
          if (this.source !== 'csv') {
            void this.loadMarketData();
          }
        }, 60_000);
      }
    });

    $effect(() => {
      this.period;
      this.interval;
      if (!this.initialLoadDone) return;
      if (this.source === 'csv') return;
      void this.loadMarketData();
    });

    onDestroy(() => {
      if (this.#refreshIntervalId) clearInterval(this.#refreshIntervalId);
      if (this.#wsClient) this.#wsClient.disconnect();
      if (this.#liveUnsubscribe) this.#liveUnsubscribe();
    });
  }

  loadMarketData = async (): Promise<void> => {
    if (this.source === 'csv') {
      this.errorMessage =
        'Choose a CSV file with the Load button, or pick another data source.';
      this.initialLoadDone = true;
      return;
    }
    this.errorMessage = null;
    this.isLoading = true;
    try {
      const data = await fetchMarketOHLCV(
        this.symbol,
        this.source,
        this.period,
        this.interval,
      );
      this.candles = data.candles ?? [];
      this.loadedSymbol = this.symbol;
      this.marketDataVersion += 1;
      this.#onSymbolFetched?.(
        this.symbol,
        this.source,
        data.candles?.length ?? 0,
      );
      if (providerSupportsWs(this.source)) {
        this.#startLiveStream(this.source, this.symbol.trim(), this.interval);
      } else if (this.#liveUnsubscribe) {
        this.#liveUnsubscribe();
        this.#liveUnsubscribe = null;
      }
    } catch (e) {
      this.errorMessage = e instanceof Error ? e.message : 'Failed to load';
    } finally {
      this.isLoading = false;
      this.initialLoadDone = true;
    }
  };

  startStream = (): void => {
    // Toggle: if a stream is already active, clicking Stream stops it.
    if (this.#liveUnsubscribe || this.#wsClient) {
      this.stopStream();
      return;
    }
    const sym = this.symbol.trim();
    if (!sym) {
      this.errorMessage = 'Enter a symbol';
      return;
    }
    this.errorMessage = null;
    if (this.source === 'csv') {
      this.#startWsStream('csv', sym);
      return;
    }
    if (!providerSupportsWs(this.source)) {
      this.errorMessage = `Live streaming is not available for ${this.source}.`;
      return;
    }
    this.#startLiveStream(this.source, sym, this.interval);
  };

  stopStream = (): void => {
    if (this.#liveUnsubscribe) {
      this.#liveUnsubscribe();
      this.#liveUnsubscribe = null;
    }
    if (this.#wsClient) {
      this.#wsClient.disconnect();
      this.#wsClient = null;
    }
    this.connectionStatus = 'disconnected';
  };

  #startLiveStream(
    provider: MarketDataProviderValue,
    sym: string,
    interval: string,
  ): void {
    if (this.#wsClient) {
      this.#wsClient.disconnect();
      this.#wsClient = null;
    }
    if (this.#liveUnsubscribe) {
      this.#liveUnsubscribe();
      this.#liveUnsubscribe = null;
    }

    const existing = this.candles ?? [];
    const historyEndIso = existing.length
      ? existing[existing.length - 1].timestamp
      : undefined;
    const liveCandles: OHLCVCandle[] = existing.slice();
    this.candles = liveCandles;

    const mapStatus = (s: StreamStatus): ConnectionStatus =>
      s === 'connected'
        ? 'connected'
        : s === 'connecting'
          ? 'connecting'
          : s === 'error'
            ? 'error'
            : 'disconnected';

    this.#liveUnsubscribe = subscribeMarketStream({
      provider,
      symbol: sym,
      interval,
      historyEndIso,
      onCandle: (c, _isFinal) => {
        const last = liveCandles[liveCandles.length - 1];
        if (last && last.timestamp === c.timestamp) {
          liveCandles[liveCandles.length - 1] = c;
        } else {
          liveCandles.push(c);
        }
        this.chartApi?.appendCandle(c);
      },
      onStatus: s => {
        this.connectionStatus = mapStatus(s);
      },
    });
  }

  handleCsvUpload = async (file: File): Promise<void> => {
    const sym = this.symbol.trim() || 'CSV';
    this.errorMessage = null;
    this.isLoading = true;
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await apiFetch(
        `/data/csv?symbol=${encodeURIComponent(sym)}`,
        { method: 'POST', body: form },
      );
      if (!res.ok) throw new Error(await readErrorMessage(res));
      await res.json();
      this.#startWsStream('csv', sym);
    } catch (e) {
      this.errorMessage = e instanceof Error ? e.message : 'Upload failed';
    } finally {
      this.isLoading = false;
    }
  };

  #startWsStream(
    provider: MarketDataProviderValue,
    sym: string,
    opts: { reconnectDelayMs?: number; maxReconnectAttempts?: number } = {},
  ): void {
    if (this.#liveUnsubscribe) {
      this.#liveUnsubscribe();
      this.#liveUnsubscribe = null;
    }
    if (this.#wsClient) this.#wsClient.disconnect();
    const streamCandles: OHLCVCandle[] = [];
    this.candles = streamCandles;
    this.#wsClient = new WSClient({
      provider,
      symbol: sym,
      onCandle: c => {
        streamCandles.push(c);
        this.chartApi?.appendCandle(c);
      },
      onStatus: s => {
        this.connectionStatus = s;
      },
      ...opts,
    });
    this.#wsClient.connect();
  }
}
