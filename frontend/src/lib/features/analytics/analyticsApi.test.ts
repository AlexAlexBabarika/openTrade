import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  fetchSharpe,
  fetchSortino,
  fetchMaxDrawdown,
  fetchVaR,
  fetchVariance,
  fetchStdev,
  fetchSkewness,
  fetchKurtosis,
  fetchCorrelation,
  fetchVolatilityClustering,
  fetchHurst,
  fetchReturnDistribution,
} from './analyticsApi';

type Call = { url: string; init: RequestInit | undefined };

function mockFetch(payload: unknown, calls: Call[]): typeof fetch {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ url: String(input), init });
    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    });
  }) as unknown as typeof fetch;
}

describe('analyticsApi', () => {
  let calls: Call[];

  beforeEach(() => {
    calls = [];
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('fetchSharpe builds URL with symbol and parses scalar', async () => {
    const payload = { symbol: 'AAPL', metric: 'sharpe', value: 1.42, n: 252 };
    vi.stubGlobal('fetch', mockFetch(payload, calls));

    const result = await fetchSharpe('AAPL');

    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe('/data/analytics/sharpe?symbol=AAPL');
    expect(result).toEqual(payload);
  });

  it('fetchSharpe forwards rf when provided', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch({ symbol: 'AAPL', metric: 'sharpe', value: 1, n: 10 }, calls),
    );
    await fetchSharpe('AAPL', 0.05);
    expect(calls[0].url).toBe('/data/analytics/sharpe?symbol=AAPL&rf=0.05');
  });

  it('fetchSortino forwards rf when provided', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch({ symbol: 'A', metric: 'sortino', value: 2, n: 10 }, calls),
    );
    await fetchSortino('A', 0.01);
    expect(calls[0].url).toBe('/data/analytics/sortino?symbol=A&rf=0.01');
  });

  it('fetchMaxDrawdown parses series', async () => {
    const payload = {
      symbol: 'AAPL',
      metric: 'max_drawdown',
      max_drawdown: -0.34,
      series: [{ timestamp: '2024-01-01T00:00:00Z', value: -0.05 }],
    };
    vi.stubGlobal('fetch', mockFetch(payload, calls));

    const result = await fetchMaxDrawdown('AAPL');

    expect(calls[0].url).toBe('/data/analytics/max_drawdown?symbol=AAPL');
    expect(result).toEqual(payload);
    expect(result.series[0].timestamp).toBe('2024-01-01T00:00:00Z');
  });

  it('fetchVaR parses both percentiles', async () => {
    const payload = {
      symbol: 'AAPL',
      metric: 'var',
      var_95: -0.021,
      var_99: -0.038,
      n: 252,
    };
    vi.stubGlobal('fetch', mockFetch(payload, calls));

    const result = await fetchVaR('AAPL');

    expect(calls[0].url).toBe('/data/analytics/var?symbol=AAPL');
    expect(result.var_95).toBe(-0.021);
    expect(result.var_99).toBe(-0.038);
  });

  it.each([
    ['variance', fetchVariance],
    ['stdev', fetchStdev],
    ['skewness', fetchSkewness],
    ['kurtosis', fetchKurtosis],
    ['hurst', fetchHurst],
  ] as const)('fetch%s targets the right endpoint', async (name, fn) => {
    const payload = { symbol: 'X', metric: name, value: 1, n: 5 };
    vi.stubGlobal('fetch', mockFetch(payload, calls));
    const result = await fn('X');
    expect(calls[0].url).toBe(`/data/analytics/${name}?symbol=X`);
    expect(result).toEqual(payload);
  });

  it('fetchCorrelation joins benchmarks with comma', async () => {
    const payload = {
      symbol: 'AAPL',
      metric: 'correlation',
      rows: [
        { benchmark: 'SPY', value: 0.81 },
        { benchmark: 'QQQ', value: 0.92 },
      ],
    };
    vi.stubGlobal('fetch', mockFetch(payload, calls));

    const result = await fetchCorrelation('AAPL', ['SPY', 'QQQ']);

    expect(calls[0].url).toBe(
      '/data/analytics/correlation?symbol=AAPL&benchmarks=SPY%2CQQQ',
    );
    expect(result.rows).toHaveLength(2);
  });

  it('fetchCorrelation omits benchmarks when not provided', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch({ symbol: 'AAPL', metric: 'correlation', rows: [] }, calls),
    );
    await fetchCorrelation('AAPL');
    expect(calls[0].url).toBe('/data/analytics/correlation?symbol=AAPL');
  });

  it('fetchVolatilityClustering forwards lag', async () => {
    const payload = {
      symbol: 'AAPL',
      metric: 'volatility_clustering',
      lag: 20,
      q: 41.2,
      p_value: 1e-5,
    };
    vi.stubGlobal('fetch', mockFetch(payload, calls));

    const result = await fetchVolatilityClustering('AAPL', 20);

    expect(calls[0].url).toBe(
      '/data/analytics/volatility_clustering?symbol=AAPL&lag=20',
    );
    expect(result.q).toBe(41.2);
  });

  it('fetchReturnDistribution forwards bins', async () => {
    const payload = {
      symbol: 'AAPL',
      metric: 'return_distribution',
      bins: [{ left: -0.05, right: -0.045, count: 3 }],
    };
    vi.stubGlobal('fetch', mockFetch(payload, calls));

    const result = await fetchReturnDistribution('AAPL', 50);

    expect(calls[0].url).toBe(
      '/data/analytics/return_distribution?symbol=AAPL&bins=50',
    );
    expect(result.bins).toHaveLength(1);
  });

  it('throws on non-2xx response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: 'no cache' }), {
            status: 404,
            headers: { 'content-type': 'application/json' },
          }),
      ) as unknown as typeof fetch,
    );

    await expect(fetchSharpe('AAPL')).rejects.toThrow(/no cache/);
  });
});
