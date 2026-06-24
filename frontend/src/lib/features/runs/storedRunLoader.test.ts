import { describe, it, expect, vi } from 'vitest';
import { storedRunLoader } from './storedRunLoader';

describe('storedRunLoader', () => {
  it('returns a loader that fetches the run by id', async () => {
    const getRun = vi.fn().mockResolvedValue({ meta: { run_id: 'x' } });
    const loader = storedRunLoader('x', { getRun } as never);
    expect(await loader()).toEqual({ meta: { run_id: 'x' } });
    expect(getRun).toHaveBeenCalledWith('x');
  });
});
