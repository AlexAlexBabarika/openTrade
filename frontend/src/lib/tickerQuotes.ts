import { fetchMarketOHLCV, type RemoteMarketProvider } from './marketData';

/**
 * Fetch the latest daily close for a symbol on the given remote provider.
 * Uses `period=5d, interval=1d` so payloads stay tiny and the value is stable
 * regardless of the chart's current zoom level. Returns null if the provider
 * returns no candles. Rejections are the caller's to handle.
 */
export async function fetchLastClose(
  symbol: string,
  provider: RemoteMarketProvider,
): Promise<number | null> {
  const data = await fetchMarketOHLCV(symbol, provider, '5d', '1d');
  const candles = data.candles;
  return candles.length > 0 ? candles[candles.length - 1].close : null;
}
