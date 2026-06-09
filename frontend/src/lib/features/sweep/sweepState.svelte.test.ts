import { describe, it, expect, vi } from 'vitest';
import { SweepState } from './sweepState.svelte';
import type { ParamSchema, SweepClient, SweepProgress } from './types';

function progress(over: Partial<SweepProgress> = {}): SweepProgress {
  return {
    sweep_id: 's1',
    status: 'running',
    total: 4,
    done: 0,
    trials: [],
    best_trial_id: null,
    error: null,
    result: null,
    ...over,
  };
}

function fakeClient(polls: SweepProgress[]): SweepClient {
  let i = 0;
  return {
    schema: vi.fn(
      async (): Promise<ParamSchema> => ({
        qty: { kind: 'int', low: 1, high: 4, step: 1 },
      }),
    ),
    start: vi.fn(async () => ({ sweep_id: 's1' })),
    poll: vi.fn(async () => polls[Math.min(i++, polls.length - 1)]),
    cancel: vi.fn(async () => undefined),
    loadTrial: vi.fn(async () => ({}) as never),
  };
}

describe('SweepState', () => {
  it('starts a sweep then polls to completion', async () => {
    const done = progress({
      status: 'done',
      done: 4,
      best_trial_id: 2,
      trials: [
        {
          trial_id: 2,
          params: { qty: 3 },
          metrics: { sharpe: 1.2 },
          cached: false,
        },
      ],
      result: {
        sweep_id: 's1',
        config: {} as never,
        trials: [],
        best_trial_id: 2,
      },
    });
    const client = fakeClient([progress({ done: 2 }), done]);
    const state = new SweepState(client, 0); // 0ms poll interval for the test

    await state.run({
      code: 'x',
      symbol: 'TEST',
      provider: 'yfinance',
      search: 'grid',
      metric: 'sharpe',
      vary: ['qty'],
    });

    expect(client.start).toHaveBeenCalledOnce();
    expect(state.status).toBe('done');
    expect(state.bestTrialId).toBe(2);
    expect(state.trials).toHaveLength(1);
  });

  it('records an error status', async () => {
    const client = fakeClient([progress({ status: 'error', error: 'boom' })]);
    const state = new SweepState(client, 0);
    await state.run({
      code: 'x',
      symbol: 'TEST',
      provider: 'yfinance',
      search: 'grid',
      metric: 'sharpe',
      vary: ['qty'],
    });
    expect(state.status).toBe('error');
    expect(state.error).toBe('boom');
  });
});
