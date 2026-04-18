// frontend/src/lib/drawables/store.svelte.ts
import type { Drawable } from './types';

export function createDrawablesStore() {
  let items = $state<Drawable[]>([]);
  let selectedId = $state<string | null>(null);

  return {
    get items() {
      return items;
    },
    get selected() {
      return items.find(d => d.id === selectedId) ?? null;
    },
    forSymbol(symbol: string) {
      return items.filter(d => d.symbol === symbol);
    },
    add(d: Drawable) {
      items = [...items, d];
    },
    update(id: string, patch: Partial<Drawable>) {
      items = items.map(d => (d.id === id ? { ...d, ...patch } : d));
    },
    remove(id: string) {
      items = items.filter(d => d.id !== id);
      if (selectedId === id) selectedId = null;
    },
    replaceAll(next: Drawable[]) {
      items = [...next];
      selectedId = null;
    },
    select(id: string | null) {
      selectedId = id;
    },
  };
}

/** Singleton used by the app. Tests create their own via createDrawablesStore(). */
export const drawables = createDrawablesStore();
