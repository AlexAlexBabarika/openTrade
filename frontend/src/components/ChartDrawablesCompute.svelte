<script lang="ts">
  import { onDestroy, untrack } from 'svelte';
  import type { OHLCVCandle } from '../lib/types';
  import type { BundledDrawable } from '../lib/drawables/bundledDrawable';
  import { getTool } from '../lib/drawables';

  let {
    symbol,
    candles,
    provider,
    interval,
    items,
    computedData = $bindable(new Map<string, unknown>()),
  }: {
    symbol: string;
    candles: OHLCVCandle[];
    provider: string;
    interval: string;
    items: readonly BundledDrawable[];
    computedData?: Map<string, unknown>;
  } = $props();

  const computeControllers = new Map<string, AbortController>();

  function setComputedIfChanged(id: string, value: unknown): void {
    if (Object.is(computedData.get(id), value)) return;
    computedData = new Map(computedData).set(id, value);
  }

  $effect(() => {
    const sym = symbol;
    const cs = candles;
    const prov = provider;
    const iv = interval;
    const list = items;

    const liveIds = new Set(list.map(d => d.id));
    untrack(() => {
      let pruned = false;
      const nextMap = new Map(computedData);
      for (const id of [...computeControllers.keys()]) {
        if (!liveIds.has(id)) {
          computeControllers.get(id)?.abort();
          computeControllers.delete(id);
          if (nextMap.delete(id)) pruned = true;
        }
      }
      if (pruned) computedData = nextMap;

      for (const d of list) {
        const tool = getTool(d.type);
        if (!tool?.compute) continue;

        computeControllers.get(d.id)?.abort();
        const ctl = new AbortController();
        computeControllers.set(d.id, ctl);

        try {
          const res = tool.compute(d, {
            candles: cs,
            provider: prov,
            symbol: sym,
            interval: iv,
            signal: ctl.signal,
          });
          if (res instanceof Promise) {
            res
              .then(value => {
                if (ctl.signal.aborted) return;
                setComputedIfChanged(d.id, value);
              })
              .catch(err => {
                if (ctl.signal.aborted) return;
                console.warn(`compute failed for drawable ${d.id}`, err);
              });
          } else {
            setComputedIfChanged(d.id, res);
          }
        } catch (err) {
          console.warn(`compute failed for drawable ${d.id}`, err);
        }
      }
    });
  });

  onDestroy(() => {
    for (const ctl of computeControllers.values()) ctl.abort();
    computeControllers.clear();
  });
</script>
