import { describe, it, expect } from 'vitest';
import {
  RunsHistory,
  MAX_RUNS,
  type RunHistoryEntry,
} from './runsHistory.svelte';

function memStorage(): Storage {
  const m = new Map<string, string>();
  return {
    getItem: k => m.get(k) ?? null,
    setItem: (k, v) => void m.set(k, v),
    removeItem: k => void m.delete(k),
    clear: () => m.clear(),
    key: () => null,
    length: 0,
  } as Storage;
}

const entry = (id: string): RunHistoryEntry => ({
  run_id: id,
  kind: 'single',
  label: `L${id}`,
  created_at: '2026-01-01T00:00:00Z',
});

describe('RunsHistory', () => {
  it('records newest-first and de-dupes by run_id', () => {
    const h = new RunsHistory(memStorage());
    h.record(entry('a'));
    h.record(entry('b'));
    h.record(entry('a'));
    expect(h.entries.map(e => e.run_id)).toEqual(['a', 'b']);
  });

  it('caps at MAX_RUNS', () => {
    const h = new RunsHistory(memStorage());
    for (let i = 0; i < MAX_RUNS + 10; i++) h.record(entry(`r${i}`));
    expect(h.entries.length).toBe(MAX_RUNS);
    expect(h.entries[0].run_id).toBe(`r${MAX_RUNS + 9}`);
  });

  it('persists and reloads from storage', () => {
    const s = memStorage();
    new RunsHistory(s).record(entry('a'));
    expect(new RunsHistory(s).entries.map(e => e.run_id)).toEqual(['a']);
  });

  it('remove drops by id', () => {
    const h = new RunsHistory(memStorage());
    h.record(entry('a'));
    h.remove('a');
    expect(h.entries).toEqual([]);
  });

  it('falls back to in-memory when storage throws', () => {
    const bad = {
      getItem: () => {
        throw new Error('blocked');
      },
      setItem: () => {
        throw new Error('blocked');
      },
    } as unknown as Storage;
    const h = new RunsHistory(bad);
    expect(() => h.record(entry('a'))).not.toThrow();
    expect(h.entries.map(e => e.run_id)).toEqual(['a']);
  });
});
