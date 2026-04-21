import intervalsJson from '@shared/market_intervals.json' with { type: 'json' };
import { safeLocalStorageGet, safeLocalStorageSet } from '$lib/core/storage';

export type MarketIntervalOption = {
  value: string;
  label: string;
};

export const MARKET_INTERVAL_OPTIONS: MarketIntervalOption[] =
  intervalsJson.options.map((o: { value: string; label: string }) => ({
    value: o.value,
    label: o.label,
  }));

/** Default interval (must match an entry in ``shared/market_intervals.json``). */
export const DEFAULT_MARKET_INTERVAL = '1d' as const;

export type IntervalCategory = 'Minutes' | 'Hours' | 'Days';

const CATEGORY_ORDER: IntervalCategory[] = ['Minutes', 'Hours', 'Days'];

function categorize(value: string): IntervalCategory {
  if (value.endsWith('m') && !value.endsWith('mo')) return 'Minutes';
  if (value.endsWith('h')) return 'Hours';
  return 'Days';
}

function labelize(value: string): string {
  if (value === '1m') return '1 minute';
  if (value.endsWith('m') && !value.endsWith('mo')) {
    return `${value.slice(0, -1)} minutes`;
  }
  if (value === '1h') return '1 hour';
  if (value.endsWith('h')) return `${value.slice(0, -1)} hours`;
  if (value === '1d') return '1 day';
  if (value === '1w') return '1 week';
  if (value === '1mo') return '1 month';
  return value;
}

export interface GroupedInterval {
  category: IntervalCategory;
  options: { value: string; label: string; longLabel: string }[];
}

export const GROUPED_INTERVALS: GroupedInterval[] = CATEGORY_ORDER.map(cat => ({
  category: cat,
  options: MARKET_INTERVAL_OPTIONS.filter(o => categorize(o.value) === cat).map(
    o => ({ value: o.value, label: o.label, longLabel: labelize(o.value) }),
  ),
})).filter(g => g.options.length > 0);

const INTERVAL_FAVOURITES_KEY = 'opentrade:intervalFavourites';
const DEFAULT_FAVOURITES: readonly string[] = [
  '1m',
  '5m',
  '15m',
  '30m',
  '1h',
  '4h',
  '1d',
];

const VALID_VALUES = new Set(MARKET_INTERVAL_OPTIONS.map(o => o.value));

export function loadIntervalFavourites(): string[] {
  const stored = safeLocalStorageGet<unknown>(INTERVAL_FAVOURITES_KEY);
  if (!Array.isArray(stored)) return [...DEFAULT_FAVOURITES];
  const filtered = stored.filter(
    (v): v is string => typeof v === 'string' && VALID_VALUES.has(v),
  );
  return filtered.length > 0 ? filtered : [...DEFAULT_FAVOURITES];
}

export function persistIntervalFavourites(values: string[]): void {
  safeLocalStorageSet(INTERVAL_FAVOURITES_KEY, values);
}

/** Returns favourites sorted by the canonical order in MARKET_INTERVAL_OPTIONS. */
export function sortFavouritesByCanonical(values: string[]): string[] {
  const index = new Map(
    MARKET_INTERVAL_OPTIONS.map((o, i) => [o.value, i] as const),
  );
  return [...values].sort((a, b) => (index.get(a) ?? 0) - (index.get(b) ?? 0));
}
