<script lang="ts">
  import { onDestroy, untrack } from 'svelte';
  import type { OHLCVCandle } from '../lib/types';
  import type { BundledDrawable } from '../lib/drawables/bundledDrawable';
  import { getTool } from '../lib/drawables';
  import { measureDrawablesSync } from '../lib/dev/drawablesProfile';

  /** Stable batch identity so a new candles array reference does not N× recompute when OHLCV is unchanged. */
  function candleBatchSignature(cs: OHLCVCandle[]): string {
    const n = cs.length;
    if (n === 0) return '0';
    const row = (c: OHLCVCandle) =>
      `${c.timestamp}:${c.open}:${c.high}:${c.low}:${c.close}:${c.volume}`;
    const mid = n === 1 ? 0 : Math.floor(n / 2);
    return `${n}|${row(cs[0])}|${row(cs[mid])}|${row(cs[n - 1])}`;
  }

  function bundledListComputeKey(items: readonly BundledDrawable[]): string {
    return items
      .map(
        d =>
          `${d.id}:${d.type}:${JSON.stringify(d.geometry)}:${JSON.stringify(d.params)}:${JSON.stringify(d.style)}`,
      )
      .join('|');
  }

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

  let lastComputeWorkKey: string | undefined;

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

    const workKey = `${sym}|${prov}|${iv}|${candleBatchSignature(cs)}|${bundledListComputeKey(list)}`;
    if (workKey === lastComputeWorkKey) return;
    lastComputeWorkKey = workKey;

    const liveIds = new Set(list.map(d => d.id));
    untrack(() => {
      measureDrawablesSync('drawables:compute-pass', () => {
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
  });

  onDestroy(() => {
    for (const ctl of computeControllers.values()) ctl.abort();
    computeControllers.clear();
  });
</script>
