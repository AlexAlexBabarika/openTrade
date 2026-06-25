<!-- frontend/src/components/backtest/RecentRunsPanel.svelte -->
<script lang="ts">
  import { runsHistory } from '$lib/features/runs/runsHistory.svelte';
  import { truncateRunId } from '$lib/features/runs/format';

  let {
    open = $bindable(false),
    onOpenRun,
    onCompare,
  }: {
    open?: boolean;
    onOpenRun: (id: string) => void;
    onCompare: (a: string, b: string) => void;
  } = $props();

  let selected = $state<string[]>([]);

  function toggle(id: string): void {
    selected = selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id].slice(-2);
  }
  function compareSelected(): void {
    if (selected.length === 2) onCompare(selected[0], selected[1]);
  }
</script>

{#if open}
  <aside class="fixed right-0 top-14 bottom-0 z-50 flex w-80 max-w-full flex-col gap-2 overflow-y-auto border-l border-border bg-background p-4" aria-label="Recent runs">
    <header class="flex items-center justify-between">
      <h2 class="text-sm font-semibold">Recent runs</h2>
      <button type="button" class="text-muted-foreground hover:text-foreground" onclick={() => (open = false)}>✕</button>
    </header>

    {#if runsHistory.entries.length === 0}
      <p class="text-sm text-muted-foreground">No runs yet this session.</p>
    {:else}
      <button type="button" class="self-start rounded border px-2 py-1 text-xs disabled:opacity-50" disabled={selected.length !== 2} onclick={compareSelected}>
        Compare selected ({selected.length}/2)
      </button>
      <ul class="flex flex-col gap-1">
        {#each runsHistory.entries as e (e.run_id)}
          <li class="flex items-center gap-2 rounded px-1 py-1 hover:bg-accent">
            <input type="checkbox" checked={selected.includes(e.run_id)} onchange={() => toggle(e.run_id)} aria-label="Select for compare" />
            <button type="button" class="flex-1 text-left" onclick={() => onOpenRun(e.run_id)}>
              <span class="text-sm">{e.label}</span>
              <span class="ml-1 font-mono text-xs text-muted-foreground">{truncateRunId(e.run_id)}</span>
            </button>
            <button type="button" class="text-xs text-muted-foreground hover:text-destructive" onclick={() => runsHistory.remove(e.run_id)} aria-label="Remove">✕</button>
          </li>
        {/each}
      </ul>
    {/if}
  </aside>
{/if}
