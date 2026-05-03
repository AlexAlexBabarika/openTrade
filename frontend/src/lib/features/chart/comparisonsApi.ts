import { apiFetch, apiJson, readErrorMessage } from '$lib/core/api';
import type { MarketDataProviderValue } from '$lib/features/market/marketDataProviders';

export type ComparisonSeriesType = 'line' | 'candlestick';

export interface ComparisonRecord {
  id: string;
  main_symbol: string;
  comparison_symbol: string;
  provider: MarketDataProviderValue;
  color: string;
  series_type: ComparisonSeriesType;
  position: number;
  created_at: string;
}

interface ComparisonListResponse {
  comparisons: ComparisonRecord[];
}

export async function listComparisons(
  mainSymbol: string,
): Promise<ComparisonRecord[]> {
  const params = new URLSearchParams({ main_symbol: mainSymbol });
  const res = await apiJson<ComparisonListResponse>(
    `/user/comparisons?${params.toString()}`,
    { method: 'GET' },
    true,
  );
  return res.comparisons;
}

export interface CreateComparisonInput {
  main_symbol: string;
  comparison_symbol: string;
  provider: MarketDataProviderValue;
  color: string;
  series_type: ComparisonSeriesType;
}

export async function createComparison(
  input: CreateComparisonInput,
): Promise<ComparisonRecord> {
  return apiJson<ComparisonRecord>(
    '/user/comparisons',
    { method: 'POST', body: JSON.stringify(input) },
    true,
  );
}

export interface UpdateComparisonInput {
  color?: string;
  series_type?: ComparisonSeriesType;
}

export async function updateComparison(
  id: string,
  patch: UpdateComparisonInput,
): Promise<ComparisonRecord> {
  return apiJson<ComparisonRecord>(
    `/user/comparisons/${encodeURIComponent(id)}`,
    { method: 'PATCH', body: JSON.stringify(patch) },
    true,
  );
}

export async function deleteComparison(id: string): Promise<void> {
  const res = await apiFetch(
    `/user/comparisons/${encodeURIComponent(id)}`,
    { method: 'DELETE' },
    true,
  );
  if (!res.ok && res.status !== 204) {
    throw new Error(await readErrorMessage(res));
  }
}
