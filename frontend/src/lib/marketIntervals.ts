import intervalsJson from '@shared/market_intervals.json' with { type: 'json' };

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
