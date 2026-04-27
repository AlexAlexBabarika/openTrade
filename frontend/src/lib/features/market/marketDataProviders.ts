import type { SymbolProviders } from './symbols';

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

// Fallback order when auto-switching providers: WS-capable first, then
// yfinance preferred over twelvedata.
const PROVIDER_FALLBACK_ORDER: readonly (keyof SymbolProviders)[] = [
  'binance',
  'yfinance',
  'twelvedata',
];

/** Pick a provider for a freshly-selected ticker.
 *
 *  Keeps the current provider when it supports the symbol; otherwise picks a
 *  supported one in ``PROVIDER_FALLBACK_ORDER``. Returns the current provider
 *  unchanged when ``providers`` is null (unknown symbol) or no listed
 *  provider supports it. */
export function pickProviderForSymbol(
  currentSource: MarketDataProviderValue,
  providers: SymbolProviders | null,
): MarketDataProviderValue {
  if (!providers) return currentSource;
  if (
    currentSource !== 'csv' &&
    providers[currentSource as keyof SymbolProviders]
  ) {
    return currentSource;
  }
  const next = PROVIDER_FALLBACK_ORDER.find(p => providers[p]);
  return next ?? currentSource;
}
