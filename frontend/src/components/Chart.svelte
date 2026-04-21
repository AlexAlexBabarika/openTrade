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
    buildCoordMap,
    CURSOR,
    type ActiveTool,
    type CoordMap,
    type ChartPoint,
    type DrawableSurface,
  } from '../lib/drawables';
  import ChartViewport from './ChartViewport.svelte';

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
    provider = 'yfinance' as string,
    interval = '1d' as string,
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
    provider: string;
    interval: string;
    activeTool: ActiveTool;
    api?: ChartApi | null;
  } = $props();

  let containerEl = $state<HTMLDivElement | null>(null);
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

  /**
   * Incremented when pan/zoom/resize (or container size) invalidates chart pixel
   * mapping. Fed into `buildCoordMap(..., version)` → `coordMap.version`.
   * Depend on `coordMap` / `coordMap.version` in overlays for transforms; this
   * counter is the chart shell’s upstream invalidation signal only.
   */
  let coordVersion = $state(0);

  let coordMap = $state<CoordMap | null>(null);

  /** True while the user is dragging out a new drawable (disables chart pan/zoom). */
  let drawablePlacing = $state(false);

  function onDrawablePlacementActiveChange(active: boolean): void {
    drawablePlacing = active;
  }

  let chartDrawables = $state<DrawableSurface | undefined>(undefined);

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

    const needCandle = type === 'candlestick';
    if (needCandle && candleSeries) return;
    if (!needCandle && lineSeries) return;

    if (candleSeries) {
      chart.removeSeries(candleSeries);
      candleSeries = null;
    }
    if (lineSeries) {
      chart.removeSeries(lineSeries);
      lineSeries = null;
    }

    if (needCandle) {
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
    chartDrawables?.handlePointerDown(e);
  }

  function onChartPointerMove(e: PointerEvent) {
    chartDrawables?.handlePointerMove(e);
  }

  function onChartPointerUp(e: PointerEvent) {
    chartDrawables?.handlePointerUp(e);
  }

  function onChartKeyDown(e: KeyboardEvent) {
    chartDrawables?.handleKeyDown(e);
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

  // Suspend chart pan/zoom while the user is placing a drawable (see ChartDrawables).
  $effect(() => {
    const placing = drawablePlacing;
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

<ChartViewport
  bind:containerEl
  bind:chartDrawables
  bind:activeTool
  {coordMap}
  {symbol}
  {candles}
  {provider}
  {interval}
  toChartPoint={toChartPoint}
  onPlacementActiveChange={onDrawablePlacementActiveChange}
  onChartPointerDown={onChartPointerDown}
  onChartPointerMove={onChartPointerMove}
  onChartPointerUp={onChartPointerUp}
  onChartKeyDown={onChartKeyDown}
  showLegend={showLegend}
  legendTitle={legendName}
  legendPrice={legendPrice}
  legendDate={legendDate}
  legendVolume={legendVolume}
  legendTextColour={colours?.textColour}
/>
