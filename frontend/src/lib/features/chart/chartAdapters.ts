import type {
  AreaData,
  CandlestickData,
  HistogramData,
  Time,
} from 'lightweight-charts';
import { DEFAULT_CHART_COLOURS } from './chartDefaults';
import type { OHLCVCandle } from '$lib/core/types';

export function isoToChartTime(iso: string): Time {
  return (new Date(iso).getTime() / 1000) as Time;
}

export function candleOHLCVtoAreaData(c: OHLCVCandle): AreaData {
  return {
    time: isoToChartTime(c.timestamp),
    value: c.close,
  };
}

export function candleOHLCVtoCandlestickData(c: OHLCVCandle): CandlestickData {
  return {
    time: isoToChartTime(c.timestamp),
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close,
  };
}

export function candleOHLCVtoVolumeData(
  c: OHLCVCandle,
  volumeUpColor?: string,
  volumeDownColor?: string,
): HistogramData {
  return {
    time: isoToChartTime(c.timestamp),
    value: c.volume,
    color:
      c.close > c.open
        ? (volumeUpColor ?? DEFAULT_CHART_COLOURS.volumeUp)
        : (volumeDownColor ?? DEFAULT_CHART_COLOURS.volumeDown),
  };
}
