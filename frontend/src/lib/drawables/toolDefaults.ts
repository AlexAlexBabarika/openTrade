// frontend/src/lib/drawables/toolDefaults.ts
export const TOOL_DEFAULTS_STORAGE_KEY = 'openTrade.drawables.toolDefaults.v1';

type Stored = Record<string, { params: unknown; style: unknown }>;

function readAll(): Stored {
  try {
    const raw = localStorage.getItem(TOOL_DEFAULTS_STORAGE_KEY);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? (parsed as Stored) : {};
  } catch {
    return {};
  }
}

export function loadToolDefaults(
  type: string,
): { params: unknown; style: unknown } | null {
  return readAll()[type] ?? null;
}

export function saveToolDefaults(
  type: string,
  defaults: { params: unknown; style: unknown },
): void {
  const all = readAll();
  all[type] = defaults;
  localStorage.setItem(TOOL_DEFAULTS_STORAGE_KEY, JSON.stringify(all));
}
