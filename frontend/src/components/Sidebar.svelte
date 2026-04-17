<script lang="ts">
  import PanelRightClose from '@lucide/svelte/icons/panel-right-close';
  import Plus from '@lucide/svelte/icons/plus';
  import Flag from '@lucide/svelte/icons/flag';
  import Trash2 from '@lucide/svelte/icons/trash-2';
  import Check from '@lucide/svelte/icons/check';
  import GroupSelector from './GroupSelector.svelte';
  import { TickerPriority, PRIORITY_COLOURS } from '../lib/tickers';
  import type { TickerGroup, TrackedTicker, GroupActions } from '../lib/tickers';
  import type { TickerQuote } from '../lib/tickerQuotes';

  let {
    symbol = '',
    closePrice = null as number | null,
    groups,
    selectedGroupName,
    tickers,
    quotes,
    groupActions,
    onaddticker,
    onselectticker,
    ondeleteticker,
    onsetpriority,
    onhide = () => {},
  }: {
    symbol?: string;
    closePrice?: number | null;
    groups: TickerGroup[];
    selectedGroupName: string;
    tickers: TrackedTicker[];
    quotes: Record<string, TickerQuote>;
    groupActions: GroupActions;
    onaddticker: () => void;
    onselectticker: (symbol: string) => void;
    ondeleteticker: (symbol: string) => void;
    onsetpriority: (symbol: string, priority: TickerPriority) => void;
    onhide?: () => void;
  } = $props();

  const PRIORITY_OPTIONS: TickerPriority[] = [
    TickerPriority.None,
    TickerPriority.Ignore,
    TickerPriority.Low,
    TickerPriority.Normal,
    TickerPriority.High,
    TickerPriority.Critical,
  ];

  let contextMenu = $state<{ symbol: string; x: number; y: number } | null>(null);
  let menuEl: HTMLDivElement | undefined = $state();

  function openContextMenu(e: MouseEvent, sym: string) {
    e.preventDefault();
    const menuWidth = 180;
    const menuHeight = 260;
    contextMenu = {
      symbol: sym,
      x: Math.min(e.clientX, window.innerWidth - menuWidth - 8),
      y: Math.min(e.clientY, window.innerHeight - menuHeight - 8),
    };
  }

  $effect(() => {
    if (!contextMenu) return;
    const handleDown = (e: PointerEvent) => {
      if (menuEl && !menuEl.contains(e.target as Node)) contextMenu = null;
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') contextMenu = null;
    };
    document.addEventListener('pointerdown', handleDown, { capture: true });
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('pointerdown', handleDown, { capture: true });
      document.removeEventListener('keydown', handleKey);
    };
  });

  function formatPrice(value: number | null | undefined): string {
    if (value == null || !Number.isFinite(value)) return '—';
    return value.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function formatQuote(q: TickerQuote | undefined): string {
    if (!q || q.status === 'loading') return '…';
    if (q.status === 'error') return '—';
    return formatPrice(q.close);
  }
</script>

<aside
  class="w-[17%] min-w-[200px] border-l border-border bg-background flex flex-col shrink-0 overflow-visible"
  aria-label="Sidebar"
>
  <div class="flex items-center justify-between px-2 py-2 border-b border-border h-10">
    <GroupSelector
      {groups}
      selectedName={selectedGroupName}
      actions={groupActions}
    />
    <div class="flex items-center gap-1">
      <button
        type="button"
        class="inline-flex items-center justify-center h-7 w-7 rounded hover:bg-accent hover:text-accent-foreground text-muted-foreground transition-colors"
        aria-label="Add symbol"
        onclick={onaddticker}
      >
        <Plus class="h-4 w-4" />
      </button>
      <button
        type="button"
        class="inline-flex items-center justify-center h-7 w-7 rounded hover:bg-accent hover:text-accent-foreground text-muted-foreground transition-colors"
        aria-label="Hide sidebar"
        onclick={onhide}
      >
        <PanelRightClose class="h-4 w-4" />
      </button>
    </div>
  </div>

  <div class="flex-1 min-h-0 overflow-y-auto">
    {#if tickers.length === 0}
      <div class="px-3 py-4 text-xs text-muted-foreground">
        No symbols yet. Click + to add one.
      </div>
    {:else}
      <div class="py-1">
        {#each tickers as ticker (ticker.symbol)}
          <button
            type="button"
            class="flex w-full items-center justify-between gap-2 px-3 py-1.5 text-sm text-foreground hover:bg-accent hover:text-accent-foreground"
            onclick={() => onselectticker(ticker.symbol)}
            oncontextmenu={e => openContextMenu(e, ticker.symbol)}
          >
            <span class="flex items-center gap-1.5 min-w-0">
              {#if ticker.priority !== TickerPriority.None}
                {@const colour = PRIORITY_COLOURS[ticker.priority]}
                <Flag
                  class="h-3 w-3 shrink-0"
                  style="color: {colour}; fill: {colour};"
                />
              {/if}
              <span class="truncate">{ticker.symbol}</span>
            </span>
            <span
              class="font-mono tabular-nums text-muted-foreground shrink-0"
              title={quotes[ticker.symbol]?.status === 'error'
                ? 'Failed to fetch — will retry when group or source changes'
                : undefined}
            >
              {formatQuote(quotes[ticker.symbol])}
            </span>
          </button>
        {/each}
      </div>
    {/if}
  </div>

  <div class="border-t border-border px-3 py-2">
    <div class="text-[10px] font-medium tracking-wider uppercase text-muted-foreground">
      Current Symbol
    </div>
    <div class="mt-1 flex items-baseline justify-between gap-2">
      <span class="text-sm font-semibold text-foreground truncate">
        {symbol || '—'}
      </span>
      <span class="text-sm font-mono tabular-nums text-foreground">
        {formatPrice(closePrice)}
      </span>
    </div>
  </div>
</aside>

{#if contextMenu}
  {@const menu = contextMenu}
  {@const currentPriority =
    tickers.find(t => t.symbol === menu.symbol)?.priority ??
    TickerPriority.None}
  <div
    bind:this={menuEl}
    class="fixed z-50 w-44 rounded-md border border-border bg-popover text-popover-foreground shadow-md py-1"
    style="left: {menu.x}px; top: {menu.y}px;"
    role="menu"
  >
    <button
      type="button"
      class="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-destructive hover:bg-destructive/10"
      onclick={() => {
        ondeleteticker(menu.symbol);
        contextMenu = null;
      }}
    >
      <Trash2 class="h-3.5 w-3.5" /> Delete ticker
    </button>
    <div class="my-1 h-px bg-border"></div>
    <div class="px-3 py-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
      Priority
    </div>
    {#each PRIORITY_OPTIONS as p (p)}
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
        onclick={() => {
          onsetpriority(menu.symbol, p);
          contextMenu = null;
        }}
      >
        {#if p === TickerPriority.None}
          <span class="h-2 w-2 rounded-full border border-muted-foreground/40 shrink-0"></span>
        {:else}
          <span
            class="h-2 w-2 rounded-full shrink-0"
            style="background: {PRIORITY_COLOURS[p]};"
          ></span>
        {/if}
        <span class="flex-1 text-left capitalize">{p}</span>
        {#if p === currentPriority}
          <Check class="h-3.5 w-3.5" />
        {/if}
      </button>
    {/each}
  </div>
{/if}
