import { fetchMarketOHLCV, type RemoteMarketProvider } from './marketData';
import { getStreamClient } from '$lib/core/streamClient';

export type TickerQuote =
  | { status: 'loading' }
  | { status: 'ok'; close: number | null }
  | { status: 'error' };

/** Providers whose quotes can be streamed via `/ws/live` `subscribe_quote`. */
const STREAMING_QUOTE_PROVIDERS: ReadonlySet<RemoteMarketProvider> = new Set([
  'binance',
]);

export function providerSupportsQuoteStream(p: RemoteMarketProvider): boolean {
  return STREAMING_QUOTE_PROVIDERS.has(p);
}

export async function fetchLastClose(
  symbol: string,
  provider: RemoteMarketProvider,
): Promise<number | null> {
  const data = await fetchMarketOHLCV(symbol, provider, '5d', '1d');
  const candles = data.candles;
  return candles.length > 0 ? candles[candles.length - 1].close : null;
}

/**
 * Subscribe to live last-price ticks for one symbol. Returns an unsubscribe fn.
 *
 * Only valid for providers in `STREAMING_QUOTE_PROVIDERS`; callers should use
 * `fetchLastClose` for the others.
 */
export function subscribeQuoteStream(
  symbol: string,
  provider: RemoteMarketProvider,
  onPrice: (price: number) => void,
): () => void {
  return getStreamClient().subscribeQuote(
    { provider, symbol },
    {
      onQuote: msg => onPrice(msg.price),
    },
  );
}
