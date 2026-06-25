/**
 * TS mirror of the canonical sweep + walk-forward blobs produced by
 * `backend/backtesting/optimize/serialize.py`. Field names match the wire JSON.
 */
import type { BacktestResult } from '$lib/features/backtest/types';

export type ParamSchemaEntry =
  | { kind: 'int'; low: number; high: number; step: number }
  | { kind: 'float'; low: number; high: number; step: number }
  | { kind: 'choice'; options: (string | number)[] };

export type ParamSchema = Record<string, ParamSchemaEntry>;

export interface TrialRow {
  trial_id: number;
  params: Record<string, number | string>;
  metrics: Record<string, number | null>;
  cached: boolean;
}

export interface SweepConfig {
  search: 'grid' | 'random';
  metric: string;
  vary: string[];
  n_random: number;
  seed: number;
  starting_cash: number;
  data_version: string | null;
  fixed: Record<string, number | string>;
}

export interface SweepResultBlob {
  sweep_id: string;
  config: SweepConfig;
  trials: (TrialRow & { equity_hash: string })[];
  best_trial_id: number | null;
}

export interface SweepProgress {
  sweep_id: string;
  status: 'running' | 'done' | 'error' | 'cancelled';
  total: number;
  done: number;
  trials: TrialRow[];
  best_trial_id: number | null;
  error: string | null;
  result: SweepResultBlob | null;
}

export interface Window {
  index: number;
  is_start: number;
  is_end: number;
  oos_start: number;
  oos_end: number;
}

export interface WindowResult {
  window: Window;
  best_params: Record<string, number | string>;
  is_metric: number;
  oos_metrics: Record<string, number | null>;
}

export interface WalkForwardReport {
  metric: string;
  windows: WindowResult[];
  oos_metrics: Record<string, number | null>;
  is_aggregate: number;
  oos_aggregate: number;
}

export interface SweepFormValues {
  code: string;
  symbol: string;
  provider: string;
  period?: string;
  interval?: string;
  search: 'grid' | 'random';
  metric: string;
  vary: string[];
  fixed?: Record<string, number | string>;
  n_random?: number;
  seed?: number;
}

export interface SweepClient {
  schema(code: string): Promise<ParamSchema>;
  start(form: SweepFormValues): Promise<{ sweep_id: string }>;
  poll(sweepId: string): Promise<SweepProgress>;
  cancel(sweepId: string): Promise<void>;
  loadTrial(
    sweepId: string,
    trialId: number,
    form: SweepFormValues,
  ): Promise<BacktestResult>;
}
