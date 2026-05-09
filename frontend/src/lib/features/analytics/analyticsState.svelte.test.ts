import { describe, it, expect, vi } from 'vitest';
import { flushSync } from 'svelte';
import { AnalyticsState, type AnalyticsResult } from './analyticsState.svelte';
import type { MetricId } from './metrics';
import type { ScalarMetricResponse } from './analyticsApi';

function scalar(
  symbol: string,
  metric: MetricId,
  value: number,
): AnalyticsResult {
  const data: ScalarMetricResponse = { symbol, metric, value, n: 100 };
  return { kind: 'scalar', data };
}

function makeState() {
  const state = new AnalyticsState();
  const calls: Record<MetricId, string[]> = {} as Record<MetricId, string[]>;
  const fetchers = {} as typeof state.fetchers;
  for (const id of Object.keys(state.enabled) as MetricId[]) {
    calls[id] = [];
    fetchers[id] = vi.fn(async (symbol: string) => {
      calls[id].push(symbol);
      return scalar(symbol, id, 1);
    });
  }
  state.fetchers = fetchers;
  return { state, calls };
}

describe('AnalyticsState', () => {
  it('starts with everything disabled, no symbol, no results', () => {
    const { state } = makeState();
    flushSync();
    expect(state.symbol).toBeNull();
    expect(state.enabledIds).toEqual([]);
    expect(state.results.sharpe).toBeNull();
  });

  it('toggle without a symbol does not fetch', () => {
    const { state, calls } = makeState();
    state.toggle('sharpe');
    flushSync();
    expect(state.enabled.sharpe).toBe(true);
    expect(calls.sharpe).toEqual([]);
  });

  it('refresh fetches only enabled metrics for the new symbol', async () => {
    const { state, calls } = makeState();
    state.toggle('sharpe');
    state.toggle('variance');
    await state.refresh('AAPL');
    flushSync();
    expect(state.symbol).toBe('AAPL');
    expect(calls.sharpe).toEqual(['AAPL']);
    expect(calls.variance).toEqual(['AAPL']);
    expect(calls.sortino).toEqual([]);
    expect(state.results.sharpe?.kind).toBe('scalar');
    expect(state.errors.sharpe).toBeNull();
    expect(state.loading.sharpe).toBe(false);
  });

  it('refresh with same symbol skips metrics that already have cached results', async () => {
    const { state, calls } = makeState();
    state.toggle('sharpe');
    await state.refresh('AAPL');
    await state.refresh('AAPL');
    flushSync();
    expect(calls.sharpe).toEqual(['AAPL']);
  });

  it('refresh with new symbol invalidates cache and re-fetches', async () => {
    const { state, calls } = makeState();
    state.toggle('sharpe');
    await state.refresh('AAPL');
    await state.refresh('MSFT');
    flushSync();
    expect(calls.sharpe).toEqual(['AAPL', 'MSFT']);
    expect(state.symbol).toBe('MSFT');
    expect(state.results.sharpe?.data.symbol).toBe('MSFT');
  });

  it('toggling on after a symbol is set fetches immediately', async () => {
    const { state, calls } = makeState();
    await state.refresh('AAPL');
    state.toggle('sharpe');
    await vi.waitFor(() => expect(calls.sharpe).toEqual(['AAPL']));
  });

  it('toggling on does not refetch when a cached result exists for the current symbol', async () => {
    const { state, calls } = makeState();
    state.toggle('sharpe');
    await state.refresh('AAPL');
    state.toggle('sharpe');
    state.toggle('sharpe');
    flushSync();
    expect(calls.sharpe).toEqual(['AAPL']);
    expect(state.results.sharpe).not.toBeNull();
  });

  it('records errors per metric without affecting others', async () => {
    const { state } = makeState();
    state.fetchers = {
      ...state.fetchers,
      sharpe: vi.fn(async () => {
        throw new Error('boom');
      }),
    };
    state.toggle('sharpe');
    state.toggle('variance');
    await state.refresh('AAPL');
    flushSync();
    expect(state.errors.sharpe).toBe('boom');
    expect(state.results.sharpe).toBeNull();
    expect(state.errors.variance).toBeNull();
    expect(state.results.variance).not.toBeNull();
  });

  it('discards stale fetch results when symbol changes mid-flight', async () => {
    const { state } = makeState();
    let releaseAapl!: (r: AnalyticsResult) => void;
    state.fetchers = {
      ...state.fetchers,
      sharpe: vi.fn((symbol: string) => {
        if (symbol === 'AAPL') {
          return new Promise<AnalyticsResult>(resolve => {
            releaseAapl = resolve;
          });
        }
        return Promise.resolve(scalar(symbol, 'sharpe', 9));
      }),
    };
    state.toggle('sharpe');
    const first = state.refresh('AAPL');
    await state.refresh('MSFT');
    releaseAapl(scalar('AAPL', 'sharpe', 1));
    await first;
    flushSync();
    expect(state.symbol).toBe('MSFT');
    expect(state.results.sharpe?.data.symbol).toBe('MSFT');
  });

  it('invalidate clears cache and re-fetches enabled metrics', async () => {
    const { state, calls } = makeState();
    state.toggle('sharpe');
    await state.refresh('AAPL');
    state.invalidate();
    await vi.waitFor(() => expect(calls.sharpe).toEqual(['AAPL', 'AAPL']));
  });
});
