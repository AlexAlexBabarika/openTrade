import { describe, it, expect } from 'vitest';
import { createDrawablesStore } from './store.svelte';
import { toolbarCommandsFromStore } from './toolbarCommands';
import type { RulerDrawable } from './tools/ruler/tool';

function ruler(id: string, symbol: string): RulerDrawable {
  return {
    id,
    type: 'ruler',
    symbol,
    geometry: { startTime: 0, endTime: 1, startPrice: 1, endPrice: 2 },
    params: {},
    style: {
      upColor: 'rgb(0,0,0)',
      downColor: 'rgb(1,1,1)',
      showStats: true,
    },
    createdAt: 0,
  };
}

describe('toolbarCommandsFromStore', () => {
  it('delegates removeAllForSymbol to the store', () => {
    const store = createDrawablesStore();
    store.add(ruler('a', 'AAPL'));
    store.add(ruler('b', 'MSFT'));
    const cmds = toolbarCommandsFromStore(store);
    cmds.removeAllForSymbol('AAPL');
    expect(store.items.map(d => d.id)).toEqual(['b']);
  });
});
