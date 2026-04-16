import { createChart, CrosshairMode, ColorType } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, LineData } from 'lightweight-charts';
import { isoToChartTime } from './chartAdapters';
import { formatRgb, parse } from 'culori';
import type { ChartColours } from './chartColours';
import { DEFAULT_BORDER, DEFAULT_CHART_COLOURS } from './chartDefaults';

export function getCssVarColor(
  variableName: string,
  fallback: string = '#000000',
): string {
  if (typeof window === 'undefined') return fallback;

  const root = document.documentElement;
  const style = getComputedStyle(root);

  // Try standard variable name first (e.g. --background)
  let value = style.getPropertyValue(variableName).trim();

  // If not found, try with Tailwind --color- prefix (e.g. --color-background)
  if (!value) {
    const prefixedName = '--color-' + variableName.replace(/^--/, '');
    value = style.getPropertyValue(prefixedName).trim();
  }

  // Handle cases where the input might be missing the leading dashes
  if (!value && !variableName.startsWith('--')) {
    value = style.getPropertyValue('--' + variableName).trim();
  }

  if (!value) {
    console.warn(
      `[Chart] Variable ${variableName} not found. Using fallback ${fallback}`,
    );
    return fallback;
  }

  // Robust OKLCH parsing via RegEx to handle raw values and space/comma separation
  const oklchMatch = value.match(
    /(?:oklch\()?([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[/\s,]\s*([\d.%]+))?\)?/,
  );

  if (oklchMatch) {
    const [_, l, c, h, a] = oklchMatch;
    try {
      const alpha = a
        ? a.includes('%')
          ? parseFloat(a) / 100
          : parseFloat(a)
        : 1;
      const color = formatRgb({
        mode: 'oklch',
        l: parseFloat(l),
        c: parseFloat(c),
        h: parseFloat(h),
        alpha,
      });
      if (color) return color;
    } catch (e) {
      console.error(`[Chart] Error converting OKLCH ${value}:`, e);
    }
  }

  // Try standard culori parse
  try {
    const parsed = parse(value);
    if (parsed) {
      const color = formatRgb(parsed);
      if (color) return color;
    }
  } catch (e) {
    // Ignore
  }

  console.warn(
    `[Chart] Could not parse color "${value}" for ${variableName}. Using fallback ${fallback}`,
  );
  return fallback;
}

export function computeGridLineColor(borderColor: string): string {
  const parsed = parse(borderColor);
  if (parsed) {
    const formatted = formatRgb({ ...parsed, alpha: 0.125 });
    if (formatted) return formatted;
  }
  return borderColor;
}

export function createChartContainer(
  parent: HTMLElement,
  colours?: ChartColours,
): IChartApi {
  const bgColor =
    colours?.chartBackground ??
    getCssVarColor('--background', DEFAULT_CHART_COLOURS.chartBackground);
  const textColor =
    colours?.textColour ??
    getCssVarColor('--foreground', DEFAULT_CHART_COLOURS.textColour);
  const borderColor = getCssVarColor('--border', DEFAULT_BORDER);
  const gridLineColor = colours?.gridLines ?? computeGridLineColor(borderColor);

  const chart = createChart(parent, {
    width: parent.clientWidth,
    height: parent.clientHeight,
    layout: {
      background: { type: ColorType.Solid, color: bgColor },
      textColor: textColor,
    },
    grid: {
      vertLines: { color: gridLineColor },
      horzLines: { color: gridLineColor },
    },
    rightPriceScale: {
      borderColor: borderColor,
      scaleMargins: { top: 0.1, bottom: 0.2 },
    },
    timeScale: {
      borderColor: borderColor,
      timeVisible: true,
      secondsVisible: false,
    },
    crosshair: {
      mode: CrosshairMode.Magnet,
    },
  });
  chart.timeScale().fitContent();
  return chart;
}

export function addVolumeSeries(chart: IChartApi): ISeriesApi<'Histogram'> {
  const series = chart.addHistogramSeries({
    priceFormat: {
      type: 'volume',
    },
    priceScaleId: '',
  });
  series.priceScale().applyOptions({
    scaleMargins: {
      top: 0.77,
      bottom: 0,
    },
  });
  return series;
}

export function addCandlestickSeries(
  chart: IChartApi,
  colours?: ChartColours,
): ISeriesApi<'Candlestick'> {
  const upColor =
    colours?.candleUpBody ??
    getCssVarColor('--up-color', DEFAULT_CHART_COLOURS.candleUpBody);
  const downColor =
    colours?.candleDownBody ??
    getCssVarColor('--down-color', DEFAULT_CHART_COLOURS.candleDownBody);
  const wickUpColor = colours?.candleUpWick ?? upColor;
  const wickDownColor = colours?.candleDownWick ?? downColor;

  const series = chart.addCandlestickSeries({
    upColor,
    downColor,
    borderDownColor: downColor,
    borderUpColor: upColor,
    wickDownColor,
    wickUpColor,
  });
  return series;
}

export function addAreaSeries(
  chart: IChartApi,
  colours?: ChartColours,
): ISeriesApi<'Area'> {
  const topColor =
    colours?.areaTop ??
    getCssVarColor('--area-top-color', DEFAULT_CHART_COLOURS.areaTop);
  const bottomColor =
    colours?.areaBottom ??
    getCssVarColor('--area-bottom-color', DEFAULT_CHART_COLOURS.areaBottom);

  const series = chart.addAreaSeries({
    lastValueVisible: false,
    crosshairMarkerVisible: false,
    lineColor: 'transparent',
    topColor,
    bottomColor,
  });
  return series;
}

export function syncChartTheme(
  chart: IChartApi,
  candleSeries?: ISeriesApi<'Candlestick'> | null,
  areaSeries?: ISeriesApi<'Area'> | null,
  lineSeries?: ISeriesApi<'Line'> | null,
  colours?: ChartColours,
) {
  const bgColor =
    colours?.chartBackground ??
    getCssVarColor('--background', DEFAULT_CHART_COLOURS.chartBackground);
  const textColor =
    colours?.textColour ??
    getCssVarColor('--foreground', DEFAULT_CHART_COLOURS.textColour);
  const borderColor = getCssVarColor('--border', DEFAULT_BORDER);
  const gridLineColor = colours?.gridLines ?? computeGridLineColor(borderColor);

  chart.applyOptions({
    layout: {
      background: { type: ColorType.Solid, color: bgColor },
      textColor: textColor,
    },
    grid: {
      vertLines: { color: gridLineColor },
      horzLines: { color: gridLineColor },
    },
    rightPriceScale: {
      borderColor: borderColor,
    },
    timeScale: {
      borderColor: borderColor,
    },
  });

  if (candleSeries) {
    const upColor =
      colours?.candleUpBody ??
      getCssVarColor('--up-color', DEFAULT_CHART_COLOURS.candleUpBody);
    const downColor =
      colours?.candleDownBody ??
      getCssVarColor('--down-color', DEFAULT_CHART_COLOURS.candleDownBody);
    const wickUpColor = colours?.candleUpWick ?? upColor;
    const wickDownColor = colours?.candleDownWick ?? downColor;
    candleSeries.applyOptions({
      upColor,
      downColor,
      borderDownColor: downColor,
      borderUpColor: upColor,
      wickDownColor,
      wickUpColor,
    });
  }

  if (areaSeries) {
    const topColor =
      colours?.areaTop ??
      getCssVarColor('--area-top-color', DEFAULT_CHART_COLOURS.areaTop);
    const bottomColor =
      colours?.areaBottom ??
      getCssVarColor('--area-bottom-color', DEFAULT_CHART_COLOURS.areaBottom);
    areaSeries.applyOptions({ topColor, bottomColor });
  }

  if (lineSeries) {
    const lineColor = colours?.lineColour ?? textColor;
    lineSeries.applyOptions({ color: lineColor });
  }
}

export function addLineSeries(
  chart: IChartApi,
  color: string,
): ISeriesApi<'Line'> {
  return chart.addLineSeries({ color });
}

export function linePoint(time: string, value: number): LineData {
  return { time: isoToChartTime(time), value };
}
