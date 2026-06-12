/**
 * Holdings/attribution rows for the portfolio dashboard: one row per symbol
 * that was ever held or traded, joining its final weight (the holdings view)
 * with its exact P&L attribution and standalone Sharpe. Sorted by final
 * |weight| descending so open positions lead, closed ones follow.
 */
import type { PortfolioResult } from './types';

export type HoldingRow = {
  symbol: string;
  /** Signed final weight (0 for positions closed before the end). */
  weight: number;
  /** Exact P&L attribution in currency (costs included). */
  pnl: number;
  /** The symbol's standalone annualized Sharpe, if data existed for it. */
  sharpe: number | null;
};

export function buildHoldings(
  result: Pick<PortfolioResult, 'equity' | 'metrics'>,
): HoldingRow[] {
  const finalWeights =
    result.equity.length > 0
      ? result.equity[result.equity.length - 1].weights
      : {};
  const symbols = new Set([
    ...Object.keys(finalWeights),
    ...Object.keys(result.metrics.attribution_by_symbol),
  ]);
  const rows: HoldingRow[] = [...symbols].map(symbol => ({
    symbol,
    weight: finalWeights[symbol] ?? 0,
    pnl: result.metrics.attribution_by_symbol[symbol] ?? 0,
    sharpe: result.metrics.symbol_sharpes[symbol] ?? null,
  }));
  rows.sort(
    (a, b) =>
      Math.abs(b.weight) - Math.abs(a.weight) ||
      b.pnl - a.pnl ||
      a.symbol.localeCompare(b.symbol),
  );
  return rows;
}
