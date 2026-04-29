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

  const overlaySeries = new Map<string, ISeriesApi<'Line'>>();
  let markersPlugin: ISeriesMarkersPluginApi<Time> | null = null;
  let markersAttachedTo: ISeriesApi<'Candlestick' | 'Line'> | null = null;

  const DEFAULT_OVERLAY_COLOUR = '#3b82f6';
  const DEFAULT_MARKER_COLOUR = '#eab308';

  const LINE_STYLE_MAP: Record<string, LineStyle> = {
    dashed: LineStyle.Dashed,
    dotted: LineStyle.Dotted,
    large_dashed: LineStyle.LargeDashed,
    largedashed: LineStyle.LargeDashed,
    sparse_dotted: LineStyle.SparseDotted,
    sparsedotted: LineStyle.SparseDotted,
  };

  const MARKER_SHAPE_MAP: Record<string, SeriesMarkerShape> = {
    square: 'square',
    arrowup: 'arrowUp',
    arrow_up: 'arrowUp',
    arrowdown: 'arrowDown',
    arrow_down: 'arrowDown',
  };

  const MARKER_POSITION_MAP: Record<string, SeriesMarkerBarPosition> = {
    belowbar: 'belowBar',
    below_bar: 'belowBar',
    inbar: 'inBar',
    in_bar: 'inBar',
  };

  const lookup = <T,>(
    table: Record<string, T>,
    name: string | null | undefined,
    fallback: T,
  ): T => table[(name ?? '').toLowerCase()] ?? fallback;

  function applyOverlay(
    chart: IChartApi,
    key: string,
    output: Extract<ScriptOutput, { type: 'overlay' }>,
  ): void {
    const options = {
      color: output.color ?? DEFAULT_OVERLAY_COLOUR,
      lineWidth: (output.line_width ?? 2) as LineWidth,
      lineStyle: lookup(LINE_STYLE_MAP, output.line_style, LineStyle.Solid),
      title: output.title,
    };
    let series = overlaySeries.get(key);
    if (!series) {
      series = chart.addSeries(LineSeries, {
        ...options,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      overlaySeries.set(key, series);
    } else {
      series.applyOptions(options);
    }
    series.setData(output.data as unknown as { time: Time; value: number }[]);
  }

  function buildMarkers(
    list: Extract<ScriptOutput, { type: 'markers' }>[],
  ): SeriesMarker<Time>[] {
    const merged: SeriesMarker<Time>[] = [];
    for (const m of list) {
      const shape = lookup(MARKER_SHAPE_MAP, m.shape, 'circle');
      const position = lookup(MARKER_POSITION_MAP, m.position, 'aboveBar');
      const color = m.color ?? DEFAULT_MARKER_COLOUR;
      const text = m.text ?? undefined;
      for (const pt of m.data) {
        merged.push({ time: pt.time as Time, shape, position, color, text });
      }
    }
    // LWC requires markers sorted ascending by time.
    merged.sort((a, b) => Number(a.time) - Number(b.time));
    return merged;
  }

  function detachMarkers(): void {
    if (!markersPlugin) return;
    try {
      markersPlugin.detach();
    } catch {
      /* series already removed */
    }
    markersPlugin = null;
    markersAttachedTo = null;
  }

  function applyMarkers(
    priceSeries: ISeriesApi<'Candlestick' | 'Line'>,
    list: Extract<ScriptOutput, { type: 'markers' }>[],
  ): void {
    if (list.length === 0) {
      detachMarkers();
      return;
    }
    const data = buildMarkers(list);
    if (!markersPlugin || markersAttachedTo !== priceSeries) {
      detachMarkers();
      markersPlugin = createSeriesMarkers(priceSeries, data);
      markersAttachedTo = priceSeries;
    } else {
      markersPlugin.setMarkers(data);
    }
  }

  function removeAllOverlays(chart: IChartApi | null): void {
    for (const series of overlaySeries.values()) {
      try {
        chart?.removeSeries(series);
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
      } else {
        detachMarkers();
      }
    });
  });

  onDestroy(() => {
    detachMarkers();
    removeAllOverlays(chartFn());
  });
</script>
