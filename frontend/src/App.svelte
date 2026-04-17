<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import Header from './components/Header.svelte';
  import ErrorMessage from './components/ErrorMessage.svelte';
  import Chart from './components/Chart.svelte';
  import type { ChartApi } from './components/Chart.svelte';
  import Sidebar from './components/Sidebar.svelte';
  import PanelRight from '@lucide/svelte/icons/panel-right';
  import ChartOptionsMenu from './components/ChartOptionsMenu.svelte';
  import type {
    MovingAverageConfig,
    BollingerBandsConfig,
  } from './components/ChartOptionsMenu.svelte';
  import type { ChartType } from './lib/chartColours';
  import { fetchSMA, fetchEMA, fetchBBands } from './lib/indicators';
  import type { IndicatorPoint, BollingerBandsPoint } from './lib/types';
  import { fetchMarketOHLCV } from './lib/marketData';
  import { apiFetch, readErrorMessage } from './lib/api';
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
    loadChartSettingsFromStorage,
    persistChartSettings,
  } from './lib/chartColours';

  let symbol = $state('AAPL');
  let loadedSymbol = $state('');
  let period = $state(DEFAULT_MARKET_PERIOD);
  let interval = $state(DEFAULT_MARKET_INTERVAL);
  let source = $state<MarketDataProviderValue>('yfinance');
  let autoRefresh = $state(false);

  let errorMessage = $state<string | null>(null);
  let connectionStatus = $state<ConnectionStatus>('disconnected');
  let candles = $state.raw<OHLCVCandle[]>([]);
  let chartApi = $state<ChartApi | null>(null);
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
  let bbandsConfig = $state<BollingerBandsConfig>({
    enabled: savedSettings?.bbandsEnabled ?? false,
    period: 20,
    stdDev: 2,
    lineWidth: 1,
  });
  let smaPoints = $state<IndicatorPoint[]>([]);
  let emaPoints = $state<IndicatorPoint[]>([]);
  let bbandsPoints = $state<BollingerBandsPoint[]>([]);
  let colours = $state<ChartColours>(
    loadChartColoursFromStorage() ?? defaultChartColours(),
  );
  let hasCandles = $derived(candles.length > 0);
  let marketDataVersion = $state(0);
  let isLoading = $state(false);
  let sidebarVisible = $state(true);
  let lastClose = $derived(
    candles.length > 0 ? candles[candles.length - 1].close : null,
  );
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
      loadedSymbol = symbol;
      marketDataVersion += 1;
    } catch (e) {
      errorMessage = e instanceof Error ? e.message : 'Failed to load';
    } finally {
      isLoading = false;
    }
  }

  function startWsStream(
    provider: MarketDataProviderValue,
    sym: string,
    opts: { reconnectDelayMs?: number; maxReconnectAttempts?: number } = {},
  ): void {
    if (wsClient) wsClient.disconnect();
    const streamCandles: OHLCVCandle[] = [];
    candles = streamCandles;
    wsClient = new WSClient({
      provider,
      symbol: sym,
      onCandle: c => {
        streamCandles.push(c);
        chartApi?.appendCandle(c);
      },
      onStatus: s => {
        connectionStatus = s;
      },
      ...opts,
    });
    wsClient.connect();
  }

  function startStream(): void {
    const sym = symbol.trim();
    if (!sym) {
      errorMessage = 'Enter a symbol';
      return;
    }
    errorMessage = null;
    startWsStream(source, sym, {
      reconnectDelayMs: 3000,
      maxReconnectAttempts: 10,
    });
  }

  async function handleCsvUpload(file: File): Promise<void> {
    const sym = symbol.trim() || 'CSV';
    errorMessage = null;
    isLoading = true;
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await apiFetch(
        `/data/csv?symbol=${encodeURIComponent(sym)}`,
        { method: 'POST', body: form },
      );
      if (!res.ok) throw new Error(await readErrorMessage(res));
      await res.json();
      startWsStream('csv', sym);
    } catch (e) {
      errorMessage = e instanceof Error ? e.message : 'Upload failed';
    } finally {
      isLoading = false;
    }
  }

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

  const INDICATOR_DEBOUNCE_MS = 300;

  $effect(() => {
    const enabled = smaConfig.enabled;
    const period = smaConfig.period;
    const sym = loadedSymbol;
    marketDataVersion;
    if (!enabled || !hasCandles) {
      smaPoints = [];
      return;
    }
    const id = setTimeout(() => {
      fetchSMA(sym, period)
        .then(res => (smaPoints = res.points))
        .catch(e => {
          smaPoints = [];
          errorMessage = e instanceof Error ? e.message : 'Failed to load SMA';
        });
    }, INDICATOR_DEBOUNCE_MS);
    return () => clearTimeout(id);
  });

  $effect(() => {
    const enabled = emaConfig.enabled;
    const period = emaConfig.period;
    const sym = loadedSymbol;
    marketDataVersion;
    if (!enabled || !hasCandles) {
      emaPoints = [];
      return;
    }
    const id = setTimeout(() => {
      fetchEMA(sym, period)
        .then(res => (emaPoints = res.points))
        .catch(e => {
          emaPoints = [];
          errorMessage = e instanceof Error ? e.message : 'Failed to load EMA';
        });
    }, INDICATOR_DEBOUNCE_MS);
    return () => clearTimeout(id);
  });

  $effect(() => {
    const enabled = bbandsConfig.enabled;
    const period = bbandsConfig.period;
    const stdDev = bbandsConfig.stdDev;
    const sym = loadedSymbol;
    marketDataVersion;
    if (!enabled || !hasCandles) {
      bbandsPoints = [];
      return;
    }
    const id = setTimeout(() => {
      fetchBBands(sym, period, stdDev)
        .then(res => (bbandsPoints = res.points))
        .catch(e => {
          bbandsPoints = [];
          errorMessage = e instanceof Error ? e.message : 'Failed to load Bollinger Bands';
        });
    }, INDICATOR_DEBOUNCE_MS);
    return () => clearTimeout(id);
  });

  // Persist chart colours and settings to localStorage only when the page unloads,
  // avoiding excessive writes during drag operations in colour pickers.
  function persistOnUnload() {
    persistChartColours(colours);
    persistChartSettings({
      chartType,
      showArea,
      showVolume,
      smaEnabled: smaConfig.enabled,
      emaEnabled: emaConfig.enabled,
      bbandsEnabled: bbandsConfig.enabled,
    });
  }

  onMount(async () => {
    window.addEventListener('beforeunload', persistOnUnload);
    try {
      await fetchSession();
    } catch (err) {
      console.warn('Session fetch failed:', err);
    }
    loadMarketData().catch(() => {});
  });

  onDestroy(() => {
    persistOnUnload();
    window.removeEventListener('beforeunload', persistOnUnload);
    if (refreshIntervalId) clearInterval(refreshIntervalId);
    if (wsClient) wsClient.disconnect();
  });
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
  <div class="flex flex-1 min-h-0">
    <div class="flex-1 min-w-0 min-h-0 flex flex-col">
      <Chart
        {candles}
        {symbol}
        {chartType}
        {showArea}
        {showVolume}
        {smaPoints}
        {emaPoints}
        {bbandsPoints}
        smaLineWidth={smaConfig.lineWidth}
        emaLineWidth={emaConfig.lineWidth}
        bbandsLineWidth={bbandsConfig.lineWidth}
        {colours}
        bind:api={chartApi}
      />
    </div>
    {#if sidebarVisible}
      <Sidebar
        symbol={loadedSymbol}
        closePrice={lastClose}
        onhide={() => (sidebarVisible = false)}
      />
    {/if}
  </div>
  {#if !sidebarVisible}
    <button
      type="button"
      class="fixed bottom-10 right-18 z-40 inline-flex items-center justify-center h-9 w-9 rounded-md border border-border bg-background text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors shadow"
      aria-label="Show sidebar"
      onclick={() => (sidebarVisible = true)}
    >
      <PanelRight class="h-4 w-4" />
    </button>
  {/if}
  <ChartOptionsMenu
    bind:chartType
    bind:showArea
    bind:showVolume
    bind:smaConfig
    bind:emaConfig
    bind:bbandsConfig
    bind:colours
  />
</div>
