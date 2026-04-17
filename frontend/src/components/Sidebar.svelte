<script lang="ts">
  import PanelRightClose from '@lucide/svelte/icons/panel-right-close';
  import GroupSelector from './GroupSelector.svelte';
  import type { TickerGroup } from '../lib/tickers';

  let {
    symbol = '',
    closePrice = null as number | null,
    groups,
    selectedGroupName,
    onselectgroup,
    onrenamegroup,
    onduplicategroup,
    oncleargroup,
    onaddgroup,
    ondeletegroup,
    onhide = () => {},
  }: {
    symbol?: string;
    closePrice?: number | null;
    groups: TickerGroup[];
    selectedGroupName: string;
    onselectgroup: (name: string) => void;
    onrenamegroup: () => void;
    onduplicategroup: () => void;
    oncleargroup: () => void;
    onaddgroup: () => void;
    ondeletegroup: () => void;
    onhide?: () => void;
  } = $props();

  const priceLabel = $derived(
    closePrice == null || !Number.isFinite(closePrice)
      ? '—'
      : closePrice.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }),
  );
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
    <button
      type="button"
      class="inline-flex items-center justify-center h-7 w-7 rounded hover:bg-accent hover:text-accent-foreground text-muted-foreground transition-colors"
      aria-label="Hide sidebar"
      onclick={onhide}
    >
      <PanelRightClose class="h-4 w-4" />
    </button>
  </div>

  <div class="flex-1 min-h-0"></div>

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
