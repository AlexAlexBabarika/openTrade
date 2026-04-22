// frontend/src/lib/drawables/coordMap.ts
import type { OHLCVCandle } from '$lib/core/types';
import type { IChartApi, ISeriesApi, Time } from 'lightweight-charts';
import type { CoordMap } from './types';

export function candleUnixSeconds(c: OHLCVCandle): number {
  return Math.floor(new Date(c.timestamp).getTime() / 1000);
}

/** Seconds per horizontal pixel from last two bars, else visible time span / plot width. */
function secPerPixel(
  chart: IChartApi,
  candles: readonly OHLCVCandle[],
): number {
  const ts = chart.timeScale();
  if (candles.length >= 2) {
    const tPrev = candleUnixSeconds(candles[candles.length - 2]);
    const tLast = candleUnixSeconds(candles[candles.length - 1]);
    const xPrev = ts.timeToCoordinate(tPrev as Time);
    const xLast = ts.timeToCoordinate(tLast as Time);
    if (xPrev != null && xLast != null) {
      const dx = xLast - xPrev;
      if (dx !== 0) {
        const s = (tLast - tPrev) / dx;
        if (Number.isFinite(s) && Math.abs(s) > 1e-9) return s;
      }
    }
  }
  const vr = ts.getVisibleRange();
  const w = chart.paneSize().width;
  if (vr && w > 0) {
    const from = vr.from as number;
    const to = vr.to as number;
    const span = to - from;
    if (Number.isFinite(span) && Math.abs(span) > 0) return span / w;
  }
  return 1;
}

/**
 * Map horizontal chart pixel to unix seconds, including empty space past the last bar.
 * Keeps placement and `CoordMap.xToTime` aligned with `timeToX` extrapolation.
 */
export function chartTimeAtCoordinate(
  chart: IChartApi,
  x: number,
  candles: readonly OHLCVCandle[],
): number | null {
  const ts = chart.timeScale();
  const raw = ts.coordinateToTime(x);
  const rawNum = raw == null ? null : (raw as number);

  if (candles.length >= 1) {
    const tLast = candleUnixSeconds(candles[candles.length - 1]);
    const xLast = ts.timeToCoordinate(tLast as Time);
    if (xLast != null && x > xLast) {
      const spp = secPerPixel(chart, candles);
      return tLast + (x - xLast) * spp;
    }
  }

  if (candles.length >= 2) {
    const tFirst = candleUnixSeconds(candles[0]);
    const xFirst = ts.timeToCoordinate(tFirst as Time);
    if (xFirst != null && x < xFirst) {
      const tSecond = candleUnixSeconds(candles[1]);
      const xSecond = ts.timeToCoordinate(tSecond as Time);
      let spp: number;
      if (xSecond != null && xSecond !== xFirst) {
        spp = (tSecond - tFirst) / (xSecond - xFirst);
      } else {
        spp = secPerPixel(chart, candles);
      }
      if (!Number.isFinite(spp) || Math.abs(spp) < 1e-9) {
        spp = secPerPixel(chart, candles);
      }
      return tFirst + (x - xFirst) * spp;
    }
  }

  if (
    rawNum != null &&
    candles.length >= 1 &&
    rawNum === candleUnixSeconds(candles[candles.length - 1])
  ) {
    const tLast = candleUnixSeconds(candles[candles.length - 1]);
    const xLast = ts.timeToCoordinate(tLast as Time);
    if (xLast != null && x > xLast) {
      const spp = secPerPixel(chart, candles);
      return tLast + (x - xLast) * spp;
    }
  }

  return rawNum;
}

/**
 * Build a CoordMap from a live lightweight-charts instance. Caller is
 * responsible for incrementing `version` when the chart's visible range,
 * zoom, or container size changes.
 *
 * Pass `candles` so x/time mapping matches extrapolation past the last bar.
 */
export function buildCoordMap(
  chart: IChartApi,
  priceSeries: ISeriesApi<'Candlestick' | 'Line'>,
  version: number,
  candles: readonly OHLCVCandle[] = [],
): CoordMap {
  const ts = chart.timeScale();
  return {
    version,
    plotWidth: chart.paneSize().width,
    plotHeight: chart.paneSize().height,
    timeToX: (t: number) => {
      if (candles.length >= 1) {
        const tLast = candleUnixSeconds(candles[candles.length - 1]);
        const tFirst = candleUnixSeconds(candles[0]);
        const spp = secPerPixel(chart, candles);
        if (t > tLast) {
          const xLast = ts.timeToCoordinate(tLast as Time);
          if (xLast == null) return null;
          return xLast + (t - tLast) / spp;
        }
        if (t < tFirst) {
          const xFirst = ts.timeToCoordinate(tFirst as Time);
          if (xFirst == null) return null;
          return xFirst + (t - tFirst) / spp;
        }
      }
      return ts.timeToCoordinate(t as Time);
    },
    xToTime: (x: number) => chartTimeAtCoordinate(chart, x, candles),
    priceToY: (p: number) => priceSeries.priceToCoordinate(p),
    yToPrice: (y: number) => priceSeries.coordinateToPrice(y),
  };
}
