// frontend/src/lib/chartColours.ts
import { getCssVarColor } from './chart';

export interface ChartColours {
  candleUpBody: string;
  candleDownBody: string;
  candleUpWick: string;
  candleDownWick: string;
  lineColour: string;
  areaTop: string;
  areaBottom: string;
  volumeUp: string;
  volumeDown: string;
  smaLine: string;
  emaLine: string;
}

export function defaultChartColours(): ChartColours {
  const up = getCssVarColor('--up-color', '#5ea500');
  const down = getCssVarColor('--down-color', '#e7000b');
  return {
    candleUpBody: up,
    candleDownBody: down,
    candleUpWick: up,
    candleDownWick: down,
    lineColour: getCssVarColor('--foreground', '#d1d4dc'),
    areaTop: getCssVarColor('--area-top-color', 'rgba(56, 33, 110, 0.5)'),
    areaBottom: getCssVarColor(
      '--area-bottom-color',
      'rgba(56, 33, 110, 0.05)',
    ),
    volumeUp: '#26a63130',
    volumeDown: '#c21a2a30',
    smaLine: '#2962FF',
    emaLine: '#FF6D00',
  };
}
