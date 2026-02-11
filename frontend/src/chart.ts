import {
  createChart,
  IChartApi,
  ISeriesApi,
  LineData,
  CrosshairMode,
  ColorType
} from "lightweight-charts";
import { 
  isoToChartTime,
} from "./chartAdapters";

export function createChartContainer(parent: HTMLElement): IChartApi {
  const chart = createChart(parent, {
    layout: {
      background: { type: ColorType.Solid, color: "#141414" },
      textColor: "#d1d4dc",
    },
    grid: {
      vertLines: { color: "#fffff720" },
      horzLines: { color: "#fffff720" },
    },
    rightPriceScale: {
      borderColor: "#404040",
      scaleMargins: { top: 0.1, bottom: 0.2 },
    },
    timeScale: {
      borderColor: "#404040",
      timeVisible: true,
      secondsVisible: false,
    },
    crosshair: {
      mode: CrosshairMode.Magnet,
    },
  });
  chart.timeScale().fitContent();
  return chart;
}

export function addCandlestickSeries(chart: IChartApi): ISeriesApi<"Candlestick"> {
  const series = chart.addCandlestickSeries({
    upColor: "#26a631",
    downColor: "#c21a2a",
    borderDownColor: "#c21a2a",
    borderUpColor: "#26a631",
    wickDownColor: "#c21a2a",
    wickUpColor: "#28c41d",
  });
  return series;
}

export function addAreaSeries(chart: IChartApi): ISeriesApi<"Area"> {
  const series = chart.addAreaSeries({
    lastValueVisible: false,
    crosshairMarkerVisible: false,
    lineColor: 'transparent',
    topColor: 'rgba(56, 33, 110, 0.5)',
    bottomColor: 'rgba(56, 33, 110, 0.05)',
  });
  return series
}

export function addLineSeries(chart: IChartApi, color: string): ISeriesApi<"Line"> {
  return chart.addLineSeries({ color });
}

export function linePoint(time: string, value: number): LineData {
  return { time: isoToChartTime(time), value };
}
