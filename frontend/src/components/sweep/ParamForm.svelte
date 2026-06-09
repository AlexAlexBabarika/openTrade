<script lang="ts" module>
  import type { ParamSchemaEntry } from '$lib/features/sweep/types';
  export function describe(p: ParamSchemaEntry): string {
    if (p.kind === 'choice') return p.options.join(' | ');
    return `${p.low}…${p.high} step ${p.step}`;
  }
</script>

<script lang="ts">
  import type { ParamSchema, SweepFormValues } from '$lib/features/sweep/types';

  let {
    schema,
    code,
    symbol = 'SPY',
    provider = 'yfinance',
    onsubmit,
  }: {
    schema: ParamSchema;
    code: string;
    symbol?: string;
    provider?: string;
    onsubmit: (form: SweepFormValues) => void;
  } = $props();

  const paramNames = $derived(Object.keys(schema));
  let vary = $state<string[]>([]);
  let search = $state<'grid' | 'random'>('grid');
  let metric = $state('sharpe');
  let nRandom = $state(200);
  let seed = $state(0);

  // Default to varying the first two params once the schema arrives.
  $effect(() => {
    if (vary.length === 0 && paramNames.length > 0) {
      vary = paramNames.slice(0, 2);
    }
  });

  function toggle(name: string) {
    vary = vary.includes(name) ? vary.filter(n => n !== name) : [...vary, name];
  }

  function submit() {
    onsubmit({
      code,
      symbol,
      provider,
      search,
      metric,
      vary,
      n_random: nRandom,
      seed,
    });
  }
</script>

<form class="form" onsubmit={e => (e.preventDefault(), submit())}>
  <fieldset class="params">
    <legend>Vary parameters</legend>
    {#each paramNames as name (name)}
      <label class="param">
        <input type="checkbox" checked={vary.includes(name)} onchange={() => toggle(name)} />
        <span class="pname">{name}</span>
        <span class="prange">{describe(schema[name])}</span>
      </label>
    {:else}
      <p class="hint">No parameters declared. Add a <code>params = {'{'}…{'}'}</code> block.</p>
    {/each}
  </fieldset>

  <div class="row">
    <label>Search
      <select bind:value={search}>
        <option value="grid">Grid</option>
        <option value="random">Random</option>
      </select>
    </label>
    <label>Metric
      <select bind:value={metric}>
        <option value="sharpe">Sharpe</option>
        <option value="calmar">Calmar</option>
        <option value="sortino">Sortino</option>
        <option value="total_return">Total return</option>
      </select>
    </label>
    {#if search === 'random'}
      <label>Trials <input type="number" min="1" bind:value={nRandom} /></label>
    {/if}
    <label>Seed <input type="number" bind:value={seed} /></label>
  </div>

  <button type="submit" class="run" disabled={vary.length === 0}>Run sweep</button>
</form>

<style>
  .form { display: flex; flex-direction: column; gap: 12px; padding: 12px 16px; }
  .params { display: flex; flex-direction: column; gap: 6px; border: 1px dashed oklch(var(--border)); border-radius: 8px; padding: 10px; }
  .param { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px; font-size: 12px; }
  .pname { font-weight: 600; }
  .prange { color: oklch(var(--muted-foreground)); }
  .row { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; }
  .row label { display: flex; flex-direction: column; gap: 4px; font-size: 11px; color: oklch(var(--muted-foreground)); }
  .run { align-self: start; padding: 8px 16px; border-radius: 6px; border: 1px solid oklch(var(--primary)); background: oklch(var(--primary) / 0.15); color: oklch(var(--foreground)); cursor: pointer; }
  .run:disabled { opacity: 0.5; cursor: not-allowed; }
  .hint { font-size: 12px; color: oklch(var(--muted-foreground)); }
</style>
