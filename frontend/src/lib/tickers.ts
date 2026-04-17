export interface TrackedTicker {
  symbol: string;
}

export interface TickerGroup {
  name: string;
  tickers: TrackedTicker[];
}
