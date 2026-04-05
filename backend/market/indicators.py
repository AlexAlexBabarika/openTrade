"""
Technical indicator calculations for OHLCV data.
"""

from backend.market.models import OHLCVCandle


def calculate_sma(
    candles: list[OHLCVCandle], period: int
) -> list[dict]:
    """Calculate Simple Moving Average from close prices.

    Returns list of {"timestamp": datetime, "value": float} for each point
    where enough data exists (i.e. starting from index period-1).
    """
    if period < 1:
        raise ValueError("Period must be at least 1")
    if len(candles) < period:
        return []

    results: list[dict] = []
    closes = [c.close for c in candles]
    window_sum = sum(closes[:period])
    results.append({
        "timestamp": candles[period - 1].timestamp,
        "value": round(window_sum / period, 6),
    })
    for i in range(period, len(candles)):
        window_sum += closes[i] - closes[i - period]
        results.append({
            "timestamp": candles[i].timestamp,
            "value": round(window_sum / period, 6),
        })
    return results


def calculate_ema(
    candles: list[OHLCVCandle], period: int
) -> list[dict]:
    """Calculate Exponential Moving Average from close prices.

    Uses SMA of the first `period` values as the initial EMA seed.
    Returns list of {"timestamp": datetime, "value": float}.
    """
    if period < 1:
        raise ValueError("Period must be at least 1")
    if len(candles) < period:
        return []

    closes = [c.close for c in candles]
    multiplier = 2.0 / (period + 1)

    # Seed EMA with SMA of first `period` values
    sma_seed = sum(closes[:period]) / period
    results: list[dict] = [{
        "timestamp": candles[period - 1].timestamp,
        "value": round(sma_seed, 6),
    }]

    ema_prev = sma_seed
    for i in range(period, len(candles)):
        ema_val = (closes[i] - ema_prev) * multiplier + ema_prev
        results.append({
            "timestamp": candles[i].timestamp,
            "value": round(ema_val, 6),
        })
        ema_prev = ema_val

    return results
