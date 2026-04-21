// frontend/src/lib/drawables/store.svelte.ts
import type { BundledDrawable } from './bundledDrawable';
import type { Drawable } from './types';

export function createDrawablesStore() {
  let items = $state<BundledDrawable[]>([]);
  let selectedId = $state<string | null>(null);

  /** O(1) lookup by id; rebuilt when `items` changes (same cost as one linear scan). */
  let byId = $derived(new Map(items.map(d => [d.id, d])));

  return {
    get items() {
      return items;
    },
    get selected() {
      if (selectedId === null) return null;
      return byId.get(selectedId) ?? null;
    },
    forSymbol(symbol: string) {
      return items.filter(d => d.symbol === symbol);
    },
    add(d: BundledDrawable) {
      items = [...items, d];
    },
    update(id: string, patch: Partial<Drawable>) {
      items = items.map(d =>
        d.id === id ? ({ ...d, ...patch } as BundledDrawable) : d,
      );
    },
    remove(id: string) {
      items = items.filter(d => d.id !== id);
      if (selectedId === id) selectedId = null;
    },
    removeAllForSymbol(symbol: string) {
      const removing = new Set(
        items.filter(d => d.symbol === symbol).map(d => d.id),
      );
      if (removing.size === 0) return;
      items = items.filter(d => d.symbol !== symbol);
      if (selectedId !== null && removing.has(selectedId)) {
        selectedId = null;
      }
    },
    replaceAll(next: BundledDrawable[]) {
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
