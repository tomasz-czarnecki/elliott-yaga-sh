"""Read access to the collected data, for the analysis code.

    from ewave.data import load_1m, load_bars
    bars = load_bars("bybit_btcusdt_perp", "1h", "2024-01-01", "2024-02-01")

Only the day files that cover the requested period are opened. Times are UTC; an end time is exclusive.
"""
from __future__ import annotations

import warnings
from datetime import date, datetime, timedelta

import polars as pl

from .ingest.config import UTC, data_root, day_of_ms, raise_nofile_limit, resolve_venue
from .ingest.store import Store

__all__ = ["load_1m", "load_bars"]


def _to_dt(x: str | date | datetime) -> datetime:
    if isinstance(x, datetime):
        return x.replace(tzinfo=UTC) if x.tzinfo is None else x.astimezone(UTC)
    if isinstance(x, date):
        return datetime(x.year, x.month, x.day, tzinfo=UTC)
    d = datetime.fromisoformat(x)
    return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)


def _days(start: datetime, end: datetime) -> list[str]:
    first = start.date()
    last = (end - timedelta(microseconds=1)).date()
    return [(first + timedelta(days=i)).isoformat() for i in range((last - first).days + 1)]


def _catalog_state(root, venue: str):
    path = root / "state" / "catalog.sqlite"
    if not path.exists():
        return None
    import sqlite3

    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        return {r["day"]: r["status"] for r in con.execute("SELECT day, status FROM days WHERE venue=?", (venue,))}
    except sqlite3.Error:
        return None
    finally:
        con.close()


def load_1m(venue: str, start, end, *, root=None, warn: bool = True) -> pl.DataFrame:
    """1-minute rows with start <= ts < end (UTC). Warns about missing or not-yet-closed days."""
    v = resolve_venue(venue)
    root = root or data_root()
    store = Store(root)
    raise_nofile_limit()  # thousands of small day files may be opened at once
    s, e = _to_dt(start), _to_dt(end)
    days = _days(s, e)
    paths, missing = [], []
    for d in days:
        p = store.raw_path(v.id, d)
        if p.exists():
            paths.append(p)
        else:
            missing.append(d)
    status = _catalog_state(root, v.id)
    if warn:
        first_day = day_of_ms(v.first_minute_ms)
        really_missing = [d for d in missing if d >= first_day and d <= day_of_ms(int(datetime.now(UTC).timestamp() * 1000))]
        if really_missing:
            warnings.warn(f"{v.id}: no data file for {len(really_missing)} day(s) in range, e.g. {really_missing[:3]}")
        if status:
            not_closed = [d for d in days if status.get(d) not in (None, "closed")]
            if not_closed:
                warnings.warn(f"{v.id}: {len(not_closed)} day(s) in range are not closed yet (data may still change): "
                              f"{not_closed[:3]}")
    if not paths:
        return pl.DataFrame(schema={"ts": pl.Datetime("ms", "UTC")})
    return (pl.scan_parquet(paths).filter((pl.col("ts") >= s) & (pl.col("ts") < e)).sort("ts").collect())


def load_bars(venue: str, tf: str, start, end, *, complete_only: bool = True, root=None) -> pl.DataFrame:
    """Derived bars (15m, 1h, 4h, 1d) with start <= ts < end. By default only bars marked complete are returned."""
    v = resolve_venue(venue)
    store = Store(root or data_root())
    s, e = _to_dt(start), _to_dt(end)
    frames = []
    for year in range(s.year, (e - timedelta(microseconds=1)).year + 1):
        df = store.read_bars_year(v.id, tf, year)
        if df is not None:
            frames.append(df)
    if not frames:
        return pl.DataFrame()
    out = pl.concat(frames).filter((pl.col("ts") >= s) & (pl.col("ts") < e)).sort("ts")
    return out.filter(pl.col("complete")) if complete_only else out
