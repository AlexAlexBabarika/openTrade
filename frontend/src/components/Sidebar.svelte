<script lang="ts">
  import Plus from '@lucide/svelte/icons/plus';
  import Flag from '@lucide/svelte/icons/flag';
  import Trash2 from '@lucide/svelte/icons/trash-2';
  import Check from '@lucide/svelte/icons/check';
  import NotebookPen from '@lucide/svelte/icons/notebook-pen';
  import { ContextMenu } from 'bits-ui';
  import GroupSelector from './GroupSelector.svelte';
  import NotesPanel from './NotesPanel.svelte';
  import ProviderBadges from './ProviderBadges.svelte';
  import {
    TickerPriority,
    PRIORITY_COLOURS,
    PRIORITY_OPTIONS,
  } from '../lib/tickers';
  import type {
    TickerGroup,
    TrackedTicker,
    GroupActions,
    FlaggedPriority,
  } from '../lib/tickers';
  import type { TickerQuote } from '../lib/tickerQuotes';
  import type { TickerNote } from '../lib/notes';

  let {
    symbol = '',
    closePrice = null as number | null,
    groups,
    selectedGroupName,
    selectedPriority,
    priorityCounts,
    tickers,
    quotes,
    groupActions,
    onaddticker,
    onselectpriority,
    onselectticker,
    ondeleteticker,
    onsetpriority,
    notes = [],
    onaddnote,
    oneditnote,
    ondeletenote,
  }: {
    symbol?: string;
    closePrice?: number | null;
    groups: TickerGroup[];
    selectedGroupName: string;
    selectedPriority: FlaggedPriority | null;
    priorityCounts: Record<FlaggedPriority, number>;
    tickers: TrackedTicker[];
    quotes: Record<string, TickerQuote>;
    groupActions: GroupActions;
    onaddticker: () => void;
    onselectpriority: (p: FlaggedPriority) => void;
    onselectticker: (symbol: string) => void;
    ondeleteticker: (symbol: string) => void;
    onsetpriority: (symbol: string, priority: TickerPriority) => void;
    notes?: TickerNote[];
    onaddnote: (symbol: string) => void;
    oneditnote: (note: TickerNote) => void;
    ondeletenote: (id: string) => void;
  } = $props();

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
      {selectedPriority}
      {priorityCounts}
      actions={groupActions}
      {onselectpriority}
    />
    <div class="flex items-center gap-1">
      <button
        type="button"
        class="inline-flex items-center justify-center h-7 w-7 rounded hover:bg-accent hover:text-accent-foreground text-muted-foreground transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-muted-foreground"
        aria-label="Add symbol"
        disabled={selectedPriority !== null}
        title={selectedPriority !== null
          ? 'Switch to a group to add symbols'
          : undefined}
        onclick={onaddticker}
      >
        <Plus class="h-4 w-4" />
      </button>
    </div>
  </div>

  <div class="flex-1 min-h-0 overflow-y-auto">
    {#if tickers.length === 0}
      <div class="px-3 py-4 text-xs text-muted-foreground">
        {selectedPriority
          ? 'No tickers with this priority.'
          : 'No symbols yet. Click + to add one.'}
      </div>
    {:else}
      <div class="py-1">
        {#each tickers as ticker (ticker.symbol)}
          <ContextMenu.Root>
            <ContextMenu.Trigger class="block w-full">
              <button
                type="button"
                class="flex w-full items-center justify-between gap-2 px-3 py-1.5 text-sm text-foreground hover:bg-accent hover:text-accent-foreground"
                onclick={() => onselectticker(ticker.symbol)}
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
                  {#if ticker.providers}
                    <ProviderBadges providers={ticker.providers} size="xs" />
                  {/if}
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
            </ContextMenu.Trigger>
            <ContextMenu.Portal>
              <ContextMenu.Content
                class="z-50 w-44 rounded-md border border-border bg-popover text-popover-foreground shadow-md py-1 outline-none"
              >
                <ContextMenu.Item
                  onSelect={() => onaddnote(ticker.symbol)}
                  class="flex w-full items-center gap-2 px-3 py-1.5 text-sm data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground cursor-default outline-none"
                >
                  <NotebookPen class="h-3.5 w-3.5" /> Add note
                </ContextMenu.Item>
                <ContextMenu.Item
                  onSelect={() => ondeleteticker(ticker.symbol)}
                  class="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-destructive data-[highlighted]:bg-destructive/10 cursor-default outline-none"
                >
                  <Trash2 class="h-3.5 w-3.5" /> Delete ticker
                </ContextMenu.Item>
                <ContextMenu.Separator class="my-1 h-px bg-border" />
                <div
                  class="px-3 py-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground"
                >
                  Priority
                </div>
                {#each PRIORITY_OPTIONS as p (p)}
                  <ContextMenu.Item
                    onSelect={() => onsetpriority(ticker.symbol, p)}
                    class="flex w-full items-center gap-2 px-3 py-1.5 text-sm data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground cursor-default outline-none"
                  >
                    {#if p === TickerPriority.None}
                      <span
                        class="h-2 w-2 rounded-full border border-muted-foreground/40 shrink-0"
                      ></span>
                    {:else}
                      <span
                        class="h-2 w-2 rounded-full shrink-0"
                        style="background: {PRIORITY_COLOURS[p]};"
                      ></span>
                    {/if}
                    <span class="flex-1 text-left capitalize">{p}</span>
                    {#if p === ticker.priority}
                      <Check class="h-3.5 w-3.5" />
                    {/if}
                  </ContextMenu.Item>
                {/each}
              </ContextMenu.Content>
            </ContextMenu.Portal>
          </ContextMenu.Root>
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
    {#if symbol}
      <NotesPanel {notes} onedit={oneditnote} ondelete={ondeletenote} />
    {/if}
  </div>
</aside>
