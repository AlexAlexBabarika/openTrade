/** POST /data/position-metrics plus client-side open P&L vs last close. */
export interface PositionMetricsResponse {
  riskPriceDistance: number;
  rewardPriceDistance: number;
  riskRewardRatio: number | null;
  quantity: number | null;
  profitAtTarget: number | null;
  lossAtStop: number | null;
  quantityCappedByLeverage: boolean;
  openPnl?: number | null;
}
