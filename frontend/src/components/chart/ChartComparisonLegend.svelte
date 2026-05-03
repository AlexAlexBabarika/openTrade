<script lang="ts">
  import X from '@lucide/svelte/icons/x';
  import LineChartIcon from '@lucide/svelte/icons/chart-line';
  import CandleIcon from '@lucide/svelte/icons/chart-candlestick';
  import AlertTriangle from '@lucide/svelte/icons/triangle-alert';
  import ComparisonColorSwatch from './ComparisonColorSwatch.svelte';
  import type {
    Comparison,
    ComparisonStatus,
  } from '$lib/features/chart/comparisonController.svelte';
  import type { ComparisonSeriesType } from '$lib/features/chart/comparisonsApi';

  let {
    comparisons,
    textColour,
    onRemove,
    onSetColor,
    onSetSeriesType,
  }: {
    comparisons: Comparison[];
    textColour?: string;
    onRemove: (id: string) => void;
    onSetColor: (id: string, color: string) => void;
    onSetSeriesType: (id: string, type: ComparisonSeriesType) => void;
  } = $props();

  function formatChange(c: Comparison): string {
    if (c.candles.length < 2) return '—';
    const first = c.candles[0].close;
    if (!Number.isFinite(first) || first === 0) return '—';
    const last = c.candles[c.candles.length - 1].close;
    const pct = (last / first - 1) * 100;
    const sign = pct >= 0 ? '+' : '';
    return `${sign}${pct.toFixed(2)}%`;
  }

  function statusTooltip(s: ComparisonStatus, msg?: string): string | null {
    if (s === 'no-overlap') return 'No data overlap with main symbol';
    if (s === 'error') return msg ?? 'Failed to load';
    if (s === 'loading') return 'Loading…';
    return null;
  }

  function nextSeriesType(t: ComparisonSeriesType): ComparisonSeriesType {
    return t === 'line' ? 'candlestick' : 'line';
  }
</script>

{#if comparisons.length > 0}
  <div
    class="absolute left-4 top-[112px] z-10 flex flex-col gap-1 pointer-events-auto font-mono text-xs"
    style:color={textColour}
  >
    {#each comparisons as c (c.id)}
      {@const tip = statusTooltip(c.status, c.errorMessage)}
      <div class="flex items-center gap-2 leading-[18px]">
        <ComparisonColorSwatch
          color={c.color}
          label="Pick colour for {c.symbol}"
          onchange={(v: string) => onSetColor(c.id, v)}
        />
        <span class="font-semibold">{c.symbol}</span>
        <span style:opacity="0.85">{formatChange(c)}</span>
        {#if tip}
          <span title={tip} class="text-amber-500" aria-label={tip}>
            <AlertTriangle class="h-3.5 w-3.5" />
          </span>
        {/if}
        <button
          type="button"
          class="rounded p-0.5 hover:bg-muted"
          aria-label="Toggle series type"
          title={c.seriesType === 'line' ? 'Switch to candlestick' : 'Switch to line'}
          onclick={() => onSetSeriesType(c.id, nextSeriesType(c.seriesType))}
        >
          {#if c.seriesType === 'line'}
            <LineChartIcon class="h-3.5 w-3.5" />
          {:else}
            <CandleIcon class="h-3.5 w-3.5" />
          {/if}
        </button>
        <button
          type="button"
          class="rounded p-0.5 hover:bg-muted"
          aria-label="Remove comparison {c.symbol}"
          title="Remove"
          onclick={() => onRemove(c.id)}
        >
          <X class="h-3.5 w-3.5" />
        </button>
      </div>
    {/each}
  </div>
{/if}
