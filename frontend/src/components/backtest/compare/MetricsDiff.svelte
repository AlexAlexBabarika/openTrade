<!-- frontend/src/components/backtest/compare/MetricsDiff.svelte -->
<script lang="ts">
  import type { MetricDiffRow } from '$lib/features/runs/runTypes';
  import { formatDelta } from '$lib/features/runs/format';
  let { rows }: { rows: MetricDiffRow[] } = $props();
  const fmt = (v: number | null) => (v === null ? '—' : String(v));
</script>

<section>
  <h3 class="mb-1 text-sm font-semibold">Metrics</h3>
  <table class="w-full text-sm tabular-nums">
    <thead><tr class="text-muted-foreground"><th class="text-left">Metric</th><th class="text-right">A</th><th class="text-right">B</th><th class="text-right">Δ</th></tr></thead>
    <tbody>
      {#each rows as r (r.metric)}
        <tr class="border-b border-border/50">
          <td class="py-1">{r.metric}</td>
          <td class="py-1 text-right font-mono">{fmt(r.a)}</td>
          <td class="py-1 text-right font-mono">{fmt(r.b)}</td>
          <td class="py-1 text-right font-mono" class:text-emerald-500={(r.delta ?? 0) > 0} class:text-destructive={(r.delta ?? 0) < 0}>{formatDelta(r.delta)}</td>
        </tr>
      {/each}
    </tbody>
  </table>
</section>
