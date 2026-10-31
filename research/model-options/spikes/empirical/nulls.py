"""Null paths: same bars, same start price, no order. All in log price; each bar is kept relative to the previous close.

  shuffle   every bar in a random order: keeps the marginal distribution of bars and candle shapes, destroys everything
            that depends on time, including volatility clustering. Same total return as BTC exactly.
  block     circular block bootstrap of `block` bars. Anything shorter than a block survives, so the block must be short
            against the swing being tested or the null simply is BTC.
  signflip  every bar stays in its place and is mirrored with probability 1/2. Keeps the volatility path of BTC bar by bar
            (the crash months stay where they were) and destroys direction structure at every scale. This is the
            volatility-only null. Bars and the total return are re-centred so that drift matches BTC.
  trendflip the same mirror, but around BTC's own local drift (centred mean of bar returns over +-trend_days): keeps the
            volatility path AND the drift at each date, so bull and bear phases stay where they were. The price level still
            wanders, since the noise around the drift is random. Destroys direction structure faster than the trend window.
            It uses the future to build the drift, which is fine for a null. It asks: does a swing pattern exist beyond
            what regimes and volatility already give?

Block, signflip and trendflip paths get a tiny constant per-bar shift so that they end at BTC's total return as well.

null_days() does the same with whole days as the unit and carries the intraday bars with them, so one null path has a
consistent 1D and 4H view. That is what section C needs: cycle marks on the 1D view and structures on the 4H view.

Not a script.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

KINDS = ("shuffle", "block", "signflip", "trendflip")
TREND_DAYS = 60


@dataclass(frozen=True)
class Rel:
    """Bars relative to the previous close, in log price."""
    ro: np.ndarray
    rh: np.ndarray
    rl: np.ndarray
    rc: np.ndarray
    high_first: np.ndarray
    start: float  # the close before the first bar
    mu: np.ndarray  # local drift per bar, for trendflip

    @property
    def total(self) -> float:
        return float(self.rc.sum())


def local_drift(rc: np.ndarray, w: int) -> np.ndarray:
    """Centred mean of bar returns over +-w bars, narrower at the edges."""
    total = np.r_[0.0, np.cumsum(rc)]
    n = rc.size
    lo = np.maximum(0, np.arange(n) - w)
    hi = np.minimum(n, np.arange(n) + w + 1)
    return (total[hi] - total[lo]) / (hi - lo)


def to_rel(o, h, l, c, high_first, bars_per_day: int = 1, trend_days: int = TREND_DAYS) -> Rel:
    prev = np.r_[o[0], c[:-1]]
    rc = c - prev
    return Rel(o - prev, h - prev, l - prev, rc, high_first, float(o[0]), local_drift(rc, trend_days * bars_per_day))


def block_order(m: int, block: int, rng: np.random.Generator) -> np.ndarray:
    starts = rng.integers(0, m, size=m // block + 1)
    return (starts[:, None] + np.arange(block)).ravel()[:m] % m


def null_bars(rel: Rel, kind: str, rng: np.random.Generator, block: int = 20):
    """One null path: (open, high, low, close, high_first) in log price."""
    m = rel.rc.size
    if kind in ("signflip", "trendflip"):
        flip = rng.random(m) < 0.5
        mu2 = 2 * rel.mu if kind == "trendflip" else 0.0
        ro = np.where(flip, mu2 - rel.ro, rel.ro)
        rh = np.where(flip, mu2 - rel.rl, rel.rh)
        rl = np.where(flip, mu2 - rel.rh, rel.rl)
        rc = np.where(flip, mu2 - rel.rc, rel.rc)
        hf = np.where(flip, ~rel.high_first, rel.high_first)
    else:
        order = rng.permutation(m) if kind == "shuffle" else block_order(m, block, rng)
        ro, rh, rl, rc, hf = rel.ro[order], rel.rh[order], rel.rl[order], rel.rc[order], rel.high_first[order]
    if kind != "shuffle":
        shift = (rel.total - rc.sum()) / m
        ro, rh, rl, rc = ro + shift, rh + shift, rl + shift, rc + shift
    prev = rel.start + np.r_[0.0, np.cumsum(rc)[:-1]]
    return prev + ro, prev + rh, prev + rl, prev + rc, hf


@dataclass(frozen=True)
class DayRel:
    """Whole days: bars of one day relative to the close before that day. Shape (days, bars per day)."""
    ro: np.ndarray
    rh: np.ndarray
    rl: np.ndarray
    rc: np.ndarray
    high_first: np.ndarray
    start: float
    mu: np.ndarray  # local drift per day, for trendflip

    @property
    def day_change(self) -> np.ndarray:
        return self.rc[:, -1]


def to_day_rel(o, h, l, c, high_first, per_day: int, trend_days: int = TREND_DAYS) -> DayRel:
    days = o.size // per_day
    if o.size != days * per_day:
        raise ValueError("whole days only")
    last = c[per_day - 1::per_day]
    prev = np.r_[o[0], last[:-1]][:, None]
    shape = (days, per_day)
    rc = c.reshape(shape) - prev
    return DayRel(o.reshape(shape) - prev, h.reshape(shape) - prev, l.reshape(shape) - prev, rc,
                  high_first.reshape(shape), float(o[0]), local_drift(rc[:, -1], trend_days))


def null_days(rel: DayRel, kind: str, rng: np.random.Generator, block: int = 20):
    """One null path on whole days: flat arrays (open, high, low, close, high_first) of the intraday bars."""
    m = rel.rc.shape[0]
    if kind in ("signflip", "trendflip"):
        flip = (rng.random(m) < 0.5)[:, None]
        # A mirrored day is reflected around its share of the local drift, reached in steps through the day.
        frac = (np.arange(1, rel.rc.shape[1] + 1) / rel.rc.shape[1])[None, :]
        mu2 = (2 * rel.mu)[:, None] * frac if kind == "trendflip" else 0.0
        ro = np.where(flip, mu2 - rel.ro, rel.ro)
        rh = np.where(flip, mu2 - rel.rl, rel.rh)
        rl = np.where(flip, mu2 - rel.rh, rel.rl)
        rc = np.where(flip, mu2 - rel.rc, rel.rc)
        hf = np.where(flip, ~rel.high_first, rel.high_first)
    else:
        order = rng.permutation(m) if kind == "shuffle" else block_order(m, block, rng)
        ro, rh, rl, rc, hf = rel.ro[order], rel.rh[order], rel.rl[order], rel.rc[order], rel.high_first[order]
    day_change = rc[:, -1]
    if kind != "shuffle":
        # The shift is spread evenly over the day's bars: the day's own shape stays, the day's total moves by `shift`.
        shift = (rel.day_change.sum() - day_change.sum()) / m
        frac = (np.arange(1, rc.shape[1] + 1) / rc.shape[1])[None, :]
        ro, rh, rl, rc = ro + shift * frac, rh + shift * frac, rl + shift * frac, rc + shift * frac
        day_change = rc[:, -1]
    prev = (rel.start + np.r_[0.0, np.cumsum(day_change)[:-1]])[:, None]
    return (prev + ro).ravel(), (prev + rh).ravel(), (prev + rl).ravel(), (prev + rc).ravel(), hf.ravel()
