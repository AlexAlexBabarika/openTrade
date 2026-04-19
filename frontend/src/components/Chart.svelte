<script lang="ts">
  import { onMount, onDestroy, untrack } from 'svelte';
  import type {
    IChartApi,
    ISeriesApi,
    LineWidth,
    MouseEventParams,
    Time,
  } from 'lightweight-charts';
  import {
    candleOHLCVtoAreaData,
    candleOHLCVtoCandlestickData,
    candleOHLCVtoVolumeData,
  } from '../lib/chartAdapters';
  import {
    createChartContainer,
    addCandlestickSeries,
    addVolumeSeries,
    addAreaSeries,
    addLineSeries,
    syncChartTheme,
    resolveColour,
  } from '../lib/chart';
  import type {
    OHLCVCandle,
    IndicatorPoint,
    BollingerBandsPoint,
  } from '../lib/types';
  import type { ChartColours, ChartType } from '../lib/chartColours';
  import { linePoint } from '../lib/chart';
  import {
    toCrosshairMode,
    type CrosshairModeName,
  } from '../lib/crosshair';
  import {
    drawables,
    ensureToolsRegistered,
    getTool,
    buildCoordMap,
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

  export type ChartApi = { appendCandle: (c: OHLCVCandle) => void };

  let {
    candles = [] as OHLCVCandle[],
    symbol = '',
    chartType = 'candlestick' as ChartType,
    showArea = true,
    showVolume = true,
    smaPoints = [] as IndicatorPoint[],
    emaPoints = [] as IndicatorPoint[],
    bbandsPoints = [] as BollingerBandsPoint[],
    smaLineWidth = 2,
    emaLineWidth = 2,
    bbandsLineWidth = 1,
    colours = undefined as ChartColours | undefined,
    crosshairMode = 'magnet' as CrosshairModeName,
    activeTool = $bindable<ActiveTool>(CURSOR),
    api = $bindable<ChartApi | null>(null),
  }: {
    candles: OHLCVCandle[];
    symbol: string;
    chartType?: ChartType;
    showArea?: boolean;
    showVolume?: boolean;
    smaPoints?: IndicatorPoint[];
    emaPoints?: IndicatorPoint[];
    bbandsPoints?: BollingerBandsPoint[];
    smaLineWidth?: number;
    emaLineWidth?: number;
    bbandsLineWidth?: number;
    colours?: ChartColours;
    crosshairMode?: CrosshairModeName;
    activeTool: ActiveTool;
    api?: ChartApi | null;
  } = $props();

  let containerEl: HTMLDivElement;
  let chart: IChartApi | null = null;
  let candleSeries: ISeriesApi<'Candlestick'> | null = null;
  let lineSeries: ISeriesApi<'Line'> | null = null;
  let areaSeries: ISeriesApi<'Area'> | null = null;
  let volumeSeries: ISeriesApi<'Histogram'> | null = null;
  let smaSeries: ISeriesApi<'Line'> | null = null;
  let emaSeries: ISeriesApi<'Line'> | null = null;
  let bbandsUpperSeries: ISeriesApi<'Line'> | null = null;
  let bbandsMiddleSeries: ISeriesApi<'Line'> | null = null;
  let bbandsLowerSeries: ISeriesApi<'Line'> | null = null;
  let resizeObserver: ResizeObserver | null = null;

  // Bumped whenever pan/zoom/resize invalidates our cached pixel coords.
  let coordVersion = $state(0);

  ensureToolsRegistered();

  let coordMap = $state<CoordMap | null>(null);

  let placement = $state<{
    type: string;
    machine: PlacementMachine<unknown>;
    preview: Drawable | null;
  } | null>(null);

  // Computed data per drawable. Synchronous for Phase 1; async in later phases.
  let computedData = $state<Map<string, unknown>>(new Map());

  // Anchor points are updated by Renderers via onAnchorPoint. We store the
  // Map outside reactivity to avoid feedback loops — `anchorTick` is the
  // reactive read used by the popup's position derivation.
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
    anchorTick; // re-run when anchors change
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
    if (id === 'settings') {
      // Phase 2b: open settings modal. For now, no-op.
      return;
    }
    if (id === 'custom' && action.id === 'custom') {
      action.handler(sel);
    }
  }

  let legendName = $state('');
  let legendPrice = $state('');
  let legendDate = $state('');
  let legendVolume = $state('');
  let showLegend = $state(false);

  function formatPrice(price: number): string {
    return (Math.round(price * 100) / 100).toFixed(2);
  }

  const dateFormatter = new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  function formatDate(time: Time): string {
    let date: Date;
    if (typeof time === 'string') {
      date = new Date(time);
    } else if (typeof time === 'number') {
      date = new Date(time * 1000);
    } else {
      date = new Date(time.year, time.month - 1, time.day);
    }
    return dateFormatter.format(date);
  }

  function updateLegend(param: MouseEventParams | undefined): void {
    const priceSeries = candleSeries ?? lineSeries;
    if (!priceSeries) return;

    const validCrosshairPoint = !(
      param === undefined ||
      param.time === undefined ||
      param.point === undefined ||
      param.point.x < 0 ||
      param.point.y < 0
    );

    const bar = validCrosshairPoint
      ? param.seriesData.get(priceSeries)
      : priceSeries.dataByIndex(Number.MAX_SAFE_INTEGER, -1);

    const volumeBar = volumeSeries
      ? validCrosshairPoint
        ? param.seriesData.get(volumeSeries)
        : volumeSeries.dataByIndex(Number.MAX_SAFE_INTEGER, -1)
      : null;

    if (!bar) return;

    let price: number | undefined;
    if ('value' in bar && typeof bar.value === 'number') {
      price = bar.value;
    } else if ('close' in bar && typeof bar.close === 'number') {
      price = bar.close;
    }
    if (price === undefined) return;

    let volume: number | undefined;
    if (
      volumeBar &&
      'value' in volumeBar &&
      typeof volumeBar.value === 'number'
    ) {
      volume = volumeBar.value;
    }

    legendName = symbol || 'Unknown';
    legendPrice = formatPrice(price);
    legendDate = formatDate(bar.time);
    legendVolume = volume !== undefined ? volume.toLocaleString() : '—';
    showLegend = true;
  }

  function initChart(): void {
    if (!containerEl) return;

    chart = createChartContainer(containerEl, colours);
    chart.subscribeCrosshairMove(updateLegend);
    updateLegend(undefined);
  }

  function applyVolume(enabled: boolean): void {
    if (!chart) return;

    if (enabled && !volumeSeries) {
      volumeSeries = addVolumeSeries(chart);
    } else if (!enabled && volumeSeries) {
      chart.removeSeries(volumeSeries);
      volumeSeries = null;
    }
  }

  function applyArea(enabled: boolean): void {
    if (!chart) return;

    if (enabled && !areaSeries) {
      areaSeries = addAreaSeries(chart, colours);
    } else if (!enabled && areaSeries) {
      chart.removeSeries(areaSeries);
      areaSeries = null;
    }
  }

  function applySeries(type: ChartType): void {
    if (!chart) return;

    if (candleSeries) {
      chart.removeSeries(candleSeries);
      candleSeries = null;
    }
    if (lineSeries) {
      chart.removeSeries(lineSeries);
      lineSeries = null;
    }

    if (type === 'candlestick') {
      candleSeries = addCandlestickSeries(chart, colours);
    } else {
      lineSeries = addLineSeries(chart, resolveColour(colours, 'lineColour'));
    }
  }

  function toVolume(c: OHLCVCandle) {
    return candleOHLCVtoVolumeData(c, colours?.volumeUp, colours?.volumeDown);
  }

  function appendCandle(c: OHLCVCandle): void {
    if (!chart) return;

    if (candleSeries) {
      candleSeries.update(candleOHLCVtoCandlestickData(c));
    }
    if (lineSeries) {
      lineSeries.update(candleOHLCVtoAreaData(c));
    }
    if (areaSeries && candles.length >= 20) {
      if (candles.length === 20) {
        areaSeries.setData(candles.map(candleOHLCVtoAreaData));
      } else {
        areaSeries.update(candleOHLCVtoAreaData(c));
      }
    }
    if (volumeSeries) {
      volumeSeries.update(toVolume(c));
    }
    updateLegend(undefined);
  }

  function setSeriesData(data: OHLCVCandle[]): void {
    if (!chart) return;

    if (areaSeries) {
      areaSeries.setData(
        data.length >= 20 ? data.map(candleOHLCVtoAreaData) : [],
      );
    }
    if (candleSeries) {
      candleSeries.setData(data.map(candleOHLCVtoCandlestickData));
    }
    if (lineSeries) {
      lineSeries.setData(data.map(candleOHLCVtoAreaData));
    }
    if (volumeSeries) {
      volumeSeries.setData(data.map(toVolume));
    }
    updateLegend(undefined);
  }

  function handleResize(): void {
    if (chart && containerEl) {
      chart.applyOptions({
        width: containerEl.clientWidth,
        height: containerEl.clientHeight,
      });
      coordVersion += 1;
    }
  }

  function priceSeries(): ISeriesApi<'Candlestick' | 'Line'> | null {
    return candleSeries ?? lineSeries;
  }

  function pointerToChart(
    clientX: number,
    clientY: number,
  ): { time: number; price: number } | null {
    if (!chart || !containerEl) return null;
    const series = priceSeries();
    if (!series) return null;
    const rect = containerEl.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    const time = chart.timeScale().coordinateToTime(x);
    const price = series.coordinateToPrice(y);
    if (time == null || price == null) return null;
    return { time: time as number, price };
  }

  function toChartPoint(e: PointerEvent): ChartPoint | null {
    const pt = pointerToChart(e.clientX, e.clientY);
    return pt ? { time: pt.time, price: pt.price } : null;
  }

  function onChartPointerDown(e: PointerEvent) {
    // Selection path: cursor mode, click on chart background deselects.
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

    // Placement path.
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
          params: tool.defaults.params,
          style: tool.defaults.style,
          createdAt: Date.now(),
        });
        placement = null;
        activeTool = CURSOR;
      });
      placement = { type: toolType, machine, preview: null };
    }
    placement.machine.onPointerDown(pt);
    containerEl?.setPointerCapture?.(e.pointerId);
    e.preventDefault();
    refreshPlacementPreview();
  }

  function onChartPointerMove(e: PointerEvent) {
    if (!placement) return;
    const pt = toChartPoint(e);
    if (!pt) return;
    placement.machine.onPointerMove(pt);
    refreshPlacementPreview();
  }

  function onChartPointerUp(e: PointerEvent) {
    if (!placement) return;
    const pt = toChartPoint(e);
    if (pt) placement.machine.onPointerUp(pt);
    if (containerEl?.hasPointerCapture?.(e.pointerId)) {
      containerEl.releasePointerCapture(e.pointerId);
    }
    refreshPlacementPreview();
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

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      if (placement) {
        placement.machine.cancel();
        placement = null;
        activeTool = CURSOR;
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

  $effect(() => {
    const version = coordVersion;
    if (!chart) {
      coordMap = null;
      return;
    }
    const series = priceSeries();
    if (!series) {
      coordMap = null;
      return;
    }
    coordMap = buildCoordMap(chart, series, version);
  });

  $effect(() => {
    const sym = symbol;
    const cs = candles;
    const items = drawables.forSymbol(sym);
    const next = new Map<string, unknown>();
    for (const d of items) {
      const tool = getTool(d.type);
      if (!tool?.compute) continue;
      try {
        const res = tool.compute(d, { candles: cs });
        if (res instanceof Promise) {
          // Phase 1 tools are synchronous. Ignore async results for now.
          continue;
        }
        next.set(d.id, res);
      } catch (err) {
        console.warn(`compute failed for drawable ${d.id}`, err);
      }
    }
    computedData = next;
  });

  // Suspend chart scroll/scale while placing a drawable.
  $effect(() => {
    const placing = placement !== null;
    if (!chart) return;
    untrack(() => {
      chart?.applyOptions({
        handleScroll: !placing,
        handleScale: !placing,
      });
    });
  });

  onMount(() => {
    initChart();
    api = { appendCandle };
    window.addEventListener('resize', handleResize);

    if (containerEl) {
      resizeObserver = new ResizeObserver(handleResize);
      resizeObserver.observe(containerEl);
    }

    let lastFrom: number | null = null;
    let lastTo: number | null = null;
    chart?.timeScale().subscribeVisibleLogicalRangeChange(range => {
      const from = range?.from ?? null;
      const to = range?.to ?? null;
      if (from === lastFrom && to === lastTo) return;
      lastFrom = from;
      lastTo = to;
      coordVersion += 1;
    });
  });

  onDestroy(() => {
    api = null;
    window.removeEventListener('resize', handleResize);
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    if (chart) {
      chart.remove();
      chart = null;
    }
  });

  let prevCandles: OHLCVCandle[] | undefined;

  $effect(() => {
    if (!chart) return;
    const type = chartType;
    const area = showArea;
    const volume = showVolume;
    const data = candles;
    untrack(() => {
      if (!chart) return;
      applySeries(type);
      applyArea(area);
      applyVolume(volume);
      setSeriesData(data);
      if (data !== prevCandles) {
        chart.timeScale().fitContent();
        prevCandles = data;
      }
    });
  });

  $effect(() => {
    if (!chart) return;
    const points = smaPoints;
    const width = smaLineWidth;
    untrack(() => {
      if (!chart) return;
      if (points.length > 0) {
        if (!smaSeries) {
          smaSeries = addLineSeries(chart, resolveColour(colours, 'smaLine'));
        }
        smaSeries.applyOptions({ lineWidth: width as LineWidth });
        smaSeries.setData(points.map(p => linePoint(p.timestamp, p.value)));
      } else if (smaSeries) {
        chart.removeSeries(smaSeries);
        smaSeries = null;
      }
    });
  });

  $effect(() => {
    if (!chart) return;
    const points = emaPoints;
    const width = emaLineWidth;
    untrack(() => {
      if (!chart) return;
      if (points.length > 0) {
        if (!emaSeries) {
          emaSeries = addLineSeries(chart, resolveColour(colours, 'emaLine'));
        }
        emaSeries.applyOptions({ lineWidth: width as LineWidth });
        emaSeries.setData(points.map(p => linePoint(p.timestamp, p.value)));
      } else if (emaSeries) {
        chart.removeSeries(emaSeries);
        emaSeries = null;
      }
    });
  });

  $effect(() => {
    if (!chart) return;
    const points = bbandsPoints;
    const width = bbandsLineWidth;
    untrack(() => {
      if (!chart) return;
      if (points.length > 0) {
        if (!bbandsUpperSeries) {
          bbandsUpperSeries = addLineSeries(
            chart,
            resolveColour(colours, 'bbandsUpper'),
          );
        }
        if (!bbandsMiddleSeries) {
          bbandsMiddleSeries = addLineSeries(
            chart,
            resolveColour(colours, 'bbandsMiddle'),
          );
        }
        if (!bbandsLowerSeries) {
          bbandsLowerSeries = addLineSeries(
            chart,
            resolveColour(colours, 'bbandsLower'),
          );
        }
        bbandsUpperSeries.applyOptions({ lineWidth: width as LineWidth });
        bbandsMiddleSeries.applyOptions({
          lineWidth: width as LineWidth,
          lineStyle: 2,
        });
        bbandsLowerSeries.applyOptions({ lineWidth: width as LineWidth });
        bbandsUpperSeries.setData(
          points.map(p => linePoint(p.timestamp, p.upper)),
        );
        bbandsMiddleSeries.setData(
          points.map(p => linePoint(p.timestamp, p.middle)),
        );
        bbandsLowerSeries.setData(
          points.map(p => linePoint(p.timestamp, p.lower)),
        );
      } else {
        if (bbandsUpperSeries) {
          chart.removeSeries(bbandsUpperSeries);
          bbandsUpperSeries = null;
        }
        if (bbandsMiddleSeries) {
          chart.removeSeries(bbandsMiddleSeries);
          bbandsMiddleSeries = null;
        }
        if (bbandsLowerSeries) {
          chart.removeSeries(bbandsLowerSeries);
          bbandsLowerSeries = null;
        }
      }
    });
  });

  $effect(() => {
    if (!chart) return;
    const mode = crosshairMode;
    untrack(() => {
      chart?.applyOptions({ crosshair: { mode: toCrosshairMode(mode) } });
    });
  });

  $effect(() => {
    if (!chart || !colours) return;
    syncChartTheme({
      chart,
      candleSeries,
      areaSeries,
      lineSeries,
      smaSeries,
      emaSeries,
      bbandsUpperSeries,
      bbandsMiddleSeries,
      bbandsLowerSeries,
      colours,
    });
  });

  $effect(() => {
    if (!chart || !colours || !volumeSeries) return;
    colours.volumeUp;
    colours.volumeDown;
    untrack(() => {
      if (volumeSeries && candles.length > 0) {
        volumeSeries.setData(candles.map(toVolume));
      }
    });
  });
</script>

<div
  class="flex-1 min-h-[400px] relative w-full z-0 overflow-hidden"
  class:cursor-crosshair={activeTool !== CURSOR}
  bind:this={containerEl}
  role="presentation"
  tabindex="0"
  onpointerdown={onChartPointerDown}
  onpointermove={onChartPointerMove}
  onpointerup={onChartPointerUp}
  onpointercancel={onChartPointerUp}
  onkeydown={onKeyDown}
>
  {#if showLegend}
    <div
      class="absolute left-4 top-4 z-10 text-sm font-light pointer-events-none font-mono leading-[18px]"
      style:color={colours?.textColour}
    >
      <div class="text-2xl my-1 font-medium">{legendName}</div>
      <div class="text-[22px] my-1 font-semibold font-mono">{legendPrice}</div>
      <div style:opacity="0.7" class="font-mono">{legendDate}</div>
      <div style:opacity="0.7" class="font-mono">Volume: {legendVolume}</div>
    </div>
  {/if}

  {#if coordMap}
    <svg
      class="absolute inset-0 w-full h-full z-10 pointer-events-none"
      style="overflow: visible;"
    >
      {#each drawables.forSymbol(symbol) as d (d.id)}
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
            onAnchorPoint={(pt) => setAnchorPoint(d.id, pt)}
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
</div>

<style>
  /* lightweight-charts injects canvas elements that need full sizing */
  div :global(canvas) {
    width: 100% !important;
    height: 100% !important;
  }
</style>
