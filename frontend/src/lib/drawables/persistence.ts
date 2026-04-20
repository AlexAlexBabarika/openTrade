// frontend/src/lib/drawables/persistence.ts
import type { BundledDrawable } from './bundledDrawable';
import {
  extractDrawableFieldBag,
  narrowBundledDrawable,
} from './bundledNarrow';
import { getTool } from './registry';

export const DRAWABLES_STORAGE_KEY = 'openTrade.drawables.v1';

function hydrateEntry(entry: unknown): BundledDrawable | null {
  if (!entry || typeof entry !== 'object') return null;
  const e = entry as { schemaVersion?: number; type?: unknown };
  if (typeof e.type !== 'string') return null;
  const tool = getTool(e.type);
  if (!tool) return null;

  let candidate: unknown = entry;
  if (e.schemaVersion !== tool.schemaVersion) {
    if (!tool.migrate) return null;
    const migrated = tool.migrate(entry);
    if (!migrated) return null;
    candidate = migrated;
  }

  const fields = extractDrawableFieldBag(candidate);
  if (!fields) return null;
  return narrowBundledDrawable(fields);
}

export function loadAll(): BundledDrawable[] {
  try {
    const raw = localStorage.getItem(DRAWABLES_STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    return parsed.flatMap((entry: unknown): BundledDrawable[] => {
      const d = hydrateEntry(entry);
      return d ? [d] : [];
    });
  } catch {
    return [];
  }
}

export function saveAll(items: readonly BundledDrawable[]): void {
  const stamped = items.flatMap((d: BundledDrawable) => {
    const tool = getTool(d.type);
    if (!tool) return [];
    return [{ ...d, schemaVersion: tool.schemaVersion }];
  });
  localStorage.setItem(DRAWABLES_STORAGE_KEY, JSON.stringify(stamped));
}
