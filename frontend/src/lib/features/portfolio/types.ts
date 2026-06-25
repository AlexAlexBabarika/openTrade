/**
 * TypeScript mirror of the canonical portfolio run blob produced by the
 * backend (`backend/backtesting/multi/serialize.py::portfolio_result_to_dict`).
 * Field names and casing match the JSON on the wire; bar/equity/constraint
 * timestamps are unix seconds (`t`). Orders/fills/trades reuse the
 * single-run shapes plus their `symbol` stamp.
 */

import type {
  BacktestBar,
  BacktestFill,
  BacktestMetrics,
  BacktestOrder,
  BacktestTrade,
  RunMeta,
} from '$lib/features/backtest/types';

export interface PortfolioEquityPoint {
  t: number; // unix seconds (UTC)
  value: number;
  cash: number;
  holdings: number;
  /** Signed weight per open symbol as a fraction of equity. */
  weights: Record<string, number>;
}

export interface ConstraintEvent {
  t: number; // unix seconds (UTC)
  constraint: string;
  symbol: string | null;
  requested: number;
  /** `null` when the action was dropped (no-trade target, skipped dust trade). */
  applied: number | null;
  detail: string;
}

export interface SectorExposurePoint {
  t: number; // unix seconds (UTC)
  exposures: Record<string, number>;
}

export interface TurnoverPoint {
  index: number; // event index that traded
  turnover: number; // traded value / equity at that event
}

export interface PortfolioMetrics {
  /** Full single-run taxonomy computed on the portfolio equity curve. */
  portfolio: BacktestMetrics;
  symbol_sharpes: Record<string, number>;
  avg_hhi: number;
  max_hhi: number;
  avg_top5_weight: number;
  max_top5_weight: number;
  max_single_name_weight: number;
  correlation_symbols: string[];
  correlation_matrix: number[][];
  sector_exposure: SectorExposurePoint[];
  turnover_annualized: number;
  turnover_per_event: TurnoverPoint[];
  attribution_by_symbol: Record<string, number>;
  attribution_by_sector: Record<string, number>;
}

export interface PortfolioResult {
  meta: RunMeta;
  symbols: string[];
  bars: Record<string, BacktestBar[]>;
  orders: (BacktestOrder & { symbol: string | null })[];
  fills: (BacktestFill & { symbol: string | null })[];
  equity: PortfolioEquityPoint[];
  trades: (BacktestTrade & { symbol: string | null })[];
  constraint_events: ConstraintEvent[];
  metrics: PortfolioMetrics;
}
