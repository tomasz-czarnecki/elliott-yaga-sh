"""`export-site`: complete bars and stats.json for the static site (site/data, gitignored).

    stats.json                 what the pages read first: per venue totals and the list of bar files
    bars/{venue}/{tf}.json     one venue and timeframe, loaded by the chart only when asked for

A bar file is columnar JSON of integers, so that 15 years of 1h bars stay small:

    t  bar open time in s for the first bar, then the distance to the previous bar in units of bar_s
    o  open x price_scale for the first bar, then the change from the previous open
    h  (high - open) x price_scale      l  (open - low) x price_scale      c  (close - open) x price_scale
    v  volume in base currency x volume_scale
    short  [[index, n_minutes], ...] for bars holding fewer minutes than their length (exchange outages)

Only complete bars are written (``complete_only=True``). Each file is replaced atomically, and stats.json goes last,
so a reader never finds a list that points at files which are not there yet.
"""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from ..data import load_bars
from .config import DAY_MS, MINUTE_MS, TIMEFRAMES, VENUES, project_root
from .store import atomic_write
from .sync import Collector

FORMAT = "ewave-bars-1"
PRICE_SCALE = 100  # every venue quotes in steps of 0.01 or coarser
VOLUME_SCALE = 1000
RECENT_DAYS = {"15m": 365}  # timeframes capped to a recent window; the others hold the whole history


def site_data_dir() -> Path:
    return project_root() / "site" / "data"


def _ms(df: pl.DataFrame, col: str = "ts") -> list[int]:
    return df[col].dt.epoch("ms").to_list()


def encode_bars(df: pl.DataFrame, venue: str, tf: str) -> dict:
    """The file for one venue and timeframe, from bars sorted by time (see the module docstring)."""
    bar_ms = TIMEFRAMES[tf] * MINUTE_MS
    ts = _ms(df)
    if any(t % bar_ms for t in ts):
        raise ValueError(f"{venue} {tf}: a bar is not on the {tf} grid")
    t = [ts[0] // 1000] + [(b - a) // bar_ms for a, b in zip(ts, ts[1:])]
    o, h, l, c = ((df[col] * PRICE_SCALE).round().cast(pl.Int64) for col in ("open", "high", "low", "close"))
    opens = o.to_list()
    n_full = TIMEFRAMES[tf]
    return {
        "format": FORMAT,
        "venue": venue,
        "tf": tf,
        "bar_s": bar_ms // 1000,
        "price_scale": PRICE_SCALE,
        "volume_scale": VOLUME_SCALE,
        "n": df.height,
        "t": t,
        "o": [opens[0]] + [b - a for a, b in zip(opens, opens[1:])],
        "h": (h - o).to_list(),
        "l": (o - l).to_list(),
        "c": (c - o).to_list(),
        "v": (df["volume"] * VOLUME_SCALE).round().cast(pl.Int64).to_list(),
        "short": [[i, n] for i, n in enumerate(df["n_minutes"].to_list()) if n < n_full],
    }


def _write_json(path: Path, obj: dict) -> int:
    data = json.dumps(obj, separators=(",", ":")).encode()
    atomic_write(path, lambda f: f.write(data))
    return len(data)


def _venue_totals(c: Collector, vid: str) -> dict:
    days = c.catalog.days(vid)
    gaps = c.catalog.gaps(vid)
    firsts = [d["first_ts"] for d in days if d["first_ts"] is not None]
    return {
        "title": VENUES[vid].title,
        "first_minute_ms": min(firsts) if firsts else None,
        "last_minute_ms": c.catalog.last_ts(vid),
        "days": len(days),
        "rows_1m": sum(d["n_rows"] for d in days),
        "missing_minutes": sum(g["minutes"] for g in gaps),
        "gaps": len(gaps),
        "last_ok_sync_ms": c.catalog.venue_state(vid)["last_ok_run"],
    }


def export_site(c: Collector, out: Path | str | None = None) -> list[str]:
    """Write every venue and timeframe, then stats.json. Returns one line per file for the CLI."""
    out = Path(out) if out else site_data_dir()
    now = c.clock.now_ms()
    lines: list[str] = []
    venues: dict[str, dict] = {}
    for vid in VENUES:
        info = _venue_totals(c, vid)
        info["bars"] = {}
        for tf in TIMEFRAMES:
            df = load_bars(vid, tf, "2000-01-01", "2100-01-01", root=c.root)
            if df.height == 0:
                continue
            last = _ms(df)[-1]
            days = RECENT_DAYS.get(tf)
            if days:
                df = df.filter(pl.col("ts").dt.epoch("ms") > last - days * DAY_MS)
            path = out / "bars" / vid / f"{tf}.json"
            size = _write_json(path, encode_bars(df, vid, tf))
            info["bars"][tf] = {
                "file": f"bars/{vid}/{tf}.json",
                "n": df.height,
                "first_ms": _ms(df)[0],
                "last_ms": last,
                "bytes": size,
                "recent_days": days,
            }
            lines.append(f"{vid} {tf}: {df.height} bars, {size / 1e6:.2f} MB")
        venues[vid] = info
    _write_json(out / "stats.json", {"generated_at_ms": now, "default_venue": "bybit_btcusdt_perp", "venues": venues})
    lines.append(f"stats.json written to {out}")
    return lines

