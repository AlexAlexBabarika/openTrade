import { describe, it, expect, vi } from 'vitest';
import { PortfolioState } from './portfolioState.svelte';
import type { PortfolioClient, PortfolioRunResponse } from './portfolioClient';

function okRun(over: Partial<PortfolioRunResponse> = {}): PortfolioRunResponse {
  return {
    status: 'ok',
    meta: {},
    symbols: ['AAPL', 'MSFT'],
    bars: {},
    orders: [],
    fills: [],
    equity: [],
    trades: [],
    constraint_events: [],
    metrics: {},
    stdout: '',
    stderr: '',
    elapsed_ms: 1,
    ...over,
  } as PortfolioRunResponse;
}

function fakeClient(over: Partial<PortfolioClient> = {}): PortfolioClient {
  return {
    run: vi.fn(async () => okRun()),
    ...over,
  };
}

const CTX = { provider: 'yfinance', period: '1y', interval: '1d' } as const;

describe('PortfolioState', () => {
  it('builds the universe from pasted text and removes symbols', () => {
    const state = new PortfolioState(fakeClient());
    state.add('aapl, msft goog');
    expect(state.symbols).toEqual(['AAPL', 'MSFT', 'GOOG']);
    state.remove('MSFT');
    expect(state.symbols).toEqual(['AAPL', 'GOOG']);
    state.clear();
    expect(state.symbols).toEqual([]);
  });

  it('refuses to run with an empty universe', async () => {
    const client = fakeClient();
    const state = new PortfolioState(client);
    await state.run('def on_bar(ctx): pass', CTX);
    expect(state.runError).toMatch(/at least one symbol/i);
    expect(client.run).not.toHaveBeenCalled();
  });

  it('sends the universe and stores a successful response', async () => {
    const client = fakeClient();
    const state = new PortfolioState(client);
    state.add('msft aapl');
    await state.run('def on_bar(ctx): pass', CTX);
    expect(client.run).toHaveBeenCalledWith(
      expect.objectContaining({
        symbols: ['MSFT', 'AAPL'],
        provider: 'yfinance',
      }),
    );
    expect(state.response?.status).toBe('ok');
    expect(state.runError).toBeNull();
    expect(state.isRunning).toBe(false);
  });

  it('surfaces sandbox failures as runError and keeps the last good run', async () => {
    const responses = [okRun(), okRun({ status: 'error', stderr: 'boom\n' })];
    const client = fakeClient({
      run: vi.fn(async () => responses.shift()!),
    });
    const state = new PortfolioState(client);
    state.add('AAPL');
    await state.run('code', CTX);
    const first = state.response;
    await state.run('code', CTX);
    expect(state.runError).toBe('boom');
    expect(state.response).toBe(first); // previous dashboard stays readable
  });

  it('includes constraints only when set', async () => {
    const client = fakeClient();
    const state = new PortfolioState(client);
    state.add('AAPL');
    state.constraints = { max_position_weight: 0.2 };
    await state.run('code', CTX);
    expect(client.run).toHaveBeenCalledWith(
      expect.objectContaining({
        constraints: { max_position_weight: 0.2 },
      }),
    );
  });
});
