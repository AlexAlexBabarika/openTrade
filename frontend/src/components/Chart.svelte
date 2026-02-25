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
  } from '../lib/chart';
  import type { OHLCVCandle } from '../lib/types';

  let {
    candles = [] as OHLCVCandle[],
    symbol = '',
  }: { candles: OHLCVCandle[]; symbol: string } = $props();

  let containerEl: HTMLDivElement;
  let chart: IChartApi | null = null;
  let candleSeries: ISeriesApi<'Candlestick'> | null = null;
  let areaSeries: ISeriesApi<'Area'> | null = null;
  let volumeSeries: ISeriesApi<'Histogram'> | null = null;

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
    if (!candleSeries) return;

    const validCrosshairPoint = !(
      param === undefined ||
      param.time === undefined ||
      param.point === undefined ||
      param.point.x < 0 ||
      param.point.y < 0
    );

    const bar = validCrosshairPoint
      ? param.seriesData.get(candleSeries)
      : candleSeries.dataByIndex(Number.MAX_SAFE_INTEGER, -1);

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
    areaSeries = addAreaSeries(chart);
    candleSeries = addCandlestickSeries(chart);

    chart.subscribeCrosshairMove(updateLegend);
    updateLegend(undefined);
  }

  function updateChartData(data: OHLCVCandle[]): void {
    if (!chart || !candleSeries || !areaSeries || !volumeSeries) return;

    if (data.length >= 20) {
      areaSeries.setData(data.map(candleOHLCVtoAreaData));
    } else {
      areaSeries.setData([]);
    }

    candleSeries.setData(data.map(candleOHLCVtoCandlestickData));
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
  });

  onDestroy(() => {
    window.removeEventListener('resize', handleResize);
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
</script>

<div class="flex-1 min-h-[400px] relative" bind:this={containerEl}>
  {#if showLegend}
    <div
      class="absolute left-3 top-3 z-10 text-sm font-light text-white pointer-events-none font-sans leading-[18px]"
    >
      <div class="text-2xl my-1">{legendName}</div>
      <div class="text-[22px] my-1">{legendPrice}</div>
      <div>{legendDate}</div>
      <div>Volume: {legendVolume}</div>
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
