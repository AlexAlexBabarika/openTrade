// frontend/src/lib/drawables/placement/point.test.ts
import { describe, it, expect } from 'vitest';
import { pointPlacement } from './point';

describe('pointPlacement', () => {
  it('completes on pointerDown with the first point', () => {
    const m = pointPlacement();
    let received: { time: number; price: number } | null = null;
    m.onComplete(g => (received = g));

    m.onPointerDown({ time: 100, price: 50 });

    expect(received).toEqual({ time: 100, price: 50 });
    expect(m.done).toBe(true);
  });

  it('ignores further pointer events after completion', () => {
    const m = pointPlacement();
    let callCount = 0;
    m.onComplete(() => callCount++);
    m.onPointerDown({ time: 1, price: 1 });
    m.onPointerDown({ time: 2, price: 2 });
    m.onPointerMove({ time: 3, price: 3 });
    m.onPointerUp({ time: 4, price: 4 });
    expect(callCount).toBe(1);
  });

  it('preview is null before any event and after completion', () => {
    const m = pointPlacement();
    expect(m.preview).toBeNull();
    m.onComplete(() => {});
    m.onPointerDown({ time: 1, price: 1 });
    expect(m.preview).toBeNull();
  });

  it('cancel marks machine done without invoking callback', () => {
    const m = pointPlacement();
    let invoked = false;
    m.onComplete(() => (invoked = true));
    m.cancel();
    expect(m.done).toBe(true);
    expect(invoked).toBe(false);
  });
});
