import { getCssVarColor, computeGridLineColor } from './chart';
import { DEFAULT_BORDER, DEFAULT_CHART_COLOURS } from './chartDefaults';
import { safeLocalStorageGet, safeLocalStorageSet } from './storage';

export interface ChartTemplate {
  name: string;
  colours: ChartColours;
  smaLineWidth: number;
  emaLineWidth: number;
  bbandsLineWidth?: number;
  chartType?: 'candlestick' | 'line';
  showArea?: boolean;
  showVolume?: boolean;
  smaEnabled?: boolean;
  emaEnabled?: boolean;
  bbandsEnabled?: boolean;
}

export interface ChartSettings {
  chartType: 'candlestick' | 'line';
  showArea: boolean;
  showVolume: boolean;
  smaEnabled: boolean;
  emaEnabled: boolean;
  bbandsEnabled: boolean;
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
  bbandsUpper: string;
  bbandsMiddle: string;
  bbandsLower: string;
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
  'bbandsUpper',
  'bbandsMiddle',
  'bbandsLower',
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
    bbandsEnabled:
      typeof data.bbandsEnabled === 'boolean' ? data.bbandsEnabled : false,
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
  const up = getCssVarColor('--up-color', DEFAULT_CHART_COLOURS.candleUpBody);
  const down = getCssVarColor(
    '--down-color',
    DEFAULT_CHART_COLOURS.candleDownBody,
  );
  return {
    candleUpBody: up,
    candleDownBody: down,
    candleUpWick: up,
    candleDownWick: down,
    lineColour: getCssVarColor(
      '--foreground',
      DEFAULT_CHART_COLOURS.lineColour,
    ),
    areaTop: getCssVarColor('--area-top-color', DEFAULT_CHART_COLOURS.areaTop),
    areaBottom: getCssVarColor(
      '--area-bottom-color',
      DEFAULT_CHART_COLOURS.areaBottom,
    ),
    volumeUp: DEFAULT_CHART_COLOURS.volumeUp,
    volumeDown: DEFAULT_CHART_COLOURS.volumeDown,
    smaLine: DEFAULT_CHART_COLOURS.smaLine,
    emaLine: DEFAULT_CHART_COLOURS.emaLine,
    bbandsUpper: DEFAULT_CHART_COLOURS.bbandsUpper,
    bbandsMiddle: DEFAULT_CHART_COLOURS.bbandsMiddle,
    bbandsLower: DEFAULT_CHART_COLOURS.bbandsLower,
    chartBackground: getCssVarColor(
      '--background',
      DEFAULT_CHART_COLOURS.chartBackground,
    ),
    gridLines: computeGridLineColor(getCssVarColor('--border', DEFAULT_BORDER)),
    textColour: getCssVarColor(
      '--foreground',
      DEFAULT_CHART_COLOURS.textColour,
    ),
  };
}
