/**
 * HTTP wrapper for the portfolio backtest endpoint
 * (`POST /portfolio-backtests/run`). Bundled into a `PortfolioClient` so
 * `PortfolioState` tests can stub the network, mirroring `StrategyClient`.
 */
import { apiJson } from '$lib/core/api';
import type { MarketDataProviderValue } from '$lib/features/market/marketDataProviders';
import type { PortfolioResult } from './types';

/** Mirrors the route's `ConstraintsModel`; omitted fields mean "no limit". */
export type PortfolioConstraintsBody = {
  max_position_weight?: number | null;
  max_position_value?: number | null;
  max_sector_weight?: number | null;
  sectors?: Record<string, string>;
  long_only?: boolean;
  no_short?: string[];
  no_trade?: string[];
  max_gross?: number | null;
  max_net?: number | null;
  min_trade_value?: number;
};

export type PortfolioRunParams = {
  code: string;
  symbols: string[];
  provider: MarketDataProviderValue;
  period?: string;
  interval?: string;
  starting_cash?: number;
  seed?: number;
  params?: Record<string, number | string>;
  constraints?: PortfolioConstraintsBody;
};

/** The canonical portfolio blob plus the sandbox run envelope. */
export type PortfolioRunResponse = PortfolioResult & {
  status: 'ok' | 'error' | 'timeout' | 'killed';
  stdout: string;
  stderr: string;
  elapsed_ms: number;
};

/** Mirrors the backend `IngestReport` returned by `POST /datastore/ingest`. */
export type IngestReport = {
  data_version: string;
  rows_written: Record<string, number>;
  quarantined: Record<string, number>;
  gap_warnings: string[];
};

export function ingestSymbols(
  symbols: string[],
  interval = '1d',
): Promise<IngestReport> {
  return apiJson<IngestReport>(
    '/datastore/ingest',
    { method: 'POST', body: JSON.stringify({ symbols, interval }) },
    true,
  );
}

export function runPortfolioBacktest(
  params: PortfolioRunParams,
): Promise<PortfolioRunResponse> {
  return apiJson<PortfolioRunResponse>(
    '/portfolio-backtests/run',
    { method: 'POST', body: JSON.stringify(params) },
    true,
  );
}

export type PortfolioClient = {
  run(params: PortfolioRunParams): Promise<PortfolioRunResponse>;
  ingest(symbols: string[], interval?: string): Promise<IngestReport>;
};

export const httpPortfolioClient: PortfolioClient = {
  run: runPortfolioBacktest,
  ingest: ingestSymbols,
};
