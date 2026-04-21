import { apiJson, getAccessToken } from '$lib/core/api';
import type { MarketDataProviderValue } from './marketDataProviders';
import type { OHLCVCandle } from '$lib/core/types';

/** Providers served by GET /data/market (CSV uses POST /data/csv). */
export type RemoteMarketProvider = Exclude<MarketDataProviderValue, 'csv'>;

export interface MarketOHLCVResponse {
  symbol: string;
  candles: OHLCVCandle[];
}

/**
 * Load OHLCV from the backend unified market endpoint.
 * Twelve Data requires a Bearer token + stored API key; Binance sends auth when logged in.
 */
export async function fetchMarketOHLCV(
  symbol: string,
  provider: RemoteMarketProvider,
  period: string,
  interval: string,
): Promise<MarketOHLCVResponse> {
  const sym = symbol.trim();
  if (!sym) {
    throw new Error('Enter a symbol');
  }

  if (provider === 'twelvedata' && !getAccessToken()) {
    throw new Error(
      'Twelve Data requires you to sign in and add a Twelve Data API key (API Keys in the header).',
    );
  }

  const params = new URLSearchParams({
    symbol: sym,
    provider,
    period,
    interval,
  });

  const withAuth = provider === 'twelvedata' || provider === 'binance';
  return apiJson<MarketOHLCVResponse>(
    `/data/market?${params.toString()}`,
    { method: 'GET' },
    withAuth,
  );
}
