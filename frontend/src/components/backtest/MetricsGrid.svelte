<script lang="ts">
  import type { BacktestMetrics } from '$lib/features/backtest/types';
  import {
    METRIC_GROUPS,
    formatMetric,
    metricSign,
  } from '$lib/features/backtest/metricDefs';

  let { metrics }: { metrics: BacktestMetrics } = $props();
</script>

<div class="groups">
  {#each METRIC_GROUPS as group (group.title)}
    <section class="group">
      <h4 class="group-title">{group.title}</h4>
      <dl class="rows">
        {#each group.metrics as m (m.key)}
          {@const v = metrics[m.key] as number | null}
          {@const sign = metricSign(m, v)}
          <div class="row">
            <dt>{m.label}</dt>
            <dd class:pos={sign === 'pos'} class:neg={sign === 'neg'}>
              {formatMetric(m.kind, v)}
            </dd>
          </div>
        {/each}
      </dl>
    </section>
  {/each}
</div>

<style>
  .groups {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 14px;
    padding: 16px;
  }
  .group {
    border: 1px solid color-mix(in oklab, oklch(var(--border)) 100%, transparent);
    border-radius: 6px;
    background: color-mix(in oklab, oklch(var(--popover)) 100%, black 4%);
    overflow: hidden;
  }
  .group-title {
    margin: 0;
    padding: 8px 12px;
    font-size: 9.5px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: oklch(var(--muted-foreground));
    border-bottom: 1px dashed
      color-mix(in oklab, oklch(var(--border)) 90%, transparent);
  }
  .rows {
    margin: 0;
    padding: 4px 0;
  }
  .row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
    padding: 5px 12px;
    font-size: 12px;
  }
  dt {
    color: oklch(var(--muted-foreground));
  }
  dd {
    margin: 0;
    font-weight: 600;
    color: oklch(var(--foreground));
    font-variant-numeric: tabular-nums;
  }
  dd.pos {
    color: oklch(var(--up-color));
  }
  dd.neg {
    color: oklch(var(--down-color));
  }

  :global(html:not(.dark)) .group {
    background: #ffffff;
    border-color: #000;
  }
  :global(html:not(.dark)) .group-title {
    border-bottom-color: #000;
  }
</style>
