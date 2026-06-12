/**
 * Weights-over-time heatmap data: symbols on Y, time on X, value = signed
 * weight. Equity points are bucketed down to at most `maxCols` columns (each
 * bucket reports its last point's weights — "weights at end of bucket") so a
 * ten-year daily run stays a few thousand SVG rects, not a hundred thousand.
 * Rows are ordered by peak |weight| descending so the heaviest names sit on
 * top.
 */
import type { PortfolioEquityPoint } from './types';

export type HeatmapData = {
  symbols: string[];
  /** Bucket timestamps (unix seconds, the last point of each bucket). */
  times: number[];
  /** rows[symbolIndex][columnIndex] = signed weight at that bucket. */
  rows: number[][];
  /** Largest |weight| anywhere, for color scaling (0 when flat). */
  maxAbs: number;
};

export function buildHeatmap(
  equity: PortfolioEquityPoint[],
  maxCols = 120,
): HeatmapData {
  if (equity.length === 0) {
    return { symbols: [], times: [], rows: [], maxAbs: 0 };
  }

  const bucketSize = Math.max(1, Math.ceil(equity.length / maxCols));
  const buckets: PortfolioEquityPoint[] = [];
  for (let i = bucketSize - 1; i < equity.length; i += bucketSize) {
    buckets.push(equity[i]);
  }
  if (buckets[buckets.length - 1] !== equity[equity.length - 1]) {
    buckets.push(equity[equity.length - 1]);
  }

  const peak = new Map<string, number>();
  for (const point of buckets) {
    for (const [symbol, weight] of Object.entries(point.weights)) {
      peak.set(symbol, Math.max(peak.get(symbol) ?? 0, Math.abs(weight)));
    }
  }
  const symbols = [...peak.keys()].sort(
    (a, b) => peak.get(b)! - peak.get(a)! || a.localeCompare(b),
  );

  const rows = symbols.map(symbol =>
    buckets.map(point => point.weights[symbol] ?? 0),
  );
  const maxAbs = Math.max(0, ...peak.values());
  return { symbols, times: buckets.map(p => p.t), rows, maxAbs };
}
