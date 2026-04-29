import type { Drawable, ComputeCtx } from '../../types';
import type { PositionGeo } from '../../placement/positionBand';
import { fetchPositionMetrics } from './api';
import type { PositionMetricsResponse } from './types';

export type { PositionGeo };

/** No tool params; sizing was removed from the UI. */
export type PositionParams = Record<string, never>;

export interface PositionStyle {
  stopColor: string;
  targetColor: string;
  showRiskZone: boolean;
  showRewardZone: boolean;
  showMetrics: boolean;
}

export const DEFAULT_POSITION_STYLE: PositionStyle = {
  stopColor: 'rgb(239, 83, 80)',
  targetColor: 'rgb(38, 166, 154)',
  showRiskZone: true,
  showRewardZone: true,
  showMetrics: true,
};

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null && !Array.isArray(x);
}

/**
 * Merge persisted style with defaults. Drops legacy keys (riskFill, entryColor,
 * rewardFill). Uses entryColor → targetColor and riskFill → stopColor when the
 * new fields are missing.
 */
export function normalizePositionStyle(raw: unknown): PositionStyle {
  const d = DEFAULT_POSITION_STYLE;
  if (!isRecord(raw)) return { ...d };
  const targetColor =
    typeof raw.targetColor === 'string'
      ? raw.targetColor
      : typeof raw.entryColor === 'string'
        ? raw.entryColor
        : d.targetColor;
  const stopColor =
    typeof raw.stopColor === 'string'
      ? raw.stopColor
      : typeof raw.riskFill === 'string'
        ? raw.riskFill
        : d.stopColor;
  return {
    stopColor,
    targetColor,
    showRiskZone:
      typeof raw.showRiskZone === 'boolean' ? raw.showRiskZone : d.showRiskZone,
    showRewardZone:
      typeof raw.showRewardZone === 'boolean'
        ? raw.showRewardZone
        : d.showRewardZone,
    showMetrics:
      typeof raw.showMetrics === 'boolean' ? raw.showMetrics : d.showMetrics,
  };
}

export async function computePositionMetrics(
  side: 'long' | 'short',
  d: Drawable<PositionGeo, PositionParams, PositionStyle>,
  ctx: ComputeCtx,
): Promise<PositionMetricsResponse> {
  return fetchPositionMetrics(
    {
      side,
      entryPrice: d.geometry.entryPrice,
      stopPrice: d.geometry.stopPrice,
      targetPrice: d.geometry.targetPrice,
    },
    ctx.signal,
  );
}

export type { PositionMetricsResponse };
