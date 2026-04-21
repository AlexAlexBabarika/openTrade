import { describe, expect, it } from 'vitest';
import { deepCloneDrawableSnapshot } from './clone';

describe('deepCloneDrawableSnapshot', () => {
  it('unwraps Proxy-wrapped plain objects (Svelte $state)', () => {
    const plain = {
      upColor: 'rgb(1,2,3)',
      downColor: 'rgb(4,5,6)',
      showStats: true,
    };
    const proxied = new Proxy(plain, {});
    const copy = deepCloneDrawableSnapshot(proxied);
    expect(copy).toEqual(plain);
    expect(copy).not.toBe(plain);
  });

  it('preserves Date', () => {
    const d = new Date('2020-01-02T03:04:05Z');
    const copy = deepCloneDrawableSnapshot({ d });
    expect(copy.d).toEqual(d);
    expect(copy.d).not.toBe(d);
  });
});
