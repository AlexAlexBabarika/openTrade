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
    invalidateCssVarCache,
  } from '../lib/chart';
  import type {
    OHLCVCandle,
    IndicatorPoint,
    BollingerBandsPoint,
  } from '../lib/types';
  import type { ChartColours, ChartType } from '../lib/chartColours';
  import { linePoint } from '../lib/chart';

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
  let themeObserver: MutationObserver | null = null;

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
    }
  }

  onMount(() => {
    initChart();
    api = { appendCandle };
    window.addEventListener('resize', handleResize);

    themeObserver = new MutationObserver(() => {
      if (chart) {
        invalidateCssVarCache();
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
      }
    });

    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    });
  });

  onDestroy(() => {
    api = null;
    window.removeEventListener('resize', handleResize);
    if (themeObserver) {
      themeObserver.disconnect();
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
  bind:this={containerEl}
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
</div>

<style>
  /* lightweight-charts injects canvas elements that need full sizing */
  div :global(canvas) {
    width: 100% !important;
    height: 100% !important;
  }
</style>
