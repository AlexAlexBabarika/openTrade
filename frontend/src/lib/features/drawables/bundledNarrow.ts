import type { RangeGeo } from './placement/range';
import type { RulerParams, RulerStyle } from './tools/ruler/tool';
import type {
  AvpGeo,
  AvpParams,
  AvpStyle,
} from './tools/volume-profile/avp/compute';
import {
  normalizePositionStyle,
  type PositionGeo,
  type PositionParams,
  type PositionStyle,
} from './tools/position/compute';
import {
  POSITION_LONG_TYPE,
  POSITION_SHORT_TYPE,
} from './tools/position/constants';
import type { BundledDrawable } from './bundledDrawable';
import { isBundledToolType, type BundledToolType } from './toolCatalog';
import {
  extractDrawableFieldBag,
  finiteNumber,
  isRecord,
  type DrawableFieldBag,
} from './drawableFieldBag';

export { extractDrawableFieldBag };
export type { DrawableFieldBag };

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

function isPositionGeo(g: unknown): g is PositionGeo {
  if (!isRecord(g)) return false;
  return (
    finiteNumber(g.startTime) &&
    finiteNumber(g.endTime) &&
    finiteNumber(g.entryPrice) &&
    finiteNumber(g.stopPrice) &&
    finiteNumber(g.targetPrice)
  );
}

function isPositionParams(p: unknown): p is PositionParams {
  return p == null || isRecord(p);
}

function isPositionStyle(s: unknown): s is PositionStyle {
  if (!isRecord(s)) return false;
  return (
    typeof s.stopColor === 'string' &&
    typeof s.targetColor === 'string' &&
    typeof s.showRiskZone === 'boolean' &&
    typeof s.showRewardZone === 'boolean' &&
    typeof s.showMetrics === 'boolean'
  );
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
    case POSITION_LONG_TYPE:
      if (
        !isPositionGeo(fields.geometry) ||
        !isPositionParams(fields.params) ||
        !isPositionStyle(fields.style)
      ) {
        return null;
      }
      return {
        id: fields.id,
        type: POSITION_LONG_TYPE,
        symbol: fields.symbol,
        createdAt: fields.createdAt,
        geometry: fields.geometry,
        params: {},
        style: normalizePositionStyle(fields.style),
      };
    case POSITION_SHORT_TYPE:
      if (
        !isPositionGeo(fields.geometry) ||
        !isPositionParams(fields.params) ||
        !isPositionStyle(fields.style)
      ) {
        return null;
      }
      return {
        id: fields.id,
        type: POSITION_SHORT_TYPE,
        symbol: fields.symbol,
        createdAt: fields.createdAt,
        geometry: fields.geometry,
        params: {},
        style: normalizePositionStyle(fields.style),
      };
    default:
      return null;
  }
}
