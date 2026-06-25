import { describe, it, expect, vi } from 'vitest';
import { CompareState } from './compareState.svelte';
import type { RunDiff } from './runTypes';

const DIFF = {
  inputs_diff: [],
  metrics_diff: [],
  equity_overlay: { a: [], b: [], residual: [] },
  trades_diff: { changed: [], unchanged: [], only_in_a: [], only_in_b: [] },
  status: {
    a: { stale: false, recorded: '1', current: '1' },
    b: { stale: false, recorded: '1', current: '1' },
  },
} as RunDiff;

describe('CompareState', () => {
  it('load() fetches and stores the diff', async () => {
    const compareRuns = vi.fn().mockResolvedValue(DIFF);
    const s = new CompareState({ compareRuns } as never);
    await s.load('a', 'b');
    expect(compareRuns).toHaveBeenCalledWith('a', 'b');
    expect(s.diff).toEqual(DIFF);
    expect(s.a).toBe('a');
    expect(s.error).toBeNull();
  });

  it('setDiff stores without fetching', () => {
    const compareRuns = vi.fn();
    const s = new CompareState({ compareRuns } as never);
    s.setDiff('a', 'b', DIFF);
    expect(compareRuns).not.toHaveBeenCalled();
    expect(s.diff).toEqual(DIFF);
  });

  it('load() captures errors', async () => {
    const s = new CompareState({
      compareRuns: vi.fn().mockRejectedValue(new Error('nope')),
    } as never);
    await s.load('a', 'b');
    expect(s.error).toBe('nope');
    expect(s.diff).toBeNull();
  });
});
