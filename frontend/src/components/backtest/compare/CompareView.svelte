<!-- frontend/src/components/backtest/compare/CompareView.svelte -->
<script lang="ts">
  import type { CompareState } from '$lib/features/runs/compareState.svelte';
  import { truncateRunId } from '$lib/features/runs/format';
  import InputsDiff from './InputsDiff.svelte';
  import MetricsDiff from './MetricsDiff.svelte';
  import TradesDiff from './TradesDiff.svelte';
  import EquityOverlay from './EquityOverlay.svelte';

  let { open = $bindable(false), compare }: { open?: boolean; compare: CompareState } = $props();
</script>

{#if open}
  <aside class="fixed right-0 top-14 bottom-0 z-50 flex w-[40rem] max-w-full flex-col gap-3 overflow-y-auto border-l border-border bg-background p-4" aria-label="Run comparison">
    <header class="flex items-center justify-between">
      <h2 class="text-sm font-semibold">
        Compare {compare.a ? truncateRunId(compare.a) : '—'} vs {compare.b ? truncateRunId(compare.b) : '—'}
      </h2>
      <button type="button" class="text-muted-foreground hover:text-foreground" onclick={() => (open = false)}>✕</button>
    </header>

    {#if compare.loading}
      <p class="text-sm text-muted-foreground">Loading diff…</p>
    {:else if compare.error}
      <p class="text-sm text-destructive">{compare.error}</p>
    {:else if compare.diff}
      <div class="flex gap-2 text-xs text-muted-foreground">
        <span>A: engine {compare.diff.status.a.recorded}</span>
        <span>B: engine {compare.diff.status.b.recorded}{compare.diff.status.b.stale ? ' ⚠ stale' : ''}</span>
      </div>
      <InputsDiff rows={compare.diff.inputs_diff} />
      <MetricsDiff rows={compare.diff.metrics_diff} />
      <EquityOverlay overlay={compare.diff.equity_overlay} />
      <TradesDiff trades={compare.diff.trades_diff} />
    {/if}
  </aside>
{/if}
