import { describe, it, expect } from 'vitest';
import { candleBatchSignature } from './candleFingerprint';
import type { OHLCVCandle } from './types';

const base = (overrides: Partial<OHLCVCandle> = {}): OHLCVCandle => ({
  symbol: 'X',
  timestamp: '2024-01-01T00:00:00.000Z',
  open: 1,
  high: 2,
  low: 0.5,
  close: 1.5,
  volume: 100,
  ...overrides,
});

describe('candleBatchSignature', () => {
  it('is stable for same data with different array identity', () => {
    const a = [base()];
    const b = [base()];
    expect(candleBatchSignature(a)).toBe(candleBatchSignature(b));
  });

  it('changes when any bar field changes', () => {
    const a = candleBatchSignature([base()]);
    const b = candleBatchSignature([base({ close: 1.51 })]);
    expect(a).not.toBe(b);
  });
});
