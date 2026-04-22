import type { Drawable, ComputeCtx } from '../../types';
import type { PositionGeo } from '../../placement/positionBand';
import { fetchPositionMetrics } from './api';
import type { PositionMetricsResponse } from './types';

export type { PositionGeo };

export interface PositionParams {
  /** 0 = omit (use risk-based sizing only when other fields set). */
  accountBalance: number;
  riskPercent: number;
  riskAmount: number;
  quantity: number;
  leverage: number;
}

export interface PositionStyle {
  riskFill: string;
  rewardFill: string;
  entryColor: string;
  stopColor: string;
  targetColor: string;
  showRiskZone: boolean;
  showRewardZone: boolean;
  showMetrics: boolean;
}

function pickSizing(p: PositionParams): {
  accountBalance?: number;
  riskPercent?: number;
  riskAmount?: number;
  quantity?: number;
  leverage: number;
} {
  return {
    accountBalance: p.accountBalance > 0 ? p.accountBalance : undefined,
    riskPercent: p.riskPercent > 0 ? p.riskPercent : undefined,
    riskAmount: p.riskAmount > 0 ? p.riskAmount : undefined,
    quantity: p.quantity > 0 ? p.quantity : undefined,
    leverage: p.leverage > 0 ? p.leverage : 1,
  };
}

export async function computePositionMetrics(
  side: 'long' | 'short',
  d: Drawable<PositionGeo, PositionParams, PositionStyle>,
  ctx: ComputeCtx,
): Promise<PositionMetricsResponse> {
  const s = pickSizing(d.params);
  const m = await fetchPositionMetrics(
    {
      side,
      entryPrice: d.geometry.entryPrice,
      stopPrice: d.geometry.stopPrice,
      targetPrice: d.geometry.targetPrice,
      ...s,
    },
    ctx.signal,
  );

  const lastClose = ctx.candles.length
    ? ctx.candles[ctx.candles.length - 1].close
    : undefined;
  const qty = m.quantity;
  let openPnl: number | null = null;
  if (
    lastClose != null &&
    qty != null &&
    Number.isFinite(lastClose) &&
    Number.isFinite(qty)
  ) {
    openPnl =
      side === 'long'
        ? qty * (lastClose - d.geometry.entryPrice)
        : qty * (d.geometry.entryPrice - lastClose);
  }

  return { ...m, openPnl };
}

export type { PositionMetricsResponse };
