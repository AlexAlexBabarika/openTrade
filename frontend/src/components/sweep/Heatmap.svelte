<script lang="ts">
  import { heatmapMatrix } from '$lib/features/sweep/derive';
  import type { TrialRow } from '$lib/features/sweep/types';

  let {
    trials,
    xParam,
    yParam,
    metric,
    ontrial,
  }: {
    trials: TrialRow[];
    xParam: string;
    yParam: string;
    metric: string;
    ontrial?: (trialId: number) => void;
  } = $props();

  const m = $derived(heatmapMatrix(trials, xParam, yParam, metric));

  // metric -> color: low = cool, high = warm. Uses the app's primary hue ramp.
  function color(v: number | null): string {
    if (v == null) return 'transparent';
    const span = m.max - m.min || 1;
    const t = (v - m.min) / span; // 0..1
    const hue = 250 - 250 * t; // blue -> red
    return `oklch(0.6 0.15 ${hue})`;
  }

  function trialAt(xi: number, yi: number): TrialRow | undefined {
    const x = m.xValues[xi];
    const y = m.yValues[yi];
    return trials.find(
      t => Number(t.params[xParam]) === x && Number(t.params[yParam]) === y,
    );
  }
</script>

<div class="wrap">
  <div class="grid" style={`grid-template-columns: 28px repeat(${m.xValues.length}, 1fr);`}>
    <div></div>
    {#each m.xValues as xv (xv)}<div class="axis x">{xv}</div>{/each}
    {#each m.yValues as yv, yi (yv)}
      <div class="axis y">{yv}</div>
      {#each m.xValues as _xv, xi (xi)}
        {@const v = m.cells[yi][xi]}
        <button
          type="button"
          class="cell"
          style={`background:${color(v)}`}
          title={`${yParam}=${m.yValues[yi]} ${xParam}=${m.xValues[xi]} → ${v ?? '—'}`}
          onclick={() => {
            const t = trialAt(xi, yi);
            if (t && ontrial) ontrial(t.trial_id);
          }}
          aria-label={`${yParam}=${m.yValues[yi]} ${xParam}=${m.xValues[xi]}`}
        ></button>
      {/each}
    {/each}
  </div>
  <div class="legend">
    <span>{m.min.toFixed(2)}</span>
    <div class="ramp"></div>
    <span>{m.max.toFixed(2)}</span>
  </div>
</div>

<style>
  .wrap { display: flex; flex-direction: column; gap: 8px; padding: 12px; }
  .grid { display: grid; gap: 2px; }
  .axis { font-size: 10px; color: oklch(var(--muted-foreground)); display: flex; align-items: center; justify-content: center; }
  .cell { aspect-ratio: 1; border: 0; border-radius: 2px; cursor: pointer; }
  .cell:hover { outline: 1px solid oklch(var(--foreground)); }
  .legend { display: flex; align-items: center; gap: 8px; font-size: 10px; color: oklch(var(--muted-foreground)); }
  .ramp { flex: 1; height: 8px; border-radius: 4px; background: linear-gradient(90deg, oklch(0.6 0.15 250), oklch(0.6 0.15 0)); }
</style>
