import { describe, it, expect } from 'vitest';
import {
  computeStats,
  formatPriceDelta,
  formatPct,
  formatVolume,
} from './compute';
import type { OHLCVCandle } from '../../../types';

function candle(tsIso: string, volume: number): OHLCVCandle {
  return {
    timestamp: tsIso,
    open: 1,
    high: 1,
    low: 1,
    close: 1,
    volume,
  } as OHLCVCandle;
}

describe('ruler computeStats', () => {
  it('sums volume for candles inside the range (inclusive)', () => {
    const t0 = new Date('2024-01-01T00:00:00Z').getTime() / 1000;
    const candles = [
      candle('2024-01-01T00:00:00Z', 10),
      candle('2024-01-01T01:00:00Z', 20),
      candle('2024-01-01T02:00:00Z', 30),
    ];
    const stats = computeStats(
      { startTime: t0, endTime: t0 + 3600, startPrice: 100, endPrice: 110 },
      candles,
    );
    expect(stats.barCount).toBe(2);
    expect(stats.volumeSum).toBe(30);
    expect(stats.priceDelta).toBe(10);
    expect(stats.pctDelta).toBeCloseTo(10);
    expect(stats.isUp).toBe(true);
  });

  it('marks negative price movement as not up', () => {
    const s = computeStats(
      { startTime: 0, endTime: 1, startPrice: 100, endPrice: 90 },
      [],
    );
    expect(s.isUp).toBe(false);
  });

  it('formats price delta with sign', () => {
    expect(formatPriceDelta(1.5)).toBe('+1.50');
    expect(formatPriceDelta(-1.5)).toBe('−1.50');
  });

  it('formats pct with sign', () => {
    expect(formatPct(2.5)).toBe('+2.50%');
    expect(formatPct(-2.5)).toBe('−2.50%');
  });

  it('formats volume with magnitude suffixes', () => {
    expect(formatVolume(1500)).toBe('1.50K');
    expect(formatVolume(1_500_000)).toBe('1.50M');
    expect(formatVolume(2_000_000_000)).toBe('2.00B');
    expect(formatVolume(999)).toBe('999');
  });
});
