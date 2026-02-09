"""
Technical indicators. Example: SMA.
Returns same-length series aligned with input candles.
"""

from backend.models import OHLCVCandle


def sma(candles: list[OHLCVCandle], period: int) -> list[float | None]:
    """
    Simple Moving Average of close price.
    Returns list of same length; first (period-1) values are None.
    """
    if period <= 0 or period > len(candles):
        return [None] * len(candles)
    out: list[float | None] = [None] * (period - 1)
    for i in range(period - 1, len(candles)):
        s = sum(candles[j].close for j in range(i - period + 1, i + 1))
        out.append(s / period)
    return out
