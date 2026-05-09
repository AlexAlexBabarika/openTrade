import { apiJson } from '$lib/core/api';

export type ScalarMetricResponse = {
  symbol: string;
  metric: string;
  value: number;
  n: number;
};

export type VaRResponse = {
  symbol: string;
  metric: 'var';
  var_95: number;
  var_99: number;
  n: number;
};

export type DrawdownPoint = { timestamp: string; value: number };

export type MaxDrawdownResponse = {
  symbol: string;
  metric: 'max_drawdown';
  max_drawdown: number;
  series: DrawdownPoint[];
};

export type CorrelationRow = { benchmark: string; value: number };

export type CorrelationResponse = {
  symbol: string;
  metric: 'correlation';
  rows: CorrelationRow[];
};

export type VolatilityClusteringResponse = {
  symbol: string;
  metric: 'volatility_clustering';
  lag: number;
  q: number;
  p_value: number;
};

export type DistributionBin = { left: number; right: number; count: number };

export type ReturnDistributionResponse = {
  symbol: string;
  metric: 'return_distribution';
  bins: DistributionBin[];
};

function qs(params: Record<string, string | number | undefined>): string {
  const parts: string[] = [];
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined) continue;
    parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  }
  return parts.length ? `?${parts.join('&')}` : '';
}

export function fetchSharpe(
  symbol: string,
  rf?: number,
): Promise<ScalarMetricResponse> {
  return apiJson<ScalarMetricResponse>(
    `/data/analytics/sharpe${qs({ symbol, rf })}`,
  );
}

export function fetchSortino(
  symbol: string,
  rf?: number,
): Promise<ScalarMetricResponse> {
  return apiJson<ScalarMetricResponse>(
    `/data/analytics/sortino${qs({ symbol, rf })}`,
  );
}

export function fetchMaxDrawdown(symbol: string): Promise<MaxDrawdownResponse> {
  return apiJson<MaxDrawdownResponse>(
    `/data/analytics/max_drawdown${qs({ symbol })}`,
  );
}

export function fetchVaR(symbol: string): Promise<VaRResponse> {
  return apiJson<VaRResponse>(`/data/analytics/var${qs({ symbol })}`);
}

export function fetchVariance(symbol: string): Promise<ScalarMetricResponse> {
  return apiJson<ScalarMetricResponse>(
    `/data/analytics/variance${qs({ symbol })}`,
  );
}

export function fetchStdev(symbol: string): Promise<ScalarMetricResponse> {
  return apiJson<ScalarMetricResponse>(
    `/data/analytics/stdev${qs({ symbol })}`,
  );
}

export function fetchSkewness(symbol: string): Promise<ScalarMetricResponse> {
  return apiJson<ScalarMetricResponse>(
    `/data/analytics/skewness${qs({ symbol })}`,
  );
}

export function fetchKurtosis(symbol: string): Promise<ScalarMetricResponse> {
  return apiJson<ScalarMetricResponse>(
    `/data/analytics/kurtosis${qs({ symbol })}`,
  );
}

export function fetchCorrelation(
  symbol: string,
  benchmarks?: readonly string[],
): Promise<CorrelationResponse> {
  const benchParam =
    benchmarks && benchmarks.length ? benchmarks.join(',') : undefined;
  return apiJson<CorrelationResponse>(
    `/data/analytics/correlation${qs({ symbol, benchmarks: benchParam })}`,
  );
}

export function fetchVolatilityClustering(
  symbol: string,
  lag?: number,
): Promise<VolatilityClusteringResponse> {
  return apiJson<VolatilityClusteringResponse>(
    `/data/analytics/volatility_clustering${qs({ symbol, lag })}`,
  );
}

export function fetchHurst(symbol: string): Promise<ScalarMetricResponse> {
  return apiJson<ScalarMetricResponse>(
    `/data/analytics/hurst${qs({ symbol })}`,
  );
}

export function fetchReturnDistribution(
  symbol: string,
  bins?: number,
): Promise<ReturnDistributionResponse> {
  return apiJson<ReturnDistributionResponse>(
    `/data/analytics/return_distribution${qs({ symbol, bins })}`,
  );
}
