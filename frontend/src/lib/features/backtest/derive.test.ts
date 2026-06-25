import { describe, it, expect } from 'vitest';
import sampleRun from './fixtures/sample-run.json';
import { loadResult } from './loadResult';
import {
  benchmarkCurve,
  drawdownEpisodes,
  monthlyReturns,
  monthlyReturnsGrid,
  topDrawdowns,
  underwaterSeries,
  yearlyReturns,
} from './derive';
import type { EquityPoint } from './types';

const result = loadResult(sampleRun);

// equity points walked by the derivations, with explicit values for the
// hand-computed cases below.
const eq = (t: number, value: number): EquityPoint => ({
  t,
  value,
  cash: value,
  holdings: 0,
});

describe('drawdownEpisodes', () => {
  it('matches a hand-computed peak/trough/recovery', () => {
    // peak 100 -> trough 80 (-20%) -> recovers at 100, then ends mid-drawdown.
    const curve = [
      eq(0, 100),
      eq(1, 90),
      eq(2, 80),
      eq(3, 100), // recovery
      eq(4, 95), // open drawdown to the end
    ];
    const episodes = drawdownEpisodes(curve);
    expect(episodes).toHaveLength(2);
    expect(episodes[0]).toMatchObject({
      start: 0,
      trough: 2,
      recovery: 3,
      length: 3,
    });
    expect(episodes[0].depth).toBeCloseTo(-0.2, 12);
    expect(episodes[1].recovery).toBeNull();
    expect(episodes[1].depth).toBeCloseTo(-0.05, 12);
  });

  it("deepest episode depth reconciles with the blob's max_drawdown", () => {
    const episodes = drawdownEpisodes(result.equity);
    const deepest = Math.min(...episodes.map(e => e.depth));
    expect(deepest).toBeCloseTo(result.metrics.max_drawdown, 10);
  });
});

describe('topDrawdowns', () => {
  it('returns at most n, deepest first', () => {
    const top = topDrawdowns(result.equity, 10);
    expect(top.length).toBeGreaterThan(0);
    expect(top.length).toBeLessThanOrEqual(10);
    for (let i = 1; i < top.length; i++) {
      expect(top[i].depth).toBeGreaterThanOrEqual(top[i - 1].depth);
    }
    expect(top[0].depth).toBeCloseTo(result.metrics.max_drawdown, 10);
  });
});

describe('underwaterSeries', () => {
  it('is bar-aligned, never positive, and bottoms at max_drawdown', () => {
    const uw = underwaterSeries(result.equity);
    expect(uw).toHaveLength(result.equity.length);
    expect(Math.max(...uw.map(p => p.value))).toBeLessThanOrEqual(0);
    const trough = Math.min(...uw.map(p => p.value));
    expect(trough).toBeCloseTo(result.metrics.max_drawdown, 10);
  });
});

describe('benchmarkCurve', () => {
  it('starts at the strategy starting equity and tracks close ratio', () => {
    const start = result.equity[0].value;
    const bench = benchmarkCurve(result.bars, start);
    expect(bench).toHaveLength(result.bars.length);
    expect(bench[0].value).toBeCloseTo(start, 6);
    const lastBar = result.bars[result.bars.length - 1];
    const last = start * (lastBar.close / result.bars[0].close);
    expect(bench[bench.length - 1].value).toBeCloseTo(last, 6);
  });
});

describe('monthly/yearly returns', () => {
  it('best/worst month reconcile with the blob metrics', () => {
    const months = monthlyReturns(result.equity).map(m => m.ret);
    expect(Math.max(...months)).toBeCloseTo(result.metrics.best_month!, 10);
    expect(Math.min(...months)).toBeCloseTo(result.metrics.worst_month!, 10);
  });

  it('best/worst year reconcile with the blob metrics', () => {
    const years = yearlyReturns(result.equity).map(y => y.ret);
    expect(Math.max(...years)).toBeCloseTo(result.metrics.best_year!, 10);
    expect(Math.min(...years)).toBeCloseTo(result.metrics.worst_year!, 10);
  });

  it('grid exposes one row per year with 12 month cells', () => {
    const grid = monthlyReturnsGrid(result.equity);
    expect(grid.years.length).toBeGreaterThan(0);
    for (const y of grid.years) {
      expect(grid.cells[y]).toHaveLength(12);
      expect(grid.yearTotals[y]).toBeTypeOf('number');
    }
  });
});
