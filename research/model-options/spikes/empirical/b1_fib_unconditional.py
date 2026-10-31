"""Section B1: is any Fibonacci level over-represented among BTC's swing ratios, beyond what random paths give?

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/b1_fib_unconditional.py \\
        --tf 1h --paths 500
    (one --tf at a time: 15m about 12 minutes at 400 paths, 1h about 4, 4h and 1d about 1; run them one after the other,
    then --report with no --tf to pool them)

Ratios on all consecutive zigzag legs, per scale:
  ret       |leg2| / |leg1|, every pair
  ret_up    the same, a down leg retracing an up leg
  ret_down  the same, an up leg retracing a down leg
  ext       |leg3| / |leg1| where leg2 retraced less than leg1: a 3-pivot extension pull (pull a-b-c)
in log price, and in linear price from 1h up (the rulebook calls the difference immaterial below 4h).

The test for each level L, band half-width w in ln(ratio): count in the band against the count in the shoulders on both
sides, w < |ln(ratio/L)| <= 4w. excess = band / (shoulders / 3): 1 means no local bump. The global shape of the density
therefore cannot produce a hit; only a local feature at the level can. Widths: narrow 0.015 (about +-1.5 percent of the
level, a fib drawn to the wick) and wide 0.04.

Each statistic on BTC is compared with the same statistic on each null family (nulls.py): z against the null's mean and
sd, one-sided Monte Carlo p. Multiple testing, because there are thousands of tests:
  - Benjamini-Hochberg q on normal p from z, checked against placebos: null paths treated as if they were BTC.
  - Westfall-Young max-T: a test's family-wise p is the share of null paths whose largest z over all tests beats it.
  - Omnibus: how many tests reach z >= 1.645 on BTC against the distribution of that count on null paths.
  - Level summary: the mean z of one level across scales, against the same mean on null paths. This has the most power
    for a small effect that is present everywhere.
Fingerprint: shape of the density against each null (distance to the null mean, Monte Carlo p), and a learnability test: a
histogram fitted on BTC up to 2021 against the pooled null, both scored on BTC 2022-2026, on the fine bins and on the 12 bands of
the density table. Null paths run the same way give the distribution of that gain under no structure.

Writes to the scratch folder: b1_{tf}.npz (raw), and with --report: b1_tests.csv, b1_levels.csv, b1_shape.csv, b1_density.csv,
b1_summary.json and density plots.
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from common import (ANALYSIS_VENUE, BARS_PER_DAY, ERAS, FIB_LEVELS, OUT, SCALES, bh_qvalues, load_series, mc_p_high, mc_p_two,
                    q5_50_95, to_ms, write_csv, write_json)
from nulls import KINDS, null_bars, to_rel
from zigzag import Pivots, pivots, zigzag_raw

TYPES = ("ret", "ret_up", "ret_down", "ext")
PRICES = ("log", "lin")
WIDTHS = (0.015, 0.04)
BINS = np.arange(np.log(0.05), np.log(20.0) + 0.05, 0.05)  # histogram of ln(ratio)
SPANS = (("before_2014", "2013-01-01", "2014-01-01"), *ERAS)
HIST_TYPES = ("ret", "ext")
SEED = 20261030


def _ratio_arrays(p: Pivots, price: str) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """For each type: ln(ratio) and the pivot position of the pivot that closes the ratio."""
    x = p.x if price == "log" else np.exp(p.x)
    legs = np.abs(np.diff(x))
    if legs.size < 3:
        e = np.empty(0)
        return {t: (e, np.empty(0, np.int64)) for t in TYPES}
    with np.errstate(divide="ignore", invalid="ignore"):
        ret = np.log(legs[1:] / legs[:-1])
        ext = np.log(legs[2:] / legs[:-2])
    closes = np.arange(2, legs.size + 1)
    # A leg ending at a high is an up leg: pivot j is the end of leg j-1.
    first_leg_up = p.kind[1:-1] == 1
    keep_ext = legs[1:-1] < legs[:-2]
    ok = np.isfinite(ret)
    return {
        "ret": (ret[ok], closes[ok]),
        "ret_up": (ret[ok & first_leg_up], closes[ok & first_leg_up]),
        "ret_down": (ret[ok & ~first_leg_up], closes[ok & ~first_leg_up]),
        "ext": (ext[keep_ext & np.isfinite(ext)], closes[1:][keep_ext & np.isfinite(ext)]),
    }


_LN_LEVELS = np.log(np.array(FIB_LEVELS))
# Edges per (width, level): shoulder lo, band lo, band hi, shoulder hi.
_EDGES = np.array([[_LN_LEVELS - 4 * w, _LN_LEVELS - w, _LN_LEVELS + w, _LN_LEVELS + 4 * w] for w in WIDTHS])  # (w, 4, levels)


def excess(values: np.ndarray) -> np.ndarray:
    """(widths, levels) of band / (shoulders / 3), with a half-count so empty shoulders stay finite."""
    a = np.sort(values)
    pos = np.searchsorted(a, _EDGES)
    band = pos[:, 2, :] - pos[:, 1, :]
    shoulders = pos[:, 3, :] - pos[:, 0, :] - band
    return (band + 0.5) / ((shoulders + 1.5) / 3)


def measure(p: Pivots, span_edges: np.ndarray, with_lin: bool) -> tuple[np.ndarray, np.ndarray]:
    """X: (types, prices, widths, levels). H: (hist types, spans, bins), log price, by the span of the closing pivot."""
    X = np.full((len(TYPES), len(PRICES), len(WIDTHS), len(FIB_LEVELS)), np.nan)
    H = np.zeros((len(HIST_TYPES), len(SPANS), BINS.size - 1), np.int32)
    conf = p.confirmed
    for pi, price in enumerate(PRICES):
        if price == "lin" and not with_lin:
            continue
        arrs = _ratio_arrays(p, price)
        for ti, t in enumerate(TYPES):
            values, closes = arrs[t]
            if values.size:
                X[ti, pi] = excess(values)
            if price == "log" and t in HIST_TYPES and values.size:
                span = np.searchsorted(span_edges, conf[closes], side="right") - 1
                bins = np.searchsorted(BINS, values, side="right") - 1
                ok = (bins >= 0) & (bins < BINS.size - 1) & (span >= 0) & (span < len(SPANS))
                H[HIST_TYPES.index(t)] += np.bincount(span[ok] * (BINS.size - 1) + bins[ok],
                                                      minlength=len(SPANS) * (BINS.size - 1)).reshape(len(SPANS), -1).astype(np.int32)
    return X, H


def run_tf(tf: str, paths: int) -> None:
    t0 = time.time()
    s = load_series(ANALYSIS_VENUE, tf)
    per_day = BARS_PER_DAY[tf]
    cells = [x for x in SCALES if x.tf == tf]
    with_lin = tf != "15m"
    span_edges = np.array([np.searchsorted(s.ts, to_ms(a)) for _, a, _ in SPANS] + [len(s)])
    rel = to_rel(s.o, s.h, s.l, s.c, s.high_first, per_day)
    blocks = {}
    btc_X, btc_H = [], []
    for sc in cells:
        p = pivots(s, sc)
        blocks[sc.name] = max(3, int(round(float(np.median(np.diff(p.i))))))
        X, H = measure(p, span_edges, with_lin)
        btc_X.append(X)
        btc_H.append(H)
    tf_i = list(BARS_PER_DAY).index(tf)
    null_X = {k: np.empty((paths, len(cells), *btc_X[0].shape), np.float32) for k in KINDS}
    null_H = {k: np.empty((paths, len(cells), *btc_H[0].shape), np.int32) for k in KINDS}
    rngs = {k: np.random.default_rng([SEED, tf_i, i]) for i, k in enumerate(KINDS)}
    for n in range(paths):
        for kind in ("shuffle", "signflip", "trendflip"):
            o, h, l, c, hf = null_bars(rel, kind, rngs[kind])
            for ci, sc in enumerate(cells):
                null_X[kind][n, ci], null_H[kind][n, ci] = measure(zigzag_raw(h, l, c, hf, sc), span_edges, with_lin)
        for ci, sc in enumerate(cells):
            o, h, l, c, hf = null_bars(rel, "block", rngs["block"], block=blocks[sc.name])
            null_X["block"][n, ci], null_H["block"][n, ci] = measure(zigzag_raw(h, l, c, hf, sc), span_edges, with_lin)
        if (n + 1) % 50 == 0:
            print(f"{tf} {n + 1}/{paths} {time.time() - t0:.0f}s", flush=True)
    np.savez(OUT / f"b1_{tf}.npz", btc_X=np.array(btc_X), btc_H=np.array(btc_H), cells=np.array([c.name for c in cells]),
             blocks=np.array([blocks[c.name] for c in cells]), **{f"X_{k}": v for k, v in null_X.items()},
             **{f"H_{k}": v for k, v in null_H.items()})
    print(f"{tf} done {time.time() - t0:.0f}s", flush=True)


def _law_cdf(r: np.ndarray) -> np.ndarray:
    """CDF of the ratio of two independent legs, each threshold x (1 + Exp(1)): the law of a zigzag on a driftless random
    walk. Integrating over the first leg gives r/(1+r) exp(1-1/r) below 1 and 1 - exp(1-r)/(1+r) from 1 up."""
    r = np.asarray(r, float)
    out = np.zeros(r.shape)
    above = r >= 1
    middle = (r > 0) & ~above
    out[above] = 1 - np.exp(1 - r[above]) / (1 + r[above])
    out[middle] = r[middle] / (1 + r[middle]) * np.exp(1 - 1 / r[middle])
    return out


def report() -> None:
    data = {}
    for tf in BARS_PER_DAY:
        path = OUT / f"b1_{tf}.npz"
        if path.exists():
            data[tf] = np.load(path)
    z_null_by_kind: dict[str, list[np.ndarray]] = {k: [] for k in KINDS}
    # One flat list of tests per timeframe; for each kind a z matrix (paths, tests).
    meta = []
    btc_values = []
    means = {k: [] for k in KINDS}
    sds = {k: [] for k in KINDS}
    z_btc = {k: [] for k in KINDS}
    p_mc = {k: [] for k in KINDS}
    for tf, d in data.items():
        cells = [str(c) for c in d["cells"]]
        btc = d["btc_X"]
        for ci, cell in enumerate(cells):
            for ti, t in enumerate(TYPES):
                for pi, price in enumerate(PRICES):
                    for wi, w in enumerate(WIDTHS):
                        for li, level in enumerate(FIB_LEVELS):
                            if not np.isfinite(btc[ci, ti, pi, wi, li]):
                                continue
                            meta.append((tf, cell, t, price, w, level))
                            btc_values.append(float(btc[ci, ti, pi, wi, li]))
        for k in KINDS:
            X = d[f"X_{k}"]
            mask = np.isfinite(btc)
            nulls = X[:, mask]  # (paths, tests)
            mean, sd = np.nanmean(nulls, axis=0), np.nanstd(nulls, axis=0)
            sd = np.where(sd > 0, sd, np.nan)
            b = btc[mask]
            z_b = (b - mean) / sd
            z_n = (nulls - mean) / sd
            means[k].append(mean)
            sds[k].append(sd)
            z_btc[k].append(z_b)
            z_null_by_kind[k].append(z_n)
            p_mc[k].append((1 + np.sum(nulls >= b, axis=0)) / (1 + nulls.shape[0]))
    from scipy.stats import norm
    summary: dict = {"tests": len(meta), "omnibus": {}, "paths": {k: int(sum(z.shape[0] for z in z_null_by_kind[k]) / max(1, len(z_null_by_kind[k]))) for k in KINDS}}
    per_kind = {}
    for k in KINDS:
        zb = np.concatenate(z_btc[k])
        minp = min(z.shape[0] for z in z_null_by_kind[k])
        zn = np.concatenate([z[:minp] for z in z_null_by_kind[k]], axis=1)
        mean = np.concatenate(means[k])
        sd = np.concatenate(sds[k])
        p = np.concatenate(p_mc[k])
        q = bh_qvalues(norm.sf(zb))
        max_null = np.nanmax(zn, axis=1)
        fw = np.array([(1 + np.sum(max_null >= z)) / (1 + max_null.size) for z in zb])
        # Omnibus: how many tests clear 1.645 on BTC, against the same count on each null path.
        count_b = int(np.nansum(zb >= 1.645))
        counts_n = np.nansum(zn >= 1.645, axis=1)
        count_b_neg = int(np.nansum(zb <= -1.645))
        counts_n_neg = np.nansum(zn <= -1.645, axis=1)
        # Placebos: null paths treated as BTC, how many BH discoveries do they make?
        placebo_disc = [int(np.nansum(bh_qvalues(norm.sf(zn[j])) < 0.05)) for j in range(min(100, zn.shape[0]))]
        lo, mid, hi = q5_50_95(counts_n)
        summary["omnibus"][k] = {
            "tests_z_ge_1645_btc": count_b, "null_p5": lo, "null_median": mid, "null_p95": hi, "p_high": mc_p_high(count_b, counts_n),
            "tests_z_le_-1645_btc": count_b_neg, "null_neg_median": float(np.median(counts_n_neg)), "p_neg_high": mc_p_high(count_b_neg, counts_n_neg),
            "max_z_btc": float(np.nanmax(zb)), "max_z_null_median": float(np.median(max_null)), "max_z_null_p95": float(np.percentile(max_null, 95)),
            "bh_discoveries_btc": int(np.nansum(q < 0.05)), "bh_discoveries_placebo_median": float(np.median(placebo_disc)),
            "bh_discoveries_placebo_p95": float(np.percentile(placebo_disc, 95)),
            "familywise_hits_btc": int(np.nansum(fw < 0.05)),
        }
        per_kind[k] = {"z": zb, "q": q, "p": p, "fw": fw, "mean": mean, "sd": sd, "zn": zn}
    rows = []
    for j, (tf, cell, t, price, w, level) in enumerate(meta):
        row = {"tf": tf, "scale": cell, "type": t, "price": price, "width": w, "level": level, "excess_btc": btc_values[j]}
        for k in KINDS:
            pk = per_kind[k]
            row.update({f"{k}_mean": float(pk["mean"][j]), f"{k}_sd": float(pk["sd"][j]), f"{k}_z": float(pk["z"][j]),
                        f"{k}_p": float(pk["p"][j]), f"{k}_q": float(pk["q"][j]), f"{k}_fw": float(pk["fw"][j])})
        rows.append(row)
    write_csv("b1_tests.csv", rows)

    # Level summary: mean z of one level across all scales, separately per ratio type, price and width.
    level_rows = []
    keys = sorted({(t, price, w, level) for (_, _, t, price, w, level) in meta}, key=lambda x: (TYPES.index(x[0]), x[1], x[2], x[3]))
    idx = {}
    for j, (_, _, t, price, w, level) in enumerate(meta):
        idx.setdefault((t, price, w, level), []).append(j)
    for key in keys:
        t, price, w, level = key
        row = {"type": t, "price": price, "width": w, "level": level, "cells": len(idx[key]),
               "excess_btc_mean": float(np.mean([btc_values[j] for j in idx[key]]))}
        for k in KINDS:
            pk = per_kind[k]
            value = float(np.nanmean(pk["z"][idx[key]]))
            nulls = np.nanmean(pk["zn"][:, idx[key]], axis=1)
            row.update({f"{k}_mean_z": value, f"{k}_null_sd": float(np.std(nulls)), f"{k}_p": mc_p_two(value, nulls), f"{k}_p_high": mc_p_high(value, nulls),
                        f"{k}_excess_null_mean": float(np.nanmean(pk["mean"][idx[key]]))})
        level_rows.append(row)
    for k in KINDS:
        qs = bh_qvalues(np.array([r[f"{k}_p"] for r in level_rows]))
        for r, q in zip(level_rows, qs):
            r[f"{k}_q"] = float(q)
    write_csv("b1_levels.csv", level_rows)

    # Shape and density: distance of each BTC histogram to the null mean, against the same distance of each null path.
    shape_rows, density_rows = [], []
    centers = np.exp((BINS[:-1] + BINS[1:]) / 2)
    report_edges = np.array([0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618, 2.0, 2.618, 4.236, 1e9])
    # Assign the fine bins to the coarse table.
    coarse = np.searchsorted(report_edges, centers, side="right") - 1
    fit_spans = [0, 1, 2]  # up to 2021
    test_span = 3
    for tf, d in data.items():
        cells = [str(c) for c in d["cells"]]
        for ci, cell in enumerate(cells):
            for hi_, ht in enumerate(HIST_TYPES):
                btc_h = d["btc_H"][ci, hi_].astype(float)  # (spans, bins)
                row = {"tf": tf, "scale": cell, "type": ht, "n": int(btc_h.sum()),
                       "n_train": int(btc_h[fit_spans].sum()), "n_test": int(btc_h[test_span].sum())}
                btc_full = btc_h.sum(axis=0)
                for k in KINDS:
                    H = d[f"H_{k}"][:, ci, hi_].astype(float)  # (paths, spans, bins)
                    full = H.sum(axis=1)
                    pool = full.sum(axis=0)
                    pool_share = pool / pool.sum()
                    tv_b = 0.5 * np.abs(btc_full / max(btc_full.sum(), 1) - pool_share).sum()
                    shares = full / np.maximum(full.sum(axis=1, keepdims=True), 1)
                    tv_n = 0.5 * np.abs(shares - pool_share).sum(axis=1)
                    # Cumulative distance: more power for a change of shape than bin noise. KS on the fine grid.
                    ks_b = np.abs(np.cumsum(btc_full / max(btc_full.sum(), 1)) - np.cumsum(pool_share)).max()
                    ks_n = np.abs(np.cumsum(shares, axis=1) - np.cumsum(pool_share)).max(axis=1)
                    row.update({f"{k}_ks": float(ks_b), f"{k}_ks_null_median": float(np.median(ks_n)), f"{k}_ks_p": mc_p_high(ks_b, ks_n),
                                f"{k}_tv": float(tv_b), f"{k}_tv_p": mc_p_high(tv_b, tv_n)})
                    # Learnability: fit on the early spans, score on 2022-2026.
                    test_pool = H[:, test_span].sum(axis=0) + 0.5
                    f_null = test_pool / test_pool.sum()
                    def gain(train: np.ndarray, test: np.ndarray) -> float:
                        f = train + 0.5
                        f = f / f.sum()
                        return float((test * (np.log(f) - np.log(f_null))).sum() / max(test.sum(), 1))
                    g_b = gain(btc_h[fit_spans].sum(axis=0), btc_h[test_span])
                    g_n = np.array([gain(H[j, fit_spans].sum(axis=0), H[j, test_span]) for j in range(H.shape[0])])
                    row.update({f"{k}_gain_nats": g_b, f"{k}_gain_null_median": float(np.median(g_n)), f"{k}_gain_null_p95": float(np.percentile(g_n, 95)),
                                f"{k}_gain_p": mc_p_high(g_b, g_n)})
                    # The same with only the 12 bands of the density table: far fewer parameters to fit, so more power for a broad shape.
                    def to_coarse(h_: np.ndarray) -> np.ndarray:
                        return np.stack([h_[..., coarse == b_].sum(axis=-1) for b_ in range(report_edges.size - 1)], axis=-1)
                    null_c = to_coarse(H[:, test_span]).sum(axis=0) + 0.5
                    f_null_c = null_c / null_c.sum()
                    train_c = to_coarse(H[:, fit_spans].sum(axis=1)) + 0.5  # (paths, bands)
                    train_c = train_c / train_c.sum(axis=1, keepdims=True)
                    test_c = to_coarse(H[:, test_span])
                    with np.errstate(invalid="ignore", divide="ignore"):
                        g_cn = (test_c * (np.log(train_c) - np.log(f_null_c))).sum(axis=1) / np.maximum(test_c.sum(axis=1), 1)
                    tb = to_coarse(btc_h[fit_spans].sum(axis=0)) + 0.5
                    tb = tb / tb.sum()
                    te = to_coarse(btc_h[test_span])
                    g_cb = float((te * (np.log(tb) - np.log(f_null_c))).sum() / max(te.sum(), 1))
                    row.update({f"{k}_coarse_gain": g_cb, f"{k}_coarse_gain_null_median": float(np.median(g_cn)), f"{k}_coarse_gain_null_p95": float(np.percentile(g_cn, 95)),
                                f"{k}_coarse_gain_p": mc_p_high(g_cb, g_cn)})
                    # Per era: distance of BTC's era histogram to the null's pool of that era.
                    for si, (era, _, _) in enumerate(SPANS):
                        if era == "before_2014":
                            continue
                        era_pool = H[:, si].sum(axis=0)
                        era_share = era_pool / max(era_pool.sum(), 1)
                        ks_be = np.abs(np.cumsum(btc_h[si] / max(btc_h[si].sum(), 1)) - np.cumsum(era_share)).max()
                        s_ = H[:, si] / np.maximum(H[:, si].sum(axis=1, keepdims=True), 1)
                        ks_ne = np.abs(np.cumsum(s_, axis=1) - np.cumsum(era_share)).max(axis=1)
                        row[f"{k}_ks_p_{era}"] = mc_p_high(ks_be, ks_ne)
                    # Coarse density table. law: the random-walk leg law, for all consecutive legs only.
                    for b in range(report_edges.size - 1):
                        m = coarse == b
                        btc_share = btc_full[m].sum() / max(btc_full.sum(), 1)
                        lo, mid, hi = q5_50_95(shares[:, m].sum(axis=1))
                        law = float(_law_cdf(report_edges[b + 1:b + 2])[0] - _law_cdf(report_edges[b:b + 1])[0]) if ht == "ret" else float("nan")
                        density_rows.append({"tf": tf, "scale": cell, "type": ht, "null": k, "from": report_edges[b], "to": report_edges[b + 1],
                                             "btc": btc_share, "null_p5": lo, "null_median": mid, "null_p95": hi, "law": law})
                shape_rows.append(row)
    for k in KINDS:
        for key in ("ks_p", "gain_p", "coarse_gain_p"):
            qs = bh_qvalues(np.array([r[f"{k}_{key}"] for r in shape_rows]))
            for r, q in zip(shape_rows, qs):
                r[f"{k}_{key}_q"] = float(q)
    write_csv("b1_shape.csv", shape_rows)
    write_csv("b1_density.csv", density_rows)
    write_json("b1_summary.json", summary)
    print(summary)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", choices=list(BARS_PER_DAY))
    ap.add_argument("--paths", type=int, default=500)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.tf:
        run_tf(args.tf, args.paths)
    if args.report:
        report()
