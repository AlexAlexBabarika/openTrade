<script lang="ts">
  import { onDestroy, untrack } from 'svelte';
  import {
    HistogramSeries,
    LineSeries,
    LineStyle,
    createSeriesMarkers,
    type IChartApi,
    type IPaneApi,
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

  type PaneSeriesEntry = {
    series: ISeriesApi<'Line' | 'Histogram'>;
    paneKey: string;
    kind: 'line' | 'histogram';
  };

  const overlaySeries = new Map<string, ISeriesApi<'Line'>>();
  const paneSeries = new Map<string, PaneSeriesEntry>();
  const panes = new Map<string, IPaneApi<Time>>();
  let markersPlugin: ISeriesMarkersPluginApi<Time> | null = null;
  let markersAttachedTo: ISeriesApi<'Candlestick' | 'Line'> | null = null;

  const DEFAULT_OVERLAY_COLOUR = '#3b82f6';
  const DEFAULT_PANE_COLOUR = '#3b82f6';
  const DEFAULT_HISTOGRAM_COLOUR = '#94a3b8';
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

  function ensurePane(
    chart: IChartApi,
    paneKey: string,
    height: number | null | undefined,
  ): number {
    let pane = panes.get(paneKey);
    if (!pane) {
      pane = chart.addPane(true) as IPaneApi<Time>;
      panes.set(paneKey, pane);
      if (height && height > 0) {
        try {
          pane.setHeight(height);
        } catch {
          /* invalid height — ignore */
        }
      }
    }
    return pane.paneIndex();
  }

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

  function applyPaneLine(
    chart: IChartApi,
    key: string,
    paneKey: string,
    output: Extract<ScriptOutput, { type: 'pane' }>,
  ): void {
    const paneIndex = ensurePane(chart, paneKey, output.height);
    const options = {
      color: output.color ?? DEFAULT_PANE_COLOUR,
      lineWidth: 2 as LineWidth,
      title: output.title,
      priceLineVisible: false,
      lastValueVisible: false,
    };
    const existing = paneSeries.get(key);
    if (existing && existing.kind === 'line' && existing.paneKey === paneKey) {
      existing.series.applyOptions(options);
      (existing.series as ISeriesApi<'Line'>).setData(
        output.data as unknown as { time: Time; value: number }[],
      );
      return;
    }
    if (existing) removeSeriesEntry(chart, key);
    const series = chart.addSeries(LineSeries, options, paneIndex);
    series.setData(
      output.data as unknown as { time: Time; value: number }[],
    );
    paneSeries.set(key, { series, paneKey, kind: 'line' });
  }

  function applyPaneHistogram(
    chart: IChartApi,
    key: string,
    paneKey: string,
    output: Extract<ScriptOutput, { type: 'histogram' }>,
  ): void {
    const paneIndex = ensurePane(chart, paneKey, null);
    const options = {
      color: DEFAULT_HISTOGRAM_COLOUR,
      title: output.title,
      priceLineVisible: false,
      lastValueVisible: false,
    };
    const data = output.data.map(p => ({
      time: p.time as unknown as Time,
      value: p.value,
      color: p.color ?? undefined,
    }));
    const existing = paneSeries.get(key);
    if (
      existing &&
      existing.kind === 'histogram' &&
      existing.paneKey === paneKey
    ) {
      existing.series.applyOptions(options);
      (existing.series as ISeriesApi<'Histogram'>).setData(data);
      return;
    }
    if (existing) removeSeriesEntry(chart, key);
    const series = chart.addSeries(HistogramSeries, options, paneIndex);
    series.setData(data);
    paneSeries.set(key, { series, paneKey, kind: 'histogram' });
  }

  function removeSeriesEntry(chart: IChartApi, key: string): void {
    const entry = paneSeries.get(key);
    if (!entry) return;
    try {
      chart.removeSeries(entry.series);
    } catch {
      /* already removed */
    }
    paneSeries.delete(key);
  }

  function removeOrphanPanes(chart: IChartApi): void {
    const referenced = new Set<string>();
    for (const entry of paneSeries.values()) referenced.add(entry.paneKey);
    for (const [paneKey, paneApi] of panes) {
      if (referenced.has(paneKey)) continue;
      try {
        chart.removePane(paneApi.paneIndex());
      } catch {
        /* already gone */
      }
      panes.delete(paneKey);
    }
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

  function removeAllPaneSeries(chart: IChartApi | null): void {
    for (const entry of paneSeries.values()) {
      try {
        chart?.removeSeries(entry.series);
      } catch {
        /* chart already disposed */
      }
    }
    paneSeries.clear();
  }

  function removeAllPanes(chart: IChartApi | null): void {
    if (!chart) {
      panes.clear();
      return;
    }
    const apis = Array.from(panes.values());
    apis.sort((a, b) => b.paneIndex() - a.paneIndex());
    for (const api of apis) {
      try {
        chart.removePane(api.paneIndex());
      } catch {
        /* already gone */
      }
    }
    panes.clear();
  }

  $effect(() => {
    const next = outputs;
    untrack(() => {
      const chart = chartFn();
      const priceSeries = priceSeriesFn();
      if (!chart) return;

      const keepOverlayKeys = new Set<string>();
      const keepPaneSeriesKeys = new Set<string>();
      const markerOutputs: Extract<ScriptOutput, { type: 'markers' }>[] = [];

      for (let i = 0; i < next.length; i += 1) {
        const out = next[i];
        if (out.type === 'overlay') {
          const key = `overlay:${i}:${out.title}`;
          keepOverlayKeys.add(key);
          applyOverlay(chart, key, out);
        } else if (out.type === 'pane') {
          const paneKey = out.pane_id ?? `pane:${i}:${out.title}`;
          const key = `pane:${i}:${out.title}`;
          keepPaneSeriesKeys.add(key);
          applyPaneLine(chart, key, paneKey, out);
        } else if (out.type === 'histogram') {
          const paneKey = out.pane_id ?? `hist:${i}:${out.title}`;
          const key = `hist:${i}:${out.title}`;
          keepPaneSeriesKeys.add(key);
          applyPaneHistogram(chart, key, paneKey, out);
        } else if (out.type === 'markers') {
          markerOutputs.push(out);
        }
      }

      for (const [key, series] of overlaySeries) {
        if (keepOverlayKeys.has(key)) continue;
        try {
          chart.removeSeries(series);
        } catch {
          /* already removed */
        }
        overlaySeries.delete(key);
      }

      for (const key of Array.from(paneSeries.keys())) {
        if (keepPaneSeriesKeys.has(key)) continue;
        removeSeriesEntry(chart, key);
      }

      removeOrphanPanes(chart);

      if (priceSeries) {
        applyMarkers(priceSeries, markerOutputs);
      } else {
        detachMarkers();
      }
    });
  });

  onDestroy(() => {
    detachMarkers();
    const chart = chartFn();
    removeAllOverlays(chart);
    removeAllPaneSeries(chart);
    removeAllPanes(chart);
  });
</script>
