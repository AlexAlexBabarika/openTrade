import { apiJson } from './api';
import { smaUrl, emaUrl } from './config';
import type { IndicatorResponse } from './types';

export function fetchSMA(
  symbol: string,
  period: number,
): Promise<IndicatorResponse> {
  return apiJson<IndicatorResponse>(smaUrl(symbol, period));
}

export function fetchEMA(
  symbol: string,
  period: number,
): Promise<IndicatorResponse> {
  return apiJson<IndicatorResponse>(emaUrl(symbol, period));
}
