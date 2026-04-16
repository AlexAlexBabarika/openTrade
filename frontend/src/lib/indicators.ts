import { apiJson } from './api';
import { maUrl, bbandsUrl } from './config';
import type { IndicatorResponse, BollingerBandsResponse } from './types';
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

export function fetchBBands(
  symbol: string,
  period: number,
  numStd: number,
): Promise<BollingerBandsResponse> {
  return apiJson<BollingerBandsResponse>(bbandsUrl(symbol, period, numStd));
}
