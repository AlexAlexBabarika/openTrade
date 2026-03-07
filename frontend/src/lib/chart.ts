import { createChart, CrosshairMode, ColorType } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, LineData } from 'lightweight-charts';
import { isoToChartTime } from './chartAdapters';
import { formatRgb, parse } from 'culori';

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

export function createChartContainer(parent: HTMLElement): IChartApi {
  const bgColor = getCssVarColor('--background', '#141414');
  const textColor = getCssVarColor('--foreground', '#d1d4dc');
  const borderColor = getCssVarColor('--border', '#404040');

  const chart = createChart(parent, {
    width: parent.clientWidth,
    height: parent.clientHeight,
    layout: {
      background: { type: ColorType.Solid, color: bgColor },
      textColor: textColor,
    },
    grid: {
      vertLines: { color: borderColor }, // adding transparency
      horzLines: { color: borderColor },
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
): ISeriesApi<'Candlestick'> {
  const upColor = getCssVarColor('--up-color', '#5ea500');
  const downColor = getCssVarColor('--down-color', '#e7000b');

  const series = chart.addCandlestickSeries({
    upColor: upColor,
    downColor: downColor,
    borderDownColor: downColor,
    borderUpColor: upColor,
    wickDownColor: downColor,
    wickUpColor: upColor,
  });
  return series;
}

export function addAreaSeries(chart: IChartApi): ISeriesApi<'Area'> {
  const topColor = getCssVarColor('--area-top-color', 'rgba(56, 33, 110, 0.5)');
  const bottomColor = getCssVarColor(
    '--area-bottom-color',
    'rgba(56, 33, 110, 0.05)',
  );

  const series = chart.addAreaSeries({
    lastValueVisible: false,
    crosshairMarkerVisible: false,
    lineColor: 'transparent',
    topColor: topColor,
    bottomColor: bottomColor,
  });
  return series;
}

export function syncChartTheme(
  chart: IChartApi,
  candleSeries?: ISeriesApi<'Candlestick'> | null,
  areaSeries?: ISeriesApi<'Area'> | null,
) {
  const bgColor = getCssVarColor('--background', '#141414');
  const textColor = getCssVarColor('--foreground', '#d1d4dc');
  const borderColor = getCssVarColor('--border', '#404040');

  const parsedBorderColor = parse(borderColor);
  let gridLineColor = borderColor;
  if (parsedBorderColor) {
    const formatted = formatRgb({ ...parsedBorderColor, alpha: 0.125 });
    if (formatted) {
      gridLineColor = formatted;
    }
  }

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
    const upColor = getCssVarColor('--up-color', '#5ea500');
    const downColor = getCssVarColor('--down-color', '#e7000b');
    candleSeries.applyOptions({
      upColor: upColor,
      downColor: downColor,
      borderDownColor: downColor,
      borderUpColor: upColor,
      wickDownColor: downColor,
      wickUpColor: upColor,
    });
  }

  if (areaSeries) {
    const topColor = getCssVarColor(
      '--area-top-color',
      'rgba(56, 33, 110, 0.5)',
    );
    const bottomColor = getCssVarColor(
      '--area-bottom-color',
      'rgba(56, 33, 110, 0.05)',
    );
    areaSeries.applyOptions({
      topColor: topColor,
      bottomColor: bottomColor,
    });
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
