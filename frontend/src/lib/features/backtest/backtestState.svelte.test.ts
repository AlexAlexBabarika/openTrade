import { describe, it, expect } from 'vitest';
import sampleRun from './fixtures/sample-run.json';
import { BacktestState } from './backtestState.svelte';

function makeState() {
  return new BacktestState(async () => sampleRun);
}

describe('BacktestState.load', () => {
  it('loads and parses the blob through the injected loader', async () => {
    const s = makeState();
    await s.load();
    expect(s.loading).toBe(false);
    expect(s.error).toBeNull();
    expect(s.result?.trades.length).toBeGreaterThan(0);
  });

  it('is idempotent — a second load does not refetch', async () => {
    let calls = 0;
    const s = new BacktestState(async () => {
      calls++;
      return sampleRun;
    });
    await s.load();
    await s.load();
    expect(calls).toBe(1);
  });

  it('captures loader errors', async () => {
    const s = new BacktestState(async () => {
      throw new Error('boom');
    });
    await s.load();
    expect(s.result).toBeNull();
    expect(s.error).toBe('boom');
  });

  it('surfaces a structurally invalid blob as an error', async () => {
    const s = new BacktestState(async () => ({ nope: true }));
    await s.load();
    expect(s.result).toBeNull();
    expect(s.error).toMatch(/array "bars"/);
  });
});

describe('BacktestState interaction', () => {
  it('switches tabs', () => {
    const s = makeState();
    expect(s.activeTab).toBe('equity');
    s.setTab('trades');
    expect(s.activeTab).toBe('trades');
  });

  it('tracks the hovered trade for the marker↔row link', () => {
    const s = makeState();
    expect(s.hoveredTrade).toBeNull();
    s.hoverTrade(3);
    expect(s.hoveredTrade).toBe(3);
    s.hoverTrade(null);
    expect(s.hoveredTrade).toBeNull();
  });
});
