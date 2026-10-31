"""Section B1, venue check: the Fibonacci level test on Bybit (Tomasz's chart) and Binance. Same statistic as b1_fib_unconditional.py,
level summary only: mean z of one level across the 24 scales, against the same mean on null paths.

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/b1c_venues.py --paths 300

These venues cover the same market as Bitstamp after 2017 and 2020, so this rules out a Bitstamp artefact and is not independent
evidence. Writes b1c_levels.csv to the scratch folder. About 5 minutes.
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from b1_fib_unconditional import TYPES, WIDTHS, measure
from common import BARS_PER_DAY, FIB_LEVELS, SCALES, bh_qvalues, load_series, mc_p_two, write_csv
from nulls import null_bars, to_rel
from zigzag import pivots, zigzag_raw

SEED = 20261041
VENUES_C = ("bybit_btcusdt_perp", "binance_btcusdt")
KINDS_C = ("signflip", "trendflip")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=300)
    args = ap.parse_args()
    t0 = time.time()
    rows = []
    for vi, venue in enumerate(VENUES_C):
        z_b = {k: [] for k in KINDS_C}
        z_n = {k: [] for k in KINDS_C}
        ex_b = []
        for tf_i, (tf, per_day) in enumerate(BARS_PER_DAY.items()):
            s = load_series(venue, tf)
            span_edges = np.array([0, 0, 0, 0, len(s)])  # the histogram part of measure() is not used here
            cells = [x for x in SCALES if x.tf == tf]
            with_lin = False
            btc = np.array([measure(pivots(s, sc), span_edges, with_lin)[0] for sc in cells])[:, :, 0]  # (cells, types, widths, levels)
            ex_b.append(btc)
            rel = to_rel(s.o, s.h, s.l, s.c, s.high_first, per_day)
            for kind_i, kind in enumerate(KINDS_C):
                rng = np.random.default_rng([SEED, vi, tf_i, kind_i])
                sims = np.empty((args.paths, *btc.shape), np.float32)
                for n in range(args.paths):
                    o, h, l, c, hf = null_bars(rel, kind, rng)
                    for ci, sc in enumerate(cells):
                        sims[n, ci] = measure(zigzag_raw(h, l, c, hf, sc), span_edges, with_lin)[0][:, 0]
                mean, sd = np.nanmean(sims, axis=0), np.nanstd(sims, axis=0)
                sd = np.where(sd > 0, sd, np.nan)
                z_b[kind].append((btc - mean) / sd)
                z_n[kind].append((sims - mean) / sd)
            print(venue, tf, f"{time.time() - t0:.0f}s", flush=True)
        ex = np.concatenate(ex_b, axis=0)
        for ti, t in enumerate(TYPES):
            for wi, w in enumerate(WIDTHS):
                for li, level in enumerate(FIB_LEVELS):
                    row = {"venue": venue, "type": t, "width": w, "level": level, "excess_btc_mean": float(np.nanmean(ex[:, ti, wi, li]))}
                    for kind in KINDS_C:
                        zb = np.concatenate(z_b[kind], axis=0)[:, ti, wi, li]
                        zn = np.concatenate(z_n[kind], axis=1)[:, :, ti, wi, li]
                        value = float(np.nanmean(zb))
                        nulls = np.nanmean(zn, axis=1)
                        row[f"{kind}_mean_z"] = value
                        row[f"{kind}_p"] = mc_p_two(value, nulls)
                    rows.append(row)
    for kind in KINDS_C:
        for venue in VENUES_C:
            chosen = [r for r in rows if r["venue"] == venue]
            for r, q in zip(chosen, bh_qvalues(np.array([r[f"{kind}_p"] for r in chosen]))):
                r[f"{kind}_q"] = float(q)
    write_csv("b1c_levels.csv", rows)
    print("done", f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
