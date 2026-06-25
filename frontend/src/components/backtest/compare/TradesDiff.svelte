<!-- frontend/src/components/backtest/compare/TradesDiff.svelte -->
<script lang="ts">
  import type { TradesDiff } from '$lib/features/runs/runTypes';
  let { trades }: { trades: TradesDiff } = $props();
  const keyStr = (k: [string | null, string, string]) => `${k[0] ?? '·'} ${k[1]} ${k[2]}`;
</script>

<section>
  <h3 class="mb-1 text-sm font-semibold">
    Trades — changed {trades.changed.length} · only A {trades.only_in_a.length} · only B {trades.only_in_b.length}
  </h3>
  {#if trades.changed.length}
    <h4 class="mt-2 text-xs font-semibold text-muted-foreground">Changed</h4>
    <ul class="text-sm">
      {#each trades.changed as c (keyStr(c.key))}
        <li class="border-b border-border/50 py-1">
          <span class="font-mono">{keyStr(c.key)}</span>
          {#each Object.entries(c.fields) as [field, d] (field)}
            <span class="ml-2 text-muted-foreground">{field}: {JSON.stringify(d.a)} → {JSON.stringify(d.b)}</span>
          {/each}
        </li>
      {/each}
    </ul>
  {/if}
  {#if trades.only_in_a.length}
    <h4 class="mt-2 text-xs font-semibold text-muted-foreground">Only in A</h4>
    <ul class="text-sm">{#each trades.only_in_a as t (keyStr(t.key))}<li class="py-0.5 font-mono">{keyStr(t.key)}</li>{/each}</ul>
  {/if}
  {#if trades.only_in_b.length}
    <h4 class="mt-2 text-xs font-semibold text-muted-foreground">Only in B</h4>
    <ul class="text-sm">{#each trades.only_in_b as t (keyStr(t.key))}<li class="py-0.5 font-mono">{keyStr(t.key)}</li>{/each}</ul>
  {/if}
</section>
