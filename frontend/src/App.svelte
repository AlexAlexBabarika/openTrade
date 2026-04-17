<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import TopHeader from './components/TopHeader.svelte';
  import BottomHeader from './components/BottomHeader.svelte';
  import ErrorMessage from './components/ErrorMessage.svelte';
  import Chart from './components/Chart.svelte';
  import type { ChartApi } from './components/Chart.svelte';
  import Sidebar from './components/Sidebar.svelte';
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
  import type {
    TickerGroup,
    FlaggedPriority,
    PriorityConflict,
    TickerPriority,
  } from './lib/tickers';
  import {
    loadGroupsFromStorage,
    persistGroups,
    loadSelectedGroupName,
    persistSelectedGroupName,
    loadSelectedPriority,
    persistSelectedPriority,
    addGroup,
    renameGroup,
    duplicateGroup,
    deleteGroup,
    clearGroup,
    addTickerToGroup,
    removeTickerFromGroup,
    setTickerPriority,
    collectTickersByPriority,
    priorityCounts as computePriorityCounts,
    setPriorityEverywhere,
    removeTickerEverywhere,
    findPriorityConflict,
  } from './lib/tickers';
  import { fetchLastClose, type TickerQuote } from './lib/tickerQuotes';
  import { untrack } from 'svelte';
  import TextPromptDialog from './components/TextPromptDialog.svelte';
  import PriorityConflictDialog from './components/PriorityConflictDialog.svelte';

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

  const initialGroups = loadGroupsFromStorage();
  let groups = $state<TickerGroup[]>(initialGroups);
  let selectedGroupName = $state(loadSelectedGroupName(initialGroups));
  let selectedPriority = $state<FlaggedPriority | null>(loadSelectedPriority());
  let groupDialogMode = $state<null | 'add' | 'rename'>(null);
  let addSymbolDialogOpen = $state(false);
  let priorityConflictState = $state<{
    symbol: string;
    desired: TickerPriority;
    conflict: PriorityConflict;
  } | null>(null);

  $effect(() => {
    persistGroups(groups);
  });
  $effect(() => {
    persistSelectedGroupName(selectedGroupName);
  });
  $effect(() => {
    persistSelectedPriority(selectedPriority);
  });

  let currentGroup = $derived(groups.find(g => g.name === selectedGroupName));

  function handleDuplicateGroup() {
    const result = duplicateGroup(groups, selectedGroupName);
    if (!result) return;
    groups = result.groups;
    selectedGroupName = result.newName;
  }

  function handleDeleteGroup() {
    const next = deleteGroup(groups, selectedGroupName);
    if (!next) return;
    groups = next;
    selectedGroupName = next[0].name;
  }

  function handleClearGroup() {
    groups = clearGroup(groups, selectedGroupName);
  }

  function openAddDialog() {
    groupDialogMode = 'add';
  }

  function openRenameDialog() {
    groupDialogMode = 'rename';
  }

  function handleGroupDialogSubmit(name: string) {
    if (groupDialogMode === 'add') {
      groups = addGroup(groups, name);
      selectedGroupName = name;
      selectedPriority = null;
    } else if (groupDialogMode === 'rename') {
      groups = renameGroup(groups, selectedGroupName, name);
      selectedGroupName = name;
    }
  }

  function handleAddSymbolSubmit(sym: string) {
    groups = addTickerToGroup(groups, selectedGroupName, sym);
  }

  function handleSelectGroup(name: string) {
    selectedGroupName = name;
    selectedPriority = null;
  }

  function handleSelectPriority(p: FlaggedPriority) {
    selectedPriority = p;
  }

  function handleDeleteTicker(sym: string) {
    groups = selectedPriority
      ? removeTickerEverywhere(groups, sym)
      : removeTickerFromGroup(groups, selectedGroupName, sym);
  }

  function handleSetPriority(sym: string, priority: TickerPriority) {
    if (selectedPriority) {
      groups = setPriorityEverywhere(groups, sym, priority);
      return;
    }
    const conflict = findPriorityConflict(
      groups,
      sym,
      priority,
      selectedGroupName,
    );
    if (conflict) {
      priorityConflictState = { symbol: sym, desired: priority, conflict };
      return;
    }
    groups = setTickerPriority(groups, selectedGroupName, sym, priority);
  }

  function resolveConflictKeepExisting() {
    if (!priorityConflictState) return;
    const { symbol: sym, conflict } = priorityConflictState;
    groups = setTickerPriority(
      groups,
      selectedGroupName,
      sym,
      conflict.existingPriority,
    );
    priorityConflictState = null;
  }

  function resolveConflictSwitchGroup(groupName: string) {
    selectedGroupName = groupName;
    selectedPriority = null;
    priorityConflictState = null;
  }

  let groupDialogInitial = $derived(
    groupDialogMode === 'rename' ? selectedGroupName : '',
  );
  let groupDialogExistingNames = $derived(groups.map(g => g.name));
  let currentTickers = $derived(currentGroup?.tickers ?? []);
  let currentTickerSymbols = $derived(currentTickers.map(t => t.symbol));
  let displayTickers = $derived(
    selectedPriority
      ? collectTickersByPriority(groups, selectedPriority)
      : currentTickers,
  );
  let priorityCountsMap = $derived(computePriorityCounts(groups));

  let tickerQuotes = $state<Record<string, TickerQuote>>({});

  $effect(() => {
    const currentSource = source;
    const tickers = displayTickers;
    if (currentSource === 'csv') return;

    const snapshot = untrack(() => tickerQuotes);
    const missing = tickers.filter(t => {
      const entry = snapshot[`${currentSource}:${t.symbol}`];
      return !entry || entry.status === 'error';
    });
    if (missing.length === 0) return;

    const seeded: Record<string, TickerQuote> = { ...snapshot };
    for (const t of missing) {
      seeded[`${currentSource}:${t.symbol}`] = { status: 'loading' };
    }
    tickerQuotes = seeded;

    for (const t of missing) {
      const key = `${currentSource}:${t.symbol}`;
      fetchLastClose(t.symbol, currentSource)
        .then(close => {
          tickerQuotes = { ...tickerQuotes, [key]: { status: 'ok', close } };
        })
        .catch(() => {
          tickerQuotes = { ...tickerQuotes, [key]: { status: 'error' } };
        });
    }
  });

  let tickerQuotesForGroup = $derived.by(() => {
    const out: Record<string, TickerQuote> = {};
    for (const t of displayTickers) {
      const entry = tickerQuotes[`${source}:${t.symbol}`];
      if (entry) out[t.symbol] = entry;
    }
    return out;
  });
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
          void loadMarketData();
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

  let initialLoadDone = $state(false);

  onMount(async () => {
    window.addEventListener('beforeunload', persistOnUnload);
    try {
      await fetchSession();
    } catch (err) {
      console.warn('Session fetch failed:', err);
    }
    await loadMarketData();
    initialLoadDone = true;
  });

  $effect(() => {
    period;
    interval;
    if (!initialLoadDone) return;
    if (source === 'csv') return;
    void loadMarketData();
  });

  onDestroy(() => {
    persistOnUnload();
    window.removeEventListener('beforeunload', persistOnUnload);
    if (refreshIntervalId) clearInterval(refreshIntervalId);
    if (wsClient) wsClient.disconnect();
  });
</script>

<div class="flex flex-col h-screen bg-background">
  <TopHeader
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
        {groups}
        {selectedGroupName}
        {selectedPriority}
        priorityCounts={priorityCountsMap}
        tickers={displayTickers}
        quotes={tickerQuotesForGroup}
        groupActions={{
          select: handleSelectGroup,
          rename: openRenameDialog,
          duplicate: handleDuplicateGroup,
          clear: handleClearGroup,
          add: openAddDialog,
          delete: handleDeleteGroup,
        }}
        onaddticker={() => (addSymbolDialogOpen = true)}
        onselectpriority={handleSelectPriority}
        onselectticker={sym => {
          symbol = sym;
          void loadMarketData();
        }}
        ondeleteticker={handleDeleteTicker}
        onsetpriority={handleSetPriority}
      />
    {/if}
  </div>
  <BottomHeader
    bind:chartType
    bind:showArea
    bind:showVolume
    bind:smaConfig
    bind:emaConfig
    bind:bbandsConfig
    bind:colours
    {sidebarVisible}
    ontogglesidebar={() => (sidebarVisible = !sidebarVisible)}
  />
  <TextPromptDialog
    open={groupDialogMode !== null}
    onopenchange={v => {
      if (!v) groupDialogMode = null;
    }}
    title={groupDialogMode === 'rename' ? 'Rename group' : 'Add group'}
    placeholder="Group name"
    initialValue={groupDialogInitial}
    existingNames={groupDialogExistingNames}
    duplicateMessage="A group with this name already exists."
    onsubmit={handleGroupDialogSubmit}
  />
  <PriorityConflictDialog
    open={priorityConflictState !== null}
    onopenchange={v => {
      if (!v) priorityConflictState = null;
    }}
    conflict={priorityConflictState?.conflict ?? null}
    desired={priorityConflictState?.desired ?? null}
    onkeepexisting={resolveConflictKeepExisting}
    onswitchgroup={resolveConflictSwitchGroup}
  />
  <TextPromptDialog
    open={addSymbolDialogOpen}
    onopenchange={v => (addSymbolDialogOpen = v)}
    title="Add symbol"
    placeholder="Symbol (e.g. AAPL)"
    existingNames={currentTickerSymbols}
    duplicateMessage="This symbol is already in the group."
    normalize={s => s.toUpperCase()}
    onsubmit={handleAddSymbolSubmit}
  />
</div>
