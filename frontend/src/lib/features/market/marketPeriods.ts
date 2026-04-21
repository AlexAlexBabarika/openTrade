import periodsJson from '@shared/market_periods.json' with { type: 'json' };
import { safeLocalStorageGet, safeLocalStorageSet } from '$lib/core/storage';

export type MarketPeriodOption = {
  value: string;
  label: string;
};

export const MARKET_PERIOD_OPTIONS: MarketPeriodOption[] =
  periodsJson.options.map((o: { value: string; label: string }) => ({
    value: o.value,
    label: o.label,
  }));

/** Default period (must match an entry in ``shared/market_periods.json``). */
export const DEFAULT_MARKET_PERIOD = '1y' as const;

export type PeriodCategory = 'Days' | 'Weeks' | 'Months' | 'Years' | 'All';

const PERIOD_CATEGORY_ORDER: PeriodCategory[] = [
  'Days',
  'Weeks',
  'Months',
  'Years',
  'All',
];

function categorizePeriod(value: string): PeriodCategory {
  if (value === 'max') return 'All';
  if (value.endsWith('d')) return 'Days';
  if (value.endsWith('w')) return 'Weeks';
  if (value.endsWith('mo')) return 'Months';
  if (value.endsWith('y')) return 'Years';
  return 'All';
}

function labelizePeriod(value: string): string {
  if (value === 'max') return 'All available';
  if (value === '1d') return '1 day';
  if (value.endsWith('d')) return `${value.slice(0, -1)} days`;
  if (value === '1w') return '1 week';
  if (value.endsWith('w')) return `${value.slice(0, -1)} weeks`;
  if (value === '1mo') return '1 month';
  if (value.endsWith('mo')) return `${value.slice(0, -2)} months`;
  if (value === '1y') return '1 year';
  if (value.endsWith('y')) return `${value.slice(0, -1)} years`;
  return value;
}

export interface GroupedPeriod {
  category: PeriodCategory;
  options: { value: string; label: string; longLabel: string }[];
}

export const GROUPED_PERIODS: GroupedPeriod[] = PERIOD_CATEGORY_ORDER.map(
  cat => ({
    category: cat,
    options: MARKET_PERIOD_OPTIONS.filter(
      o => categorizePeriod(o.value) === cat,
    ).map(o => ({
      value: o.value,
      label: o.label,
      longLabel: labelizePeriod(o.value),
    })),
  }),
).filter(g => g.options.length > 0);

const PERIOD_FAVOURITES_KEY = 'opentrade:periodFavourites';
const DEFAULT_PERIOD_FAVOURITES: readonly string[] = [
  '1d',
  '5d',
  '1mo',
  '3mo',
  '1y',
  '5y',
  'max',
];

const VALID_PERIOD_VALUES = new Set(MARKET_PERIOD_OPTIONS.map(o => o.value));

export function loadPeriodFavourites(): string[] {
  const stored = safeLocalStorageGet<unknown>(PERIOD_FAVOURITES_KEY);
  if (!Array.isArray(stored)) return [...DEFAULT_PERIOD_FAVOURITES];
  const filtered = stored.filter(
    (v): v is string => typeof v === 'string' && VALID_PERIOD_VALUES.has(v),
  );
  return filtered.length > 0 ? filtered : [...DEFAULT_PERIOD_FAVOURITES];
}

export function persistPeriodFavourites(values: string[]): void {
  safeLocalStorageSet(PERIOD_FAVOURITES_KEY, values);
}

/** Returns favourites sorted by the canonical order in MARKET_PERIOD_OPTIONS. */
export function sortPeriodFavouritesByCanonical(values: string[]): string[] {
  const index = new Map(
    MARKET_PERIOD_OPTIONS.map((o, i) => [o.value, i] as const),
  );
  return [...values].sort((a, b) => (index.get(a) ?? 0) - (index.get(b) ?? 0));
}
