<script lang="ts">
  import type { OHLCVCandle } from '../lib/types';
  import {
    CURSOR,
    type ActiveTool,
    type CoordMap,
    type ChartPoint,
    type DrawableSurface,
  } from '../lib/drawables';
  import ChartDrawables from './ChartDrawables.svelte';
  import ChartLegend from './ChartLegend.svelte';

  let {
    containerEl = $bindable<HTMLDivElement | null>(null),
    chartDrawables = $bindable<DrawableSurface | undefined>(undefined),
    activeTool = $bindable(CURSOR as ActiveTool),
    coordMap = null as CoordMap | null,
    symbol = '',
    candles = [] as OHLCVCandle[],
    provider = 'yfinance',
    interval = '1d',
    toChartPoint,
    onPlacementActiveChange,
    onChartPointerDown,
    onChartPointerMove,
    onChartPointerUp,
    onChartKeyDown,
    showLegend = false,
    legendTitle = '',
    legendPrice = '',
    legendDate = '',
    legendVolume = '',
    legendTextColour = undefined as string | undefined,
  }: {
    containerEl?: HTMLDivElement | null;
    chartDrawables?: DrawableSurface | undefined;
    activeTool?: ActiveTool;
    coordMap: CoordMap | null;
    symbol: string;
    candles: OHLCVCandle[];
    provider: string;
    interval: string;
    toChartPoint: (e: PointerEvent) => ChartPoint | null;
    onPlacementActiveChange?: (active: boolean) => void;
    onChartPointerDown: (e: PointerEvent) => void;
    onChartPointerMove: (e: PointerEvent) => void;
    onChartPointerUp: (e: PointerEvent) => void;
    onChartKeyDown: (e: KeyboardEvent) => void;
    showLegend?: boolean;
    legendTitle?: string;
    legendPrice?: string;
    legendDate?: string;
    legendVolume?: string;
    legendTextColour?: string;
  } = $props();
</script>

<!-- Hit target for chart + drawables: lightweight-charts canvas is not focusable; we need tabindex and keyboard handlers here. -->
<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
  class="flex-1 min-h-[400px] relative w-full z-0 overflow-hidden"
  class:cursor-crosshair={activeTool !== CURSOR}
  bind:this={containerEl}
  role="region"
  aria-label="Chart"
  tabindex="0"
  onpointerdown={onChartPointerDown}
  onpointermove={onChartPointerMove}
  onpointerup={onChartPointerUp}
  onpointercancel={onChartPointerUp}
  onkeydown={onChartKeyDown}
>
  <ChartLegend
    show={showLegend}
    title={legendTitle}
    price={legendPrice}
    date={legendDate}
    volume={legendVolume}
    textColour={legendTextColour}
  />

  <ChartDrawables
    bind:this={chartDrawables}
    {activeTool}
    onActiveToolChange={t => (activeTool = t)}
    {coordMap}
    {symbol}
    {candles}
    {provider}
    {interval}
    {toChartPoint}
    containerEl={containerEl}
    {onPlacementActiveChange}
  />
</div>

<style>
  /* lightweight-charts injects canvas elements that need full sizing */
  div :global(canvas) {
    width: 100% !important;
    height: 100% !important;
  }
</style>
