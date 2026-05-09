"""Pydantic response models for the analytics HTTP API.

Kept separate from ``backend.market.analytics`` (numeric core) so that the
compute layer has no FastAPI/Pydantic coupling.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_serializer


class ScalarMetricResponse(BaseModel):
    """Single-number metric (sharpe, sortino, variance, stdev, skewness,
    kurtosis, hurst)."""

    symbol: str
    metric: str
    value: float
    n: int = Field(..., description="Number of log-returns used")


class VaRResponse(BaseModel):
    symbol: str
    metric: str = "var"
    var_95: float
    var_99: float
    n: int


class DrawdownPointModel(BaseModel):
    timestamp: datetime
    value: float

    @field_serializer("timestamp")
    def _ser_ts(self, v: datetime) -> str:
        return v.strftime("%Y-%m-%dT%H:%M:%SZ")


class MaxDrawdownResponse(BaseModel):
    symbol: str
    metric: str = "max_drawdown"
    max_drawdown: float
    series: list[DrawdownPointModel]


class CorrelationRowModel(BaseModel):
    benchmark: str
    value: float


class CorrelationResponse(BaseModel):
    symbol: str
    metric: str = "correlation"
    rows: list[CorrelationRowModel]


class VolatilityClusteringResponse(BaseModel):
    symbol: str
    metric: str = "volatility_clustering"
    lag: int
    q: float
    p_value: float


class DistributionBinModel(BaseModel):
    left: float
    right: float
    count: int


class ReturnDistributionResponse(BaseModel):
    symbol: str
    metric: str = "return_distribution"
    bins: list[DistributionBinModel]
