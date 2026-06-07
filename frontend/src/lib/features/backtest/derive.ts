/**
 * Pure derivations the dashboard needs but the blob does not pre-serialize:
 * per-episode drawdowns, the monthly/yearly returns grid, the underwater
 * series, and the buy-and-hold benchmark curve. Each is computed from the
 * serialized `equity`/`bars` using the same formulas as the backend
 * (`backend/backtesting/metrics.py`), so the dashboard stays a pure reader and
 * derived values reconcile with the pre-computed `metrics`.
 */
import type { BacktestBar, EquityPoint } from './types';

export interface DrawdownEpisode {
  start: number; // unix seconds of the prior peak
  trough: number; // unix seconds of the lowest point
  recovery: number | null; // unix seconds of recovery, or null if never recovered
  depth: number; // negative fraction (e.g. -0.13)
  length: number; // bars from peak to recovery (or to the end)
}

export interface TimeValue {
  t: number;
  value: number;
}

export interface MonthlyReturn {
  year: number;
  month: number; // 0-11 (UTC)
  ret: number;
}

export interface YearlyReturn {
  year: number;
  ret: number;
}

/** Every peak-to-recovery drawdown episode, in time order. Mirrors
 * `metrics.compute_drawdowns`. */
export function drawdownEpisodes(equity: EquityPoint[]): DrawdownEpisode[] {
  if (equity.length === 0) return [];
  const episodes: DrawdownEpisode[] = [];
  let peak = equity[0].value;
  let peakTime = equity[0].t;
  let peakIndex = 0;
  let inDd = false;
  let trough = peak;
  let troughTime = peakTime;
  for (let i = 0; i < equity.length; i++) {
    const p = equity[i];
    if (p.value >= peak) {
      if (inDd) {
        episodes.push({
          start: peakTime,
          trough: troughTime,
          recovery: p.t,
          depth: trough / peak - 1,
          length: i - peakIndex,
        });
        inDd = false;
      }
      peak = p.value;
      peakTime = p.t;
      peakIndex = i;
    } else {
      if (!inDd) {
        inDd = true;
        trough = p.value;
        troughTime = p.t;
      } else if (p.value < trough) {
        trough = p.value;
        troughTime = p.t;
      }
    }
  }
  if (inDd) {
    episodes.push({
      start: peakTime,
      trough: troughTime,
      recovery: null,
      depth: trough / peak - 1,
      length: equity.length - 1 - peakIndex,
    });
  }
  return episodes;
}

/** The `n` deepest drawdowns, deepest first. */
export function topDrawdowns(equity: EquityPoint[], n = 10): DrawdownEpisode[] {
  return [...drawdownEpisodes(equity)]
    .sort((a, b) => a.depth - b.depth)
    .slice(0, n);
}

/** Underwater series: equity as a fraction below its running peak (<= 0). */
export function underwaterSeries(equity: EquityPoint[]): TimeValue[] {
  let peak = equity.length ? equity[0].value : 0;
  return equity.map(p => {
    peak = Math.max(peak, p.value);
    return { t: p.t, value: peak ? p.value / peak - 1 : 0 };
  });
}

/**
 * Buy-and-hold benchmark equity, normalized so it starts at the same equity as
 * the strategy. `bars` and `equity` are bar-aligned in this engine, so the two
 * curves share an x-axis.
 */
export function benchmarkCurve(
  bars: BacktestBar[],
  startingEquity: number,
): TimeValue[] {
  if (bars.length === 0 || bars[0].close === 0) return [];
  const base = bars[0].close;
  return bars.map(b => ({ t: b.t, value: startingEquity * (b.close / base) }));
}

/**
 * Returns chained over calendar periods keyed by `keyOf(t)`. The end-of-period
 * equity is the last point in that period; the first period's base is the first
 * point's own equity, each later period's base is the prior period's end.
 * Mirrors `metrics._period_returns`.
 */
function periodReturns<K>(
  equity: EquityPoint[],
  keyOf: (date: Date) => K,
): { key: K; ret: number }[] {
  if (equity.length === 0) return [];
  const ends: { key: K; equity: number }[] = [];
  let lastKey: K | undefined;
  let started = false;
  for (const p of equity) {
    const key = keyOf(new Date(p.t * 1000));
    if (started && key === lastKey) {
      ends[ends.length - 1].equity = p.value;
    } else {
      ends.push({ key, equity: p.value });
      lastKey = key;
      started = true;
    }
  }
  const out: { key: K; ret: number }[] = [];
  let prev = equity[0].value;
  for (const e of ends) {
    out.push({ key: e.key, ret: prev ? e.equity / prev - 1 : 0 });
    prev = e.equity;
  }
  return out;
}

export function monthlyReturns(equity: EquityPoint[]): MonthlyReturn[] {
  return periodReturns(
    equity,
    d => `${d.getUTCFullYear()}-${d.getUTCMonth()}`,
  ).map(({ key, ret }) => {
    const [year, month] = key.split('-').map(Number);
    return { year, month, ret };
  });
}

export function yearlyReturns(equity: EquityPoint[]): YearlyReturn[] {
  return periodReturns(equity, d => d.getUTCFullYear()).map(({ key, ret }) => ({
    year: key,
    ret,
  }));
}

export interface MonthlyGrid {
  years: number[];
  /** `cells[year][month]` is the return, or `null` for months with no data. */
  cells: Record<number, (number | null)[]>;
  /** Full-year return per year, chained from monthly data. */
  yearTotals: Record<number, number>;
}

/** Years × 12 months grid for the heatmap, plus per-year totals. */
export function monthlyReturnsGrid(equity: EquityPoint[]): MonthlyGrid {
  const months = monthlyReturns(equity);
  const years = [...new Set(months.map(m => m.year))].sort((a, b) => a - b);
  const cells: Record<number, (number | null)[]> = {};
  for (const y of years) cells[y] = Array<number | null>(12).fill(null);
  for (const m of months) cells[m.year][m.month] = m.ret;
  const yearTotals: Record<number, number> = {};
  for (const { year, ret } of yearlyReturns(equity)) yearTotals[year] = ret;
  return { years, cells, yearTotals };
}
