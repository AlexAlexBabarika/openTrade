import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  makeRunsClient,
  RunNotFoundError,
  RerunFailedError,
} from './runsClient';

function res(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

afterEach(() => vi.restoreAllMocks());

describe('runsClient', () => {
  it('getRun returns the blob on 200', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(res(200, { meta: { run_id: 'x' } }));
    const c = makeRunsClient(fetchImpl);
    const blob = (await c.getRun('x')) as { meta: { run_id: string } };
    expect(blob.meta.run_id).toBe('x');
    expect(fetchImpl).toHaveBeenCalledWith('/backtests/runs/x', {}, true);
  });

  it('getRun throws RunNotFoundError on 404', async () => {
    const c = makeRunsClient(
      vi.fn().mockResolvedValue(res(404, { detail: 'run x not found' })),
    );
    await expect(c.getRun('x')).rejects.toBeInstanceOf(RunNotFoundError);
  });

  it('compareRuns returns the diff on 200', async () => {
    const diff = {
      inputs_diff: [],
      metrics_diff: [],
      equity_overlay: { a: [], b: [], residual: [] },
      trades_diff: { changed: [], unchanged: [], only_in_a: [], only_in_b: [] },
      status: { a: {}, b: {} },
    };
    const c = makeRunsClient(vi.fn().mockResolvedValue(res(200, diff)));
    expect(await c.compareRuns('a', 'b')).toEqual(diff);
  });

  it('rerunRun throws RerunFailedError(message) on 422', async () => {
    const c = makeRunsClient(
      vi
        .fn()
        .mockResolvedValue(res(422, { detail: 'rerun failed (error): boom' })),
    );
    await expect(c.rerunRun('x')).rejects.toMatchObject({
      message: 'rerun failed (error): boom',
    });
  });
});
