import type { OHLCVCandle } from './types';

/** FNV-1a 32-bit; hex digest for logging / keys (not cryptographic). */
export function fnv1a32Hex(s: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16);
}

/**
 * Fingerprint of the full candle series: any change to any bar’s OHLCV or
 * timestamp changes the result. Used in drawable `compute` `workKey` so we
 * do not skip work when only the array reference changes.
 */
export function candleBatchSignature(cs: OHLCVCandle[]): string {
  if (cs.length === 0) return '0';
  const rows: string[] = new Array(cs.length);
  for (let i = 0; i < cs.length; i++) {
    const c = cs[i];
    rows[i] =
      `${c.timestamp}\x1f${c.open}\x1f${c.high}\x1f${c.low}\x1f${c.close}\x1f${c.volume}`;
  }
  return `${cs.length}:${fnv1a32Hex(rows.join('\x1e'))}`;
}
