import { describe, it, expect } from 'vitest';
import type { OHLCVCandle } from '$lib/core/types';
import {
  computeBase,
  percent,
  transformCandles,
  transformLine,
} from './percentageTransform';

const c = (
  ts: string,
  o: number,
  h: number,
  l: number,
  cl: number,
): OHLCVCandle => ({
  symbol: 'X',
  timestamp: ts,
  open: o,
  high: h,
  low: l,
  close: cl,
  volume: 0,
});

describe('computeBase', () => {
  const candles = [
    c('2026-01-01T00:00:00Z', 10, 11, 9, 10),
    c('2026-01-02T00:00:00Z', 10, 12, 9, 11),
    c('2026-01-03T00:00:00Z', 11, 13, 10, 12),
  ];

  it('returns close of first candle when left edge precedes all', () => {
    expect(computeBase(candles, Date.parse('2025-12-01T00:00:00Z'))).toBe(10);
  });

  it('returns close at exact left-edge timestamp', () => {
    expect(computeBase(candles, Date.parse('2026-01-02T00:00:00Z'))).toBe(11);
  });

  it('returns close of next candle when left edge is between candles', () => {
    expect(computeBase(candles, Date.parse('2026-01-01T12:00:00Z'))).toBe(11);
  });

  it('returns null when left edge is after every candle', () => {
    expect(computeBase(candles, Date.parse('2027-01-01T00:00:00Z'))).toBeNull();
  });

  it('returns null for empty array', () => {
    expect(computeBase([], 0)).toBeNull();
  });
});

describe('percent', () => {
  it('returns 0 at base', () => {
    expect(percent(100, 100)).toBe(0);
  });

  it('returns positive for higher value', () => {
    expect(percent(110, 100)).toBeCloseTo(10, 10);
  });

  it('returns negative for lower value', () => {
    expect(percent(90, 100)).toBeCloseTo(-10, 10);
  });
});

describe('transformCandles', () => {
  it('rebases all OHLC fields against base', () => {
    const [out] = transformCandles(
      [c('2026-01-01T00:00:00Z', 100, 110, 90, 100)],
      100,
    );
    expect(out.open).toBeCloseTo(0, 10);
    expect(out.high).toBeCloseTo(10, 10);
    expect(out.low).toBeCloseTo(-10, 10);
    expect(out.close).toBeCloseTo(0, 10);
  });

  it('returns empty array when base is 0', () => {
    expect(
      transformCandles([c('2026-01-01T00:00:00Z', 1, 1, 1, 1)], 0),
    ).toEqual([]);
  });
});

describe('transformLine', () => {
  it('emits {timestamp,value=close%} points', () => {
    const out = transformLine(
      [
        c('2026-01-01T00:00:00Z', 0, 0, 0, 100),
        c('2026-01-02T00:00:00Z', 0, 0, 0, 120),
      ],
      100,
    );
    expect(out).toHaveLength(2);
    expect(out[0].timestamp).toBe('2026-01-01T00:00:00Z');
    expect(out[0].value).toBeCloseTo(0, 10);
    expect(out[1].timestamp).toBe('2026-01-02T00:00:00Z');
    expect(out[1].value).toBeCloseTo(20, 10);
  });

  it('returns [] for empty input', () => {
    expect(transformLine([], 100)).toEqual([]);
  });
});
