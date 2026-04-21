// frontend/src/lib/drawables/placement/range.test.ts
import { describe, it, expect } from 'vitest';
import { rangePlacement } from './range';

describe('rangePlacement', () => {
  it('starts placement on pointerDown and exposes preview', () => {
    const m = rangePlacement();
    m.onPointerDown({ time: 10, price: 100 });
    expect(m.preview?.geometry).toEqual({
      startTime: 10,
      startPrice: 100,
      endTime: 10,
      endPrice: 100,
    });
  });

  it('updates preview on pointerMove without completing', () => {
    const m = rangePlacement();
    let completed = false;
    m.onComplete(() => (completed = true));

    m.onPointerDown({ time: 10, price: 100 });
    m.onPointerMove({ time: 20, price: 150 });

    expect(m.preview?.geometry).toEqual({
      startTime: 10,
      startPrice: 100,
      endTime: 20,
      endPrice: 150,
    });
    expect(completed).toBe(false);
    expect(m.done).toBe(false);
  });

  it('completes on pointerUp with the final geometry', () => {
    const m = rangePlacement();
    let received: unknown = null;
    m.onComplete(g => (received = g));

    m.onPointerDown({ time: 10, price: 100 });
    m.onPointerMove({ time: 20, price: 150 });
    m.onPointerUp({ time: 25, price: 160 });

    expect(received).toEqual({
      startTime: 10,
      startPrice: 100,
      endTime: 25,
      endPrice: 160,
    });
    expect(m.done).toBe(true);
    expect(m.preview).toBeNull();
  });

  it('ignores events until pointerDown', () => {
    const m = rangePlacement();
    m.onPointerMove({ time: 1, price: 1 });
    m.onPointerUp({ time: 2, price: 2 });
    expect(m.preview).toBeNull();
    expect(m.done).toBe(false);
  });

  it('cancel clears preview and marks done without invoking callback', () => {
    const m = rangePlacement();
    let invoked = false;
    m.onComplete(() => (invoked = true));
    m.onPointerDown({ time: 10, price: 100 });
    m.cancel();
    expect(m.preview).toBeNull();
    expect(m.done).toBe(true);
    expect(invoked).toBe(false);
  });
});
