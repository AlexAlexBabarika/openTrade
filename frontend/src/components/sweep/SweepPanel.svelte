<script lang="ts">
  import { SweepState } from '$lib/features/sweep/sweepState.svelte';
  import { BacktestState } from '$lib/features/backtest/backtestState.svelte';
  import { httpSweepClient } from '$lib/features/sweep/sweepClient';
  import type { SweepFormValues } from '$lib/features/sweep/types';
  import ParamForm from './ParamForm.svelte';
  import Heatmap from './Heatmap.svelte';
  import ParallelCoords from './ParallelCoords.svelte';
  import TrialsTable from './TrialsTable.svelte';
  import BacktestPanel from '../backtest/BacktestPanel.svelte';

  let { code, sweep = new SweepState() }: { code: string; sweep?: SweepState } = $props();

  let lastForm = $state<SweepFormValues | null>(null);
  let drillOpen = $state(false);
  let drillState = $state<BacktestState | null>(null);

  // Schema introspection when the panel mounts / code changes.
  $effect(() => {
    if (code) void sweep.loadSchema(code);
  });

  function start(form: SweepFormValues) {
    lastForm = form;
    void sweep.run(form);
  }

  async function openTrial(trialId: number) {
    if (!lastForm || !sweep.sweepId) return;
    // Drill-in reuses the dashboard reader: load this trial's full BacktestResult.
    const loader = () => httpSweepClient.loadTrial(sweep.sweepId!, trialId, lastForm!);
    drillState = new BacktestState(loader);
    drillOpen = true;
  }

  const varied = $derived(lastForm?.vary ?? []);
  const metric = $derived(lastForm?.metric ?? 'sharpe');
</script>

<div class="sweep">
  <ParamForm schema={sweep.schema} {code} onsubmit={start} />

  {#if sweep.status !== 'idle'}
    <div class="status">
      <span class="badge {sweep.status}">{sweep.status}</span>
      <progress max={sweep.total || 1} value={sweep.done}></progress>
      <span>{sweep.done}/{sweep.total}</span>
      {#if sweep.status === 'running'}
        <button type="button" onclick={() => sweep.cancel()}>cancel</button>
      {/if}
      {#if sweep.error}<span class="err">{sweep.error}</span>{/if}
    </div>
  {/if}

  {#if sweep.trials.length > 0}
    <div class="viz">
      {#if varied.length === 2}
        <Heatmap trials={sweep.trials} xParam={varied[0]} yParam={varied[1]} {metric} ontrial={openTrial} />
      {:else if varied.length > 2}
        <ParallelCoords trials={sweep.trials} {varied} {metric} ontrial={openTrial} />
      {/if}
    </div>
    <TrialsTable trials={sweep.trials} {metric} {varied} bestTrialId={sweep.bestTrialId} onopen={openTrial} />
  {/if}
</div>

{#if drillState}
  <BacktestPanel bind:open={drillOpen} backtest={drillState} />
{/if}

<style>
  .sweep { display: flex; flex-direction: column; gap: 12px; height: 100%; overflow: auto; }
  .status { display: flex; align-items: center; gap: 12px; padding: 0 16px; font-size: 12px; }
  .status progress { flex: 0 0 200px; }
  .badge { padding: 2px 8px; border-radius: 999px; font-size: 10px; text-transform: uppercase; border: 1px solid oklch(var(--border)); }
  .badge.done { color: oklch(var(--primary)); }
  .badge.error { color: #ff9c9c; }
  .err { color: #ff9c9c; }
  .viz { min-height: 220px; }
</style>
