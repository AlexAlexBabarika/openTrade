import periodsJson from '@shared/market_periods.json' with { type: 'json' };

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
export const DEFAULT_MARKET_PERIOD = '1mo' as const;
