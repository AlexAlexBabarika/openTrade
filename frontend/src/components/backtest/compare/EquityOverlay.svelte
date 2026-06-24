<!-- frontend/src/components/backtest/compare/EquityOverlay.svelte -->
<script lang="ts">
  import TimeSeriesChart from '../TimeSeriesChart.svelte';
  import { equityToLines } from '$lib/features/runs/format';
  import type { EquityOverlay } from '$lib/features/runs/runTypes';

  let { overlay }: { overlay: EquityOverlay } = $props();
  const COLOR_A = '#3b82f6';
  const COLOR_B = '#f59e0b';
  const COLOR_R = '#94a3b8';

  const overlayLines = $derived(equityToLines(overlay, COLOR_A, COLOR_B));
  const residualLines = $derived([{ data: overlay.residual, color: COLOR_R }]);
</script>

<section>
  <h3 class="mb-1 text-sm font-semibold">Equity (A blue · B amber)</h3>
  <div class="h-48"><TimeSeriesChart lines={overlayLines} /></div>
  <h4 class="mt-2 text-xs font-semibold text-muted-foreground">Residual (B − A)</h4>
  <div class="h-24"><TimeSeriesChart lines={residualLines} /></div>
</section>
