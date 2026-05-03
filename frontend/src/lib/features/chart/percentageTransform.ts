import type { OHLCVCandle } from '$lib/core/types';

/**
 * Find the close of the first candle whose timestamp is >= leftEdgeMs.
 * Returns null when no candle in the series overlaps the visible range.
 * Assumes `candles` is sorted ascending by timestamp.
 */
export function computeBase(
  candles: readonly OHLCVCandle[],
  leftEdgeMs: number,
): number | null {
  for (const c of candles) {
    const t = Date.parse(c.timestamp);
    if (Number.isFinite(t) && t >= leftEdgeMs) {
      return c.close;
    }
  }
  return null;
}

export function percent(value: number, base: number): number {
  return (value / base - 1) * 100;
}

/** Transform OHLCV candles in-place values: each OHLC re-based to `base` (close-of-base = 0%). */
export function transformCandles(
  candles: readonly OHLCVCandle[],
  base: number,
): OHLCVCandle[] {
  if (!Number.isFinite(base) || base === 0) return [];
  return candles.map(c => ({
    ...c,
    open: percent(c.open, base),
    high: percent(c.high, base),
    low: percent(c.low, base),
    close: percent(c.close, base),
  }));
}

export interface LinePoint {
  timestamp: string;
  value: number;
}

/** Project candles to {timestamp, value=close%} points for a LineSeries. */
export function transformLine(
  candles: readonly OHLCVCandle[],
  base: number,
): LinePoint[] {
  if (!Number.isFinite(base) || base === 0) return [];
  return candles.map(c => ({
    timestamp: c.timestamp,
    value: percent(c.close, base),
  }));
}
