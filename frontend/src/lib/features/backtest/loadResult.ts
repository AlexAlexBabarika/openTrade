/**
 * Parse and lightly validate a raw blob into a typed `BacktestResult`.
 *
 * The dashboard is a pure reader of the canonical blob; this is the single entry
 * point that turns an untyped value (a fixture import, or a future API response)
 * into the typed shape, failing loudly on a structurally wrong blob rather than
 * letting `undefined` leak into the UI.
 */
import type { BacktestResult } from './types';

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

/** Throws if `raw` is not a structurally valid `BacktestResult` blob. */
export function loadResult(raw: unknown): BacktestResult {
  if (!isObject(raw)) {
    throw new Error('Backtest result must be an object');
  }
  for (const key of ['bars', 'orders', 'fills', 'equity', 'trades'] as const) {
    if (!Array.isArray(raw[key])) {
      throw new Error(`Backtest result is missing array "${key}"`);
    }
  }
  if (!isObject(raw.meta)) {
    throw new Error('Backtest result is missing "meta"');
  }
  if (!isObject(raw.metrics)) {
    throw new Error('Backtest result is missing "metrics"');
  }
  return raw as unknown as BacktestResult;
}
