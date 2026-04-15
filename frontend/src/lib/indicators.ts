import { apiJson } from './api';
import { maUrl } from './config';
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

export async function fetchBBands(
  symbol: string,
  period: number,
  numStd: number,
): Promise<BollingerBandsResponse> {
  const res = await apiFetch(bbandsUrl(symbol, period, numStd));
  if (!res.ok) throw new Error(await readErrorMessage(res));
  return res.json();
}
