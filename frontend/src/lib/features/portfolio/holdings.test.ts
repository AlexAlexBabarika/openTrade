import { describe, it, expect } from 'vitest';
import { buildHoldings } from './holdings';
import type { PortfolioMetrics, PortfolioEquityPoint } from './types';

function point(
  t: number,
  weights: Record<string, number>,
): PortfolioEquityPoint {
  return { t, value: 1000, cash: 0, holdings: 1000, weights };
}

function metrics(over: Partial<PortfolioMetrics> = {}): PortfolioMetrics {
  return {
    attribution_by_symbol: {},
    symbol_sharpes: {},
    ...over,
  } as PortfolioMetrics;
}

describe('buildHoldings', () => {
  it('joins final weights with attribution and sharpe, heaviest first', () => {
    const rows = buildHoldings({
      equity: [point(1, { A: 0.5, B: 0.1 }), point(2, { A: 0.2, B: 0.6 })],
      metrics: metrics({
        attribution_by_symbol: { A: 12, B: -3 },
        symbol_sharpes: { A: 1.1, B: 0.4 },
      }),
    });
    expect(rows.map(r => r.symbol)).toEqual(['B', 'A']); // final |w| ordering
    expect(rows[0]).toEqual({ symbol: 'B', weight: 0.6, pnl: -3, sharpe: 0.4 });
  });

  it('includes closed positions with zero weight but realized pnl', () => {
    const rows = buildHoldings({
      equity: [point(1, { A: 0.5 }), point(2, {})],
      metrics: metrics({ attribution_by_symbol: { A: 7 } }),
    });
    expect(rows).toEqual([{ symbol: 'A', weight: 0, pnl: 7, sharpe: null }]);
  });

  it('handles an empty run', () => {
    expect(buildHoldings({ equity: [], metrics: metrics() })).toEqual([]);
  });
});
