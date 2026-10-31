"""Section A, follow-up: what does a growing count predict, one leg at a time? Pass rate of each stage on BTC against null
paths, by direction and era, with the family-wise test over scales and the sensitivity to the trend window.

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/a3_stages.py --paths 300

Stages (impulse.stages): s1 W2 holds above the start of W1; s2 W3 goes beyond W1; s3 W4 stays out of W1; s4 W5 goes beyond W3
with W3 not the shortest; s5 after a legal five, the next leg reaches the end of W4. Each is a causal question: the condition
is known when the previous pivot confirms.

Writes a3_stages.csv and a3_familywise.csv to the scratch folder. About 6 minutes.
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from common import ANALYSIS_VENUE, BARS_PER_DAY, ERAS, SCALES, load_series, mc_p_high, q5_50_95, to_ms, wilson, write_csv
from impulse import STAGES, stages
from nulls import null_bars, to_rel
from zigzag import pivots, zigzag_raw

SEED = 20261035
FAMILIES = (("signflip", 60), ("trendflip", 30), ("trendflip", 60), ("trendflip", 120))
SLICES = ("all", "up", "down", *[e[0] for e in ERAS])


def rates(piv, era_of_bar: np.ndarray) -> np.ndarray:
    """(stages, slices, 2): passes and n."""
    out = np.zeros((len(STAGES), len(SLICES), 2))
    st = stages(piv)
    for si, name in enumerate(STAGES):
        a = st[name]
        if a.shape[1] == 0:
            continue
        passed = a[1] > 0
        era = era_of_bar[piv.i[a[2].astype(np.int64)]]
        masks = [np.ones(a.shape[1], bool), a[0] == 1, a[0] == -1] + [era == k for k in range(len(ERAS))]
        for li, m in enumerate(masks):
            out[si, li] = passed[m].sum(), m.sum()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=300)
    args = ap.parse_args()
    t0 = time.time()
    rows, fw = [], []
    for fam_i, (kind, days) in enumerate(FAMILIES):
        z_btc, z_null, names = [], [], []
        for tf_i, (tf, per_day) in enumerate(BARS_PER_DAY.items()):
            s = load_series(ANALYSIS_VENUE, tf)
            cells = [x for x in SCALES if x.tf == tf]
            edges = [int(np.searchsorted(s.ts, to_ms(a))) for _, a, _ in ERAS]
            era_of_bar = np.searchsorted(edges, np.arange(len(s)), side="right") - 1
            era_of_bar = np.where(np.arange(len(s)) >= int(np.searchsorted(s.ts, to_ms(ERAS[-1][2]))), -1, era_of_bar)
            rel = to_rel(s.o, s.h, s.l, s.c, s.high_first, per_day, trend_days=days)
            rng = np.random.default_rng([SEED, fam_i, tf_i])
            store = np.empty((args.paths, len(cells), len(STAGES), len(SLICES), 2))
            for n in range(args.paths):
                o, h, l, c, hf = null_bars(rel, kind, rng)
                for ci, sc in enumerate(cells):
                    store[n, ci] = rates(zigzag_raw(h, l, c, hf, sc), era_of_bar)
            btc = np.array([rates(pivots(s, sc), era_of_bar) for sc in cells])
            with np.errstate(divide="ignore", invalid="ignore"):
                null_rate = store[..., 0] / store[..., 1]
                btc_rate = btc[..., 0] / btc[..., 1]
            for ci, sc in enumerate(cells):
                for si, st_name in enumerate(STAGES):
                    for li, sl in enumerate(SLICES):
                        v = float(btc_rate[ci, si, li])
                        lo, mid, hi = q5_50_95(null_rate[:, ci, si, li])
                        n_ = int(btc[ci, si, li, 1])
                        w_lo, w_hi = wilson(int(btc[ci, si, li, 0]), n_)
                        rows.append({"null": kind, "trend_days": days if kind == "trendflip" else "", "scale": sc.name, "stage": st_name, "slice": sl, "n": n_,
                                     "btc": v, "btc_lo": w_lo, "btc_hi": w_hi, "null_p5": lo, "null_median": mid, "null_p95": hi,
                                     "difference": v - mid if np.isfinite(v) and np.isfinite(mid) else float("nan"),
                                     "p_high": mc_p_high(v, null_rate[:, ci, si, li]) if np.isfinite(v) else float("nan"),
                                     "p_low": mc_p_high(-v, -null_rate[:, ci, si, li]) if np.isfinite(v) else float("nan")})
            mean = np.nanmean(null_rate, axis=0)
            sd = np.nanstd(null_rate, axis=0)
            with np.errstate(divide="ignore", invalid="ignore"):
                z_btc.append(((btc_rate - mean) / sd)[:, :, 0])  # all directions, whole period
                z_null.append(((null_rate - mean) / sd)[:, :, :, 0])
            names += [sc.name for sc in cells]
        zb = np.concatenate(z_btc, axis=0)  # (cells, stages)
        zn = np.concatenate(z_null, axis=1)  # (paths, cells, stages)
        for si, st_name in enumerate(STAGES):
            mx_high = np.nanmax(zn[:, :, si], axis=1)
            mx_low = np.nanmax(-zn[:, :, si], axis=1)
            for ci, name in enumerate(names):
                z = float(zb[ci, si])
                fw.append({"null": kind, "trend_days": days if kind == "trendflip" else "", "scale": name, "stage": st_name, "z": z,
                           "fw_p_high": mc_p_high(z, mx_high), "fw_p_low": mc_p_high(-z, mx_low)})
        print(f"{kind} {days} done {time.time() - t0:.0f}s", flush=True)
    write_csv("a3_stages.csv", rows)
    write_csv("a3_familywise.csv", fw)


if __name__ == "__main__":
    main()
