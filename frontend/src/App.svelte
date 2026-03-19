<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import Header from './components/Header.svelte';
  import ErrorMessage from './components/ErrorMessage.svelte';
  import Chart from './components/Chart.svelte';
  import { API_BASE } from './lib/config';
  import { fetchMarketOHLCV } from './lib/marketData';
  import { readErrorMessage } from './lib/api';
  import { WSClient } from './lib/ws';
  import type { ConnectionStatus } from './lib/ws';
  import type { OHLCVCandle } from './lib/types';
  import { fetchSession } from './lib/auth';
  import type { MarketDataProviderValue } from './lib/marketDataProviders';

  let symbol = $state('AAPL');
  let period = $state('1mo');
  let interval = $state('1d');
  let source = $state<MarketDataProviderValue>('yfinance');
  let autoRefresh = $state(false);

  let errorMessage = $state<string | null>(null);
  let connectionStatus = $state<ConnectionStatus>('disconnected');
  let candles = $state<OHLCVCandle[]>([]);
  let isLoading = $state(false);
  let wsClient: WSClient | null = null;
  let refreshIntervalId: ReturnType<typeof setInterval> | null = null;

  async function loadMarketData(): Promise<void> {
    if (source === 'csv') {
      errorMessage = 'Choose a CSV file with the Load button, or pick another data source.';
      return;
    }
    errorMessage = null;
    isLoading = true;
    try {
      const data = await fetchMarketOHLCV(symbol, source, period, interval);
      candles = data.candles ?? [];
    } catch (e) {
      errorMessage = e instanceof Error ? e.message : 'Failed to load';
    } finally {
      isLoading = false;
    }
  }

  function startStream(): void {
    const sym = symbol.trim();
    if (!sym) {
      errorMessage = 'Enter a symbol';
      return;
    }
    errorMessage = null;
    if (wsClient) wsClient.disconnect();
    const streamCandles: OHLCVCandle[] = [];
    wsClient = new WSClient({
      symbol: sym,
      onCandle: c => {
        streamCandles.push(c);
        candles = [...streamCandles];
      },
      onStatus: s => {
        connectionStatus = s;
      },
      reconnectDelayMs: 3000,
      maxReconnectAttempts: 10,
    });
    wsClient.connect();
  }

  async function handleCsvUpload(file: File): Promise<void> {
    const sym = symbol.trim() || 'CSV';
    errorMessage = null;
    isLoading = true;
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await fetch(
        `${API_BASE}/data/csv?symbol=${encodeURIComponent(sym)}`,
        { method: 'POST', body: form },
      );
      if (!res.ok) throw new Error(await readErrorMessage(res));
      await res.json();
      candles = [];
      if (wsClient) wsClient.disconnect();
      const streamCandles: OHLCVCandle[] = [];
      wsClient = new WSClient({
        symbol: sym,
        onCandle: c => {
          streamCandles.push(c);
          candles = [...streamCandles];
        },
        onStatus: s => {
          connectionStatus = s;
        },
      });
      wsClient.connect();
    } catch (e) {
      errorMessage = e instanceof Error ? e.message : 'Upload failed';
    } finally {
      isLoading = false;
    }
  }

  // Auto-refresh effect
  $effect(() => {
    if (refreshIntervalId) {
      clearInterval(refreshIntervalId);
      refreshIntervalId = null;
    }
    if (autoRefresh) {
      refreshIntervalId = setInterval(() => {
        if (source !== 'csv') {
          loadMarketData().catch(() => {});
        }
      }, 60_000);
    }
  });

  onDestroy(() => {
    if (refreshIntervalId) clearInterval(refreshIntervalId);
    if (wsClient) wsClient.disconnect();
  });

  onMount(() => {
    fetchSession().catch(err => {
      console.warn('Session fetch failed:', err);
    });
  });

  // Initial load (default source: yfinance)
  loadMarketData().catch(() => {});
</script>

<div class="flex flex-col h-screen bg-background">
  <Header
    bind:symbol
    bind:period
    bind:interval
    bind:source
    bind:autoRefresh
    {connectionStatus}
    {isLoading}
    onload={loadMarketData}
    onstream={startStream}
    oncsvupload={handleCsvUpload}
  />
  <ErrorMessage message={errorMessage} />
  <Chart {candles} {symbol} />
</div>
