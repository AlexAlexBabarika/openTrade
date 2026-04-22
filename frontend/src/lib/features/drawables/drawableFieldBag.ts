/** Shared field extraction for persistence and tool migrate (no toolCatalog import). */

export function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null && !Array.isArray(x);
}

export function finiteNumber(x: unknown): x is number {
  return typeof x === 'number' && Number.isFinite(x);
}

export type DrawableFieldBag = {
  id: string;
  type: string;
  symbol: string;
  createdAt: number;
  geometry: unknown;
  params: unknown;
  style: unknown;
};

/** Extract core drawable fields from a stored or migrated object. */
export function extractDrawableFieldBag(
  candidate: unknown,
): DrawableFieldBag | null {
  if (!isRecord(candidate)) return null;
  if (typeof candidate.id !== 'string') return null;
  if (typeof candidate.type !== 'string') return null;
  if (typeof candidate.symbol !== 'string') return null;
  if (!finiteNumber(candidate.createdAt)) return null;
  return {
    id: candidate.id,
    type: candidate.type,
    symbol: candidate.symbol,
    createdAt: candidate.createdAt,
    geometry: candidate.geometry,
    params: candidate.params,
    style: candidate.style,
  };
}
