// frontend/src/lib/drawables/persistence.ts
import type { Drawable } from './types';
import { getTool } from './registry';

export const DRAWABLES_STORAGE_KEY = 'openTrade.drawables.v1';

export function loadAll(): Drawable[] {
  const raw = localStorage.getItem(DRAWABLES_STORAGE_KEY);
  if (!raw) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return [];
  }
  if (!Array.isArray(parsed)) return [];

  return parsed.flatMap((entry: unknown): Drawable[] => {
    if (!entry || typeof entry !== 'object') return [];
    const e = entry as Partial<Drawable> & { schemaVersion?: number };
    if (typeof e.type !== 'string') return [];
    const tool = getTool(e.type);
    if (!tool) return [];
    if (e.schemaVersion === tool.schemaVersion) {
      return [e as Drawable];
    }
    if (!tool.migrate) return [];
    const migrated = tool.migrate(entry);
    return migrated ? [migrated] : [];
  });
}

export function saveAll(items: Drawable[]): void {
  const stamped = items.flatMap(d => {
    const tool = getTool(d.type);
    if (!tool) return [];
    return [{ ...d, schemaVersion: tool.schemaVersion }];
  });
  localStorage.setItem(DRAWABLES_STORAGE_KEY, JSON.stringify(stamped));
}
