import { getCssVarColor, computeGridLineColor } from './chart';
import { safeLocalStorageGet, safeLocalStorageSet } from './storage';

export interface ChartTemplate {
  name: string;
  colours: ChartColours;
  smaLineWidth: number;
  emaLineWidth: number;
  chartType?: 'candlestick' | 'line';
  showArea?: boolean;
  showVolume?: boolean;
  smaEnabled?: boolean;
  emaEnabled?: boolean;
}

export interface ChartSettings {
  chartType: 'candlestick' | 'line';
  showArea: boolean;
  showVolume: boolean;
  smaEnabled: boolean;
  emaEnabled: boolean;
}

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
  chartBackground: string;
  gridLines: string;
  textColour: string;
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
  'chartBackground',
  'gridLines',
  'textColour',
];

/** Shallow copy; reading each field helps Svelte effects track nested `$state` updates. */
export function snapshotChartColours(c: ChartColours): ChartColours {
  return { ...c };
}

export function loadChartColoursFromStorage(): ChartColours | null {
  const data = safeLocalStorageGet<Record<string, unknown>>(STORAGE_KEY);
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null;
  const partial: Partial<ChartColours> = {};
  for (const key of CHART_COLOUR_KEYS) {
    const v = data[key as string];
    if (typeof v === 'string' && v.trim()) partial[key] = v.trim();
  }
  if (Object.keys(partial).length === 0) return null;
  return { ...defaultChartColours(), ...partial };
}

export function persistChartColours(colours: ChartColours): void {
  safeLocalStorageSet(STORAGE_KEY, colours);
}

const SETTINGS_KEY = 'opentrade:chartSettings';

export function loadChartSettingsFromStorage(): ChartSettings | null {
  const data = safeLocalStorageGet<Record<string, unknown>>(SETTINGS_KEY);
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null;
  return {
    chartType: data.chartType === 'line' ? 'line' : 'candlestick',
    showArea: typeof data.showArea === 'boolean' ? data.showArea : true,
    showVolume: typeof data.showVolume === 'boolean' ? data.showVolume : true,
    smaEnabled: typeof data.smaEnabled === 'boolean' ? data.smaEnabled : false,
    emaEnabled: typeof data.emaEnabled === 'boolean' ? data.emaEnabled : false,
  };
}

export function persistChartSettings(settings: ChartSettings): void {
  safeLocalStorageSet(SETTINGS_KEY, settings);
}

const TEMPLATES_KEY = 'opentrade:chartTemplates';

export function loadTemplates(): ChartTemplate[] {
  const data = safeLocalStorageGet<unknown>(TEMPLATES_KEY);
  if (!Array.isArray(data)) return [];
  return data.filter(
    (t: unknown): t is ChartTemplate =>
      !!t &&
      typeof t === 'object' &&
      typeof (t as ChartTemplate).name === 'string' &&
      typeof (t as ChartTemplate).colours === 'object',
  );
}

export function saveTemplate(template: ChartTemplate): void {
  const templates = loadTemplates();
  const idx = templates.findIndex(t => t.name === template.name);
  if (idx >= 0) templates[idx] = template;
  else templates.push(template);
  safeLocalStorageSet(TEMPLATES_KEY, templates);
}

export function deleteTemplate(name: string): void {
  const templates = loadTemplates().filter(t => t.name !== name);
  safeLocalStorageSet(TEMPLATES_KEY, templates);
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
    chartBackground: getCssVarColor('--background', '#141414'),
    gridLines: computeGridLineColor(getCssVarColor('--border', '#404040')),
    textColour: getCssVarColor('--foreground', '#d1d4dc'),
  };
}
