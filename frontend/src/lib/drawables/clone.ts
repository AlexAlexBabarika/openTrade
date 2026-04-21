/**
 * Deep copy for drawable tool snapshots (params/style defaults and persisted copies).
 * Uses `structuredClone` (not JSON): preserves `Date`, `Map`, `Set`, `BigInt`, etc.;
 * JSON round-trips would stringify or drop those.
 */
export function deepCloneDrawableSnapshot<T>(value: T): T {
  return structuredClone(value);
}
