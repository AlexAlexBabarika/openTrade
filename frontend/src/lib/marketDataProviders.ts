export const MARKET_DATA_PROVIDERS = [
  { value: 'twelvedata', label: 'Twelve Data' },
  { value: 'yfinance', label: 'YFinance' },
  { value: 'binance', label: 'Binance' },
  { value: 'csv', label: 'CSV' },
] as const;

export type MarketDataProviderValue =
  (typeof MARKET_DATA_PROVIDERS)[number]['value'];