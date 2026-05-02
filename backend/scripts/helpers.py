"""Pure-polars helpers exposed to user scripts."""

from __future__ import annotations

import polars as pl


def crossover(a: pl.Series, b: pl.Series) -> pl.Series:
    """True where `a` crosses above `b` (current >= b, previous < b)."""
    prev_a = a.shift(1)
    prev_b = b.shift(1)
    return (a >= b) & (prev_a < prev_b)


def crossunder(a: pl.Series, b: pl.Series) -> pl.Series:
    """True where `a` crosses below `b`."""
    return crossover(b, a)


def rsi(series: pl.Series, period: int = 14) -> pl.Series:
    delta = series.diff()
    gain = delta.clip(lower_bound=0.0)
    loss = (-delta).clip(lower_bound=0.0)
    avg_gain = gain.ewm_mean(alpha=1 / period, adjust=False, min_periods=period)
    avg_loss = loss.ewm_mean(alpha=1 / period, adjust=False, min_periods=period)
    avg_loss_safe = pl.select(
        pl.when(avg_loss == 0.0).then(float("nan")).otherwise(avg_loss)
    ).to_series()
    rs = avg_gain / avg_loss_safe
    return 100.0 - (100.0 / (1.0 + rs))


def macd(
    series: pl.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pl.Series, pl.Series, pl.Series]:
    """Returns (macd_line, signal_line, histogram)."""
    ema_fast = series.ewm_mean(span=fast, adjust=False)
    ema_slow = series.ewm_mean(span=slow, adjust=False)
    line = ema_fast - ema_slow
    sig = line.ewm_mean(span=signal, adjust=False)
    return line, sig, line - sig


def bbands(
    series: pl.Series, period: int = 20, num_std: float = 2.0
) -> tuple[pl.Series, pl.Series, pl.Series]:
    """Returns (upper, middle, lower)."""
    middle = series.rolling_mean(period)
    std = series.rolling_std(period, ddof=0)
    return middle + num_std * std, middle, middle - num_std * std


def atr(
    high: pl.Series, low: pl.Series, close: pl.Series, period: int = 14
) -> pl.Series:
    prev_close = close.shift(1)
    tr1 = (high - low).abs()
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = (
        pl.DataFrame({"a": tr1, "b": tr2, "c": tr3})
        .select(pl.max_horizontal("a", "b", "c"))
        .to_series()
    )
    return tr.ewm_mean(alpha=1 / period, adjust=False, min_periods=period)
