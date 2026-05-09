import { METRICS, type MetricId } from './metrics';
import {
  fetchCorrelation,
  fetchHurst,
  fetchKurtosis,
  fetchMaxDrawdown,
  fetchReturnDistribution,
  fetchSharpe,
  fetchSkewness,
  fetchSortino,
  fetchStdev,
  fetchVaR,
  fetchVariance,
  fetchVolatilityClustering,
  type CorrelationResponse,
  type MaxDrawdownResponse,
  type ReturnDistributionResponse,
  type ScalarMetricResponse,
  type VaRResponse,
  type VolatilityClusteringResponse,
} from './analyticsApi';

export type AnalyticsResult =
  | { kind: 'scalar'; data: ScalarMetricResponse }
  | { kind: 'var'; data: VaRResponse }
  | { kind: 'max_drawdown'; data: MaxDrawdownResponse }
  | { kind: 'correlation'; data: CorrelationResponse }
  | { kind: 'volatility_clustering'; data: VolatilityClusteringResponse }
  | { kind: 'return_distribution'; data: ReturnDistributionResponse };

type Fetcher = (symbol: string) => Promise<AnalyticsResult>;

const FETCHERS: Record<MetricId, Fetcher> = {
  sharpe: async s => ({ kind: 'scalar', data: await fetchSharpe(s) }),
  sortino: async s => ({ kind: 'scalar', data: await fetchSortino(s) }),
  max_drawdown: async s => ({
    kind: 'max_drawdown',
    data: await fetchMaxDrawdown(s),
  }),
  var: async s => ({ kind: 'var', data: await fetchVaR(s) }),
  variance: async s => ({ kind: 'scalar', data: await fetchVariance(s) }),
  stdev: async s => ({ kind: 'scalar', data: await fetchStdev(s) }),
  skewness: async s => ({ kind: 'scalar', data: await fetchSkewness(s) }),
  kurtosis: async s => ({ kind: 'scalar', data: await fetchKurtosis(s) }),
  correlation: async s => ({
    kind: 'correlation',
    data: await fetchCorrelation(s),
  }),
  volatility_clustering: async s => ({
    kind: 'volatility_clustering',
    data: await fetchVolatilityClustering(s),
  }),
  hurst: async s => ({ kind: 'scalar', data: await fetchHurst(s) }),
  return_distribution: async s => ({
    kind: 'return_distribution',
    data: await fetchReturnDistribution(s),
  }),
};

function emptyBoolMap(): Record<MetricId, boolean> {
  const out = {} as Record<MetricId, boolean>;
  for (const m of METRICS) out[m.id] = false;
  return out;
}

function emptyResultMap(): Record<MetricId, AnalyticsResult | null> {
  const out = {} as Record<MetricId, AnalyticsResult | null>;
  for (const m of METRICS) out[m.id] = null;
  return out;
}

function emptyErrorMap(): Record<MetricId, string | null> {
  const out = {} as Record<MetricId, string | null>;
  for (const m of METRICS) out[m.id] = null;
  return out;
}

export class AnalyticsState {
  enabled = $state<Record<MetricId, boolean>>(emptyBoolMap());
  results = $state<Record<MetricId, AnalyticsResult | null>>(emptyResultMap());
  loading = $state<Record<MetricId, boolean>>(emptyBoolMap());
  errors = $state<Record<MetricId, string | null>>(emptyErrorMap());
  symbol = $state<string | null>(null);

  /** Override the per-metric fetchers (used by tests). */
  fetchers: Record<MetricId, Fetcher> = FETCHERS;

  enabledIds = $derived<MetricId[]>(
    METRICS.map(m => m.id).filter(id => this.enabled[id]),
  );

  toggle(id: MetricId): void {
    const next = !this.enabled[id];
    this.enabled[id] = next;
    if (next && this.symbol && this.results[id] === null) {
      void this.#fetchOne(id, this.symbol);
    }
  }

  /**
   * Set the active symbol. If it changed, drop cached results/errors and
   * re-fetch every currently-enabled metric. If the symbol is unchanged, only
   * fills in metrics that have no cached result yet.
   */
  async refresh(symbol: string): Promise<void> {
    const trimmed = symbol.trim();
    if (!trimmed) return;
    if (trimmed !== this.symbol) {
      this.symbol = trimmed;
      this.results = emptyResultMap();
      this.errors = emptyErrorMap();
    }
    const targets = this.enabledIds.filter(id => this.results[id] === null);
    await Promise.all(targets.map(id => this.#fetchOne(id, trimmed)));
  }

  /** Drop cached results for the current symbol and re-fetch enabled metrics. */
  invalidate(): void {
    this.results = emptyResultMap();
    this.errors = emptyErrorMap();
    if (!this.symbol) return;
    for (const id of this.enabledIds) {
      void this.#fetchOne(id, this.symbol);
    }
  }

  async #fetchOne(id: MetricId, symbol: string): Promise<void> {
    this.loading[id] = true;
    this.errors[id] = null;
    try {
      const result = await this.fetchers[id](symbol);
      if (this.symbol !== symbol) return;
      this.results[id] = result;
    } catch (err) {
      if (this.symbol !== symbol) return;
      this.errors[id] = err instanceof Error ? err.message : 'Fetch failed';
    } finally {
      this.loading[id] = false;
    }
  }
}
