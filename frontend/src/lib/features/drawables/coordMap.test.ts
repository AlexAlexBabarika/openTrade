import { describe, expect, it } from 'vitest';
import type { IChartApi, ISeriesApi, Time } from 'lightweight-charts';
import type { OHLCVCandle } from '$lib/core/types';
import {
  buildCoordMap,
  candleUnixSeconds,
  chartTimeAtCoordinate,
} from './coordMap';

function makeCandles(times: number[]): OHLCVCandle[] {
  return times.map((t, i) => ({
    symbol: 'TEST',
    timestamp: new Date(t * 1000).toISOString(),
    open: 100 + i,
    high: 101 + i,
    low: 99 + i,
    close: 100.5 + i,
    volume: 1000,
  }));
}

function mockChart(opts: {
  coordinateToTime: (x: number) => Time | null;
  timeToCoordinate: (t: Time) => number | null;
  visibleRange?: { from: Time; to: Time } | null;
  paneWidth?: number;
  paneHeight?: number;
}): IChartApi {
  const w = opts.paneWidth ?? 800;
  const h = opts.paneHeight ?? 400;
  return {
    timeScale: () => ({
      coordinateToTime: opts.coordinateToTime,
      timeToCoordinate: opts.timeToCoordinate,
      getVisibleRange: () =>
        opts.visibleRange ?? { from: 1000 as Time, to: 2000 as Time },
    }),
    paneSize: () => ({ width: w, height: h }),
  } as unknown as IChartApi;
}

const mockPriceSeries = {} as ISeriesApi<'Candlestick' | 'Line'>;

describe('chartTimeAtCoordinate', () => {
  it('extrapolates time when x is past the last bar pixel', () => {
    const t0 = 1_700_000_000;
    const t1 = 1_700_000_900;
    const candles = makeCandles([t0, t1]);
    const chart = mockChart({
      coordinateToTime: x => {
        if (x <= 100) return t1 as Time;
        return t1 as Time;
      },
      timeToCoordinate: t => {
        if (t === (t0 as Time)) return 0;
        if (t === (t1 as Time)) return 100;
        return null;
      },
      visibleRange: { from: t0 as Time, to: t1 as Time },
      paneWidth: 800,
    });

    const tAt120 = chartTimeAtCoordinate(chart, 120, candles);
    expect(tAt120).not.toBeNull();
    expect(tAt120!).toBeGreaterThan(t1);
    const spp = (t1 - t0) / 100;
    expect(tAt120!).toBeCloseTo(t1 + 20 * spp, 5);
  });

  it('returns library time when x is not past the last bar', () => {
    const t0 = 1_700_000_000;
    const t1 = 1_700_000_900;
    const candles = makeCandles([t0, t1]);
    const chart = mockChart({
      coordinateToTime: x => (x < 50 ? (t0 as Time) : (t1 as Time)),
      timeToCoordinate: t => {
        if (t === (t0 as Time)) return 0;
        if (t === (t1 as Time)) return 100;
        return null;
      },
    });

    expect(chartTimeAtCoordinate(chart, 80, candles)).toBe(t1);
  });

  it('extrapolates left of first bar when x is left of first pixel', () => {
    const t0 = 1_700_000_000;
    const t1 = 1_700_000_900;
    const t2 = 1_700_001_800;
    const candles = makeCandles([t0, t1, t2]);
    const chart = mockChart({
      coordinateToTime: () => t0 as Time,
      timeToCoordinate: t => {
        if (t === (t0 as Time)) return 100;
        if (t === (t1 as Time)) return 200;
        if (t === (t2 as Time)) return 300;
        return null;
      },
    });

    const left = chartTimeAtCoordinate(chart, 50, candles);
    expect(left).not.toBeNull();
    const spp = (t1 - t0) / 100;
    expect(left!).toBeCloseTo(t0 - 50 * spp, 5);
  });
});

describe('buildCoordMap with candles', () => {
  it('timeToX and xToTime round-trip for a synthetic future time', () => {
    const t0 = 1_700_000_000;
    const t1 = 1_700_000_900;
    const candles = makeCandles([t0, t1]);
    const chart = mockChart({
      coordinateToTime: x => (x <= 100 ? (t1 as Time) : (t1 as Time)),
      timeToCoordinate: t => {
        if (t === (t0 as Time)) return 0;
        if (t === (t1 as Time)) return 100;
        return null;
      },
      visibleRange: { from: t0 as Time, to: t1 as Time },
    });

    const map = buildCoordMap(chart, mockPriceSeries, 1, candles);
    const futureT = t1 + 3600;
    const x = map.timeToX(futureT);
    expect(x).not.toBeNull();
    const back = map.xToTime(x!);
    expect(back).not.toBeNull();
    expect(back!).toBeCloseTo(futureT, 3);
  });

  it('candleUnixSeconds matches floor seconds from ISO timestamp', () => {
    const c = makeCandles([1_700_000_123])[0];
    expect(candleUnixSeconds(c)).toBe(1_700_000_123);
  });

  it('timeToX extrapolates past last bar when timeToCoordinate clamps future times', () => {
    const t0 = 1_700_000_000;
    const t1 = 1_700_000_900;
    const candles = makeCandles([t0, t1]);
    const chart = mockChart({
      coordinateToTime: () => t1 as Time,
      timeToCoordinate: t => {
        const tn = t as number;
        if (tn === t0) return 0;
        if (tn === t1) return 100;
        if (tn > t1) return 100;
        return null;
      },
      visibleRange: { from: t0 as Time, to: t1 as Time },
    });

    const map = buildCoordMap(chart, mockPriceSeries, 1, candles);
    const xAtLast = map.timeToX(t1);
    expect(xAtLast).toBe(100);
    const xa = map.timeToX(t1 + 100);
    const xb = map.timeToX(t1 + 500);
    expect(xa).not.toBeNull();
    expect(xb).not.toBeNull();
    expect(xa!).toBeGreaterThan(100);
    expect(xb!).toBeGreaterThan(xa!);
  });
});
