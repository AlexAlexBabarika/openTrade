<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import type {
    IChartApi,
    ISeriesApi,
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
  import type { OHLCVCandle } from '../lib/types';
  import type { ChartType } from './ChartOptionsMenu.svelte';

  let {
    candles = [] as OHLCVCandle[],
    symbol = '',
    chartType = 'candlestick' as ChartType,
    showArea = true,
  }: {
    candles: OHLCVCandle[];
    symbol: string;
    chartType?: ChartType;
    showArea?: boolean;
  } = $props();

  let containerEl: HTMLDivElement;
  let chart: IChartApi | null = null;
  let candleSeries: ISeriesApi<'Candlestick'> | null = null;
  let lineSeries: ISeriesApi<'Line'> | null = null;
  let areaSeries: ISeriesApi<'Area'> | null = null;
  let volumeSeries: ISeriesApi<'Histogram'> | null = null;
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

    chart = createChartContainer(containerEl);
    volumeSeries = addVolumeSeries(chart);
    applyArea(showArea);
    applySeries(chartType);

    chart.subscribeCrosshairMove(updateLegend);
    updateLegend(undefined);
  }

  function applyArea(enabled: boolean): void {
    if (!chart) return;

    if (enabled && !areaSeries) {
      areaSeries = addAreaSeries(chart);
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
      candleSeries = addCandlestickSeries(chart);
    } else {
      const lineColor = getCssVarColor('--foreground', '#d1d4dc');
      lineSeries = addLineSeries(chart, lineColor);
    }
  }

  function updateChartData(data: OHLCVCandle[]): void {
    if (!chart || !volumeSeries) return;

    if (areaSeries) {
      if (data.length >= 20) {
        areaSeries.setData(data.map(candleOHLCVtoAreaData));
      } else {
        areaSeries.setData([]);
      }
    }

    if (candleSeries) {
      candleSeries.setData(data.map(candleOHLCVtoCandlestickData));
    }
    if (lineSeries) {
      lineSeries.setData(data.map(candleOHLCVtoAreaData));
    }

    volumeSeries.setData(data.map(candleOHLCVtoVolumeData));
    chart.timeScale().fitContent();
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
    if (candles.length > 0) {
      updateChartData(candles);
    }
    window.addEventListener('resize', handleResize);

    // Watch for theme changes on the html element
    themeObserver = new MutationObserver(() => {
      if (chart) {
        syncChartTheme(chart, candleSeries, areaSeries, lineSeries);
      }
    });

    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    });
  });

  onDestroy(() => {
    window.removeEventListener('resize', handleResize);
    if (themeObserver) {
      themeObserver.disconnect();
    }
    if (chart) {
      chart.remove();
      chart = null;
    }
  });

  $effect(() => {
    if (chart && candles) {
      updateChartData(candles);
    }
  });

  $effect(() => {
    if (!chart) return;
    const type = chartType;
    applySeries(type);
    if (candles.length > 0) {
      updateChartData(candles);
    }
  });

  $effect(() => {
    if (!chart) return;
    const enabled = showArea;
    applyArea(enabled);
    if (candles.length > 0) {
      updateChartData(candles);
    }
  });
</script>

<div class="flex-1 flex flex-col relative z-0 w-full overflow-hidden">
  <div class="flex-1 min-h-[400px] relative w-full" bind:this={containerEl}>
    {#if showLegend}
      <div
        class="absolute left-4 top-4 z-10 text-sm font-light text-foreground pointer-events-none font-sans leading-[18px]"
      >
        <div class="text-2xl my-1 font-medium">{legendName}</div>
        <div class="text-[22px] my-1 font-semibold">{legendPrice}</div>
        <div class="text-muted-foreground">{legendDate}</div>
        <div class="text-muted-foreground">Volume: {legendVolume}</div>
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
