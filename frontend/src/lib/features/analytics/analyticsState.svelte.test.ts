import { describe, it, expect, vi, afterEach } from 'vitest';
import { flushSync } from 'svelte';
import {
  AnalyticsState,
  type AnalyticsResult,
  loadCorrelationBenchmarksFromStorage,
  persistCorrelationBenchmarks,
} from './analyticsState.svelte';
import type { MetricId } from './metrics';
import type { ScalarMetricResponse } from './analyticsApi';

function makeLocalStorageStub(): Storage {
  const store = new Map<string, string>();
  return {
    get length() {
      return store.size;
    },
    clear: () => store.clear(),
    getItem: (k: string) => store.get(k) ?? null,
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    removeItem: (k: string) => {
      store.delete(k);
    },
    setItem: (k: string, v: string) => {
      store.set(k, v);
    },
  };
}

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

  it('correlationBenchmarks defaults to SPY,QQQ', () => {
    const { state } = makeState();
    expect(state.correlationBenchmarks).toEqual(['SPY', 'QQQ']);
  });

  it('addBenchmark normalizes case, dedupes, and refetches when enabled', async () => {
    const { state } = makeState();
    const calls: string[][] = [];
    state.fetchers = {
      ...state.fetchers,
      correlation: vi.fn(async (s: string): Promise<AnalyticsResult> => {
        calls.push([...state.correlationBenchmarks]);
        return {
          kind: 'correlation',
          data: { symbol: s, metric: 'correlation', rows: [] },
        };
      }),
    };
    state.toggle('correlation');
    await state.refresh('AAPL');
    state.addBenchmark('msft');
    await vi.waitFor(() =>
      expect(calls[calls.length - 1]).toEqual(['SPY', 'QQQ', 'MSFT']),
    );
    // duplicate is a no-op
    const before = calls.length;
    state.addBenchmark('MSFT');
    flushSync();
    expect(calls.length).toBe(before);
  });

  it('removeBenchmark drops the symbol and refetches', async () => {
    const { state } = makeState();
    const calls: string[][] = [];
    state.fetchers = {
      ...state.fetchers,
      correlation: vi.fn(async (s: string): Promise<AnalyticsResult> => {
        calls.push([...state.correlationBenchmarks]);
        return {
          kind: 'correlation',
          data: { symbol: s, metric: 'correlation', rows: [] },
        };
      }),
    };
    state.toggle('correlation');
    await state.refresh('AAPL');
    state.removeBenchmark('SPY');
    await vi.waitFor(() => expect(calls[calls.length - 1]).toEqual(['QQQ']));
  });

  it('empty benchmark list yields synthetic empty rows without fetching', async () => {
    const { state } = makeState();
    let fetchCount = 0;
    state.fetchers = {
      ...state.fetchers,
      correlation: vi.fn(async (s: string): Promise<AnalyticsResult> => {
        fetchCount += 1;
        return {
          kind: 'correlation',
          data: { symbol: s, metric: 'correlation', rows: [] },
        };
      }),
    };
    state.toggle('correlation');
    await state.refresh('AAPL');
    expect(fetchCount).toBe(1);
    state.setCorrelationBenchmarks([]);
    flushSync();
    expect(state.correlationBenchmarks).toEqual([]);
    expect(fetchCount).toBe(1); // no extra fetch
    const result = state.results.correlation;
    expect(result?.kind).toBe('correlation');
    if (result?.kind === 'correlation') {
      expect(result.data.rows).toEqual([]);
    }
  });

  it('benchmark change preserves the previous result while refetching', async () => {
    const { state } = makeState();
    let release!: () => void;
    state.fetchers = {
      ...state.fetchers,
      correlation: vi.fn((s: string) => {
        return new Promise<AnalyticsResult>(resolve => {
          release = () =>
            resolve({
              kind: 'correlation',
              data: {
                symbol: s,
                metric: 'correlation',
                rows: [{ benchmark: 'SPY', value: 0.5 }],
              },
            });
        });
      }),
    };
    state.toggle('correlation');
    const first = state.refresh('AAPL');
    release();
    await first;
    expect(state.results.correlation).not.toBeNull();
    state.addBenchmark('MSFT');
    // Still has the prior result while the new fetch is pending.
    expect(state.results.correlation).not.toBeNull();
  });

  it('setCorrelationBenchmarks with same list is a no-op', async () => {
    const { state } = makeState();
    let fetchCount = 0;
    state.fetchers = {
      ...state.fetchers,
      correlation: vi.fn(async (s: string): Promise<AnalyticsResult> => {
        fetchCount += 1;
        return {
          kind: 'correlation',
          data: { symbol: s, metric: 'correlation', rows: [] },
        };
      }),
    };
    state.toggle('correlation');
    await state.refresh('AAPL');
    expect(fetchCount).toBe(1);
    state.setCorrelationBenchmarks(['SPY', 'QQQ']);
    flushSync();
    expect(fetchCount).toBe(1);
  });

  it('invalidate clears cache and re-fetches enabled metrics', async () => {
    const { state, calls } = makeState();
    state.toggle('sharpe');
    await state.refresh('AAPL');
    state.invalidate();
    await vi.waitFor(() => expect(calls.sharpe).toEqual(['AAPL', 'AAPL']));
  });

  it('drops stale correlation result when benchmarks change mid-flight', async () => {
    const { state } = makeState();
    const releases: Array<(r: AnalyticsResult) => void> = [];
    state.fetchers = {
      ...state.fetchers,
      correlation: vi.fn(
        () =>
          new Promise<AnalyticsResult>(resolve => {
            releases.push(resolve);
          }),
      ),
    };
    state.toggle('correlation');
    // First fetch on refresh.
    const first = state.refresh('AAPL');
    // Add a benchmark — triggers a second fetch.
    state.addBenchmark('NVDA');
    // Resolve the second (newer) fetch first.
    releases[1]({
      kind: 'correlation',
      data: {
        symbol: 'AAPL',
        metric: 'correlation',
        rows: [
          { benchmark: 'SPY', value: 0.9 },
          { benchmark: 'QQQ', value: 0.8 },
          { benchmark: 'NVDA', value: 0.7 },
        ],
      },
    });
    // Then resolve the older fetch — its result must be discarded.
    releases[0]({
      kind: 'correlation',
      data: {
        symbol: 'AAPL',
        metric: 'correlation',
        rows: [
          { benchmark: 'SPY', value: 0.1 },
          { benchmark: 'QQQ', value: 0.2 },
        ],
      },
    });
    await first;
    flushSync();
    const result = state.results.correlation;
    expect(result?.kind).toBe('correlation');
    if (result?.kind === 'correlation') {
      expect(result.data.rows.map(r => r.benchmark)).toEqual([
        'SPY',
        'QQQ',
        'NVDA',
      ]);
    }
    expect(state.loading.correlation).toBe(false);
  });

  it('empty benchmark list with no symbol clears the cached result', async () => {
    const { state } = makeState();
    state.fetchers = {
      ...state.fetchers,
      correlation: vi.fn(
        async (s: string): Promise<AnalyticsResult> => ({
          kind: 'correlation',
          data: {
            symbol: s,
            metric: 'correlation',
            rows: [{ benchmark: 'SPY', value: 0.5 }],
          },
        }),
      ),
    };
    state.toggle('correlation');
    await state.refresh('AAPL');
    expect(state.results.correlation).not.toBeNull();
    // Drop the symbol manually to simulate the no-symbol case.
    state.symbol = null;
    state.setCorrelationBenchmarks([]);
    flushSync();
    expect(state.correlationBenchmarks).toEqual([]);
    expect(state.results.correlation).toBeNull();
  });
});

describe('correlation benchmark persistence', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('loads from localStorage when present', () => {
    const stub = makeLocalStorageStub();
    stub.setItem(
      'opentrade:analytics:correlationBenchmarks',
      JSON.stringify(['IWM', 'DIA']),
    );
    vi.stubGlobal('localStorage', stub);
    expect(loadCorrelationBenchmarksFromStorage()).toEqual(['IWM', 'DIA']);
    const state = new AnalyticsState();
    expect(state.correlationBenchmarks).toEqual(['IWM', 'DIA']);
  });

  it('returns null when storage is empty or invalid', () => {
    vi.stubGlobal('localStorage', makeLocalStorageStub());
    expect(loadCorrelationBenchmarksFromStorage()).toBeNull();
    const state = new AnalyticsState();
    expect(state.correlationBenchmarks).toEqual(['SPY', 'QQQ']);
  });

  it('honours an explicitly-empty stored list', () => {
    const stub = makeLocalStorageStub();
    stub.setItem(
      'opentrade:analytics:correlationBenchmarks',
      JSON.stringify([]),
    );
    vi.stubGlobal('localStorage', stub);
    const state = new AnalyticsState();
    expect(state.correlationBenchmarks).toEqual([]);
  });

  it('setCorrelationBenchmarks persists the normalized list', () => {
    const stub = makeLocalStorageStub();
    vi.stubGlobal('localStorage', stub);
    const state = new AnalyticsState();
    state.setCorrelationBenchmarks(['msft', 'nvda', 'MSFT']);
    expect(stub.getItem('opentrade:analytics:correlationBenchmarks')).toBe(
      JSON.stringify(['MSFT', 'NVDA']),
    );
  });

  it('persistCorrelationBenchmarks writes through safeLocalStorageSet', () => {
    const stub = makeLocalStorageStub();
    vi.stubGlobal('localStorage', stub);
    persistCorrelationBenchmarks(['GLD', 'TLT']);
    expect(stub.getItem('opentrade:analytics:correlationBenchmarks')).toBe(
      JSON.stringify(['GLD', 'TLT']),
    );
  });
});
