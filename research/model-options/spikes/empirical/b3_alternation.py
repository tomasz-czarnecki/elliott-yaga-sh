"""Section B2, follow-up: alternation. Rulebook section 1: a shallow W2 means expect a deeper W4. b2 found a small negative rank
correlation between W2 depth and W4 depth on BTC, more negative than on null paths. Is it there in each era?

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/b3_alternation.py --paths 300

Spearman of W2 depth (pull 0-1) and W4 depth (pull 2-3) over rule-legal impulses, all 24 scales pooled per timeframe, per era.
The rule itself couples the two a little (a deep W2 leaves W3 a lower start), which is why the null is not zero.

Writes b3_alternation.csv to the scratch folder. About 2 minutes.
"""
from __future__ import annotations

import argparse

import numpy as np

from common import ANALYSIS_VENUE, BARS_PER_DAY, ERAS, SCALES, load_series, mc_p_high, q5_50_95, to_ms, write_csv
from impulse import check
from nulls import null_bars, to_rel
from zigzag import pivots, zigzag_raw

SEED = 20261040
PERIODS = (("all", "2013-01-01", "2027-01-01"), *ERAS)


def _rank(x: np.ndarray) -> np.ndarray:
    r = np.empty(x.size)
    r[np.argsort(x)] = np.arange(x.size)
    return r


def spearman_by_period(piv_list, edges) -> np.ndarray:
    """Per period: numerator, denominator and n, the ranks being taken inside each scale and period, so scales can be pooled."""
    out = np.zeros((len(edges), 3))
    for p in piv_list:
        c = check(p)
        if not len(c):
            continue
        legal = c.subset(c.legal)
        first = legal.i[:, 0]
        for k, (a, b) in enumerate(edges):
            m = (first >= a) & (first < b)
            if m.sum() < 3:
                continue
            x, y = _rank(legal.log["w2"][m]), _rank(legal.log["w4"][m])
            x, y = x - x.mean(), y - y.mean()
            out[k, 0] += float((x * y).sum())
            out[k, 1] += float(np.sqrt((x * x).sum() * (y * y).sum()))
            out[k, 2] += int(m.sum())
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=300)
    args = ap.parse_args()
    rows = []
    for tf_i, (tf, per_day) in enumerate(BARS_PER_DAY.items()):
        s = load_series(ANALYSIS_VENUE, tf)
        edges = [(int(np.searchsorted(s.ts, to_ms(a))), int(np.searchsorted(s.ts, to_ms(b)))) for _, a, b in PERIODS]
        cells = [x for x in SCALES if x.tf == tf]
        btc = spearman_by_period([pivots(s, sc) for sc in cells], edges)
        rel = to_rel(s.o, s.h, s.l, s.c, s.high_first, per_day)
        for kind_i, kind in enumerate(("signflip", "trendflip")):
            rng = np.random.default_rng([SEED, tf_i, kind_i])
            sims = []
            for _ in range(args.paths):
                o, h, l, c, hf = null_bars(rel, kind, rng)
                sims.append(spearman_by_period([zigzag_raw(h, l, c, hf, sc) for sc in cells], edges))
            sims = np.array(sims)
            with np.errstate(divide="ignore", invalid="ignore"):
                rates = sims[:, :, 0] / sims[:, :, 1]
                value = btc[:, 0] / btc[:, 1]
            for k, (period, _, _) in enumerate(PERIODS):
                lo, mid, hi = q5_50_95(rates[:, k])
                rows.append({"tf": tf, "null": kind, "period": period, "n": int(btc[k, 2]), "spearman": float(value[k]), "null_p5": lo, "null_median": mid, "null_p95": hi,
                             "p_low": mc_p_high(-float(value[k]), -rates[:, k])})
        print(tf, "done", flush=True)
    write_csv("b3_alternation.csv", rows)


if __name__ == "__main__":
    main()
