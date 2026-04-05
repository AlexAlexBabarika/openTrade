import { apiFetch, readErrorMessage } from './api';
import { smaUrl, emaUrl } from './config';
import type { IndicatorResponse } from './types';

export async function fetchSMA(
  symbol: string,
  period: number,
): Promise<IndicatorResponse> {
  const res = await apiFetch(smaUrl(symbol, period));
  if (!res.ok) throw new Error(await readErrorMessage(res));
  return res.json();
}

export async function fetchEMA(
  symbol: string,
  period: number,
): Promise<IndicatorResponse> {
  const res = await apiFetch(emaUrl(symbol, period));
  if (!res.ok) throw new Error(await readErrorMessage(res));
  return res.json();
}
