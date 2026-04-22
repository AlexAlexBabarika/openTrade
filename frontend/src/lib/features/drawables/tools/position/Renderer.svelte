<script lang="ts">
  import type { RendererProps } from '../../types';
  import type { PositionGeo, PositionParams, PositionStyle } from './compute';
  import type { PositionMetricsResponse } from './types';
  import DrawableSvgHitRect from '../../ui/DrawableSvgHitRect.svelte';
  import { POSITION_LONG_TYPE } from './constants';

  const HANDLE = 9;
  const MIN_TIME_SPAN = 1;

  let {
    drawable,
    data,
    selected,
    coordMap,
    onGeometryChange,
    onRequestSelect,
    onAnchorPoint,
    toChartPoint,
  }: RendererProps<
    PositionGeo,
    PositionParams,
    PositionStyle,
    PositionMetricsResponse
  > = $props();

  let isLong = $derived(drawable.type === POSITION_LONG_TYPE);

  let layout = $derived.by(() => {
    coordMap.version;
    const g = drawable.geometry;
    const xL = coordMap.timeToX(g.startTime);
    const xR = coordMap.timeToX(g.endTime);
    const yE = coordMap.priceToY(g.entryPrice);
    const yS = coordMap.priceToY(g.stopPrice);
    const yT = coordMap.priceToY(g.targetPrice);
    if (xL == null || xR == null || yE == null || yS == null || yT == null) {
      return null;
    }
    const xLeft = Math.min(xL, xR);
    const xRight = Math.max(xL, xR);
    const pad = 4;
    const yRiskTop = Math.min(yE, yS);
    const yRiskBot = Math.max(yE, yS);
    const yRewTop = Math.min(yE, yT);
    const yRewBot = Math.max(yE, yT);
    return {
      xLeft,
      xRight,
      yE,
      yS,
      yT,
      yRiskTop,
      yRiskBot,
      yRewTop,
      yRewBot,
      pad,
      width: Math.max(1, xRight - xLeft),
    };
  });

  let metrics = $derived(data ?? null);

  let dragKind = $state<null | 'target' | 'stop' | 't0' | 't1'>(null);

  $effect(() => {
    if (!layout) {
      onAnchorPoint(null);
      return;
    }
    onAnchorPoint({ x: layout.xRight + 8, y: layout.yE });
  });

  function onHitPointerDown(e: PointerEvent) {
    e.stopPropagation();
    onRequestSelect();
  }

  function fmt(n: number | null | undefined, d = 2): string {
    if (n == null || !Number.isFinite(n)) return '—';
    return n.toFixed(d);
  }

  function pctFromEntry(price: number, entry: number): number {
    if (!Number.isFinite(price) || !Number.isFinite(entry) || entry === 0) {
      return 0;
    }
    return ((price - entry) / entry) * 100;
  }

  function patchGeo(patch: Partial<PositionGeo>): void {
    onGeometryChange({ ...drawable.geometry, ...patch });
  }

  function handleDown(
    kind: 'target' | 'stop' | 't0' | 't1',
    e: PointerEvent,
  ): void {
    if (!toChartPoint) return;
    e.stopPropagation();
    e.preventDefault();
    onRequestSelect();
    dragKind = kind;
    (e.currentTarget as Element).setPointerCapture(e.pointerId);
  }

  function handleMove(e: PointerEvent): void {
    if (!dragKind || !toChartPoint) return;
    const pt = toChartPoint(e);
    if (!pt) return;
    const g = drawable.geometry;
    if (dragKind === 'target') {
      patchGeo({ targetPrice: pt.price });
    } else if (dragKind === 'stop') {
      patchGeo({ stopPrice: pt.price });
    } else if (dragKind === 't0') {
      const next = Math.min(pt.time, g.endTime - MIN_TIME_SPAN);
      patchGeo({ startTime: next });
    } else if (dragKind === 't1') {
      const next = Math.max(pt.time, g.startTime + MIN_TIME_SPAN);
      patchGeo({ endTime: next });
    }
  }

  function handleUp(e: PointerEvent): void {
    if (dragKind) {
      try {
        (e.currentTarget as Element).releasePointerCapture(e.pointerId);
      } catch {
        /* already released */
      }
    }
    dragKind = null;
  }

  function handlePos(
    kind: 'target' | 'stop' | 't0' | 't1',
    L: NonNullable<typeof layout>,
  ): { x: number; y: number } {
    const g = drawable.geometry;
    if (kind === 'target') {
      return { x: L.xLeft - HANDLE / 2, y: L.yT - HANDLE / 2 };
    }
    if (kind === 'stop') {
      return { x: L.xLeft - HANDLE / 2, y: L.yS - HANDLE / 2 };
    }
    if (kind === 't0') {
      const x = coordMap.timeToX(g.startTime);
      return {
        x: (x ?? L.xLeft) - HANDLE / 2,
        y: L.yE - HANDLE / 2,
      };
    }
    const x = coordMap.timeToX(g.endTime);
    return {
      x: (x ?? L.xRight) - HANDLE / 2,
      y: L.yE - HANDLE / 2,
    };
  }
</script>

{#if layout}
  {@const L = layout}
  {@const strokeW = selected ? 2 : 1}
  {@const g = drawable.geometry}
  {@const entry = g.entryPrice}
  {@const targetPct = Math.abs(pctFromEntry(g.targetPrice, entry))}
  {@const stopPct = Math.abs(pctFromEntry(g.stopPrice, entry))}
  {@const targetDist = Math.abs(g.targetPrice - entry)}
  {@const stopDist = Math.abs(g.stopPrice - entry)}
  <g>
    <DrawableSvgHitRect
      x={L.xLeft - L.pad}
      y={Math.min(L.yRiskTop, L.yRewTop) - L.pad}
      width={L.width + L.pad * 2}
      height={Math.max(L.yRiskBot, L.yRewBot) -
        Math.min(L.yRiskTop, L.yRewTop) +
        L.pad * 2}
      drawableId={drawable.id}
      ariaLabel="{isLong ? 'Long' : 'Short'} position"
      onPointerDown={onHitPointerDown}
      mode="stroke"
    />

    {#if drawable.style.showRiskZone}
      <rect
        x={L.xLeft}
        y={L.yRiskTop}
        width={L.width}
        height={Math.max(1, L.yRiskBot - L.yRiskTop)}
        fill={drawable.style.riskFill}
        fill-opacity="0.18"
        pointer-events="none"
      />
    {/if}
    {#if drawable.style.showRewardZone}
      <rect
        x={L.xLeft}
        y={L.yRewTop}
        width={L.width}
        height={Math.max(1, L.yRewBot - L.yRewTop)}
        fill={drawable.style.rewardFill}
        fill-opacity="0.18"
        pointer-events="none"
      />
    {/if}

    <line
      x1={L.xLeft}
      x2={L.xRight}
      y1={L.yE}
      y2={L.yE}
      stroke={drawable.style.entryColor}
      stroke-width={strokeW}
      stroke-dasharray="4 3"
      pointer-events="none"
    />
    <line
      x1={L.xLeft}
      x2={L.xRight}
      y1={L.yS}
      y2={L.yS}
      stroke={drawable.style.stopColor}
      stroke-width={1}
      pointer-events="none"
    />
    <line
      x1={L.xLeft}
      x2={L.xRight}
      y1={L.yT}
      y2={L.yT}
      stroke={drawable.style.targetColor}
      stroke-width={1}
      pointer-events="none"
    />

    {#if drawable.style.showMetrics && metrics}
      <foreignObject
        x={L.xLeft + L.width / 2 - 70}
        y={L.yRewTop - 42}
        width="140"
        height="36"
        pointer-events="none"
      >
        <div
          class="rounded px-2 py-1 text-[10px] font-mono text-white shadow-md text-center"
          style:background-color="rgb(38, 166, 154)"
        >
          Target: {fmt(targetDist)} ({fmt(targetPct, 3)}%){#if metrics.profitAtTarget != null},
            Amt: {fmt(metrics.profitAtTarget)}{/if}
        </div>
      </foreignObject>

      <foreignObject
        x={L.xLeft + L.width / 2 - 72}
        y={L.yE - 36}
        width="144"
        height="72"
        pointer-events="none"
      >
        <div
          class="rounded border-2 border-white px-2 py-1.5 text-[10px] font-mono text-white shadow-md leading-tight text-center"
          style:background-color="rgb(38, 166, 154)"
        >
          {#if metrics.openPnl != null && Number.isFinite(metrics.openPnl)}
            <div>Open P&amp;L: {fmt(metrics.openPnl)}</div>
          {/if}
          {#if metrics.quantity != null}
            <div>Qty: {fmt(metrics.quantity, 4)}</div>
          {/if}
          <div>Risk/reward: {fmt(metrics.riskRewardRatio, 2)}</div>
        </div>
      </foreignObject>

      <foreignObject
        x={L.xLeft + L.width / 2 - 70}
        y={L.yRiskBot + 6}
        width="140"
        height="36"
        pointer-events="none"
      >
        <div
          class="rounded px-2 py-1 text-[10px] font-mono text-white shadow-md text-center"
          style:background-color="rgb(239, 83, 80)"
        >
          Stop: {fmt(stopDist)} ({fmt(stopPct, 3)}%){#if metrics.lossAtStop != null},
            Amt: {fmt(metrics.lossAtStop)}{/if}
        </div>
      </foreignObject>
    {/if}

    {#if selected && toChartPoint}
      {@const pT = handlePos('target', L)}
      {@const pS = handlePos('stop', L)}
      {@const pL = handlePos('t0', L)}
      {@const pR = handlePos('t1', L)}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <rect
        x={pT.x}
        y={pT.y}
        width={HANDLE}
        height={HANDLE}
        rx="2"
        fill="white"
        stroke="rgb(59, 130, 246)"
        stroke-width="1.5"
        role="button"
        tabindex="-1"
        aria-label="Drag target price"
        class="cursor-ns-resize"
        style:pointer-events="auto"
        onpointerdown={e => handleDown('target', e)}
        onpointermove={handleMove}
        onpointerup={handleUp}
        onpointercancel={handleUp}
      />
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <rect
        x={pS.x}
        y={pS.y}
        width={HANDLE}
        height={HANDLE}
        rx="2"
        fill="white"
        stroke="rgb(59, 130, 246)"
        stroke-width="1.5"
        role="button"
        tabindex="-1"
        aria-label="Drag stop price"
        class="cursor-ns-resize"
        style:pointer-events="auto"
        onpointerdown={e => handleDown('stop', e)}
        onpointermove={handleMove}
        onpointerup={handleUp}
        onpointercancel={handleUp}
      />
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <rect
        x={pL.x}
        y={pL.y}
        width={HANDLE}
        height={HANDLE}
        rx="2"
        fill="white"
        stroke="rgb(59, 130, 246)"
        stroke-width="1.5"
        role="button"
        tabindex="-1"
        aria-label="Drag band start time"
        class="cursor-ew-resize"
        style:pointer-events="auto"
        onpointerdown={e => handleDown('t0', e)}
        onpointermove={handleMove}
        onpointerup={handleUp}
        onpointercancel={handleUp}
      />
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <rect
        x={pR.x}
        y={pR.y}
        width={HANDLE}
        height={HANDLE}
        rx="2"
        fill="white"
        stroke="rgb(59, 130, 246)"
        stroke-width="1.5"
        role="button"
        tabindex="-1"
        aria-label="Drag band end time"
        class="cursor-ew-resize"
        style:pointer-events="auto"
        onpointerdown={e => handleDown('t1', e)}
        onpointermove={handleMove}
        onpointerup={handleUp}
        onpointercancel={handleUp}
      />
    {/if}
  </g>
{/if}
