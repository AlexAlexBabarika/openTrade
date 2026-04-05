<script lang="ts">
  import { onDestroy, onMount, untrack } from 'svelte';
  import Header from './components/Header.svelte';
  import ErrorMessage from './components/ErrorMessage.svelte';
  import Chart from './components/Chart.svelte';
  import ChartOptionsMenu from './components/ChartOptionsMenu.svelte';
  import type {
    ChartType,
    MovingAverageConfig,
  } from './components/ChartOptionsMenu.svelte';
  import { fetchSMA, fetchEMA } from './lib/indicators';
  import type { IndicatorPoint } from './lib/types';
  import { API_BASE } from './lib/config';
  import { fetchMarketOHLCV } from './lib/marketData';
  import { readErrorMessage } from './lib/api';
  import { WSClient } from './lib/ws';
  import type { ConnectionStatus } from './lib/ws';
  import type { OHLCVCandle } from './lib/types';
  import { fetchSession } from './lib/auth';
  import type { MarketDataProviderValue } from './lib/marketDataProviders';
  import { DEFAULT_MARKET_INTERVAL } from './lib/marketIntervals';
  import { DEFAULT_MARKET_PERIOD } from './lib/marketPeriods';
  import type { ChartColours } from './lib/chartColours';
  import {
    defaultChartColours,
    loadChartColoursFromStorage,
    persistChartColours,
    snapshotChartColours,
    loadChartSettingsFromStorage,
    persistChartSettings,
  } from './lib/chartColours';

  let symbol = $state('AAPL');
  let period = $state(DEFAULT_MARKET_PERIOD);
  let interval = $state(DEFAULT_MARKET_INTERVAL);
  let source = $state<MarketDataProviderValue>('yfinance');
  let autoRefresh = $state(false);

  let errorMessage = $state<string | null>(null);
  let connectionStatus = $state<ConnectionStatus>('disconnected');
  let candles = $state<OHLCVCandle[]>([]);
  const savedSettings = loadChartSettingsFromStorage();
  let chartType = $state<ChartType>(savedSettings?.chartType ?? 'candlestick');
  let showArea = $state(savedSettings?.showArea ?? true);
  let showVolume = $state(savedSettings?.showVolume ?? true);
  let smaConfig = $state<MovingAverageConfig>({
    enabled: savedSettings?.smaEnabled ?? false,
    period: 20,
    lineWidth: 2,
  });
  let emaConfig = $state<MovingAverageConfig>({
    enabled: savedSettings?.emaEnabled ?? false,
    period: 20,
    lineWidth: 2,
  });
  let smaPoints = $state<IndicatorPoint[]>([]);
  let emaPoints = $state<IndicatorPoint[]>([]);
  let colours = $state<ChartColours>(
    loadChartColoursFromStorage() ?? defaultChartColours(),
  );
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
      provider: source,
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
        provider: 'csv',
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

  // Fetch SMA when enabled or config changes
  $effect(() => {
    const cfg = smaConfig;
    const sym = symbol;
    if (!cfg.enabled || untrack(() => candles).length === 0) {
      smaPoints = [];
      return;
    }
    fetchSMA(sym, cfg.period)
      .then(res => (smaPoints = res.points))
      .catch(e => {
        smaPoints = [];
        errorMessage = e instanceof Error ? e.message : 'Failed to load SMA';
      });
  });

  // Fetch EMA when enabled or config changes
  $effect(() => {
    const cfg = emaConfig;
    const sym = symbol;
    if (!cfg.enabled || untrack(() => candles).length === 0) {
      emaPoints = [];
      return;
    }
    fetchEMA(sym, cfg.period)
      .then(res => (emaPoints = res.points))
      .catch(e => {
        emaPoints = [];
        errorMessage = e instanceof Error ? e.message : 'Failed to load EMA';
      });
  });

  // Persist chart colours and settings to localStorage only when the page unloads,
  // avoiding excessive writes during drag operations in colour pickers.
  function persistOnUnload() {
    persistChartColours(snapshotChartColours(colours));
    persistChartSettings({
      chartType,
      showArea,
      showVolume,
      smaEnabled: smaConfig.enabled,
      emaEnabled: emaConfig.enabled,
    });
  }

  onMount(() => {
    window.addEventListener('beforeunload', persistOnUnload);
    fetchSession().catch(err => {
      console.warn('Session fetch failed:', err);
    });
  });

  onDestroy(() => {
    persistOnUnload();
    window.removeEventListener('beforeunload', persistOnUnload);
    if (refreshIntervalId) clearInterval(refreshIntervalId);
    if (wsClient) wsClient.disconnect();
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
  <ErrorMessage bind:message={errorMessage} />
  <Chart
    {candles}
    {symbol}
    {chartType}
    {showArea}
    {showVolume}
    {smaPoints}
    {emaPoints}
    smaLineWidth={smaConfig.lineWidth}
    emaLineWidth={emaConfig.lineWidth}
    {colours}
  />
  <ChartOptionsMenu
    bind:chartType
    bind:showArea
    bind:showVolume
    bind:smaConfig
    bind:emaConfig
    bind:colours
  />
</div>
