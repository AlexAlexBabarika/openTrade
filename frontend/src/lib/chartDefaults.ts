import { formatRgb, parse } from 'culori';
import type { ChartColours } from './chartColours';

export const DEFAULT_BORDER = '#404040';

export function computeGridLineColor(borderColor: string): string {
  const parsed = parse(borderColor);
  if (parsed) {
    const formatted = formatRgb({ ...parsed, alpha: 0.125 });
    if (formatted) return formatted;
  }
  return borderColor;
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
  bbandsUpper: '#7B1FA2',
  bbandsMiddle: '#9C27B0',
  bbandsLower: '#7B1FA2',
  chartBackground: '#141414',
  gridLines: computeGridLineColor(DEFAULT_BORDER),
  textColour: '#d1d4dc',
};
