<script lang="ts">
  import type { RendererProps, ScreenPoint } from '../../../types';
  import type { AvpGeo, AvpParams, AvpStyle } from './compute';
  import type {
    VolumeProfileBin,
    VolumeProfileResponse,
  } from '../shared/types';
  import DrawableSvgHitRect from '../../../ui/DrawableSvgHitRect.svelte';
  import { measureDrawablesSync } from '../../../../dev/drawablesProfile';

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

  let boxLeft = $derived.by(() => {
    coordMap.version;
    if (drawable.style.placement === 'right') {
      const pw = coordMap.plotWidth;
      return pw > boxWidth ? pw - boxWidth : 0;
    }
    return 0;
  });

  let plotHeight = $derived(coordMap.plotHeight);

  let maxBinVol = $derived.by(() => {
    if (!data?.bins.length) return 0;
    let m = 0;
    for (const b of data.bins) {
      const v = b.upVol + b.downVol;
      if (v > m) m = v;
    }
    return m;
  });

  /** Precomputed rows so bin geometry is measurable (`drawables:avp-bin-layout`) and matches the prior `{#each}` math. */
  let binLayoutRows = $derived.by(() => {
    coordMap.version;
    if (
      !data?.bins.length ||
      !drawable.style.showProfile ||
      maxBinVol <= 0
    ) {
      return [] as Array<{
        bin: VolumeProfileBin;
        top: number;
        h: number;
        upW: number;
        downW: number;
        fullW: number;
      }>;
    }
    const d = data;
    const rowSize = d.rowSize;
    return measureDrawablesSync('drawables:avp-bin-layout', () => {
      const rows: Array<{
        bin: VolumeProfileBin;
        top: number;
        h: number;
        upW: number;
        downW: number;
        fullW: number;
      }> = [];
      for (const bin of d.bins) {
        const y = coordMap.priceToY(bin.price);
        const yNext = coordMap.priceToY(bin.price + rowSize);
        if (y == null || yNext == null) continue;
        const h = Math.max(1, Math.abs(y - yNext));
        const top = Math.min(y, yNext);
        const total = bin.upVol + bin.downVol;
        const fullW = (total / maxBinVol) * boxWidth;
        const upW = total > 0 ? fullW * (bin.upVol / total) : 0;
        const downW = fullW - upW;
        rows.push({ bin, top, h, upW, downW, fullW });
      }
      return rows;
    });
  });

  $effect(() => {
    if (anchorX == null) {
      onAnchorPoint(null);
      return;
    }
    const anchorY = coordMap.priceToY(data?.poc ?? 0) ?? 0;
    onAnchorPoint({ x: anchorX, y: anchorY } satisfies ScreenPoint);
  });

  function onHitPointerDown(e: PointerEvent) {
    e.stopPropagation();
    onRequestSelect();
  }
</script>

{#if anchorX != null}
  {@const placement = drawable.style.placement}
  <g>
    <line
      x1={anchorX}
      y1={0}
      x2={anchorX}
      y2={plotHeight}
      stroke={drawable.style.upColor}
      stroke-width={selected ? 2 : 1}
      stroke-dasharray="2 4"
      opacity="0.8"
    />

    {#if drawable.style.showProfile && data && maxBinVol > 0}
      {#each binLayoutRows as row (row.bin.price)}
        {#if placement === 'right'}
          <rect
            x={boxLeft + boxWidth - row.upW}
            y={row.top}
            width={row.upW}
            height={row.h}
            fill={drawable.style.upColor}
            fill-opacity="0.6"
          />
          <rect
            x={boxLeft + boxWidth - row.fullW}
            y={row.top}
            width={row.downW}
            height={row.h}
            fill={drawable.style.downColor}
            fill-opacity="0.6"
          />
        {:else}
          <rect
            x={boxLeft}
            y={row.top}
            width={row.upW}
            height={row.h}
            fill={drawable.style.upColor}
            fill-opacity="0.6"
          />
          <rect
            x={boxLeft + row.upW}
            y={row.top}
            width={row.downW}
            height={row.h}
            fill={drawable.style.downColor}
            fill-opacity="0.6"
          />
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

    <DrawableSvgHitRect
      x={anchorX - 5}
      y={0}
      width={10}
      height={plotHeight}
      drawableId={drawable.id}
      ariaLabel="Anchored Volume Profile"
      onPointerDown={onHitPointerDown}
    />
  </g>
{/if}
