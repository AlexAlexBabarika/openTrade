/**
 * Unified OHLCV  (Open, High, Low, Close, Volume) candle (matches backend schema).
 */
export interface OHLCVCandle {
  symbol: string;
  timestamp: string; // ISO8601 UTC
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorPoint {
  timestamp: string;
  value: number;
}

export interface IndicatorResponse {
  symbol: string;
  indicator: string;
  period: number;
  points: IndicatorPoint[];
}
