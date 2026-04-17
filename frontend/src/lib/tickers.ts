export enum TickerPriority {
  Ignore = 'ignore',
  Low = 'low',
  Normal = 'normal',
  High = 'high',
  Critical = 'critical',
}

export interface TrackedTicker {
  symbol: string;
  priority: TickerPriority;
}

export const PRIORITY_COLOURS: Record<TickerPriority, string> = {
  [TickerPriority.Ignore]: '#6b7280',
  [TickerPriority.Low]: '#60a5fa',
  [TickerPriority.Normal]: '#22c55e',
  [TickerPriority.High]: '#f59e0b',
  [TickerPriority.Critical]: '#ef4444',
};

export function getPriorityColour(priority: TickerPriority): string {
  return PRIORITY_COLOURS[priority];
}

export interface TickerGroup {
  name: string;
  tickers: TrackedTicker[];
}
