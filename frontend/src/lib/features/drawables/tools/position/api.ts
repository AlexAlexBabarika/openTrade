import type { PositionMetricsResponse } from './types';

export interface FetchPositionMetricsParams {
  side: 'long' | 'short';
  entryPrice: number;
  stopPrice: number;
  targetPrice: number;
}

export async function fetchPositionMetrics(
  params: FetchPositionMetricsParams,
  signal: AbortSignal,
): Promise<PositionMetricsResponse> {
  const res = await fetch('/data/position-metrics', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
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
