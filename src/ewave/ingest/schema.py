"""Schemas, validation, content hashing and minute-grid helpers.

Inside the program every frame keeps ``ts``/``close_ts`` as Int64 epoch milliseconds (no timezone pitfalls);
they are converted to ``Datetime('ms', 'UTC')`` only when written to disk and back when read.
"""
from __future__ import annotations

import hashlib
import sys
from array import array
from collections.abc import Sequence
from dataclasses import dataclass, field

import polars as pl

from .config import DAY_MS, MINUTE_MS, Venue, day_start_ms

SCHEMA_VERSION = 1

# ---- raw 1-minute rows -------------------------------------------------------
RAW_COLUMNS = [
    "ts",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_volume",
    "trades",
    "taker_buy_volume",
    "taker_buy_quote_volume",
    "close_ts",
]
RAW_SCHEMA: dict[str, pl.DataType] = {
    "ts": pl.Int64,
    "open": pl.Float64,
    "high": pl.Float64,
    "low": pl.Float64,
    "close": pl.Float64,
    "volume": pl.Float64,
    "quote_volume": pl.Float64,
    "trades": pl.Int64,
    "taker_buy_volume": pl.Float64,
    "taker_buy_quote_volume": pl.Float64,
    "close_ts": pl.Int64,
}
_FLOAT_COLS = {c for c, t in RAW_SCHEMA.items() if t == pl.Float64}

Row = tuple  # one tuple per minute, in RAW_COLUMNS order


def make_row(
    ts: int,
    open: float,
    high: float,
    low: float,
    close: float,
    volume: float,
    quote_volume: float | None = None,
    trades: int | None = None,
    taker_buy_volume: float | None = None,
    taker_buy_quote_volume: float | None = None,
    close_ts: int | None = None,
) -> Row:
    return (
        ts,
        open,
        high,
        low,
        close,
        volume,
        quote_volume,
        trades,
        taker_buy_volume,
        taker_buy_quote_volume,
        close_ts,
    )


def empty_frame() -> pl.DataFrame:
    return pl.DataFrame(schema=RAW_SCHEMA)


def frame_from_rows(rows: Sequence[Row]) -> pl.DataFrame:
    if not rows:
        return empty_frame()
    return pl.DataFrame(list(rows), schema=RAW_SCHEMA, orient="row", strict=False)


def to_disk(df: pl.DataFrame) -> pl.DataFrame:
    return df.select(RAW_COLUMNS).with_columns(
        pl.col("ts").cast(pl.Datetime("ms")).dt.replace_time_zone("UTC"),
        pl.col("close_ts").cast(pl.Datetime("ms")).dt.replace_time_zone("UTC"),
    )


def from_disk(df: pl.DataFrame) -> pl.DataFrame:
    return df.select(RAW_COLUMNS).with_columns(
        pl.col("ts").dt.epoch("ms"),
        pl.col("close_ts").dt.epoch("ms"),
    )


def merge_frames(existing: pl.DataFrame | None, new: pl.DataFrame) -> pl.DataFrame:
    """Union by ``ts``. Rows in ``new`` win; rows only in ``existing`` are kept (never deleted)."""
    if existing is None or existing.height == 0:
        base = new
    elif new.height == 0:
        base = existing
    else:
        base = pl.concat([existing, new])
    return base.unique(subset="ts", keep="last", maintain_order=True).sort("ts")


def diff_frames(old: pl.DataFrame | None, new: pl.DataFrame) -> tuple[int, int]:
    """(rows added, rows whose values changed) going from ``old`` to ``new``."""
    if old is None or old.height == 0:
        return new.height, 0
    old_rows = {r[0]: r for r in old.iter_rows()}
    added = changed = 0
    for r in new.iter_rows():
        prev = old_rows.get(r[0])
        if prev is None:
            added += 1
        elif prev != r:
            changed += 1
    return added, changed


def content_hash(df: pl.DataFrame) -> str:
    """Hash of the logical content (sorted rows, fixed-width values, schema version).

    Independent of Parquet writer version/settings, so a library upgrade never looks like an exchange correction.
    """
    h = hashlib.sha256()
    h.update(f"ewave-raw-v{SCHEMA_VERSION}".encode())
    if df.height == 0:
        return h.hexdigest()
    df = df.sort("ts")
    for col in RAW_COLUMNS:
        vals = df[col].to_list()
        h.update(col.encode())
        h.update(bytes(1 if v is None else 0 for v in vals))
        if col in _FLOAT_COLS:
            arr = array("d", [0.0 if v is None else v for v in vals])
        else:
            arr = array("q", [0 if v is None else v for v in vals])
        if sys.byteorder == "big":
            arr.byteswap()
        h.update(arr.tobytes())
    return h.hexdigest()


# ---- minute grid helpers ------------------------------------------------------


def grid_bounds(venue: Venue, day: str, upto_ms: int | None = None) -> tuple[int, int] | None:
    """First and last minute-open of the expected grid for ``day`` (inclusive), or None if empty."""
    d0 = day_start_ms(day)
    lo = max(d0, venue.first_minute_ms)
    hi = d0 + DAY_MS - MINUTE_MS
    if upto_ms is not None:
        hi = min(hi, upto_ms)
    return None if hi < lo else (lo, hi)


def expected_minutes(venue: Venue, day: str, upto_ms: int | None = None) -> int:
    b = grid_bounds(venue, day, upto_ms)
    return 0 if b is None else (b[1] - b[0]) // MINUTE_MS + 1


def find_gaps(ts_sorted: Sequence[int], lo: int, hi: int) -> list[tuple[int, int, int]]:
    """Missing minute ranges in [lo, hi] as (first_missing, last_missing, minutes)."""
    gaps: list[tuple[int, int, int]] = []
    expect = lo
    for t in ts_sorted:
        if t < lo:
            continue
        if t > hi:
            break
        if t > expect:
            gaps.append((expect, t - MINUTE_MS, (t - expect) // MINUTE_MS))
        expect = t + MINUTE_MS
    if expect <= hi:
        gaps.append((expect, hi, (hi - expect) // MINUTE_MS + 1))
    return gaps


def first_missing_minute(ts_sorted: Sequence[int], lo: int, hi: int) -> int | None:
    g = find_gaps(ts_sorted, lo, hi)
    return g[0][0] if g else None


# ---- validation ---------------------------------------------------------------


@dataclass
class Validation:
    hard: list[str] = field(default_factory=list)
    soft: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.hard


def _examples(items: list[str], limit: int = 3) -> str:
    more = f" (+{len(items) - limit} more)" if len(items) > limit else ""
    return "; ".join(items[:limit]) + more


def validate_day(
    df: pl.DataFrame,
    venue: Venue,
    day: str,
    last_closed_ms: int | None,
    prev_close: float | None = None,
    bybit_open_rule: bool = False,
) -> Validation:
    """Hard rules block the write of that day; soft rules are only logged."""
    v = Validation()
    n = df.height
    if n == 0:
        return v
    d0 = day_start_ms(day)
    d1 = d0 + DAY_MS
    lo = max(d0, venue.first_minute_ms)
    ts = df["ts"].to_list()
    o, h, l, c, vol = (df[k].to_list() for k in ("open", "high", "low", "close", "volume"))

    if n > expected_minutes(venue, day):
        v.hard.append(f"{n} rows exceeds the {expected_minutes(venue, day)} minutes possible on {day}")
    if ts[0] < lo:
        v.hard.append(f"first ts {ts[0]} is before the venue/day start {lo}")
    if ts[-1] >= d1:
        v.hard.append(f"last ts {ts[-1]} is outside {day}")
    if last_closed_ms is not None and ts[-1] > last_closed_ms:
        v.hard.append(f"last ts {ts[-1]} is after the last closed minute {last_closed_ms}")

    off, unordered, bad_ohlc, bad_price, bad_vol, bad_dur = [], [], [], [], [], []
    for i in range(n):
        t = ts[i]
        if t % MINUTE_MS:
            off.append(str(t))
        if i and t <= ts[i - 1]:
            unordered.append(str(t))
        if None in (o[i], h[i], l[i], c[i], vol[i]) or any(x != x for x in (o[i], h[i], l[i], c[i], vol[i])):
            bad_ohlc.append(f"{t}: null/NaN")
            continue
        if not (l[i] <= o[i] <= h[i] and l[i] <= c[i] <= h[i]):
            bad_ohlc.append(f"{t}: o={o[i]} h={h[i]} l={l[i]} c={c[i]}")
        if l[i] <= 0 or o[i] <= 0 or h[i] <= 0 or c[i] <= 0:
            bad_price.append(f"{t}: price<=0")
        if vol[i] < 0:
            bad_vol.append(f"{t}: volume={vol[i]}")
    if off:
        v.hard.append(f"{len(off)} timestamps not on a minute boundary: {_examples(off)}")
    if unordered:
        v.hard.append(f"{len(unordered)} timestamps not strictly increasing: {_examples(unordered)}")
    if bad_ohlc:
        v.hard.append(f"{len(bad_ohlc)} rows violate low<=open,close<=high: {_examples(bad_ohlc)}")
    if bad_price:
        v.hard.append(f"{len(bad_price)} non-positive prices: {_examples(bad_price)}")
    if bad_vol:
        v.hard.append(f"{len(bad_vol)} negative volumes: {_examples(bad_vol)}")

    if venue.has_close_ts:
        cts = df["close_ts"].to_list()
        for i in range(n):
            if cts[i] is None or not (0 <= cts[i] - ts[i] <= MINUTE_MS - 1):
                bad_dur.append(f"{ts[i]}: close_ts={cts[i]}")
        if bad_dur:
            v.hard.append(f"{len(bad_dur)} rows with candle duration outside 0..59999 ms: {_examples(bad_dur)}")

    # ---- soft rules -----------------------------------------------------------
    nonflat = [str(ts[i]) for i in range(n) if vol[i] == 0 and not (o[i] == h[i] == l[i] == c[i])]
    if nonflat:
        v.soft.append(f"{len(nonflat)} zero-volume minutes are not flat: {_examples(nonflat)}")
    if bybit_open_rule:
        broken = []
        for i in range(n):
            if i and ts[i] - ts[i - 1] == MINUTE_MS and o[i] != c[i - 1]:
                broken.append(f"{ts[i]}: open={o[i]} prev_close={c[i - 1]}")
            elif i == 0 and prev_close is not None and ts[0] == d0 and o[0] != prev_close:
                broken.append(f"{ts[0]}: open={o[0]} prev_day_close={prev_close}")
        if broken:
            v.soft.append(f"{len(broken)} opens differ from the previous close: {_examples(broken)}")
    return v
