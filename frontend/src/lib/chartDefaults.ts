import { formatRgb, parse } from 'culori';
import type { ChartColours } from './chartColours';

export const DEFAULT_BORDER = '#404040';

function fadedBorder(border: string): string {
  const parsed = parse(border);
  if (parsed) {
    const formatted = formatRgb({ ...parsed, alpha: 0.125 });
    if (formatted) return formatted;
  }
  return border;
}

export const DEFAULT_CHART_COLOURS: ChartColours = {
  candleUpBody: '#5ea500',
  candleDownBody: '#e7000b',
  candleUpWick: '#5ea500',
  candleDownWick: '#e7000b',
  lineColour: '#d1d4dc',
  areaTop: 'rgba(56, 33, 110, 0.5)',
  areaBottom: 'rgba(56, 33, 110, 0.05)',
  volumeUp: '#26a63130',
  volumeDown: '#c21a2a30',
  smaLine: '#2962FF',
  emaLine: '#FF6D00',
  chartBackground: '#141414',
  gridLines: fadedBorder(DEFAULT_BORDER),
  textColour: '#d1d4dc',
};
