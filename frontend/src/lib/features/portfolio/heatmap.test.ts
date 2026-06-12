import { describe, it, expect } from 'vitest';
import { buildHeatmap } from './heatmap';
import type { PortfolioEquityPoint } from './types';

function point(
  t: number,
  weights: Record<string, number>,
): PortfolioEquityPoint {
  return { t, value: 1000, cash: 0, holdings: 1000, weights };
}

describe('buildHeatmap', () => {
  it('orders rows by peak |weight| and fills gaps with zero', () => {
    const data = buildHeatmap([
      point(1, { A: 0.2, B: -0.7 }),
      point(2, { A: 0.3 }),
    ]);
    expect(data.symbols).toEqual(['B', 'A']);
    expect(data.times).toEqual([1, 2]);
    expect(data.rows).toEqual([
      [-0.7, 0], // B drops out at t=2
      [0.2, 0.3],
    ]);
    expect(data.maxAbs).toBeCloseTo(0.7);
  });

  it('buckets long runs down to at most maxCols columns', () => {
    const equity = Array.from({ length: 1000 }, (_, i) =>
      point(i, { A: i / 1000 }),
    );
    const data = buildHeatmap(equity, 100);
    expect(data.times.length).toBeLessThanOrEqual(101);
    // Last bucket is always the final point.
    expect(data.times[data.times.length - 1]).toBe(999);
    expect(data.rows[0][data.rows[0].length - 1]).toBeCloseTo(0.999);
  });

  it('handles empty and flat runs', () => {
    expect(buildHeatmap([])).toEqual({
      symbols: [],
      times: [],
      rows: [],
      maxAbs: 0,
    });
    const flat = buildHeatmap([point(1, {})]);
    expect(flat.symbols).toEqual([]);
    expect(flat.maxAbs).toBe(0);
  });
});
