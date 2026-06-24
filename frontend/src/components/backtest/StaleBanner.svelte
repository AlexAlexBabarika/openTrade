<!-- frontend/src/components/backtest/StaleBanner.svelte -->
<script lang="ts">
  import type { RunStatus } from '$lib/features/runs/runTypes';

  let {
    status,
    reranning = false,
    error = null,
    onRerun,
  }: {
    status: RunStatus | null;
    reranning?: boolean;
    error?: string | null;
    onRerun: () => void;
  } = $props();
</script>

{#if status?.stale}
  <div role="status" class="flex items-center gap-3 rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm">
    <span>Engine version changed: <strong>{status.recorded}</strong> → <strong>{status.current}</strong>. Stored numbers are preserved.</span>
    <button type="button" class="rounded border px-2 py-1 hover:bg-accent disabled:opacity-50" disabled={reranning} onclick={onRerun}>
      {reranning ? 'Rerunning…' : 'Rerun on current engine'}
    </button>
    {#if error}<span class="text-destructive">{error}</span>{/if}
  </div>
{/if}
