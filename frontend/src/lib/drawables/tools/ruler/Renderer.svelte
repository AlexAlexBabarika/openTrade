<!-- frontend/src/lib/drawables/tools/ruler/Renderer.svelte -->
<script lang="ts">
  import type {
    ScreenPoint,
    RendererProps,
  } from '../../types';
  import type { RulerStats } from './compute';
  import {
    formatPct,
    formatPriceDelta,
    formatVolume,
  } from './compute';
  import DrawableSvgHitRect from '../../ui/DrawableSvgHitRect.svelte';

  interface RulerGeo {
    startTime: number;
    endTime: number;
    startPrice: number;
    endPrice: number;
  }
  interface RulerParams {
    [k: string]: never;
  }
  interface RulerStyle {
    upColor: string;
    downColor: string;
    showStats: boolean;
  }

  let {
    drawable,
    data,
    selected,
    coordMap,
    onRequestSelect,
    onAnchorPoint,
  }: RendererProps<RulerGeo, RulerParams, RulerStyle, RulerStats> = $props();

  let box = $derived.by(() => {
    coordMap.version; // re-run on coord invalidation
    const g = drawable.geometry;
    const x1 = coordMap.timeToX(g.startTime);
    const x2 = coordMap.timeToX(g.endTime);
    const y1 = coordMap.priceToY(g.startPrice);
    const y2 = coordMap.priceToY(g.endPrice);
    if (x1 == null || x2 == null || y1 == null || y2 == null) return null;
    return {
      left: Math.min(x1, x2),
      top: Math.min(y1, y2),
      width: Math.abs(x2 - x1),
      height: Math.abs(y2 - y1),
      x1,
      y1,
      x2,
      y2,
    };
  });

  let stats = $derived(data ?? null);

  $effect(() => {
    if (!box) {
      onAnchorPoint(null);
      return;
    }
    const pt: ScreenPoint = { x: box.left + box.width, y: box.top };
    onAnchorPoint(pt);
  });

  function onHitPointerDown(e: PointerEvent) {
    e.stopPropagation();
    onRequestSelect();
  }
</script>

{#if box && stats}
  {@const up = stats.isUp}
  {@const fill = up ? drawable.style.upColor : drawable.style.downColor}
  {@const stroke = fill}
  <g>
    <rect
      x={box.left}
      y={box.top}
      width={box.width}
      height={box.height}
      fill={fill}
      fill-opacity="0.18"
      stroke={stroke}
      stroke-width={selected ? 2 : 1}
    />
    <line
      x1={box.x1}
      y1={box.y1}
      x2={box.x2}
      y2={box.y1}
      stroke={stroke}
      stroke-width="1.5"
    />
    <line
      x1={box.x1}
      y1={box.y1}
      x2={box.x1}
      y2={box.y2}
      stroke={stroke}
      stroke-width="1.5"
    />
    <DrawableSvgHitRect
      x={box.left - 4}
      y={box.top - 4}
      width={box.width + 8}
      height={box.height + 8}
      drawableId={drawable.id}
      ariaLabel="Ruler drawable"
      onPointerDown={onHitPointerDown}
      mode="stroke"
    />

    {#if drawable.style.showStats}
      <foreignObject
        x={box.x2 - 60}
        y={up ? box.y1 + 8 : box.y1 - 56}
        width="120"
        height="48"
        pointer-events="none"
      >
        <div
          class="rounded-md px-2 py-1 text-[10px] font-mono text-white shadow-lg whitespace-nowrap text-center leading-tight"
          style:background-color={fill}
        >
          <div>
            {formatPriceDelta(stats.priceDelta)} ({formatPct(stats.pctDelta)})
          </div>
          <div style:opacity="0.9">
            {stats.barCount} bars{stats.spanLabel ? `, ${stats.spanLabel}` : ''}
          </div>
          <div style:opacity="0.9">Vol {formatVolume(stats.volumeSum)}</div>
        </div>
      </foreignObject>
    {/if}
  </g>
{/if}
