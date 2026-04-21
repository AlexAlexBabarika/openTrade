import type { RangeGeo } from './placement/range';
import type { RulerParams, RulerStyle } from './tools/ruler/tool';
import type {
  AvpGeo,
  AvpParams,
  AvpStyle,
} from './tools/volume-profile/avp/compute';
import type { BundledDrawable } from './bundledDrawable';
import { isBundledToolType, type BundledToolType } from './toolCatalog';

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null && !Array.isArray(x);
}

function finiteNumber(x: unknown): x is number {
  return typeof x === 'number' && Number.isFinite(x);
}

function isRulerGeo(g: unknown): g is RangeGeo {
  if (!isRecord(g)) return false;
  return (
    finiteNumber(g.startTime) &&
    finiteNumber(g.endTime) &&
    finiteNumber(g.startPrice) &&
    finiteNumber(g.endPrice)
  );
}

function isRulerParams(p: unknown): p is RulerParams {
  return isRecord(p) && Object.keys(p).length === 0;
}

function isRulerStyle(s: unknown): s is RulerStyle {
  if (!isRecord(s)) return false;
  return (
    typeof s.upColor === 'string' &&
    typeof s.downColor === 'string' &&
    typeof s.showStats === 'boolean'
  );
}

function isAvpGeo(g: unknown): g is AvpGeo {
  return isRecord(g) && finiteNumber(g.time);
}

function isAvpParams(p: unknown): p is AvpParams {
  if (!isRecord(p)) return false;
  return finiteNumber(p.rowSize) && finiteNumber(p.vaPercent);
}

function isAvpStyle(s: unknown): s is AvpStyle {
  if (!isRecord(s)) return false;
  if (typeof s.showProfile !== 'boolean') return false;
  if (!finiteNumber(s.widthPct)) return false;
  if (s.placement !== 'left' && s.placement !== 'right') return false;
  if (typeof s.upColor !== 'string' || typeof s.downColor !== 'string')
    return false;
  if (typeof s.showPOC !== 'boolean' || typeof s.pocColor !== 'string')
    return false;
  if (typeof s.showVAH !== 'boolean' || typeof s.vahColor !== 'string')
    return false;
  if (typeof s.showVAL !== 'boolean' || typeof s.valColor !== 'string')
    return false;
  return true;
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

/** Runtime narrow for bundled tools only; returns null if shape is invalid. */
export function narrowBundledDrawable(
  fields: DrawableFieldBag,
): BundledDrawable | null {
  if (!isBundledToolType(fields.type)) return null;
  const t: BundledToolType = fields.type;
  switch (t) {
    case 'ruler':
      if (
        !isRulerGeo(fields.geometry) ||
        !isRulerParams(fields.params) ||
        !isRulerStyle(fields.style)
      ) {
        return null;
      }
      return {
        id: fields.id,
        type: 'ruler',
        symbol: fields.symbol,
        createdAt: fields.createdAt,
        geometry: fields.geometry,
        params: fields.params,
        style: fields.style,
      };
    case 'avp':
      if (
        !isAvpGeo(fields.geometry) ||
        !isAvpParams(fields.params) ||
        !isAvpStyle(fields.style)
      ) {
        return null;
      }
      return {
        id: fields.id,
        type: 'avp',
        symbol: fields.symbol,
        createdAt: fields.createdAt,
        geometry: fields.geometry,
        params: fields.params,
        style: fields.style,
      };
    default:
      return null;
  }
}
