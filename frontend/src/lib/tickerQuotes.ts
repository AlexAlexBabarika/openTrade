import { fetchMarketOHLCV, type RemoteMarketProvider } from './marketData';

export type TickerQuote =
  | { status: 'loading' }
  | { status: 'ok'; close: number | null }
  | { status: 'error' };

export async function fetchLastClose(
  symbol: string,
  provider: RemoteMarketProvider,
): Promise<number | null> {
  const data = await fetchMarketOHLCV(symbol, provider, '5d', '1d');
  const candles = data.candles;
  return candles.length > 0 ? candles[candles.length - 1].close : null;
}
