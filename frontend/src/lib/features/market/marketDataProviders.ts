export const MARKET_DATA_PROVIDERS = [
  // TwelveData does support WebSockets, but only for paid plans, so let it be false here for now
  { value: 'twelvedata', label: 'Twelve Data', supportsWs: false },
  { value: 'yfinance', label: 'YFinance', supportsWs: false },
  { value: 'binance', label: 'Binance', supportsWs: true },
  { value: 'csv', label: 'CSV', supportsWs: false },
] as const;

export type MarketDataProviderValue =
  (typeof MARKET_DATA_PROVIDERS)[number]['value'];

const _SUPPORTS_WS = new Map(
  MARKET_DATA_PROVIDERS.map(p => [p.value, p.supportsWs] as const),
);

export function providerSupportsWs(p: MarketDataProviderValue): boolean {
  return _SUPPORTS_WS.get(p) ?? false;
}
