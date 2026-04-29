<script lang="ts">
  import { onDestroy, untrack } from 'svelte';
  import {
    LineSeries,
    LineStyle,
    createSeriesMarkers,
    type IChartApi,
    type ISeriesApi,
    type ISeriesMarkersPluginApi,
    type LineWidth,
    type SeriesMarker,
    type SeriesMarkerBarPosition,
    type SeriesMarkerShape,
    type Time,
    type UTCTimestamp,
  } from 'lightweight-charts';
  import type { ScriptOutput } from '$lib/features/indicators/scripts';

  let {
    chartFn,
    priceSeriesFn,
    outputs = [] as ScriptOutput[],
  }: {
    chartFn: () => IChartApi | null;
    priceSeriesFn: () => ISeriesApi<'Candlestick' | 'Line'> | null;
    outputs?: ScriptOutput[];
  } = $props();

  // Per-key map of overlay line series we manage. Keyed by output index +
  // title so re-runs with the same shape diff cleanly without rebuilding.
  const overlaySeries = new Map<string, ISeriesApi<'Line'>>();
  let markersPlugin: ISeriesMarkersPluginApi<Time> | null = null;
  let markersAttachedTo: ISeriesApi<'Candlestick' | 'Line'> | null = null;

  const DEFAULT_OVERLAY_COLOUR = '#3b82f6';
  const DEFAULT_MARKER_COLOUR = '#eab308';

  function toLineStyle(name: string | null | undefined): LineStyle {
    switch ((name ?? '').toLowerCase()) {
      case 'dashed':
        return LineStyle.Dashed;
      case 'dotted':
        return LineStyle.Dotted;
      case 'large_dashed':
      case 'largedashed':
        return LineStyle.LargeDashed;
      case 'sparse_dotted':
      case 'sparsedotted':
        return LineStyle.SparseDotted;
      default:
        return LineStyle.Solid;
    }
  }

  function toMarkerShape(name: string | null | undefined): SeriesMarkerShape {
    switch ((name ?? '').toLowerCase()) {
      case 'square':
        return 'square';
      case 'arrowup':
      case 'arrow_up':
        return 'arrowUp';
      case 'arrowdown':
      case 'arrow_down':
        return 'arrowDown';
      default:
        return 'circle';
    }
  }

  function toMarkerPosition(
    name: string | null | undefined,
  ): SeriesMarkerBarPosition {
    switch ((name ?? '').toLowerCase()) {
      case 'belowbar':
      case 'below_bar':
        return 'belowBar';
      case 'inbar':
      case 'in_bar':
        return 'inBar';
      default:
        return 'aboveBar';
    }
  }

  function applyOverlay(
    chart: IChartApi,
    key: string,
    output: Extract<ScriptOutput, { type: 'overlay' }>,
  ): void {
    let series = overlaySeries.get(key);
    if (!series) {
      series = chart.addSeries(LineSeries, {
        color: output.color ?? DEFAULT_OVERLAY_COLOUR,
        lineWidth: (output.line_width ?? 2) as LineWidth,
        lineStyle: toLineStyle(output.line_style),
        priceLineVisible: false,
        lastValueVisible: false,
        title: output.title,
      });
      overlaySeries.set(key, series);
    } else {
      series.applyOptions({
        color: output.color ?? DEFAULT_OVERLAY_COLOUR,
        lineWidth: (output.line_width ?? 2) as LineWidth,
        lineStyle: toLineStyle(output.line_style),
        title: output.title,
      });
    }
    series.setData(
      output.data.map(p => ({
        time: p.time as UTCTimestamp,
        value: p.value,
      })),
    );
  }

  function buildMarkers(
    list: Extract<ScriptOutput, { type: 'markers' }>[],
  ): SeriesMarker<Time>[] {
    const merged: SeriesMarker<Time>[] = [];
    for (const m of list) {
      const shape = toMarkerShape(m.shape);
      const position = toMarkerPosition(m.position);
      const color = m.color ?? DEFAULT_MARKER_COLOUR;
      const text = m.text ?? undefined;
      for (const pt of m.data) {
        merged.push({
          time: pt.time as UTCTimestamp,
          shape,
          position,
          color,
          text,
        });
      }
    }
    // LWC requires markers sorted ascending by time.
    merged.sort((a, b) => Number(a.time) - Number(b.time));
    return merged;
  }

  function removeMarkers(): void {
    if (markersPlugin) {
      try {
        markersPlugin.detach();
      } catch {
        /* series already removed */
      }
      markersPlugin = null;
      markersAttachedTo = null;
    }
  }

  function applyMarkers(
    priceSeries: ISeriesApi<'Candlestick' | 'Line'>,
    list: Extract<ScriptOutput, { type: 'markers' }>[],
  ): void {
    if (list.length === 0) {
      if (markersPlugin) markersPlugin.setMarkers([]);
      return;
    }
    const data = buildMarkers(list);
    if (!markersPlugin || markersAttachedTo !== priceSeries) {
      removeMarkers();
      markersPlugin = createSeriesMarkers(priceSeries, data);
      markersAttachedTo = priceSeries;
    } else {
      markersPlugin.setMarkers(data);
    }
  }

  function removeAllOverlays(chart: IChartApi | null): void {
    if (!chart) {
      overlaySeries.clear();
      return;
    }
    for (const series of overlaySeries.values()) {
      try {
        chart.removeSeries(series);
      } catch {
        /* chart already disposed */
      }
    }
    overlaySeries.clear();
  }

  $effect(() => {
    const next = outputs;
    untrack(() => {
      const chart = chartFn();
      const priceSeries = priceSeriesFn();
      if (!chart) return;

      const keepKeys = new Set<string>();
      const markerOutputs: Extract<ScriptOutput, { type: 'markers' }>[] = [];

      for (let i = 0; i < next.length; i += 1) {
        const out = next[i];
        if (out.type === 'overlay') {
          const key = `${i}:${out.title}`;
          keepKeys.add(key);
          applyOverlay(chart, key, out);
        } else if (out.type === 'markers') {
          markerOutputs.push(out);
        }
        // Phase 4 ignores: pane, histogram, table, text.
      }

      for (const [key, series] of overlaySeries) {
        if (keepKeys.has(key)) continue;
        try {
          chart.removeSeries(series);
        } catch {
          /* already removed */
        }
        overlaySeries.delete(key);
      }

      if (priceSeries) {
        applyMarkers(priceSeries, markerOutputs);
      } else if (markerOutputs.length === 0) {
        if (markersPlugin) markersPlugin.setMarkers([]);
      }
    });
  });

  onDestroy(() => {
    removeMarkers();
    removeAllOverlays(chartFn());
  });
</script>
