<script lang="ts">
  import type { RendererProps, ScreenPoint } from '../../../types';
  import type { AvpGeo, AvpParams, AvpStyle } from './compute';
  import type { VolumeProfileResponse } from '../shared/types';

  let {
    drawable,
    data,
    selected,
    coordMap,
    onRequestSelect,
    onAnchorPoint,
  }: RendererProps<AvpGeo, AvpParams, AvpStyle, VolumeProfileResponse> =
    $props();

  let anchorX = $derived.by(() => {
    coordMap.version;
    return coordMap.timeToX(drawable.geometry.time);
  });

  const MAX_WIDTH_PX = 320;

  let boxWidth = $derived.by(() => {
    if (anchorX == null) return 0;
    const pct = Math.min(100, Math.max(0, drawable.style.widthPct)) / 100;
    return Math.round(MAX_WIDTH_PX * pct);
  });

  let maxBinVol = $derived(
    data ? Math.max(0, ...data.bins.map(b => b.upVol + b.downVol)) : 0,
  );

  $effect(() => {
    if (anchorX == null) {
      onAnchorPoint(null);
      return;
    }
    const anchorY = coordMap.priceToY(data?.poc ?? 0) ?? 0;
    const pt: ScreenPoint = { x: anchorX + (drawable.style.placement === 'right' ? boxWidth : -boxWidth), y: anchorY };
    onAnchorPoint(pt);
  });

  function onHitPointerDown(e: PointerEvent) {
    e.stopPropagation();
    onRequestSelect();
  }
</script>

{#if anchorX != null}
  {@const placement = drawable.style.placement}
  {@const boxLeft = placement === 'right' ? anchorX : anchorX - boxWidth}
  <g>
    <line
      x1={anchorX}
      y1={0}
      x2={anchorX}
      y2={10000}
      stroke={drawable.style.upColor}
      stroke-width={selected ? 2 : 1}
      stroke-dasharray="2 4"
      opacity="0.8"
    />

    {#if drawable.style.showProfile && data && maxBinVol > 0}
      {#each data.bins as bin (bin.price)}
        {@const y = coordMap.priceToY(bin.price)}
        {@const yNext = coordMap.priceToY(bin.price + data.rowSize)}
        {#if y != null && yNext != null}
          {@const h = Math.max(1, Math.abs(y - yNext))}
          {@const top = Math.min(y, yNext)}
          {@const total = bin.upVol + bin.downVol}
          {@const fullW = (total / maxBinVol) * boxWidth}
          {@const upW = total > 0 ? fullW * (bin.upVol / total) : 0}
          {@const downW = fullW - upW}
          {#if placement === 'right'}
            <rect
              x={boxLeft}
              y={top}
              width={upW}
              height={h}
              fill={drawable.style.upColor}
              fill-opacity="0.6"
            />
            <rect
              x={boxLeft + upW}
              y={top}
              width={downW}
              height={h}
              fill={drawable.style.downColor}
              fill-opacity="0.6"
            />
          {:else}
            <rect
              x={boxLeft + boxWidth - upW}
              y={top}
              width={upW}
              height={h}
              fill={drawable.style.upColor}
              fill-opacity="0.6"
            />
            <rect
              x={boxLeft + boxWidth - fullW}
              y={top}
              width={downW}
              height={h}
              fill={drawable.style.downColor}
              fill-opacity="0.6"
            />
          {/if}
        {/if}
      {/each}
    {/if}

    {#if data}
      {@const pocY = coordMap.priceToY(data.poc)}
      {@const vahY = coordMap.priceToY(data.vah)}
      {@const valY = coordMap.priceToY(data.val)}
      {#if drawable.style.showPOC && pocY != null}
        <line
          x1={boxLeft}
          y1={pocY}
          x2={boxLeft + boxWidth}
          y2={pocY}
          stroke={drawable.style.pocColor}
          stroke-width="1.5"
        />
      {/if}
      {#if drawable.style.showVAH && vahY != null}
        <line
          x1={boxLeft}
          y1={vahY}
          x2={boxLeft + boxWidth}
          y2={vahY}
          stroke={drawable.style.vahColor}
          stroke-width="1"
          stroke-dasharray="4 3"
        />
      {/if}
      {#if drawable.style.showVAL && valY != null}
        <line
          x1={boxLeft}
          y1={valY}
          x2={boxLeft + boxWidth}
          y2={valY}
          stroke={drawable.style.valColor}
          stroke-width="1"
          stroke-dasharray="4 3"
        />
      {/if}
    {/if}

    <rect
      x={anchorX - 5}
      y={0}
      width={10}
      height={10000}
      fill="transparent"
      stroke="transparent"
      pointer-events="auto"
      data-drawable-id={drawable.id}
      role="button"
      tabindex="-1"
      aria-label="Anchored Volume Profile"
      onpointerdown={onHitPointerDown}
      style:cursor="pointer"
    />
  </g>
{/if}
