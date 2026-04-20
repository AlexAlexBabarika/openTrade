<!-- Chart overlay: placement + popup orchestration; compute and SVG live in child components. -->
<script lang="ts">
  import type { OHLCVCandle } from '../lib/types';
  import {
    drawables,
    getTool,
    CURSOR,
    type BundledDrawable,
    type ActiveTool,
    type CoordMap,
    type ChartPoint,
    type PlacementMachine,
    type Drawable,
    type ScreenPoint,
    resolvePopupActions,
  } from '../lib/drawables';
  import type { PopupAction } from '../lib/drawables';
  import ChartDrawablesCompute from './ChartDrawablesCompute.svelte';
  import DrawablesSvgScene from './DrawablesSvgScene.svelte';
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

  let itemsForSymbol = $derived.by(() => drawables.forSymbol(symbol));

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
        } as BundledDrawable);
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
</script>

{#if coordMap}
  <ChartDrawablesCompute
    bind:computedData
    {symbol}
    {candles}
    {provider}
    {interval}
    items={itemsForSymbol}
  />

  <DrawablesSvgScene
    {coordMap}
    items={itemsForSymbol}
    {computedData}
    selectedId={drawables.selected?.id ?? null}
    {placement}
    onPatchGeometry={(id, geometry) => drawables.update(id, { geometry })}
    onSelectDrawable={id => drawables.select(id)}
    onAnchorPoint={(id, pt) => setAnchorPoint(id, pt)}
  />

  {#if popupAnchor && popupActions.length > 0}
    <DrawablePopup
      anchor={popupAnchor}
      actions={popupActions}
      onAction={onPopupAction}
    />
  {/if}
{/if}
