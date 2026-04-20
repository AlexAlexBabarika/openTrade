// frontend/src/lib/drawables/persistence.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { loadAll, saveAll, DRAWABLES_STORAGE_KEY } from './persistence';
import { registerTool, _resetRegistry } from './registry';
import type { DrawableTool, Drawable } from './types';

// Minimal in-memory localStorage shim: vitest defaults to the node environment
// and this project has no jsdom/happy-dom dependency, so we stub it here rather
// than add a heavier dev dep just to run these tests.
const mem = new Map<string, string>();
vi.stubGlobal('localStorage', {
  getItem: (k: string) => (mem.has(k) ? mem.get(k)! : null),
  setItem: (k: string, v: string) => void mem.set(k, String(v)),
  removeItem: (k: string) => void mem.delete(k),
  clear: () => mem.clear(),
  key: (i: number) => Array.from(mem.keys())[i] ?? null,
  get length() {
    return mem.size;
  },
});

function tool(
  type: string,
  schemaVersion = 1,
  migrate?: DrawableTool['migrate'],
): DrawableTool {
  return {
    type,
    label: type,
    icon: (() => null) as unknown as DrawableTool['icon'],
    defaults: { params: {}, style: {} },
    schemaVersion,
    migrate,
    createPlacement: () => {
      throw new Error('not used');
    },
    Renderer: (() => null) as unknown as DrawableTool['Renderer'],
    Settings: (() => null) as unknown as DrawableTool['Settings'],
  };
}

function drawable(id: string, type: string): Drawable {
  return {
    id,
    type,
    symbol: 'AAPL',
    geometry: { x: 1 },
    params: {},
    style: {},
    createdAt: 0,
  };
}

describe('persistence', () => {
  beforeEach(() => {
    _resetRegistry();
    localStorage.clear();
  });

  it('returns empty array when storage key missing', () => {
    expect(loadAll()).toEqual([]);
  });

  it('returns empty array for malformed JSON', () => {
    localStorage.setItem(DRAWABLES_STORAGE_KEY, 'not json');
    expect(loadAll()).toEqual([]);
  });

  it('saves items stamped with each tool schemaVersion', () => {
    registerTool(tool('ruler', 3));
    saveAll([drawable('a', 'ruler')]);
    const raw = JSON.parse(localStorage.getItem(DRAWABLES_STORAGE_KEY)!);
    expect(raw[0].schemaVersion).toBe(3);
  });

  it('loads matching schemaVersion unchanged', () => {
    registerTool(tool('ruler', 1));
    saveAll([drawable('a', 'ruler')]);
    const loaded = loadAll();
    expect(loaded.map(d => d.id)).toEqual(['a']);
  });

  it('drops drawables whose tool is not registered', () => {
    registerTool(tool('ruler', 1));
    saveAll([drawable('a', 'ruler'), drawable('b', 'ghost')]);
    expect(loadAll().map(d => d.id)).toEqual(['a']);
  });

  it('runs migrate when schemaVersion mismatches', () => {
    registerTool(
      tool('ruler', 2, raw => ({
        ...(raw as Drawable),
        geometry: { migrated: true },
      })),
    );
    localStorage.setItem(
      DRAWABLES_STORAGE_KEY,
      JSON.stringify([{ ...drawable('a', 'ruler'), schemaVersion: 1 }]),
    );
    const loaded = loadAll();
    expect(loaded[0].geometry).toEqual({ migrated: true });
  });

  it('drops drawables where migrate returns null', () => {
    registerTool(tool('ruler', 2, () => null));
    localStorage.setItem(
      DRAWABLES_STORAGE_KEY,
      JSON.stringify([{ ...drawable('a', 'ruler'), schemaVersion: 1 }]),
    );
    expect(loadAll()).toEqual([]);
  });

  it('drops drawables with schemaVersion mismatch and no migrate defined', () => {
    registerTool(tool('ruler', 2));
    localStorage.setItem(
      DRAWABLES_STORAGE_KEY,
      JSON.stringify([{ ...drawable('a', 'ruler'), schemaVersion: 1 }]),
    );
    expect(loadAll()).toEqual([]);
  });
});
