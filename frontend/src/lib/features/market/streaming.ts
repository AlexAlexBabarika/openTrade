import type { OHLCVCandle } from '$lib/core/types';
import {
  getStreamClient,
  type CandleSubscription,
  type StreamConnectionState,
} from '$lib/core/streamClient';

export type StreamStatus =
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'error';

export interface SubscribeMarketStreamOptions extends CandleSubscription {
  /** Last historical candle timestamp from REST. Snapshot bars at or before this are dropped. */
  historyEndIso?: string;
  /** Fired for every candle that should be applied to the chart (snapshot tail + live updates). */
  onCandle: (c: OHLCVCandle, isFinal: boolean) => void;
  onStatus?: (s: StreamStatus) => void;
}

/**
 * Subscribe to live candles for one (provider, symbol, interval). Returns an unsubscribe fn.
 *
 * Snapshot reconciliation: candles whose timestamp is <= historyEndIso are dropped, so the
 * chart never sees a duplicate of a bar it already loaded over REST.
 */
export function subscribeMarketStream(
  opts: SubscribeMarketStreamOptions,
): () => void {
  const { historyEndIso, onCandle, onStatus, ...sub } = opts;
  const cutoff = historyEndIso
    ? Date.parse(historyEndIso)
    : Number.NEGATIVE_INFINITY;

  const mapState = (s: StreamConnectionState): StreamStatus =>
    s === 'connected'
      ? 'connected'
      : s === 'connecting'
        ? 'connecting'
        : 'disconnected';

  return getStreamClient().subscribeCandles(sub, {
    onSnapshot: msg => {
      for (const c of msg.candles) {
        if (Date.parse(c.timestamp) > cutoff) onCandle(c, true);
      }
    },
    onCandle: msg => {
      onCandle(msg.candle, msg.is_final);
    },
    onConnectionChange: state => {
      onStatus?.(mapState(state));
    },
    onStatus: msg => {
      if (msg.state === 'closed') onStatus?.('disconnected');
      else if (msg.state === 'reconnecting') onStatus?.('connecting');
      else onStatus?.('connected');
    },
  });
}
