import { apiJson } from '$lib/core/api';
import { maUrl, bbandsUrl } from '$lib/core/config';
import type {
  IndicatorResponse,
  BollingerBandsResponse,
} from '$lib/core/types';
import { movingAverageType } from '$lib/core/types';

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
