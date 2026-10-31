"""Shared plumbing for the EMP spikes: paths, loading bars through ewave.data, thresholds, small statistics helpers.

Not a script. Every script in this folder runs from the repo root, for example:

    export PATH=/opt/data/.local/bin:$PATH
    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/a_census.py

The ephemeral uv layer leaves pyproject.toml and uv.lock alone. Outputs go to OUT (scratch), never into the repo.
"""
from __future__ import annotations

import csv
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ewave.data import load_bars

OUT = Path(os.environ.get("EMP_OUT", "/opt/data/cache/scratch/elliott_research_r1/emp"))  # EMP_OUT: for a trial run elsewhere
STATS_START = "2013-03-01"  # cycles-r1 and CLAUDE.md: before it mostly no-trade minutes
ANALYSIS_VENUE = "bitstamp_btcusd"
VENUES = ("bitstamp_btcusd", "binance_btcusdt", "bybit_btcusdt_perp")
ERAS = (("2014-2017", "2014-01-01", "2018-01-01"), ("2018-2021", "2018-01-01", "2022-01-01"), ("2022-2026", "2022-01-01", "2027-01-01"))
BARS_PER_DAY = {"15m": 96, "1h": 24, "4h": 6, "1d": 1}
FIB_LEVELS = (0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618, 2.0, 2.236, 2.618)
ATR_N = 14


def to_ms(day: str) -> int:
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1000)


def day_str(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date().isoformat()


@dataclass(frozen=True)
class Series:
    """Consecutive bars of one venue and timeframe, as log prices. high_first: which extreme traded first (from the 1m
    data); where the data cannot tell (same minute, flat), a down candle counts as high first."""
    venue: str
    tf: str
    ts: np.ndarray  # UTC bar open, ms
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    high_first: np.ndarray  # bool

    def __len__(self) -> int:
        return self.ts.size

    @property
    def years(self) -> float:
        return len(self) / BARS_PER_DAY[self.tf] / 365.25


def load_series(venue: str = ANALYSIS_VENUE, tf: str = "1h", start: str = STATS_START, end: str = "2100-01-01") -> Series:
    df = load_bars(venue, tf, start, end, complete_only=True)
    ts = df["ts"].dt.epoch("ms").to_numpy().astype(np.int64)
    o, h, l, c = (np.log(df[k].to_numpy()) for k in ("open", "high", "low", "close"))
    order = df["hl_order"].to_numpy()
    high_first = np.where(order == "high_first", True, np.where(order == "low_first", False, c < o))
    return Series(venue, tf, ts, o, h, l, c, high_first.astype(bool))


@dataclass(frozen=True)
class Scale:
    """One swing scale: a timeframe and a reversal threshold. kind: pct (fixed log(1+v/100)) or atr (v x ATR14 in log
    price, causal: the threshold for bar t uses bars up to t-1)."""
    tf: str
    kind: str
    value: float

    @property
    def name(self) -> str:
        v = int(self.value) if float(self.value).is_integer() else self.value
        return f"{self.tf}_{self.kind}{v}"


# The grid used in every section. Fixed thresholds differ per timeframe so that a leg stays many bars long. ATR multiples
# keep the swing rate steady across BTC's volatility regimes; fixed ones are what a trader's eye and % moves look like.
SCALES: tuple[Scale, ...] = tuple(
    Scale(tf, kind, v)
    for tf, pcts in (("15m", (1, 2, 4)), ("1h", (2, 4, 8)), ("4h", (4, 8, 16)), ("1d", (8, 16, 32)))
    for kind, values in (("pct", pcts), ("atr", (2, 4, 8)))
    for v in values
)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson interval for a rate: 95 percent by default."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def mc_p_high(value: float, null: np.ndarray) -> float:
    """One-sided Monte Carlo p for 'value is high', with the +1 that keeps it valid. NaNs in the null are dropped."""
    v = null[np.isfinite(null)]
    return float((1 + np.sum(v >= value)) / (1 + v.size)) if v.size else float("nan")


def mc_p_two(value: float, null: np.ndarray) -> float:
    return min(1.0, 2 * min(mc_p_high(value, null), mc_p_high(-value, -null)))


def bh_qvalues(p: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg q-values. NaNs stay NaN."""
    p = np.asarray(p, dtype=float)
    q = np.full(p.shape, np.nan)
    ok = np.isfinite(p)
    vals = p[ok]
    if vals.size == 0:
        return q
    order = np.argsort(vals)
    ranked = vals[order] * vals.size / np.arange(1, vals.size + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(vals.size)
    out[order] = np.minimum(ranked, 1.0)
    q[ok] = out
    return q


def q5_50_95(x: np.ndarray) -> tuple[float, float, float]:
    v = np.asarray(x, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return (float("nan"),) * 3
    a, b, c = np.percentile(v, [5, 50, 95])
    return float(a), float(b), float(c)


def write_csv(name: str, rows: list[dict]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    if not rows:
        path.write_text("")
        return path
    keys: list[str] = []
    for r in rows:
        keys.extend(k for k in r if k not in keys)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return path


def write_json(name: str, obj) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(obj, indent=1, default=float))
    return path
