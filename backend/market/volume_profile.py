"""
Volume Profile math — candle-distribution algorithm (path A).

Given a list of OHLCV candles, build a price-axis histogram:
- each candle's volume is spread uniformly across [low, high]
- each price bin has volume_size = row_size
- up/down volume split per candle direction (close >= open)

Pure numpy; no I/O, no logging.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.market.models import OHLCVCandle


@dataclass(frozen=True)
class ProfileBin:
    price: float  # lower edge of the bin
    up_vol: float
    down_vol: float


@dataclass(frozen=True)
class ProfileResult:
    row_size: float
    price_min: float
    price_max: float
    bins: list[ProfileBin]
    poc: float
    vah: float
    val: float


def bin_from_candle_distribution(
    candles: list[OHLCVCandle],
    row_size: float,
    va_pct: float,
) -> ProfileResult:
    """Bin candle volumes across their H-L range into price rows.

    - `row_size` > 0 (price units).
    - `va_pct` in (0, 1]. 0.7 = 70% value area.
    - Empty `candles` -> zero-bin result at price 0.

    Returns bin lower-edges starting at `floor(min_low / row_size) * row_size`.
    """
    if row_size <= 0:
        raise ValueError("row_size must be > 0")
    if not (0 < va_pct <= 1):
        raise ValueError("va_pct must be in (0, 1]")
    if not candles:
        return ProfileResult(
            row_size=row_size,
            price_min=0.0,
            price_max=0.0,
            bins=[],
            poc=0.0,
            vah=0.0,
            val=0.0,
        )

    lows = np.array([c.low for c in candles], dtype=np.float64)
    highs = np.array([c.high for c in candles], dtype=np.float64)
    opens = np.array([c.open for c in candles], dtype=np.float64)
    closes = np.array([c.close for c in candles], dtype=np.float64)
    vols = np.array([c.volume for c in candles], dtype=np.float64)

    price_min = float(np.floor(lows.min() / row_size) * row_size)
    price_max = float(np.ceil(highs.max() / row_size) * row_size)
    n_bins = max(1, int(round((price_max - price_min) / row_size)))

    up_vol = np.zeros(n_bins, dtype=np.float64)
    down_vol = np.zeros(n_bins, dtype=np.float64)

    for i in range(len(candles)):
        lo = lows[i]
        hi = highs[i]
        vol = vols[i]
        if vol <= 0:
            continue
        span = hi - lo
        if span <= 0:
            # Degenerate candle (doji with H==L): drop volume into the one bin.
            idx = int((lo - price_min) / row_size)
            idx = max(0, min(n_bins - 1, idx))
            if closes[i] >= opens[i]:
                up_vol[idx] += vol
            else:
                down_vol[idx] += vol
            continue
        first = int((lo - price_min) / row_size)
        last = int((hi - price_min) / row_size)
        first = max(0, min(n_bins - 1, first))
        last = max(0, min(n_bins - 1, last))
        count = last - first + 1
        share = vol / count
        if closes[i] >= opens[i]:
            up_vol[first : last + 1] += share
        else:
            down_vol[first : last + 1] += share

    total = up_vol + down_vol
    poc_idx = int(np.argmax(total))
    poc_price = price_min + poc_idx * row_size

    grand_total = float(total.sum())
    target = grand_total * va_pct

    # Expand outward from POC, greedily grabbing the heavier neighbour.
    lo_idx = poc_idx
    hi_idx = poc_idx
    captured = float(total[poc_idx])
    while captured < target and (lo_idx > 0 or hi_idx < n_bins - 1):
        left = float(total[lo_idx - 1]) if lo_idx > 0 else -1.0
        right = float(total[hi_idx + 1]) if hi_idx < n_bins - 1 else -1.0
        if left < 0 and right < 0:
            break
        if right >= left:
            hi_idx += 1
            captured += float(total[hi_idx])
        else:
            lo_idx -= 1
            captured += float(total[lo_idx])

    val_price = price_min + lo_idx * row_size
    vah_price = price_min + hi_idx * row_size

    bins = [
        ProfileBin(
            price=price_min + i * row_size,
            up_vol=float(up_vol[i]),
            down_vol=float(down_vol[i]),
        )
        for i in range(n_bins)
    ]

    return ProfileResult(
        row_size=row_size,
        price_min=price_min,
        price_max=price_max,
        bins=bins,
        poc=poc_price,
        vah=vah_price,
        val=val_price,
    )
