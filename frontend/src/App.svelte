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
  import type { ChartType } from '$lib/features/chart/chartColours';
  import { fetchSMA, fetchEMA, fetchBBands } from '$lib/features/chart/indicators';
  import type { IndicatorPoint, BollingerBandsPoint } from '$lib/core/types';
  import { fetchMarketOHLCV } from '$lib/features/market/marketData';
  import { apiFetch, readErrorMessage } from '$lib/core/api';
  import { WSClient } from '$lib/core/ws';
  import type { ConnectionStatus } from '$lib/core/ws';
  import type { OHLCVCandle } from '$lib/core/types';
  import { fetchSession } from '$lib/features/auth/auth';
  import type { MarketDataProviderValue } from '$lib/features/market/marketDataProviders';
  import { DEFAULT_MARKET_INTERVAL } from '$lib/features/market/marketIntervals';
  import { DEFAULT_MARKET_PERIOD } from '$lib/features/market/marketPeriods';
  import type { ChartColours } from '$lib/features/chart/chartColours';
  import {
    defaultChartColours,
    loadChartColoursFromStorage,
    persistChartColours,
    loadChartSettingsFromStorage,
    persistChartSettings,
  } from '$lib/features/chart/chartColours';
  import { loadTheme, persistTheme, applyTheme, type Theme } from '$lib/features/theme/theme';
  import type {
    TickerGroup,
    FlaggedPriority,
    FlaggedStance,
    PriorityConflict,
    StanceConflict,
    TickerPriority,
    TickerStance,
  } from '$lib/features/market/tickers';
  import {
    loadGroupsFromStorage,
    persistGroups,
    loadSelectedGroupName,
    persistSelectedGroupName,
    loadSelectedPriority,
    persistSelectedPriority,
    loadSelectedStance,
    persistSelectedStance,
    addGroup,
    renameGroup,
    duplicateGroup,
    deleteGroup,
    clearGroup,
    addTickerToGroup,
    removeTickerFromGroup,
    setTickerPriority,
    collectTickersByPriority,
    collectTickersByStance,
    priorityCounts as computePriorityCounts,
    stanceCounts as computeStanceCounts,
    setPriorityEverywhere,
    setTickerStance,
    setStanceEverywhere,
    removeTickerEverywhere,
    findPriorityConflict,
    findStanceConflict,
    setTickerProvidersEverywhere,
    findTickerProviders,
  } from '$lib/features/market/tickers';
  import type { SymbolProviders } from '$lib/features/market/symbols';
  import { markYFinanceSupported, DEFAULT_PROVIDERS } from '$lib/features/market/symbols';
  import { fetchLastClose, type TickerQuote } from '$lib/features/market/tickerQuotes';
  import { untrack } from 'svelte';
  import TextPromptDialog from './components/TextPromptDialog.svelte';
  import SymbolSearchDialog from './components/SymbolSearchDialog.svelte';
  import PriorityConflictDialog from './components/PriorityConflictDialog.svelte';
  import NoteDialog from './components/NoteDialog.svelte';
  import type { TickerNote, NotesBySymbol } from '$lib/features/notes/notes';
  import {
    loadNotesFromStorage,
    persistNotes,
    notesForSymbol,
    addNote,
    updateNote,
    deleteNote,
  } from '$lib/features/notes/notes';
  import ToolboxPanel from './components/ToolboxPanel.svelte';
  import LeftToolbar from './components/LeftToolbar.svelte';
  import ToolSettingsModal from './components/ToolSettingsModal.svelte';
  import DrawablesPersistence from '$lib/features/drawables/DrawablesPersistence.svelte';
  import type { CrosshairModeName } from '$lib/features/chart/crosshair';
  import {
    CURSOR,
    drawables,
    toolbarCommandsFromStore,
    type ActiveTool,
  } from '$lib/features/drawables';

  const drawableToolbarCommands = toolbarCommandsFromStore(drawables);

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
  let theme = $state<Theme>(loadTheme());

  function setTheme(next: Theme) {
    if (next === theme) return;
    applyTheme(next);
    theme = next;
    persistTheme(next);
  }
  let hasCandles = $derived(candles.length > 0);
  let marketDataVersion = $state(0);
  let isLoading = $state(false);
  let sidebarVisible = $state(true);
  let crosshairMode = $state<CrosshairModeName>('normal');
  let activeTool = $state<ActiveTool>(CURSOR);
  let toolSettingsOpen = $state(false);
  let toolSettingsType = $state<string | null>(null);

  function openToolSettings(type: string): void {
    toolSettingsType = type;
    toolSettingsOpen = true;
  }

  const initialGroups = loadGroupsFromStorage();
  let groups = $state<TickerGroup[]>(initialGroups);
  let selectedGroupName = $state(loadSelectedGroupName(initialGroups));
  let selectedPriority = $state<FlaggedPriority | null>(loadSelectedPriority());
  let selectedStance = $state<FlaggedStance | null>(loadSelectedStance());
  let groupDialogMode = $state<null | 'add' | 'rename'>(null);
  let addSymbolDialogOpen = $state(false);
  let priorityConflictState = $state<{
    symbol: string;
    desired: TickerPriority;
    conflict: PriorityConflict;
  } | null>(null);
  let stanceConflictState = $state<{
    symbol: string;
    desired: TickerStance;
    conflict: StanceConflict;
  } | null>(null);

  let notes = $state<NotesBySymbol>(loadNotesFromStorage());
  let noteDialogState = $state<{
    mode: 'create' | 'edit';
    symbol: string;
    note?: TickerNote;
  } | null>(null);

  $effect(() => {
    persistNotes(notes);
  });

  let currentNotes = $derived(notesForSymbol(notes, loadedSymbol));

  function handleAddNote(sym: string) {
    noteDialogState = { mode: 'create', symbol: sym };
  }

  function handleEditNote(note: TickerNote) {
    noteDialogState = { mode: 'edit', symbol: note.symbol, note };
  }

  function handleDeleteNote(id: string) {
    notes = deleteNote(notes, id);
  }

  function handleNoteSubmit(title: string | undefined, body: string) {
    if (!noteDialogState) return;
    if (noteDialogState.mode === 'create') {
      notes = addNote(notes, noteDialogState.symbol, body, title);
    } else if (noteDialogState.note) {
      notes = updateNote(notes, noteDialogState.note.id, { title, body });
    }
  }
  let toolboxOpen = $state(false);

  $effect(() => {
    persistGroups(groups);
  });
  $effect(() => {
    persistSelectedGroupName(selectedGroupName);
  });
  $effect(() => {
    persistSelectedPriority(selectedPriority);
  });
  $effect(() => {
    persistSelectedStance(selectedStance);
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
      selectedStance = null;
    } else if (groupDialogMode === 'rename') {
      groups = renameGroup(groups, selectedGroupName, name);
      selectedGroupName = name;
    }
  }

  function handleAddSymbolSubmit(
    sym: string,
    providers: SymbolProviders | null,
  ) {
    groups = addTickerToGroup(groups, selectedGroupName, sym, providers);
  }

  function handleSelectGroup(name: string) {
    selectedGroupName = name;
    selectedPriority = null;
    selectedStance = null;
  }

  function handleSelectPriority(p: FlaggedPriority) {
    selectedPriority = p;
    selectedStance = null;
  }

  function handleSelectStance(s: FlaggedStance) {
    selectedStance = s;
    selectedPriority = null;
  }

  function handleDeleteTicker(sym: string) {
    groups = selectedPriority || selectedStance
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

  function handleSetStance(sym: string, stance: TickerStance) {
    if (selectedStance) {
      groups = setStanceEverywhere(groups, sym, stance);
      return;
    }
    const conflict = findStanceConflict(
      groups,
      sym,
      stance,
      selectedGroupName,
    );
    if (conflict) {
      stanceConflictState = { symbol: sym, desired: stance, conflict };
      return;
    }
    groups = setTickerStance(groups, selectedGroupName, sym, stance);
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
    selectedStance = null;
    priorityConflictState = null;
  }

  function resolveStanceConflictKeepExisting() {
    if (!stanceConflictState) return;
    const { symbol: sym, conflict } = stanceConflictState;
    groups = setTickerStance(
      groups,
      selectedGroupName,
      sym,
      conflict.existingStance,
    );
    stanceConflictState = null;
  }

  function resolveStanceConflictSwitchGroup(groupName: string) {
    selectedGroupName = groupName;
    selectedPriority = null;
    selectedStance = null;
    stanceConflictState = null;
  }

  let groupDialogInitial = $derived(
    groupDialogMode === 'rename' ? selectedGroupName : '',
  );
  let groupDialogExistingNames = $derived(groups.map(g => g.name));
  let currentTickers = $derived(currentGroup?.tickers ?? []);
  let currentTickerSymbols = $derived(currentTickers.map(t => t.symbol));
  let displayTickers = $derived(
    selectedStance
      ? collectTickersByStance(groups, selectedStance)
      : selectedPriority
        ? collectTickersByPriority(groups, selectedPriority)
        : currentTickers,
  );
  let priorityCountsMap = $derived(computePriorityCounts(groups));
  let stanceCountsMap = $derived(computeStanceCounts(groups));

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
      maybeMarkYFinance(symbol, source, data.candles?.length ?? 0);
    } catch (e) {
      errorMessage = e instanceof Error ? e.message : 'Failed to load';
    } finally {
      isLoading = false;
    }
  }

  // A successful yfinance fetch is the cheapest proof that yfinance supports
  // this symbol. Once marked, we remember per-session so chart reloads and
  // untracked symbols don't keep re-POSTing.
  const markedThisSession = new Set<string>();

  function maybeMarkYFinance(
    sym: string,
    src: MarketDataProviderValue,
    candleCount: number,
  ): void {
    if (src !== 'yfinance' || candleCount === 0) return;
    if (markedThisSession.has(sym)) return;
    const cached = findTickerProviders(groups, sym);
    if (cached?.yfinance) {
      markedThisSession.add(sym);
      return;
    }
    markedThisSession.add(sym);
    markYFinanceSupported(sym);
    const nextProviders: SymbolProviders = {
      ...(cached ?? DEFAULT_PROVIDERS),
      yfinance: true,
    };
    groups = setTickerProvidersEverywhere(groups, sym, nextProviders);
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
  <DrawablesPersistence />
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
    <LeftToolbar
      chartSymbol={symbol}
      bind:crosshairMode
      bind:activeTool
      onToolSettings={openToolSettings}
      drawableCommands={drawableToolbarCommands}
    />
    <ToolSettingsModal
      toolType={toolSettingsType}
      bind:open={toolSettingsOpen}
    />
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
        {crosshairMode}
        provider={source}
        {interval}
        bind:activeTool
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
        {selectedStance}
        priorityCounts={priorityCountsMap}
        stanceCounts={stanceCountsMap}
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
        onselectstance={handleSelectStance}
        onselectticker={sym => {
          symbol = sym;
          void loadMarketData();
        }}
        ondeleteticker={handleDeleteTicker}
        onsetpriority={handleSetPriority}
        onsetstance={handleSetStance}
        notes={currentNotes}
        onaddnote={handleAddNote}
        oneditnote={handleEditNote}
        ondeletenote={handleDeleteNote}
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
    {theme}
    onthemechange={setTheme}
    {sidebarVisible}
    ontogglesidebar={() => (sidebarVisible = !sidebarVisible)}
  />
  <ToolboxPanel bind:open={toolboxOpen} {theme} />
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
    field="priority"
    open={priorityConflictState !== null}
    onopenchange={v => {
      if (!v) priorityConflictState = null;
    }}
    conflict={priorityConflictState
      ? {
          symbol: priorityConflictState.conflict.symbol,
          existing: priorityConflictState.conflict.existingPriority,
          groups: priorityConflictState.conflict.groups,
        }
      : null}
    onkeepexisting={resolveConflictKeepExisting}
    onswitchgroup={resolveConflictSwitchGroup}
  />
  <PriorityConflictDialog
    field="stance"
    open={stanceConflictState !== null}
    onopenchange={v => {
      if (!v) stanceConflictState = null;
    }}
    conflict={stanceConflictState
      ? {
          symbol: stanceConflictState.conflict.symbol,
          existing: stanceConflictState.conflict.existingStance,
          groups: stanceConflictState.conflict.groups,
        }
      : null}
    onkeepexisting={resolveStanceConflictKeepExisting}
    onswitchgroup={resolveStanceConflictSwitchGroup}
  />
  <SymbolSearchDialog
    open={addSymbolDialogOpen}
    onopenchange={v => (addSymbolDialogOpen = v)}
    existingSymbols={currentTickerSymbols}
    onsubmit={handleAddSymbolSubmit}
  />
  <NoteDialog
    open={noteDialogState !== null}
    onopenchange={v => {
      if (!v) noteDialogState = null;
    }}
    mode={noteDialogState?.mode ?? 'create'}
    symbol={noteDialogState?.symbol ?? ''}
    initialTitle={noteDialogState?.note?.title ?? ''}
    initialBody={noteDialogState?.note?.body ?? ''}
    onsubmit={handleNoteSubmit}
  />
</div>
