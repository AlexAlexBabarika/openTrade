import { describe, it, expect, vi } from 'vitest';
import {
  PortfolioState,
  toPortfolioRunResponse,
} from './portfolioState.svelte';

function storedBlob() {
  return {
    meta: {
      run_id: 'abc',
      engine_version: '1.0.0',
      seed: 0,
      strategy_id: null,
    },
    params: {},
    config: { starting_cash: 1e5 },
    symbols: ['AAPL', 'MSFT'],
    bars: {
      AAPL: [{ t: 1577836800, open: 1, high: 1, low: 1, close: 1, volume: 1 }],
      MSFT: [{ t: 1577836800, open: 2, high: 2, low: 2, close: 2, volume: 2 }],
    },
    orders: [],
    fills: [],
    equity: [],
    trades: [],
    log: [{ t: 1577836800, constraint: 'max_gross', symbol: null }],
    metrics: { portfolio: { total_return: 0.1 } },
  };
}

describe('toPortfolioRunResponse', () => {
  it('maps a stored blob into a PortfolioRunResponse', () => {
    const r = toPortfolioRunResponse(storedBlob());
    expect(r.status).toBe('ok');
    expect(r.symbols).toEqual(['AAPL', 'MSFT']);
    expect(Object.keys(r.bars)).toEqual(['AAPL', 'MSFT']);
    expect(r.constraint_events).toHaveLength(1); // mapped from `log`
    expect(r.metrics.portfolio.total_return).toBe(0.1);
  });

  it('rejects a single-symbol blob (bars is an array)', () => {
    const single = {
      ...storedBlob(),
      bars: [{ t: 1, open: 1, high: 1, low: 1, close: 1, volume: 1 }],
    };
    expect(() => toPortfolioRunResponse(single)).toThrow(/not a portfolio run/);
  });
});

describe('PortfolioState.loadStored', () => {
  it('fetches by id and populates response', async () => {
    const getRun = vi.fn().mockResolvedValue(storedBlob());
    const s = new PortfolioState(undefined, { getRun } as never);
    await s.loadStored('abc');
    expect(getRun).toHaveBeenCalledWith('abc');
    expect(s.response?.meta.run_id).toBe('abc');
    expect(s.runError).toBeNull();
    expect(s.isRunning).toBe(false);
  });

  it('captures load errors in runError', async () => {
    const getRun = vi.fn().mockRejectedValue(new Error('run abc not found'));
    const s = new PortfolioState(undefined, { getRun } as never);
    await s.loadStored('abc');
    expect(s.response).toBeNull();
    expect(s.runError).toBe('run abc not found');
  });
});
