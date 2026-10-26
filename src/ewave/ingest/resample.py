"""1m -> 15m/1h/4h/1d bars.

Rules (verified against the exchanges' own candles):
  * Bars are UTC-aligned, left-closed and labelled by their open time. None crosses a day boundary.
  * open/high/low/close are built from *traded* minutes only (volume > 0). Venues return no-trade minutes as flat
    candles at the previous close; including them would invent opens and extremes.
  * A bar without any traded minute is flat at the carried close (the last traded close before it).
  * ``ts_high`` / ``ts_low`` are the first traded minutes at the bar's high / low; ``hl_order`` says which came first.
  * ``complete`` is decided from ``covered_until`` (what a successful fetch really covered), never from the wall clock.
"""
from __future__ import annotations

import math

import polars as pl

from .config import DAY_MS, MINUTE_MS, TIMEFRAMES, Venue, day_start_ms

BAR_COLUMNS = [
    "ts", "open", "high", "low", "close", "volume", "quote_volume", "trades",
    "n_minutes", "n_traded", "ts_high", "ts_low", "hl_order", "complete",
]
BAR_DISK_SCHEMA: dict[str, pl.DataType] = {
    "ts": pl.Datetime("ms", "UTC"),
    "open": pl.Float64,
    "high": pl.Float64,
    "low": pl.Float64,
    "close": pl.Float64,
    "volume": pl.Float64,
    "quote_volume": pl.Float64,
    "trades": pl.Int64,
    "n_minutes": pl.Int32,
    "n_traded": pl.Int32,
    "ts_high": pl.Datetime("ms", "UTC"),
    "ts_low": pl.Datetime("ms", "UTC"),
    "hl_order": pl.String,
    "complete": pl.Boolean,
}


def empty_bars() -> pl.DataFrame:
    return pl.DataFrame(schema=BAR_DISK_SCHEMA)


def _bars_frame(rows: list[dict]) -> pl.DataFrame:
    if not rows:
        return empty_bars()
    int_schema = {k: (pl.Int64 if k in ("ts", "ts_high", "ts_low") else v) for k, v in BAR_DISK_SCHEMA.items()}
    df = pl.DataFrame(rows, schema=int_schema, strict=False)
    return df.with_columns(
        *(pl.col(c).cast(pl.Datetime("ms")).dt.replace_time_zone("UTC") for c in ("ts", "ts_high", "ts_low"))
    ).select(BAR_COLUMNS)


def last_traded_close(df: pl.DataFrame | None, carry_in: float | None) -> float | None:
    """Close of the last traded minute in ``df``; ``carry_in`` if the day has no traded minute."""
    if df is None or df.height == 0:
        return carry_in
    traded = df.filter(pl.col("volume") > 0)
    if traded.height == 0:
        return carry_in
    return traded["close"][-1]


def has_traded_minute(df: pl.DataFrame | None) -> bool:
    return df is not None and df.height > 0 and bool((df["volume"] > 0).any())


def resample_day(
    df: pl.DataFrame | None,
    venue: Venue,
    day: str,
    tf: str,
    carry_close: float | None,
    covered_until_ms: int | None,
    day_closed: bool,
) -> pl.DataFrame:
    """Bars (disk form) for the bars that open inside ``day``."""
    tf_minutes = TIMEFRAMES[tf]
    tf_ms = tf_minutes * MINUTE_MS
    d0 = day_start_ms(day)
    d_end = d0 + DAY_MS
    grid_lo = max(d0, venue.first_minute_ms)
    first_bar = grid_lo - (grid_lo - d0) % tf_ms

    if df is not None and df.height:
        ts = df["ts"].to_list()
        o = df["open"].to_list()
        h = df["high"].to_list()
        lo = df["low"].to_list()
        c = df["close"].to_list()
        vol = df["volume"].to_list()
        qv = df["quote_volume"].to_list()
        tr = df["trades"].to_list()
        last_ts = ts[-1]
    else:
        ts = o = h = lo = c = vol = qv = tr = []
        last_ts = None

    if day_closed:
        grid_end = d_end
    else:
        reach = max((last_ts + MINUTE_MS) if last_ts is not None else 0, covered_until_ms or 0)
        grid_end = min(d_end, reach)
    if grid_end <= first_bar:
        return empty_bars()

    covered = covered_until_ms if covered_until_ms is not None else 0
    out: list[dict] = []
    i, n = 0, len(ts)
    carry = carry_close
    start = first_bar
    while start < grid_end:
        end = start + tf_ms
        n_min = n_tr = 0
        b_o = b_h = b_l = b_c = None
        ts_h = ts_l = None
        vols: list[float] = []
        qvs: list[float] = []
        trs = 0
        have_tr = False
        while i < n and ts[i] < end:
            n_min += 1
            vols.append(vol[i])
            if qv[i] is not None:
                qvs.append(qv[i])
            if tr[i] is not None:
                trs += tr[i]
                have_tr = True
            if vol[i] > 0:
                n_tr += 1
                if b_o is None:
                    b_o = o[i]
                if b_h is None or h[i] > b_h:
                    b_h, ts_h = h[i], ts[i]
                if b_l is None or lo[i] < b_l:
                    b_l, ts_l = lo[i], ts[i]
                b_c = c[i]
            i += 1
        if n_tr == 0:
            b_o = b_h = b_l = b_c = carry
            order = "flat"
        else:
            carry = b_c
            if b_h == b_l:
                order = "flat"
            elif ts_h < ts_l:
                order = "high_first"
            elif ts_l < ts_h:
                order = "low_first"
            else:
                order = "same_minute"
        complete = day_closed or (end <= covered)
        if tf == "1d":
            complete = day_closed
        out.append({
            "ts": start, "open": b_o, "high": b_h, "low": b_l, "close": b_c,
            "volume": math.fsum(vols) if vols else 0.0,
            "quote_volume": math.fsum(qvs) if qvs else None,
            "trades": trs if have_tr else None,
            "n_minutes": n_min, "n_traded": n_tr,
            "ts_high": ts_h, "ts_low": ts_l, "hl_order": order, "complete": complete,
        })
        start = end
    return _bars_frame(out)
