<!-- frontend/src/components/backtest/compare/InputsDiff.svelte -->
<script lang="ts">
  import type { InputsDiffRow } from '$lib/features/runs/runTypes';
  let { rows }: { rows: InputsDiffRow[] } = $props();
</script>

<section>
  <h3 class="mb-1 text-sm font-semibold">Inputs</h3>
  {#if rows.length === 0}
    <p class="text-sm text-muted-foreground">No input differences.</p>
  {:else}
    <table class="w-full text-sm">
      <tbody>
        {#each rows as r (r.path)}
          <tr class="border-b border-border/50">
            <td class="py-1 font-mono">{r.path}</td>
            <td class="py-1 text-right font-mono text-muted-foreground">{JSON.stringify(r.a)}</td>
            <td class="px-2 text-center">→</td>
            <td class="py-1 font-mono">{JSON.stringify(r.b)}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</section>
