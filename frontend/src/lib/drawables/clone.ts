/**
 * Deep copy for drawable tool snapshots (params/style defaults and persisted copies).
 *
 * Staged values in `ToolSettingsModal` are Svelte `$state` proxies; `structuredClone`
 * cannot clone those. We walk plain object trees ourselves (unwraps proxies) and
 * preserve `Date`, `Map`, `Set`, and `BigInt` where applicable.
 */

function toPlainDeep<T>(value: T, seen = new WeakMap<object, unknown>()): T {
  if (value === null || typeof value !== 'object') {
    return value;
  }

  const obj = value as object;
  if (seen.has(obj)) {
    return seen.get(obj) as T;
  }

  if (value instanceof Date) {
    const d = new Date(value.getTime());
    seen.set(obj, d);
    return d as unknown as T;
  }

  if (value instanceof Map) {
    const m = new Map<unknown, unknown>();
    seen.set(obj, m);
    for (const [k, v] of value) {
      m.set(toPlainDeep(k, seen), toPlainDeep(v, seen));
    }
    return m as unknown as T;
  }

  if (value instanceof Set) {
    const s = new Set<unknown>();
    seen.set(obj, s);
    for (const v of value) {
      s.add(toPlainDeep(v, seen));
    }
    return s as unknown as T;
  }

  if (ArrayBuffer.isView(value)) {
    const copy = structuredClone(value);
    seen.set(obj, copy);
    return copy as unknown as T;
  }

  if (Array.isArray(value)) {
    const arr: unknown[] = [];
    seen.set(obj, arr);
    for (let i = 0; i < value.length; i++) {
      arr[i] = toPlainDeep((value as unknown[])[i], seen);
    }
    return arr as T;
  }

  const out: Record<string, unknown> = {};
  seen.set(obj, out);
  for (const key of Object.keys(value as object)) {
    out[key] = toPlainDeep((value as Record<string, unknown>)[key], seen);
  }
  return out as T;
}

export function deepCloneDrawableSnapshot<T>(value: T): T {
  return toPlainDeep(value);
}
