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

const STORAGE_KEY = 'opentrade:chartColours';

const CHART_COLOUR_KEYS: (keyof ChartColours)[] = [
  'candleUpBody',
  'candleDownBody',
  'candleUpWick',
  'candleDownWick',
  'lineColour',
  'areaTop',
  'areaBottom',
  'volumeUp',
  'volumeDown',
  'smaLine',
  'emaLine',
];

/** Shallow copy; reading each field helps Svelte effects track nested `$state` updates. */
export function snapshotChartColours(c: ChartColours): ChartColours {
  return { ...c };
}

export function loadChartColoursFromStorage(): ChartColours | null {
  if (typeof localStorage === 'undefined') return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as unknown;
    if (!data || typeof data !== 'object' || Array.isArray(data)) return null;
    const rec = data as Record<string, unknown>;
    const partial: Partial<ChartColours> = {};
    for (const key of CHART_COLOUR_KEYS) {
      const v = rec[key as string];
      if (typeof v === 'string' && v.trim()) partial[key] = v.trim();
    }
    if (Object.keys(partial).length === 0) return null;
    return { ...defaultChartColours(), ...partial };
  } catch {
    return null;
  }
}

export function persistChartColours(colours: ChartColours): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(colours));
  } catch (e) {
    console.warn('[opentrade] Failed to persist chart colours', e);
  }
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
