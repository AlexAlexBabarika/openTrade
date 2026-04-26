import { onDestroy } from 'svelte';
import { apiFetch, readErrorMessage } from '$lib/core/api';
import { WSClient, type ConnectionStatus } from '$lib/core/ws';
import type { OHLCVCandle } from '$lib/core/types';
import { fetchMarketOHLCV } from '$lib/features/market/marketData';
import { DEFAULT_MARKET_INTERVAL } from '$lib/features/market/marketIntervals';
import { DEFAULT_MARKET_PERIOD } from '$lib/features/market/marketPeriods';
import type { MarketDataProviderValue } from '$lib/features/market/marketDataProviders';

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
    } catch (e) {
      this.errorMessage = e instanceof Error ? e.message : 'Failed to load';
    } finally {
      this.isLoading = false;
      this.initialLoadDone = true;
    }
  };

  startStream = (): void => {
    const sym = this.symbol.trim();
    if (!sym) {
      this.errorMessage = 'Enter a symbol';
      return;
    }
    this.errorMessage = null;
    this.#startWsStream(this.source, sym, {
      reconnectDelayMs: 3000,
      maxReconnectAttempts: 10,
    });
  };

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
