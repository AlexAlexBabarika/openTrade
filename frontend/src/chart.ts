import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  LineData,
  Time,
} from "lightweight-charts";
import type { OHLCVCandle } from "./types";

function isoToChartTime(iso: string): Time {
  return (new Date(iso).getTime() / 1000) as Time;
}

export function createChartContainer(parent: HTMLElement): IChartApi {
  const chart = createChart(parent, {
    layout: {
      background: { type: "solid", color: "#141414" },
      textColor: "#d1d4dc",
    },
    grid: {
      vertLines: { color: "#fffff720" },
      horzLines: { color: "#fffff720" },
    },
    rightPriceScale: {
      borderColor: "#fffff740",
      scaleMargins: { top: 0.1, bottom: 0.2 },
    },
    timeScale: {
      borderColor: "#fffff740",
      timeVisible: true,
      secondsVisible: false,
    },
    crosshair: {
      mode: 1,
    },
  });
  chart.timeScale().fitContent();
  return chart;
}

export function candleToSeries(c: OHLCVCandle): CandlestickData {
  return {
    time: isoToChartTime(c.timestamp),
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close,
  };
}

export function addCandlestickSeries(chart: IChartApi): ISeriesApi<"Candlestick"> {
  const series = chart.addCandlestickSeries({
    upColor: "#26a631",
    downColor: "#a62633",
    borderDownColor: "#a62633",
    borderUpColor: "#26a631",
    wickDownColor: "#c41d2e",
    wickUpColor: "#28c41d",
  });
  return series;
}

export function addLineSeries(chart: IChartApi, color: string): ISeriesApi<"Line"> {
  return chart.addLineSeries({ color });
}

export function linePoint(time: string, value: number): LineData {
  return { time: isoToChartTime(time), value };
}
