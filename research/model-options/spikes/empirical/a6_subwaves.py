"""Section A, follow-up: "only 3s and 5s exist". Elliott's central claim is about what is inside a wave, and the rulebook calls
skipping that check the number one beginner error. So: inside each swing of a coarse zigzag, how many swings does a finer zigzag
see? It can only be odd (1, 3, 5, ...). If the claim holds at this level of resolution, 3 and 5 stand out against random paths.

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/a6_subwaves.py --paths 300

Coarse and fine zigzag run on the same bars, fine threshold 1/2 and 1/4 of the coarse one. A coarse extreme is also a fine extreme
except in rare bar-order cases; a coarse leg's count is taken between the fine pivots nearest its ends.
For the rule-legal impulses of the coarse zigzag also: W3 subdivides into exactly 5, and the full form: W1, W3, W5 in {1, 5} with W3
= 5, W2 and W4 in {1, 3}.

Writes a6_subwaves.csv to the scratch folder. About 3 minutes.
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from common import ANALYSIS_VENUE, BARS_PER_DAY, Scale, load_series, mc_p_high, q5_50_95, write_csv
from impulse import check
from nulls import null_bars, to_rel
from zigzag import pivots, zigzag_raw

SEED = 20261039
PAIRS = ((Scale("15m", "pct", 4), Scale("15m", "pct", 2)), (Scale("15m", "pct", 4), Scale("15m", "pct", 1)),
         (Scale("1h", "pct", 8), Scale("1h", "pct", 4)), (Scale("1h", "pct", 8), Scale("1h", "pct", 2)),
         (Scale("4h", "pct", 16), Scale("4h", "pct", 8)), (Scale("4h", "pct", 16), Scale("4h", "pct", 4)),
         (Scale("1d", "pct", 16), Scale("1d", "pct", 8)), (Scale("1d", "pct", 32), Scale("1d", "pct", 8)))
NAMES = ("share_1", "share_3", "share_5", "share_7", "share_9plus", "share_3_or_5_among_3plus", "legal_n", "w3_is_5", "w2_is_1_or_3", "full_form")


def measure(coarse, fine) -> np.ndarray:
    out = np.full(len(NAMES), np.nan)
    if len(coarse) < 7 or len(fine) < 7:
        return out
    # Number of fine pivots inside each coarse leg, ends excluded: position of the nearest fine pivot to each coarse pivot.
    pos = np.searchsorted(fine.i, coarse.i)
    pos = np.clip(pos, 0, len(fine) - 1)
    left = np.clip(pos - 1, 0, len(fine) - 1)
    pos = np.where(np.abs(fine.i[left] - coarse.i) <= np.abs(fine.i[pos] - coarse.i), left, pos)
    sub = np.diff(pos)  # number of fine legs inside each coarse leg
    sub = np.where(sub % 2 == 1, sub, sub + 1)  # alignment slips: an even count is rounded up to the next odd one
    sub = np.maximum(sub, 1)
    out[0] = np.mean(sub == 1)
    out[1] = np.mean(sub == 3)
    out[2] = np.mean(sub == 5)
    out[3] = np.mean(sub == 7)
    out[4] = np.mean(sub >= 9)
    many = sub[sub >= 3]
    out[5] = np.mean((many == 3) | (many == 5)) if many.size else np.nan
    c = check(coarse)
    legal = np.flatnonzero(c.legal)
    out[6] = legal.size
    if legal.size:
        s1, s2, s3, s4, s5 = sub[legal], sub[legal + 1], sub[legal + 2], sub[legal + 3], sub[legal + 4]
        out[7] = np.mean(s3 == 5)
        out[8] = np.mean((s2 <= 3) & (s4 <= 3))
        out[9] = np.mean((s3 == 5) & np.isin(s1, (1, 5)) & np.isin(s5, (1, 5)) & (s2 <= 3) & (s4 <= 3))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=300)
    args = ap.parse_args()
    t0 = time.time()
    rows = []
    for coarse_sc, fine_sc in PAIRS:
        s = load_series(ANALYSIS_VENUE, coarse_sc.tf)
        btc = measure(pivots(s, coarse_sc), pivots(s, fine_sc))
        rel = to_rel(s.o, s.h, s.l, s.c, s.high_first, BARS_PER_DAY[coarse_sc.tf])
        for kind_i, kind in enumerate(("shuffle", "signflip", "trendflip")):
            rng = np.random.default_rng([SEED, kind_i, int(coarse_sc.value), int(fine_sc.value), BARS_PER_DAY[coarse_sc.tf]])
            store = []
            for _ in range(args.paths):
                o, h, l, c, hf = null_bars(rel, kind, rng)
                store.append(measure(zigzag_raw(h, l, c, hf, coarse_sc), zigzag_raw(h, l, c, hf, fine_sc)))
            arr = np.array(store)
            for mi, name in enumerate(NAMES):
                lo, mid, hi = q5_50_95(arr[:, mi])
                v = float(btc[mi])
                rows.append({"coarse": coarse_sc.name, "fine": fine_sc.name, "null": kind, "metric": name, "btc": v, "null_p5": lo, "null_median": mid, "null_p95": hi,
                             "p_two": min(1.0, 2 * min(mc_p_high(v, arr[:, mi]), mc_p_high(-v, -arr[:, mi]))) if np.isfinite(v) else float("nan")})
        print(coarse_sc.name, fine_sc.name, np.round(btc, 3), f"{time.time() - t0:.0f}s", flush=True)
    write_csv("a6_subwaves.csv", rows)


if __name__ == "__main__":
    main()
