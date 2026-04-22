import type { PositionMetricsResponse } from './types';

export interface FetchPositionMetricsParams {
  side: 'long' | 'short';
  entryPrice: number;
  stopPrice: number;
  targetPrice: number;
  accountBalance?: number;
  riskPercent?: number;
  riskAmount?: number;
  quantity?: number;
  leverage?: number;
}

export async function fetchPositionMetrics(
  params: FetchPositionMetricsParams,
  signal: AbortSignal,
): Promise<PositionMetricsResponse> {
  const body: Record<string, unknown> = {
    side: params.side,
    entryPrice: params.entryPrice,
    stopPrice: params.stopPrice,
    targetPrice: params.targetPrice,
    leverage: params.leverage ?? 1,
  };
  if (params.accountBalance != null && params.accountBalance > 0) {
    body.accountBalance = params.accountBalance;
  }
  if (params.riskPercent != null && params.riskPercent > 0) {
    body.riskPercent = params.riskPercent;
  }
  if (params.riskAmount != null && params.riskAmount > 0) {
    body.riskAmount = params.riskAmount;
  }
  if (params.quantity != null && params.quantity > 0) {
    body.quantity = params.quantity;
  }

  const res = await fetch('/data/position-metrics', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(
      `position metrics failed: ${res.status}${detail ? ` ${detail}` : ''}`,
    );
  }
  return (await res.json()) as PositionMetricsResponse;
}
