"""Section A, follow-up: how many legal counts does a pivot have once degree is free? A person is not tied to one threshold, so
this asks what the hard rules alone leave open. If nearly every swing high can end some legal 5-wave count, on BTC and on random
paths alike, then "the true count" is not a label a model can be trained on.

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/a5_ambiguity.py --paths 200

For each pivot of a fine zigzag taken as the end of wave 5, enumerate every choice of p0..p4 among earlier pivots of the same
zigzag such that each wave's end points are the real extremes of the wave's own stretch (p3 is the highest high between p2 and
p4, and so on), and the wave passes R1-R4 with W5 beyond W3. Waves may contain any number of fine swings; that is what free
degree means. Lookback: 60 fine pivots. The same with direction reversed for down-counts.

Sub-wave checks (does W3 subdivide into 5?) are not applied, so this is an upper bound on what a careful counter would accept,
but the same bound applies to BTC and to the null.

Writes a5_ambiguity.csv to the scratch folder. About 3 minutes.
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from common import ANALYSIS_VENUE, BARS_PER_DAY, Scale, load_series, mc_p_high, q5_50_95, write_csv
from nulls import null_bars, to_rel
from zigzag import pivots, zigzag_raw

try:
    from numba import njit
except ImportError:
    def njit(f):
        return f

SCALES_A = (Scale("15m", "pct", 2), Scale("1h", "pct", 2), Scale("4h", "pct", 4), Scale("1d", "pct", 8))
LOOKBACK = 60
SEED = 20261037


@njit
def _legal_counts(x: np.ndarray, kind: np.ndarray, lookback: int):
    """For each pivot as p5: how many legal counts end there, and how many distinct p0 they use. A down-count is an up-count on
    mirrored prices. Walking back from the end, a candidate must be a new extreme of its own stretch, and the walk stops as soon as
    a pivot in between would beat the wave's other end. That keeps the enumeration small."""
    n = x.size
    counts = np.zeros(n, np.int64)
    starts = np.zeros(n, np.int64)
    for e in range(n):
        y = x if kind[e] == 1 else -x
        y5 = y[e]
        floor = max(e - lookback, 0)
        seen = np.zeros(lookback + 2, np.bool_)
        lo4 = np.inf
        d = e - 1
        while d >= floor:
            y4 = y[d]
            if y4 < lo4:
                lo4 = y4
                hi3 = -np.inf
                c = d - 1
                while c >= floor:
                    y3 = y[c]
                    if y3 > hi3:
                        hi3 = y3
                        if y3 >= y5:  # W5 must end beyond W3; earlier record highs are only higher
                            break
                        lo2 = np.inf
                        b = c - 1
                        while b >= floor:
                            y2 = y[b]
                            if y2 < lo2:
                                lo2 = y2
                                hi1 = -np.inf
                                a = b - 1
                                while a >= floor:
                                    y1 = y[a]
                                    if y1 > hi1:
                                        hi1 = y1
                                        if y1 >= y4 or y1 >= y3:  # R4 and R2; earlier record highs are only higher
                                            break
                                        lo0 = np.inf
                                        p = a - 1
                                        while p >= floor:
                                            y0 = y[p]
                                            if y0 < lo0:
                                                lo0 = y0
                                                w1, w3, w5 = y1 - y0, y3 - y2, y5 - y4
                                                if y2 > y0 and not (w3 <= w1 and w3 <= w5):  # R1 and R3
                                                    counts[e] += 1
                                                    if not seen[e - p]:
                                                        seen[e - p] = True
                                                        starts[e] += 1
                                            if p - 1 >= floor and y[p - 1] > y1:
                                                break
                                            p -= 2
                                    if a - 1 >= floor and y[a - 1] < y2:
                                        break
                                    a -= 2
                            if b - 1 >= floor and y[b - 1] > y3:
                                break
                            b -= 2
                    if c - 1 >= floor and y[c - 1] < y4:
                        break
                    c -= 2
            if d - 1 >= floor and y[d - 1] > y5:
                break
            d -= 2
    return counts, starts


def measure(p) -> dict[str, float]:
    c, s = _legal_counts(p.x, p.kind, LOOKBACK)
    usable = c[LOOKBACK:]
    starts = s[LOOKBACK:]
    if usable.size == 0:
        return {}
    has = usable > 0
    return {"pivots": int(usable.size), "share_with_legal_count": float(has.mean()), "mean_counts": float(usable.mean()),
            "median_counts_when_any": float(np.median(usable[has])) if has.any() else 0.0,
            "mean_distinct_starts_when_any": float(starts[has].mean()) if has.any() else 0.0,
            "share_with_3_or_more": float((usable >= 3).mean())}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=200)
    args = ap.parse_args()
    t0 = time.time()
    rows = []
    for sc in SCALES_A:
        s = load_series(ANALYSIS_VENUE, sc.tf)
        per_day = BARS_PER_DAY[sc.tf]
        rel = to_rel(s.o, s.h, s.l, s.c, s.high_first, per_day)
        btc = measure(pivots(s, sc))
        row = {"scale": sc.name, **btc}
        for kind in ("shuffle", "signflip", "trendflip"):
            rng = np.random.default_rng([SEED, per_day, ord(kind[0]), ord(kind[1])])
            runs = []
            for _ in range(args.paths):
                o, h, l, c, hf = null_bars(rel, kind, rng)
                runs.append(measure(zigzag_raw(h, l, c, hf, sc)))
            for key, value in btc.items():
                values = np.array([r.get(key, np.nan) for r in runs], float)
                lo, mid, hi = q5_50_95(values)
                row.update({f"{key}|{kind}_p5": lo, f"{key}|{kind}_median": mid, f"{key}|{kind}_p95": hi,
                            f"{key}|{kind}_p": min(1.0, 2 * min(mc_p_high(float(value), values), mc_p_high(-float(value), -values)))})
        rows.append(row)
        print(sc.name, {k: round(v, 3) for k, v in btc.items()}, f"{time.time() - t0:.0f}s", flush=True)
    write_csv("a5_ambiguity.csv", rows)


if __name__ == "__main__":
    main()
