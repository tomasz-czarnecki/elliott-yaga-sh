"""Causal zigzag pivots.

A swing extreme becomes a pivot only when price has moved back from it by the threshold. `conf_ts` is the close of the
bar that shows it; a count may label a pivot only after that. The running extreme after the last pivot is provisional
and is returned separately: it is never labelled.

The threshold is k x ATR in log price, read from the bar before the one being processed. Inside a bar the 1-minute
derived order says whether the high or the low came first; when unknown, the extension of the current leg goes first.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import inf, log

from .frames import HIGH_FIRST, UNKNOWN, Frame


@dataclass(frozen=True)
class Pivot:
    ts: int          # bar open, ms
    kind: str        # "H" or "L"
    price: float
    conf_ts: int     # close of the bar that confirmed it
    at: int | None = field(default=None, compare=False)  # the finer bar that holds the extreme (FIB-T6)

    @property
    def t(self) -> int:
        """When it happened, as well as the time frame can tell. Durations use this; bar lookups use ts."""
        return self.ts if self.at is None else self.at


@dataclass(frozen=True)
class Running:
    ts: int
    kind: str        # the extreme being extended: "H" while a high is running
    price: float


def _extreme_since(side: list[float], order: list[int], i: int, t: int, price: float, kind: str) -> tuple[float, int]:
    """The new leg's extreme when a swing at bar i is confirmed at bar t: everything printed since the swing counts, not
    only the confirming bar. A threshold that shrinks while price waits can confirm a swing long after the leg's real
    extreme. Inside bar i, only what came after the swing's own extreme; bar t counts as far as `price`, read now."""
    best, at = price, t
    after_swing = order[i] == (HIGH_FIRST if kind == "L" else -1)
    for j in range(i if after_swing else i + 1, t):
        if (side[j] < best) if kind == "L" else (side[j] > best):
            best, at = side[j], j
    return best, at


def zigzag(f: Frame, k: float, seed: Pivot | None = None, end: int | None = None) -> tuple[list[Pivot], Running | None]:
    """Pivots confirmed by bar `end` (exclusive; default all), plus the running extreme.

    With a seed the walk starts at that pivot, whose kind says what is looked for next, and the seed is the first pivot.
    """
    high, low, order, ts, atr = f.high, f.low, f.order, f.ts, f.atr
    tf_ms = f.tf_ms
    n = len(ts) if end is None else end
    pivots: list[Pivot] = []
    d = 0  # +1: looking for a high, -1: looking for a low, 0: not started
    hi_i = lo_i = ext_i = 0
    hi, lo, ext = -inf, inf, 0.0
    start = 0
    if seed is not None:
        start = f.bar_at(seed.ts)
        pivots.append(seed)
        d = 1 if seed.kind == "L" else -1
        if start < n:
            same_bar_after = order[start] == (-1 if seed.kind == "L" else HIGH_FIRST)
            ext = (high[start] if seed.kind == "L" else low[start]) if same_bar_after else f.close[start]
        else:
            ext = seed.price
        ext_i = start
        start += 1
    for t in range(start, n):
        th = k * atr[t - 1] if t > 0 else float("nan")
        if th != th:  # warm-up
            continue
        h, l, o = high[t], low[t], order[t]
        if o == UNKNOWN:
            seq = (("H", h), ("L", l)) if d >= 0 else (("L", l), ("H", h))
        else:
            seq = (("H", h), ("L", l)) if o == HIGH_FIRST else (("L", l), ("H", h))
        conf = ts[t] + tf_ms
        for kind, price in seq:
            if d == 0:
                if kind == "H":
                    if price > hi:
                        hi, hi_i = price, t
                    if lo < inf and log(price / lo) >= th:
                        pivots.append(Pivot(ts[lo_i], "L", lo, conf))
                        d, ext, ext_i = 1, hi, hi_i
                else:
                    if price < lo:
                        lo, lo_i = price, t
                    if hi > -inf and log(hi / price) >= th:
                        pivots.append(Pivot(ts[hi_i], "H", hi, conf))
                        d, ext, ext_i = -1, lo, lo_i
            elif d == 1:
                if kind == "H":
                    if price > ext:
                        ext, ext_i = price, t
                elif log(ext / price) >= th:
                    pivots.append(Pivot(ts[ext_i], "H", ext, conf))
                    d, ext, ext_i = -1, *_extreme_since(low, order, ext_i, t, price, "L")
            else:
                if kind == "L":
                    if price < ext:
                        ext, ext_i = price, t
                elif log(price / ext) >= th:
                    pivots.append(Pivot(ts[ext_i], "L", ext, conf))
                    d, ext, ext_i = 1, *_extreme_since(high, order, ext_i, t, price, "H")
    pivots = [dated(f, p) for p in pivots]
    if d == 0:
        return pivots, None
    return pivots, Running(ts[ext_i] if ext_i < len(ts) else ts[-1], "H" if d == 1 else "L", ext)


def _holding_bar(f: Frame, parent_tf_ms: int, p: Pivot) -> int:
    i = f.bar_at(p.ts)
    if i >= len(f.ts) or f.ts[i] < p.ts:
        i = min(i + 1, len(f.ts) - 1)
    best, gap = i, float("inf")
    t = i
    extreme = f.high if p.kind == "H" else f.low
    while t < len(f.ts) and f.ts[t] < p.ts + parent_tf_ms:
        g = abs(extreme[t] - p.price)
        if g < gap:
            best, gap = t, g
        t += 1
    return best


def locate(f: Frame, parent_tf_ms: int, p: Pivot) -> Pivot:
    """A parent's pivot on a finer frame: the bar inside the parent's bar that holds the extreme. Same price, finer time."""
    return dated(f, Pivot(f.ts[_holding_bar(f, parent_tf_ms, p)], p.kind, p.price, p.conf_ts, p.at))


def dated(f: Frame, p: Pivot) -> Pivot:
    """The pivot with `at` read from the frame's time frame, when it has one (FIB-T6). That frame's bars closed with the
    pivot's own bar, so this reads no later data."""
    fine = f.fine
    if fine is None or fine.tf_ms >= f.tf_ms or not fine.ts:
        return p
    at = fine.ts[_holding_bar(fine, f.tf_ms, p)]
    if not p.ts <= at < p.ts + f.tf_ms:
        return p
    return Pivot(p.ts, p.kind, p.price, p.conf_ts, at)


def ladder_scans(f: Frame, ks: list[float], max_pivots: int, limit: int, seed: Pivot | None = None) -> list[tuple[float, list[Pivot], Running | None]]:
    """The thresholds that fit a window: the largest ones whose pivot list is not over the cap, each list different."""
    out: list[tuple[float, list[Pivot], Running | None]] = []
    seen: set[tuple[int, ...]] = set()
    for k in ks:
        pivots, running = zigzag(f, k, seed)
        if len(pivots) > max_pivots and out:
            break
        if len(pivots) > max_pivots:
            continue
        key = tuple(p.ts for p in pivots)
        if key in seen:
            continue
        seen.add(key)
        out.append((k, pivots, running))
    # the finer lists hold more structure: keep those when the ladder gave more than the limit
    return out[-limit:]
