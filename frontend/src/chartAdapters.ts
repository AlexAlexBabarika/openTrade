import { AreaData, CandlestickData, HistogramData, Time } from "lightweight-charts";
import { OHLCVCandle } from "./types";

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

export function candleOHLCVtoVolumeData(c: OHLCVCandle): HistogramData {
    return {
        time: isoToChartTime(c.timestamp),
        value: c.volume,
        color: c.close > c.open ? '#26a63130' : '#c21a2a30',
    };
}