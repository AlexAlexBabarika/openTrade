<script lang="ts">
  import { onMount, onDestroy, untrack } from 'svelte';
  import { ColorType } from 'lightweight-charts';
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
    getCssVarColor,
  } from '../lib/chart';
  import type { OHLCVCandle, IndicatorPoint } from '../lib/types';
  import type { ChartType } from './ChartOptionsMenu.svelte';
  import type { ChartColours } from '../lib/chartColours';
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
    smaLineWidth = 2,
    emaLineWidth = 2,
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
    smaLineWidth?: number;
    emaLineWidth?: number;
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
  let themeObserver: MutationObserver | null = null;

  // Legend state
  let legendName = $state('');
  let legendPrice = $state('');
  let legendDate = $state('');
  let legendVolume = $state('');
  let showLegend = $state(false);

  function formatPrice(price: number): string {
    return (Math.round(price * 100) / 100).toFixed(2);
  }

  function formatDate(time: Time): string {
    let date: Date;
    if (typeof time === 'string') {
      date = new Date(time);
    } else if (typeof time === 'number') {
      date = new Date(time * 1000);
    } else {
      date = new Date(time.year, time.month - 1, time.day);
    }
    const day = date.getDate();
    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    const month = months[date.getMonth()];
    const year = date.getFullYear();
    return `${day} ${month} ${year}`;
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

    // Remove existing price series
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
      const lineColor = colours?.lineColour ?? getCssVarColor('--foreground', '#d1d4dc');
      lineSeries = addLineSeries(chart, lineColor);
    }
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
      volumeSeries.update(
        candleOHLCVtoVolumeData(c, colours?.volumeUp, colours?.volumeDown),
      );
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
      volumeSeries.setData(
        data.map(c =>
          candleOHLCVtoVolumeData(c, colours?.volumeUp, colours?.volumeDown),
        ),
      );
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

    // Watch for theme changes on the html element
    themeObserver = new MutationObserver(() => {
      if (chart) {
        syncChartTheme(chart, candleSeries, areaSeries, lineSeries, colours);
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
          smaSeries = addLineSeries(chart, colours?.smaLine ?? '#2962FF');
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
          emaSeries = addLineSeries(chart, colours?.emaLine ?? '#FF6D00');
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
    if (!chart || !colours) return;
    const c = colours;

    chart.applyOptions({
      layout: {
        background: { type: ColorType.Solid, color: c.chartBackground },
        textColor: c.textColour,
      },
      grid: {
        vertLines: { color: c.gridLines },
        horzLines: { color: c.gridLines },
      },
    });

    if (candleSeries) {
      candleSeries.applyOptions({
        upColor: c.candleUpBody,
        downColor: c.candleDownBody,
        borderUpColor: c.candleUpBody,
        borderDownColor: c.candleDownBody,
        wickUpColor: c.candleUpWick,
        wickDownColor: c.candleDownWick,
      });
    }
    if (lineSeries) lineSeries.applyOptions({ color: c.lineColour });
    if (areaSeries) {
      areaSeries.applyOptions({ topColor: c.areaTop, bottomColor: c.areaBottom });
    }
    if (smaSeries) smaSeries.applyOptions({ color: c.smaLine });
    if (emaSeries) emaSeries.applyOptions({ color: c.emaLine });
  });

  $effect(() => {
    if (!chart || !colours || !volumeSeries) return;
    const up = colours.volumeUp;
    const down = colours.volumeDown;
    untrack(() => {
      if (volumeSeries && candles.length > 0) {
        volumeSeries.setData(
          candles.map(d => candleOHLCVtoVolumeData(d, up, down)),
        );
      }
    });
  });
</script>

<div class="flex-1 flex flex-col relative z-0 w-full overflow-hidden">
  <div class="flex-1 min-h-[400px] relative w-full" bind:this={containerEl}>
    {#if showLegend}
      <div
        class="absolute left-4 top-4 z-10 text-sm font-light pointer-events-none font-sans leading-[18px]"
        style:color={colours?.textColour}
      >
        <div class="text-2xl my-1 font-medium">{legendName}</div>
        <div class="text-[22px] my-1 font-semibold">{legendPrice}</div>
        <div style:opacity="0.7">{legendDate}</div>
        <div style:opacity="0.7">Volume: {legendVolume}</div>
      </div>
    {/if}
  </div>
</div>

<style>
  /* lightweight-charts injects canvas elements that need full sizing */
  div :global(canvas) {
    width: 100% !important;
    height: 100% !important;
  }
</style>
