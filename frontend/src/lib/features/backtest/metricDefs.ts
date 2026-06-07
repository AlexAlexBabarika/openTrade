/**
 * Declarative descriptions of every metric in the blob: a label, how to format
 * it, and whether it should be sign-tinted (green/red). The headline strip and
 * the grouped stats grid both read from here so a metric is defined once.
 */
import {
  formatBars,
  formatInt,
  formatPct,
  formatRatio,
  formatSignedCurrency,
  formatSignedPct,
  signOf,
  type Sign,
} from './format';
import type { BacktestMetrics } from './types';

type MetricKind = 'pct' | 'signedPct' | 'ratio' | 'currency' | 'int' | 'bars';

export interface MetricSpec {
  key: keyof BacktestMetrics;
  label: string;
  kind: MetricKind;
  /** 'signed' tints by the value's sign; 'neutral' is never tinted. */
  tone: 'signed' | 'neutral';
}

export function formatMetric(kind: MetricKind, value: number | null): string {
  switch (kind) {
    case 'pct':
      return formatPct(value);
    case 'signedPct':
      return formatSignedPct(value);
    case 'ratio':
      return formatRatio(value);
    case 'currency':
      return formatSignedCurrency(value);
    case 'int':
      return formatInt(value);
    case 'bars':
      return formatBars(value);
  }
}

/** Sign bucket for tinting, or 'zero' for neutral-tone metrics. */
export function metricSign(spec: MetricSpec, value: number | null): Sign {
  return spec.tone === 'signed' ? signOf(value) : 'zero';
}

/** The 6-8 headline numbers for pane 1. */
export const HEADLINE_METRICS: MetricSpec[] = [
  {
    key: 'total_return',
    label: 'Total return',
    kind: 'signedPct',
    tone: 'signed',
  },
  { key: 'cagr', label: 'CAGR', kind: 'signedPct', tone: 'signed' },
  { key: 'sharpe', label: 'Sharpe', kind: 'ratio', tone: 'signed' },
  { key: 'sortino', label: 'Sortino', kind: 'ratio', tone: 'signed' },
  { key: 'max_drawdown', label: 'Max drawdown', kind: 'pct', tone: 'signed' },
  { key: 'win_rate', label: 'Win rate', kind: 'pct', tone: 'neutral' },
  {
    key: 'profit_factor',
    label: 'Profit factor',
    kind: 'ratio',
    tone: 'neutral',
  },
  {
    key: 'pct_time_in_market',
    label: 'Exposure',
    kind: 'pct',
    tone: 'neutral',
  },
];

export interface MetricGroup {
  title: string;
  metrics: MetricSpec[];
}

/** The full taxonomy, grouped for the stats grid. */
export const METRIC_GROUPS: MetricGroup[] = [
  {
    title: 'Return',
    metrics: [
      {
        key: 'total_return',
        label: 'Total return',
        kind: 'signedPct',
        tone: 'signed',
      },
      { key: 'cagr', label: 'CAGR', kind: 'signedPct', tone: 'signed' },
      {
        key: 'avg_annual_return',
        label: 'Avg annual',
        kind: 'signedPct',
        tone: 'signed',
      },
      {
        key: 'best_month',
        label: 'Best month',
        kind: 'signedPct',
        tone: 'signed',
      },
      {
        key: 'worst_month',
        label: 'Worst month',
        kind: 'signedPct',
        tone: 'signed',
      },
      {
        key: 'best_year',
        label: 'Best year',
        kind: 'signedPct',
        tone: 'signed',
      },
      {
        key: 'worst_year',
        label: 'Worst year',
        kind: 'signedPct',
        tone: 'signed',
      },
      {
        key: 'pct_positive_months',
        label: '% positive months',
        kind: 'pct',
        tone: 'neutral',
      },
      {
        key: 'pct_positive_years',
        label: '% positive years',
        kind: 'pct',
        tone: 'neutral',
      },
    ],
  },
  {
    title: 'Risk-adjusted',
    metrics: [
      { key: 'sharpe', label: 'Sharpe', kind: 'ratio', tone: 'signed' },
      { key: 'sortino', label: 'Sortino', kind: 'ratio', tone: 'signed' },
      { key: 'calmar', label: 'Calmar', kind: 'ratio', tone: 'signed' },
      {
        key: 'information_ratio',
        label: 'Information ratio',
        kind: 'ratio',
        tone: 'signed',
      },
    ],
  },
  {
    title: 'Drawdown',
    metrics: [
      {
        key: 'max_drawdown',
        label: 'Max drawdown',
        kind: 'pct',
        tone: 'signed',
      },
      {
        key: 'max_drawdown_length',
        label: 'Max DD length',
        kind: 'bars',
        tone: 'neutral',
      },
      {
        key: 'avg_drawdown',
        label: 'Avg drawdown',
        kind: 'pct',
        tone: 'signed',
      },
      {
        key: 'time_underwater',
        label: 'Time underwater',
        kind: 'pct',
        tone: 'neutral',
      },
      {
        key: 'recovery_factor',
        label: 'Recovery factor',
        kind: 'ratio',
        tone: 'signed',
      },
    ],
  },
  {
    title: 'Trade quality',
    metrics: [
      { key: 'win_rate', label: 'Win rate', kind: 'pct', tone: 'neutral' },
      { key: 'avg_win', label: 'Avg win', kind: 'currency', tone: 'signed' },
      { key: 'avg_loss', label: 'Avg loss', kind: 'currency', tone: 'signed' },
      {
        key: 'win_loss_ratio',
        label: 'Win/loss ratio',
        kind: 'ratio',
        tone: 'neutral',
      },
      {
        key: 'profit_factor',
        label: 'Profit factor',
        kind: 'ratio',
        tone: 'neutral',
      },
      {
        key: 'expectancy',
        label: 'Expectancy',
        kind: 'currency',
        tone: 'signed',
      },
      {
        key: 'max_consecutive_wins',
        label: 'Max consec. wins',
        kind: 'int',
        tone: 'neutral',
      },
      {
        key: 'max_consecutive_losses',
        label: 'Max consec. losses',
        kind: 'int',
        tone: 'neutral',
      },
      {
        key: 'avg_bars_held_winners',
        label: 'Avg bars (win)',
        kind: 'bars',
        tone: 'neutral',
      },
      {
        key: 'avg_bars_held_losers',
        label: 'Avg bars (loss)',
        kind: 'bars',
        tone: 'neutral',
      },
    ],
  },
  {
    title: 'Exposure',
    metrics: [
      {
        key: 'pct_time_in_market',
        label: 'Time in market',
        kind: 'pct',
        tone: 'neutral',
      },
      {
        key: 'avg_position_pct',
        label: 'Avg position size',
        kind: 'pct',
        tone: 'neutral',
      },
      {
        key: 'max_leverage',
        label: 'Max leverage',
        kind: 'ratio',
        tone: 'neutral',
      },
    ],
  },
];
