import type { OHLCVCandle } from '../../../types';

export interface RulerGeometry {
  startTime: number;
  endTime: number;
  startPrice: number;
  endPrice: number;
}

export interface RulerStats {
  priceDelta: number;
  pctDelta: number;
  barCount: number;
  spanLabel: string;
  volumeSum: number;
  isUp: boolean;
}

function formatSpan(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  if (days > 0) return hours > 0 ? `${days}d ${hours}h` : `${days}d`;
  if (hours > 0) return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
  if (minutes > 0) return `${minutes}m`;
  return `${s}s`;
}

export function computeStats(
  geo: RulerGeometry,
  candles: readonly OHLCVCandle[],
): RulerStats {
  const priceDelta = geo.endPrice - geo.startPrice;
  const pctDelta =
    geo.startPrice !== 0 ? (priceDelta / geo.startPrice) * 100 : 0;
  const tMin = Math.min(geo.startTime, geo.endTime);
  const tMax = Math.max(geo.startTime, geo.endTime);

  let barCount = 0;
  let volumeSum = 0;
  for (const c of candles) {
    const t = new Date(c.timestamp).getTime() / 1000;
    if (t >= tMin && t <= tMax) {
      barCount += 1;
      volumeSum += c.volume;
    }
  }

  return {
    priceDelta,
    pctDelta,
    barCount,
    spanLabel: formatSpan(tMax - tMin),
    volumeSum,
    isUp: priceDelta >= 0,
  };
}

export function formatPriceDelta(n: number): string {
  const sign = n >= 0 ? '+' : '−';
  return `${sign}${Math.abs(n).toFixed(2)}`;
}

export function formatPct(n: number): string {
  const sign = n >= 0 ? '+' : '−';
  return `${sign}${Math.abs(n).toFixed(2)}%`;
}

export function formatVolume(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${(n / 1e3).toFixed(2)}K`;
  return n.toFixed(0);
}
