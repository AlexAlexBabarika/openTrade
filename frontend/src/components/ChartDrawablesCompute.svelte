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

  $effect(() => {
    const sym = symbol;
    const cs = candles;
    const prov = provider;
    const iv = interval;
    const list = items;

    const liveIds = new Set(list.map(d => d.id));
    untrack(() => {
      for (const [id, ctl] of computeControllers) {
        if (!liveIds.has(id)) {
          ctl.abort();
          computeControllers.delete(id);
          const nextMap = new Map(computedData);
          nextMap.delete(id);
          computedData = nextMap;
        }
      }

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
                computedData = new Map(computedData).set(d.id, value);
              })
              .catch(err => {
                if (ctl.signal.aborted) return;
                console.warn(`compute failed for drawable ${d.id}`, err);
              });
          } else {
            computedData = new Map(computedData).set(d.id, res);
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
