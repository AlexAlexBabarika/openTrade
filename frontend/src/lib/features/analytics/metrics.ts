export type MetricCategory = 'Risk' | 'Statistical' | 'Advanced';

export type MetricId =
  | 'sharpe'
  | 'sortino'
  | 'max_drawdown'
  | 'var'
  | 'variance'
  | 'stdev'
  | 'skewness'
  | 'kurtosis'
  | 'correlation'
  | 'volatility_clustering'
  | 'hurst'
  | 'return_distribution';

export type MetricDef = {
  id: MetricId;
  label: string;
  category: MetricCategory;
  description: string;
};

export const METRICS: readonly MetricDef[] = [
  {
    id: 'sharpe',
    label: 'Sharpe Ratio',
    category: 'Risk',
    description: 'Annualised risk-adjusted return (excess return / stdev).',
  },
  {
    id: 'sortino',
    label: 'Sortino Ratio',
    category: 'Risk',
    description: 'Like Sharpe but penalises only downside deviation.',
  },
  {
    id: 'max_drawdown',
    label: 'Max Drawdown',
    category: 'Risk',
    description: 'Largest peak-to-trough decline; includes drawdown curve.',
  },
  {
    id: 'var',
    label: 'Value at Risk',
    category: 'Risk',
    description: 'Historical VaR at the 95% and 99% confidence levels.',
  },
  {
    id: 'variance',
    label: 'Variance',
    category: 'Statistical',
    description: 'Sample variance of log-returns.',
  },
  {
    id: 'stdev',
    label: 'Standard Deviation',
    category: 'Statistical',
    description: 'Sample standard deviation of log-returns.',
  },
  {
    id: 'skewness',
    label: 'Skewness',
    category: 'Statistical',
    description: 'Fisher–Pearson skewness of log-returns.',
  },
  {
    id: 'kurtosis',
    label: 'Kurtosis',
    category: 'Statistical',
    description: 'Excess kurtosis of log-returns (normal = 0).',
  },
  {
    id: 'correlation',
    label: 'Correlation',
    category: 'Advanced',
    description: 'Pearson correlation of log-returns vs benchmark symbols.',
  },
  {
    id: 'volatility_clustering',
    label: 'Volatility Clustering',
    category: 'Advanced',
    description: 'Ljung–Box Q on squared returns at lag 10.',
  },
  {
    id: 'hurst',
    label: 'Hurst Exponent',
    category: 'Advanced',
    description: 'Rescaled-range estimate of long-memory (0.5 = random walk).',
  },
  {
    id: 'return_distribution',
    label: 'Return Distribution',
    category: 'Advanced',
    description: 'Histogram of log-returns.',
  },
] as const;

export const METRICS_BY_ID: Readonly<Record<MetricId, MetricDef>> =
  Object.fromEntries(METRICS.map(m => [m.id, m])) as Record<
    MetricId,
    MetricDef
  >;

export const METRIC_CATEGORIES: readonly MetricCategory[] = [
  'Risk',
  'Statistical',
  'Advanced',
] as const;
