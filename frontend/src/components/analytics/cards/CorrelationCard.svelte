<script lang="ts">
  import type { CorrelationResponse } from '$lib/features/analytics/analyticsApi';

  let { data }: { data: CorrelationResponse } = $props();

  function colour(v: number): string {
    // -1 → red, 0 → muted, +1 → green. Interpolate via alpha on two hues.
    const c = Math.max(-1, Math.min(1, v));
    if (c >= 0) {
      const a = 0.10 + c * 0.70;
      return `color-mix(in oklab, #34d399 ${(a * 100).toFixed(0)}%, transparent)`;
    }
    const a = 0.10 + -c * 0.70;
    return `color-mix(in oklab, #ff7373 ${(a * 100).toFixed(0)}%, transparent)`;
  }
</script>

<div class="corr">
  <div class="head">
    <span class="lbl">vs benchmark</span>
    <span class="self">{data.symbol}</span>
  </div>
  <div class="grid">
    {#each data.rows as row (row.benchmark)}
      <div class="cell" style:background={colour(row.value)}>
        <span class="bench">{row.benchmark}</span>
        <span class="val" class:neg={row.value < 0}>{row.value.toFixed(2)}</span>
      </div>
    {/each}
    {#if data.rows.length === 0}
      <p class="empty">no benchmarks loaded.</p>
    {/if}
  </div>
</div>

<style>
  .corr {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
  }
  .lbl {
    font-size: 9.5px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: color-mix(in oklab, oklch(var(--foreground)) 50%, transparent);
  }
  .self {
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: oklch(var(--foreground));
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(64px, 1fr));
    gap: 6px;
  }
  .cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    padding: 10px 6px;
    border: 1px solid
      color-mix(in oklab, oklch(var(--border)) 100%, transparent);
    border-radius: 4px;
    font-variant-numeric: tabular-nums;
  }
  .bench {
    font-size: 9.5px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: color-mix(in oklab, oklch(var(--foreground)) 60%, transparent);
  }
  .val {
    font-size: 14px;
    font-weight: 700;
    color: oklch(var(--foreground));
  }
  .val.neg {
    color: #ff9c9c;
  }
  .empty {
    margin: 0;
    font-size: 11px;
    color: oklch(var(--muted-foreground));
  }

  :global(html:not(.dark)) .cell {
    border-color: #000;
  }
  :global(html:not(.dark)) .val.neg {
    color: #b00020;
  }
</style>
