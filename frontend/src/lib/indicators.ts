import { apiJson } from './api';
import { maUrl } from './config';
import type { IndicatorResponse } from './types';
import { movingAverageType } from './types';

export function fetchSMA(
  symbol: string,
  period: number,
): Promise<IndicatorResponse> {
  return apiJson<IndicatorResponse>(
    maUrl(movingAverageType.SMA, symbol, period),
  );
}

export function fetchEMA(
  symbol: string,
  period: number,
): Promise<IndicatorResponse> {
  return apiJson<IndicatorResponse>(
    maUrl(movingAverageType.EMA, symbol, period),
  );
}
