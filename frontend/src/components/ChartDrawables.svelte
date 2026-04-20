<!-- Chart overlay: drawable placement, compute, SVG renderers, popup. -->
<script lang="ts">
  import { onDestroy, untrack } from 'svelte';
  import type { OHLCVCandle } from '../lib/types';
  import {
    drawables,
    getTool,
    CURSOR,
    type ActiveTool,
    type CoordMap,
    type ChartPoint,
    type PlacementMachine,
    type Drawable,
    type ScreenPoint,
    resolvePopupActions,
  } from '../lib/drawables';
  import type { PopupAction } from '../lib/drawables';
  import DrawablePopup from './DrawablePopup.svelte';

  let {
    coordMap = null as CoordMap | null,
    symbol = '',
    activeTool,
    onActiveToolChange,
    candles = [] as OHLCVCandle[],
    provider = 'yfinance',
    interval = '1d',
    toChartPoint,
    containerEl = null as HTMLDivElement | null,
    onPlacementActiveChange,
  }: {
    coordMap: CoordMap | null;
    symbol: string;
    activeTool: ActiveTool;
    /** Prefer this over nested $bindable so App state always updates when placement finishes. */
    onActiveToolChange: (t: ActiveTool) => void;
    candles: OHLCVCandle[];
    provider: string;
    interval: string;
    toChartPoint: (e: PointerEvent) => ChartPoint | null;
    containerEl: HTMLDivElement | null;
    /** Lets the chart disable pan/zoom while the user is placing a drawable. */
    onPlacementActiveChange?: (active: boolean) => void;
  } = $props();

  function setActiveTool(t: ActiveTool): void {
    onActiveToolChange(t);
  }

  /** Subscribe via `drawables.items` so the list reactively updates when `add()` runs. */
  let drawablesForSymbol = $derived.by(() =>
    drawables.items.filter(d => d.symbol === symbol),
  );

  let placement = $state<{
    type: string;
    machine: PlacementMachine<unknown>;
    preview: Drawable | null;
  } | null>(null);

  $effect(() => {
    onPlacementActiveChange?.(placement !== null);
  });

  let computedData = $state<Map<string, unknown>>(new Map());

  const anchorPointsMap = new Map<string, ScreenPoint>();
  let anchorTick = $state(0);

  function setAnchorPoint(id: string, pt: ScreenPoint | null): void {
    const prev = anchorPointsMap.get(id);
    if (pt === null) {
      if (prev === undefined) return;
      anchorPointsMap.delete(id);
    } else {
      if (prev && prev.x === pt.x && prev.y === pt.y) return;
      anchorPointsMap.set(id, pt);
    }
    anchorTick += 1;
  }

  let popupAnchor = $derived.by(() => {
    anchorTick;
    const sel = drawables.selected;
    if (!sel) return null;
    const pt = anchorPointsMap.get(sel.id);
    return pt ?? null;
  });

  let popupActions = $derived.by(() => {
    const sel = drawables.selected;
    if (!sel) return [] as PopupAction[];
    const tool = getTool(sel.type);
    return tool ? resolvePopupActions(tool) : [];
  });

  function onPopupAction(id: PopupAction['id'], action: PopupAction): void {
    const sel = drawables.selected;
    if (!sel) return;
    if (id === 'delete') {
      drawables.remove(sel.id);
      return;
    }
    if (id === 'custom' && action.id === 'custom') {
      action.handler(sel);
    }
  }

  function refreshPlacementPreview() {
    if (!placement) return;
    const prev = placement.machine.preview;
    const tool = getTool(placement.type);
    if (!prev || !tool) {
      placement = { ...placement, preview: null };
      return;
    }
    const previewDrawable: Drawable = {
      id: '__preview__',
      type: placement.type,
      symbol,
      geometry: prev.geometry,
      params: tool.defaults.params,
      style: tool.defaults.style,
      createdAt: 0,
    };
    placement = { ...placement, preview: previewDrawable };
  }

  export function handlePointerDown(e: PointerEvent) {
    if (activeTool === CURSOR) {
      const target = e.target as Element | null;
      const hitId = target
        ?.closest('[data-drawable-id]')
        ?.getAttribute('data-drawable-id');
      if (hitId) {
        drawables.select(hitId);
      } else {
        drawables.select(null);
      }
      return;
    }

    const pt = toChartPoint(e);
    if (!pt || !coordMap) return;
    if (!placement) {
      const tool = getTool(activeTool);
      if (!tool) return;
      const machine = tool.createPlacement({ coordMap, symbol });
      const toolType = tool.type;
      machine.onComplete((geometry: unknown) => {
        drawables.add({
          id: crypto.randomUUID(),
          type: toolType,
          symbol,
          geometry,
          params: structuredClone(tool.defaults.params),
          style: structuredClone(tool.defaults.style),
          createdAt: Date.now(),
        });
        placement = null;
        setActiveTool(CURSOR);
      });
      placement = { type: toolType, machine, preview: null };
    }
    placement.machine.onPointerDown(pt);
    containerEl?.setPointerCapture?.(e.pointerId);
    e.preventDefault();
    refreshPlacementPreview();
  }

  export function handlePointerMove(e: PointerEvent) {
    if (!placement) return;
    const pt = toChartPoint(e);
    if (!pt) return;
    placement.machine.onPointerMove(pt);
    refreshPlacementPreview();
  }

  export function handlePointerUp(e: PointerEvent) {
    if (!placement) return;
    const pt = toChartPoint(e);
    if (pt) placement.machine.onPointerUp(pt);
    if (containerEl?.hasPointerCapture?.(e.pointerId)) {
      containerEl.releasePointerCapture(e.pointerId);
    }
    refreshPlacementPreview();
  }

  export function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      if (placement) {
        placement.machine.cancel();
        placement = null;
        setActiveTool(CURSOR);
        return;
      }
      if (drawables.selected) {
        drawables.select(null);
      }
      return;
    }
    if (
      (e.key === 'Delete' || e.key === 'Backspace') &&
      drawables.selected
    ) {
      drawables.remove(drawables.selected.id);
    }
  }

  const computeControllers = new Map<string, AbortController>();

  $effect(() => {
    const sym = symbol;
    const cs = candles;
    const prov = provider;
    const iv = interval;
    const items = drawables.items.filter(d => d.symbol === sym);

    const liveIds = new Set(items.map(d => d.id));
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

      for (const d of items) {
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

{#if coordMap}
  <svg
    class="absolute inset-0 w-full h-full z-10 pointer-events-none"
    style="overflow: visible;"
  >
    {#each drawablesForSymbol as d (d.id)}
      {@const tool = getTool(d.type)}
      {#if tool}
        {@const RendererCmp = tool.Renderer}
        <RendererCmp
          drawable={d}
          data={computedData.get(d.id)}
          selected={drawables.selected?.id === d.id}
          coordMap={coordMap}
          onGeometryChange={geo => drawables.update(d.id, { geometry: geo })}
          onRequestSelect={() => drawables.select(d.id)}
          onAnchorPoint={pt => setAnchorPoint(d.id, pt)}
        />
      {/if}
    {/each}

    {#if placement?.preview}
      {@const previewTool = getTool(placement.type)}
      {#if previewTool}
        {@const PreviewCmp = previewTool.Renderer}
        <PreviewCmp
          drawable={placement.preview}
          data={undefined}
          selected={false}
          coordMap={coordMap}
          onGeometryChange={() => {}}
          onRequestSelect={() => {}}
          onAnchorPoint={() => {}}
        />
      {/if}
    {/if}
  </svg>

  {#if popupAnchor && popupActions.length > 0}
    <DrawablePopup
      anchor={popupAnchor}
      actions={popupActions}
      onAction={onPopupAction}
    />
  {/if}
{/if}
