// frontend/src/lib/drawables/coordMap.ts
import type { IChartApi, ISeriesApi, Time } from 'lightweight-charts';
import type { CoordMap } from './types';

/**
 * Build a CoordMap from a live lightweight-charts instance. Caller is
 * responsible for incrementing `version` when the chart's visible range,
 * zoom, or container size changes.
 */
export function buildCoordMap(
  chart: IChartApi,
  priceSeries: ISeriesApi<'Candlestick' | 'Line'>,
  version: number,
): CoordMap {
  return {
    version,
    timeToX: (t: number) => chart.timeScale().timeToCoordinate(t as Time),
    xToTime: (x: number) => {
      const t = chart.timeScale().coordinateToTime(x);
      return t == null ? null : (t as number);
    },
    priceToY: (p: number) => priceSeries.priceToCoordinate(p),
    yToPrice: (y: number) => priceSeries.coordinateToPrice(y),
  };
}
