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

export enum movingAverageType {
  SMA = 'sma',
  EMA = 'ema',
}

export interface BollingerBandsPoint {
  timestamp: string;
  upper: number;
  middle: number;
  lower: number;
}

export interface BollingerBandsResponse {
  symbol: string;
  indicator: string;
  period: number;
  num_std: number;
  points: BollingerBandsPoint[];
}
