<script lang="ts">
  import { onDestroy, untrack } from 'svelte';
  import type { OHLCVCandle } from '$lib/core/types';
  import {
    bundledDrawablesFingerprint,
    candleBatchSignature,
  } from '$lib/features/chart/candleFingerprint';
  import type { BundledDrawable } from '$lib/features/drawables/bundledDrawable';
  import { getTool } from '$lib/features/drawables';
  import { measureDrawablesSync } from '$lib/core/dev/drawablesProfile';

  /** Cached pieces so we do not rescan candles / stringify drawables when only the other input changes. */
  let lastMetaKey: string | undefined;
  let lastItemsRef: readonly BundledDrawable[] | undefined;
  let lastCandlesRef: OHLCVCandle[] | undefined;
  let lastListKey: string | undefined;
  let lastCandleSig: string | undefined;

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

  let pendingComputed = new Map<string, unknown>();
  let flushComputedScheduled = false;

  function applyPendingComputed(): void {
    if (pendingComputed.size === 0) return;
    const next = new Map(computedData);
    let changed = false;
    for (const [id, value] of pendingComputed) {
      if (!Object.is(next.get(id), value)) {
        next.set(id, value);
        changed = true;
      }
    }
    pendingComputed.clear();
    if (changed) computedData = next;
  }

  function flushComputedPendingSync(): void {
    flushComputedScheduled = false;
    applyPendingComputed();
  }

  function scheduleFlushComputed(): void {
    if (flushComputedScheduled) return;
    flushComputedScheduled = true;
    queueMicrotask(() => {
      flushComputedScheduled = false;
      applyPendingComputed();
    });
  }

  function setComputedIfChanged(id: string, value: unknown): void {
    const current = pendingComputed.has(id)
      ? pendingComputed.get(id)
      : computedData.get(id);
    if (Object.is(current, value)) return;
    pendingComputed.set(id, value);
    scheduleFlushComputed();
  }

  $effect(() => {
    const sym = symbol;
    const cs = candles;
    const prov = provider;
    const iv = interval;
    const list = items;

    const metaKey = `${sym}|${prov}|${iv}`;
    if (metaKey === lastMetaKey && list === lastItemsRef && cs === lastCandlesRef) {
      return;
    }

    const { listKey, candleSig, workKey } = measureDrawablesSync(
      'drawables:workKey',
      () => {
        const lk =
          metaKey === lastMetaKey && list === lastItemsRef
            ? lastListKey!
            : bundledDrawablesFingerprint(list);
        const csig =
          metaKey === lastMetaKey && cs === lastCandlesRef
            ? lastCandleSig!
            : candleBatchSignature(cs);
        return {
          listKey: lk,
          candleSig: csig,
          workKey: `${metaKey}|${csig}|${lk}`,
        };
      },
    );

    if (workKey === lastComputeWorkKey) return;
    lastComputeWorkKey = workKey;
    lastMetaKey = metaKey;
    lastItemsRef = list;
    lastCandlesRef = cs;
    lastListKey = listKey;
    lastCandleSig = candleSig;

    const liveIds = new Set(list.map(d => d.id));
    untrack(() => {
      measureDrawablesSync('drawables:compute-pass', () => {
        flushComputedPendingSync();

        let pruned = false;
        const nextMap = new Map(computedData);
        for (const id of [...computeControllers.keys()]) {
          if (!liveIds.has(id)) {
            pendingComputed.delete(id);
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
    pendingComputed.clear();
  });
</script>
