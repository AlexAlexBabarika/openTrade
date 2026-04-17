<script lang="ts">
  import PanelRightClose from '@lucide/svelte/icons/panel-right-close';
  import Plus from '@lucide/svelte/icons/plus';
  import GroupSelector from './GroupSelector.svelte';
  import type { TickerGroup, TrackedTicker } from '../lib/tickers';

  let {
    symbol = '',
    closePrice = null as number | null,
    groups,
    selectedGroupName,
    tickers,
    closes,
    onselectgroup,
    onrenamegroup,
    onduplicategroup,
    oncleargroup,
    onaddgroup,
    ondeletegroup,
    onaddticker,
    onselectticker,
    onhide = () => {},
  }: {
    symbol?: string;
    closePrice?: number | null;
    groups: TickerGroup[];
    selectedGroupName: string;
    tickers: TrackedTicker[];
    closes: Record<string, number | null>;
    onselectgroup: (name: string) => void;
    onrenamegroup: () => void;
    onduplicategroup: () => void;
    oncleargroup: () => void;
    onaddgroup: () => void;
    ondeletegroup: () => void;
    onaddticker: () => void;
    onselectticker: (symbol: string) => void;
    onhide?: () => void;
  } = $props();

  function formatPrice(value: number | null | undefined): string {
    if (value == null || !Number.isFinite(value)) return '—';
    return value.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  const priceLabel = $derived(formatPrice(closePrice));
</script>

<aside
  class="w-[17%] min-w-[200px] border-l border-border bg-background flex flex-col shrink-0 overflow-visible"
  aria-label="Sidebar"
>
  <div class="flex items-center justify-between px-2 py-2 border-b border-border h-10">
    <GroupSelector
      {groups}
      selectedName={selectedGroupName}
      onselect={onselectgroup}
      onrename={onrenamegroup}
      onduplicate={onduplicategroup}
      onclear={oncleargroup}
      onadd={onaddgroup}
      ondelete={ondeletegroup}
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
          >
            <span class="truncate">{ticker.symbol}</span>
            <span class="font-mono tabular-nums text-muted-foreground shrink-0">
              {formatPrice(closes[ticker.symbol])}
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
        {priceLabel}
      </span>
    </div>
  </div>
</aside>
