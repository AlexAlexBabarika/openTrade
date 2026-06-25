"""Read-time corporate-action adjustment.

Store raw OHLCV; compute a cumulative back-adjustment factor from the actions
table so the *adjusted* series is continuous (what the strategy sees for
signals), while the *raw* prices are preserved (``raw_open`` ... ``raw_volume``)
for fills and cost models.

Convention (back-adjustment):
  - A bar at time ``t`` is adjusted by every action whose ``ex_date > t``.
  - split ratio ``r``  -> price factor ``1/r``, volume factor ``r``.
  - dividend ``d``     -> price factor ``(close_prev - d) / close_prev`` where
    ``close_prev`` is the raw close of the last bar strictly before ``ex_date``.
Prices on/after the last action are unchanged (factor 1.0).
"""

from __future__ import annotations

import polars as pl

ADJUST_LOGIC_VERSION = "1"

_PRICE_COLS = ("open", "high", "low", "close")


def back_adjust(bars: pl.DataFrame, actions: pl.DataFrame) -> pl.DataFrame:
    """Return ``bars`` with adjusted OHLCV and raw_* columns preserved."""
    bars = bars.sort("timestamp")
    raw = {c: bars[c].to_list() for c in (*_PRICE_COLS, "volume")}
    times = bars["timestamp"].to_list()
    closes = raw["close"]

    # One (ex_date, price_factor_step, volume_factor_step) per action.
    steps: list[tuple] = []
    for row in actions.sort("ex_date").iter_rows(named=True):
        ex = row["ex_date"]
        if row["kind"] == "split":
            r = float(row["value"])
            steps.append((ex, 1.0 / r, r))
        elif row["kind"] == "dividend":
            d = float(row["value"])
            prev_close = _last_close_before(times, closes, ex)
            f = 1.0 if not prev_close else (prev_close - d) / prev_close
            steps.append((ex, f, 1.0))

    price_factor: list[float] = []
    volume_factor: list[float] = []
    for t in times:
        pf = vf = 1.0
        for ex, pstep, vstep in steps:
            if ex > t:
                pf *= pstep
                vf *= vstep
        price_factor.append(pf)
        volume_factor.append(vf)

    out = bars.clone()
    out = out.rename({c: f"raw_{c}" for c in (*_PRICE_COLS, "volume")})
    pf_s = pl.Series("__pf", price_factor)
    vf_s = pl.Series("__vf", volume_factor)
    out = out.with_columns(
        [(pl.col(f"raw_{c}") * pf_s).alias(c) for c in _PRICE_COLS]
        + [(pl.col("raw_volume") * vf_s).alias("volume")]
    )
    return out


def _last_close_before(times: list, closes: list, ex) -> float | None:
    prev = None
    for t, c in zip(times, closes):
        if t < ex:
            prev = c
        else:
            break
    return prev
