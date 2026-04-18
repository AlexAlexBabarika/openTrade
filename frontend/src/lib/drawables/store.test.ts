// frontend/src/lib/drawables/store.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { createDrawablesStore } from './store.svelte';
import type { Drawable } from './types';

function d(id: string, symbol = 'AAPL'): Drawable {
  return {
    id,
    type: 'ruler',
    symbol,
    geometry: {},
    params: {},
    style: {},
    createdAt: 0,
  };
}

describe('drawables store', () => {
  let store: ReturnType<typeof createDrawablesStore>;
  beforeEach(() => {
    store = createDrawablesStore();
  });

  it('starts empty', () => {
    expect(store.items).toEqual([]);
    expect(store.selected).toBeNull();
  });

  it('add/update/remove and selection', () => {
    store.add(d('1'));
    store.add(d('2'));
    expect(store.items.map(x => x.id)).toEqual(['1', '2']);

    store.update('1', { symbol: 'MSFT' });
    expect(store.items[0].symbol).toBe('MSFT');

    store.select('2');
    expect(store.selected?.id).toBe('2');

    store.remove('2');
    expect(store.items.map(x => x.id)).toEqual(['1']);
    expect(store.selected).toBeNull();
  });

  it('forSymbol filters by symbol', () => {
    store.add(d('a', 'AAPL'));
    store.add(d('b', 'MSFT'));
    store.add(d('c', 'AAPL'));
    expect(store.forSymbol('AAPL').map(x => x.id)).toEqual(['a', 'c']);
  });

  it('replaceAll swaps items and clears selection', () => {
    store.add(d('1'));
    store.select('1');
    store.replaceAll([d('2'), d('3')]);
    expect(store.items.map(x => x.id)).toEqual(['2', '3']);
    expect(store.selected).toBeNull();
  });

  it('select(null) deselects', () => {
    store.add(d('1'));
    store.select('1');
    store.select(null);
    expect(store.selected).toBeNull();
  });
});
