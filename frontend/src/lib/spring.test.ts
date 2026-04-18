import { describe, it, expect } from 'vitest';
import { stepSpring } from './spring';

describe('stepSpring', () => {
  it('moves toward the target when released from rest', () => {
    const { x, v } = stepSpring(0, 0, 1, 1 / 60);
    expect(x).toBeGreaterThan(0);
    expect(x).toBeLessThan(1);
    expect(v).toBeGreaterThan(0);
  });

  it('settles near the target after enough time', () => {
    let x = 0;
    let v = 0;
    for (let i = 0; i < 600; i++) {
      const next = stepSpring(x, v, 1, 1 / 60);
      x = next.x;
      v = next.v;
    }
    expect(x).toBeCloseTo(1, 2);
    expect(Math.abs(v)).toBeLessThan(0.01);
  });

  it('overshoots the target when under-damped (produces a bounce)', () => {
    let x = 0;
    let v = 0;
    let maxX = 0;
    for (let i = 0; i < 240; i++) {
      const next = stepSpring(x, v, 1, 1 / 60, 200, 8, 1);
      x = next.x;
      v = next.v;
      if (x > maxX) maxX = x;
    }
    expect(maxX).toBeGreaterThan(1);
  });

  it('preserves initial velocity sign on the first step', () => {
    const { v } = stepSpring(0.5, -2, 0.5, 1 / 240);
    expect(v).toBeLessThan(0);
  });
});
