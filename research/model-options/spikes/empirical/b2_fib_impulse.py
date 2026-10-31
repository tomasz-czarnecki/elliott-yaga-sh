"""Sections B2 and B3: Fibonacci ratios and times inside rule-legal impulse candidates, BTC against the same detector on
null paths, and whether BTC has a stable fingerprint across eras and scales.

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/b2_fib_impulse.py --tf 1h --paths 500
    (one --tf at a time, then --report with no --tf pools them; 15m about 8 minutes at 500 paths, the others less)

Candidate: six consecutive zigzag pivots passing R1-R4 with W5 beyond W3 (impulse.py). Pull conventions are the rulebook's;
see impulse.py. The rule filter itself shapes these ratios (W2 under 1, W3 over W2 ...), which is exactly why the null runs
the same detector: only the difference from the null is evidence.

Measured per scale, direction and era (a candidate belongs to the era of p0):
  - hit rate in each window the rulebook names (WINDOWS)
  - local excess at the levels the rulebook names: band +-0.05 in ln(ratio) against shoulders up to +-0.2
  - shape: KS distance of the histogram to the pooled null, Monte Carlo p; learnability (fit on BTC up to 2021, score on
    2022-2026 against the null's pool for that span, compared with null paths doing the same; on fine bins and on bands
    between Fibonacci levels)
  - derived: Spearman(W2 depth, W4 depth) for alternation, share of candidates where W1, W3 or W5 is the longest, the add-one
    rule of lesson 14, W2 depth after a strong uptrend (causal: log return of the 90 days before p0 above +30%).

Pools: every scale of a timeframe (cells share each null path, so the null handles the overlap) and two ladders across
timeframes with thresholds about 2x apart. Ladder null paths are independent across timeframes while BTC's are the same
market, so ladder p values may overstate: read them as a screen.

Writes b2_{tf}.npz (raw), and with --report: b2_windows.csv, b2_shape.csv, b2_derived.csv, b2_summary.json to the scratch folder.
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from common import (ANALYSIS_VENUE, BARS_PER_DAY, ERAS, OUT, SCALES, bh_qvalues, load_series, mc_p_high, q5_50_95, to_ms, write_csv,
                    write_json)
from impulse import RATIOS, TIMES, Candidates, check
from nulls import KINDS, null_bars, to_rel
from zigzag import pivots, zigzag_raw

SEED = 20261031


def near(level: float, tol: float = 0.05) -> tuple[float, float]:
    return (level * (1 - tol), level * (1 + tol))


# (key, label, low, high): the claims of the compact rulebook sections 1, 4 and 7.
WINDOWS = (
    ("w2", "0.5-0.618", 0.5, 0.618),
    ("w2", "near 0.382", *near(0.382)),
    ("w2", "near 0.786", *near(0.786)),
    ("w2", "under 0.382", 0.0, 0.382),
    ("w2", "over 0.618", 0.618, 1.0),
    ("w4", "0.236-0.382", 0.236, 0.382),
    ("w4", "under 0.5", 0.0, 0.5),
    ("w4", "over 0.5", 0.5, 9.0),
    ("w3", "near 1.618", *near(1.618)),
    ("w3", "near 2.618", *near(2.618)),
    ("w3", "1.0-1.618", 1.0, 1.618),
    ("w3", "1.618-2.618", 1.618, 2.618),
    ("w3", "over 2.618", 2.618, 99.0),
    ("w5_012", "near 2.236", *near(2.236)),
    ("w5_012", "near 3.236", *near(3.236)),
    ("w5_014", "near 1.0", *near(1.0)),
    ("w5_014", "near 0.618", *near(0.618)),
    ("t2_t1", "not outlasting W1", 0.0, 1.0),
    ("t2_t1", "at least 0.25 of W1", 0.25, 1e9),
    ("t2_t1", "at least 0.33 of W1", 0.33, 1e9),
    ("t4_t3", "not outlasting W3", 0.0, 1.0),
    ("t4_t3", "at least 0.25 of W3", 0.25, 1e9),
    ("t4_t2", "near W2 (0.8-1.25)", 0.8, 1.25),
    ("t3_t1", "near 1.0", *near(1.0, 0.1)),
    ("t3_t1", "near 1.618", *near(1.618, 0.1)),
    ("t3_t1", "near 2.236", *near(2.236, 0.1)),
    ("t5_t1", "near 1.0", *near(1.0, 0.1)),
    ("t5_t1", "near 0.618", *near(0.618, 0.1)),
)
LEVELS = {"w2": (0.382, 0.5, 0.618, 0.786), "w4": (0.236, 0.382, 0.5), "w3": (1.0, 1.618, 2.0, 2.618, 3.236),
          "w5_012": (2.236, 3.236, 4.236), "w5_014": (0.618, 1.0, 1.618)}
EXCESS_W = 0.05
HIST_KEYS = (*RATIOS, *TIMES)
BINS = np.arange(np.log(0.02), np.log(50.0) + 0.1, 0.1)
COARSE = np.array([0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618, 2.0, 2.618, 4.236, 1e9])
SPANS = (("before_2014", "2013-01-01", "2014-01-01"), *ERAS)
SLICES = ("all", "up", "down", *[e[0] for e in ERAS])
LADDERS = {"ladder_pct": ("15m_pct2", "1h_pct4", "4h_pct8", "1d_pct16"), "ladder_atr": ("15m_atr4", "1h_atr4", "4h_atr4", "1d_atr2")}


def layout() -> list[str]:
    names = []
    for s in SLICES:
        names.append(f"n|{s}")
    for key, label, _, _ in WINDOWS:
        for s in SLICES:
            names.append(f"hit|{key}|{label}|{s}")
        if key in RATIOS:
            names.append(f"hit_lin|{key}|{label}|all")
    for key, levels in LEVELS.items():
        for level in levels:
            names.append(f"band|{key}|{level}")
            names.append(f"sh|{key}|{level}")
    names.extend(["longest|w1", "longest|w3", "longest|w5", "alt|num", "alt|den",
                  "addone|n1618", "addone|hit1618", "addone|n2618", "addone|hit2618",
                  "strong|n", "strong|shallow", "other|n", "other|shallow"])
    return names


NAMES = layout()
INDEX = {n: i for i, n in enumerate(NAMES)}


def _rank(x: np.ndarray) -> np.ndarray:
    r = np.empty(x.size)
    r[np.argsort(x)] = np.arange(x.size)
    return r


def measure(c: Candidates, bar_span: np.ndarray, x_close: np.ndarray, per_day: int) -> tuple[np.ndarray, np.ndarray]:
    """One scale on one path: the counters of NAMES and the histograms (keys, spans, bins)."""
    v = np.zeros(len(NAMES), np.float32)
    H = np.zeros((len(HIST_KEYS), len(SPANS), BINS.size - 1), np.int16)
    legal = c.subset(c.legal) if len(c) else c
    n = len(legal)
    if n == 0:
        return v, H
    span = bar_span[legal.i[:, 0]]
    masks = {"all": np.ones(n, bool), "up": legal.direction == 1, "down": legal.direction == -1}
    for si, (era, _, _) in enumerate(SPANS):
        if era != "before_2014":
            masks[era] = span == si
    for s in SLICES:
        v[INDEX[f"n|{s}"]] = masks[s].sum()
    values = {**legal.log, **legal.time}
    for key, label, lo, hi in WINDOWS:
        inside = (values[key] >= lo) & (values[key] < hi)
        for s in SLICES:
            v[INDEX[f"hit|{key}|{label}|{s}"]] = (inside & masks[s]).sum()
        if key in RATIOS:
            v[INDEX[f"hit_lin|{key}|{label}|all"]] = ((legal.lin[key] >= lo) & (legal.lin[key] < hi)).sum()
    for key, levels in LEVELS.items():
        with np.errstate(divide="ignore", invalid="ignore"):
            ln = np.log(values[key])
        for level in levels:
            d = np.abs(ln - np.log(level))
            band = (d <= EXCESS_W).sum()
            v[INDEX[f"band|{key}|{level}"]] = band
            v[INDEX[f"sh|{key}|{level}"]] = (d <= 4 * EXCESS_W).sum() - band
    for hi_, key in enumerate(HIST_KEYS):
        with np.errstate(divide="ignore", invalid="ignore"):
            ln = np.log(values[key])
        bins = np.searchsorted(BINS, ln, side="right") - 1
        ok = (bins >= 0) & (bins < BINS.size - 1) & (span >= 0) & (span < len(SPANS))
        H[hi_] = np.bincount(span[ok] * (BINS.size - 1) + bins[ok], minlength=len(SPANS) * (BINS.size - 1)).reshape(len(SPANS), -1).astype(np.int16)
    # Which impulse wave is the longest, on log price.
    w1 = np.ones(n)  # in units of W1
    w3 = legal.log["w3"]
    w5 = legal.log["w5_014"]
    v[INDEX["longest|w1"]] = ((w1 >= w3) & (w1 >= w5)).sum()
    v[INDEX["longest|w3"]] = ((w3 > w1) & (w3 >= w5)).sum()
    v[INDEX["longest|w5"]] = ((w5 > w1) & (w5 > w3)).sum()
    # Alternation: rank correlation of W2 depth and W4 depth. Numerator and denominator so pools can add.
    if n >= 3:
        a, b = _rank(legal.log["w2"]), _rank(legal.log["w4"])
        a, b = a - a.mean(), b - b.mean()
        v[INDEX["alt|num"]] = float((a * b).sum())
        v[INDEX["alt|den"]] = float(np.sqrt((a * a).sum() * (b * b).sum()))
    # Add-one rule (lesson 14): W3 hits 1.618 then W5 2.236; W3 hits 2.618 then W5 3.236.
    lo3, hi3 = near(1.618)
    m = (w3 >= lo3) & (w3 < hi3)
    lo5, hi5 = near(2.236)
    v[INDEX["addone|n1618"]] = m.sum()
    v[INDEX["addone|hit1618"]] = (m & (legal.log["w5_012"] >= lo5) & (legal.log["w5_012"] < hi5)).sum()
    lo3, hi3 = near(2.618)
    m = (w3 >= lo3) & (w3 < hi3)
    lo5, hi5 = near(3.236)
    v[INDEX["addone|n2618"]] = m.sum()
    v[INDEX["addone|hit2618"]] = (m & (legal.log["w5_012"] >= lo5) & (legal.log["w5_012"] < hi5)).sum()
    # W2 depth after a strong uptrend, for up impulses: "0.382 in strong BTC uptrend".
    lookback = 90 * per_day
    start = legal.i[:, 0]
    usable = (start >= lookback) & (legal.direction == 1)
    if usable.any():
        trend = x_close[start[usable]] - x_close[start[usable] - lookback]
        shallow = legal.log["w2"][usable] < 0.45
        strong = trend > np.log(1.3)
        v[INDEX["strong|n"]] = strong.sum()
        v[INDEX["strong|shallow"]] = (strong & shallow).sum()
        v[INDEX["other|n"]] = (~strong).sum()
        v[INDEX["other|shallow"]] = (~strong & shallow).sum()
    return v, H


def run_tf(tf: str, paths: int) -> None:
    t0 = time.time()
    s = load_series(ANALYSIS_VENUE, tf)
    per_day = BARS_PER_DAY[tf]
    cells = [x for x in SCALES if x.tf == tf]
    edges = [int(np.searchsorted(s.ts, to_ms(a))) for _, a, _ in SPANS] + [len(s)]
    bar_span = np.searchsorted(edges, np.arange(len(s)), side="right") - 1
    rel = to_rel(s.o, s.h, s.l, s.c, s.high_first, per_day)
    blocks = {}
    btc_v, btc_H = [], []
    for sc in cells:
        p = pivots(s, sc)
        blocks[sc.name] = max(3, int(round(float(np.median(np.diff(p.i))))))
        v, H = measure(check(p), bar_span, s.c, per_day)
        btc_v.append(v)
        btc_H.append(H)
    tf_i = list(BARS_PER_DAY).index(tf)
    null_v = {k: np.empty((paths, len(cells), len(NAMES)), np.float32) for k in KINDS}
    null_H = {k: np.empty((paths, len(cells), *btc_H[0].shape), np.int16) for k in KINDS}
    rngs = {k: np.random.default_rng([SEED, tf_i, i]) for i, k in enumerate(KINDS)}
    for n in range(paths):
        for kind in ("shuffle", "signflip", "trendflip"):
            o, h, l, c, hf = null_bars(rel, kind, rngs[kind])
            for ci, sc in enumerate(cells):
                null_v[kind][n, ci], null_H[kind][n, ci] = measure(check(zigzag_raw(h, l, c, hf, sc)), bar_span, c, per_day)
        for ci, sc in enumerate(cells):
            o, h, l, c, hf = null_bars(rel, "block", rngs["block"], block=blocks[sc.name])
            null_v["block"][n, ci], null_H["block"][n, ci] = measure(check(zigzag_raw(h, l, c, hf, sc)), bar_span, c, per_day)
        if (n + 1) % 100 == 0:
            print(f"{tf} {n + 1}/{paths} {time.time() - t0:.0f}s", flush=True)
    np.savez(OUT / f"b2_{tf}.npz", btc_v=np.array(btc_v), btc_H=np.array(btc_H), cells=np.array([c.name for c in cells]),
             median_leg_bars=np.array([blocks[c.name] for c in cells]), **{f"v_{k}": v for k, v in null_v.items()},
             **{f"H_{k}": v for k, v in null_H.items()})
    print(f"{tf} done {time.time() - t0:.0f}s", flush=True)


def _stat_rows(group: str, btc_v: np.ndarray, null_vs: dict[str, np.ndarray]) -> list[dict]:
    """btc_v: counters of a scale or a pool; null_vs: kind -> (paths, counters)."""
    rows = []
    for key, label, _, _ in WINDOWS:
        for s in SLICES:
            n_b = btc_v[INDEX[f"n|{s}"]]
            hit_b = btc_v[INDEX[f"hit|{key}|{label}|{s}"]]
            row = {"group": group, "key": key, "window": label, "slice": s, "price": "log", "n": int(n_b), "hits": int(hit_b),
                   "btc": float(hit_b / n_b) if n_b else float("nan")}
            for k, nv in null_vs.items():
                with np.errstate(divide="ignore", invalid="ignore"):
                    rates = nv[:, INDEX[f"hit|{key}|{label}|{s}"]] / nv[:, INDEX[f"n|{s}"]]
                lo, mid, hi = q5_50_95(rates)
                row.update({f"{k}_p5": lo, f"{k}_median": mid, f"{k}_p95": hi,
                            f"{k}_p_high": mc_p_high(row["btc"], rates) if n_b else float("nan"),
                            f"{k}_p_low": mc_p_high(-row["btc"], -rates) if n_b else float("nan")})
            rows.append(row)
        if key in RATIOS:
            n_b = btc_v[INDEX["n|all"]]
            hit_b = btc_v[INDEX[f"hit_lin|{key}|{label}|all"]]
            row = {"group": group, "key": key, "window": label, "slice": "all", "price": "lin", "n": int(n_b), "hits": int(hit_b),
                   "btc": float(hit_b / n_b) if n_b else float("nan")}
            for k, nv in null_vs.items():
                with np.errstate(divide="ignore", invalid="ignore"):
                    rates = nv[:, INDEX[f"hit_lin|{key}|{label}|all"]] / nv[:, INDEX["n|all"]]
                lo, mid, hi = q5_50_95(rates)
                row.update({f"{k}_p5": lo, f"{k}_median": mid, f"{k}_p95": hi,
                            f"{k}_p_high": mc_p_high(row["btc"], rates) if n_b else float("nan"),
                            f"{k}_p_low": mc_p_high(-row["btc"], -rates) if n_b else float("nan")})
            rows.append(row)
    return rows


def _excess_rows(group: str, btc_v: np.ndarray, null_vs: dict[str, np.ndarray]) -> list[dict]:
    rows = []
    for key, levels in LEVELS.items():
        for level in levels:
            b, sh = btc_v[INDEX[f"band|{key}|{level}"]], btc_v[INDEX[f"sh|{key}|{level}"]]
            value = (b + 0.5) / ((sh + 1.5) / 3)
            row = {"group": group, "key": key, "level": level, "band": int(b), "shoulders": int(sh), "excess_btc": float(value)}
            for k, nv in null_vs.items():
                x = (nv[:, INDEX[f"band|{key}|{level}"]] + 0.5) / ((nv[:, INDEX[f"sh|{key}|{level}"]] + 1.5) / 3)
                lo, mid, hi = q5_50_95(x)
                row.update({f"{k}_p5": lo, f"{k}_median": mid, f"{k}_p95": hi, f"{k}_p_high": mc_p_high(value, x)})
            rows.append(row)
    return rows


def _derived(group: str, btc_v: np.ndarray, null_vs: dict[str, np.ndarray]) -> dict:
    def stats(v: np.ndarray) -> dict[str, np.ndarray]:
        n = v[..., INDEX["n|all"]]
        with np.errstate(divide="ignore", invalid="ignore"):
            return {
                "share_w1_longest": v[..., INDEX["longest|w1"]] / n,
                "share_w3_longest": v[..., INDEX["longest|w3"]] / n,
                "share_w5_longest": v[..., INDEX["longest|w5"]] / n,
                "spearman_w2_w4": v[..., INDEX["alt|num"]] / v[..., INDEX["alt|den"]],
                "addone_1618": v[..., INDEX["addone|hit1618"]] / v[..., INDEX["addone|n1618"]],
                "addone_2618": v[..., INDEX["addone|hit2618"]] / v[..., INDEX["addone|n2618"]],
                "shallow_w2_strong_uptrend": v[..., INDEX["strong|shallow"]] / v[..., INDEX["strong|n"]],
                "shallow_w2_other": v[..., INDEX["other|shallow"]] / v[..., INDEX["other|n"]],
            }
    b = stats(btc_v)
    row = {"group": group, "n": int(btc_v[INDEX["n|all"]]), "n_strong": int(btc_v[INDEX["strong|n"]]), "n_other": int(btc_v[INDEX["other|n"]]),
           "n_addone_1618": int(btc_v[INDEX["addone|n1618"]]), "n_addone_2618": int(btc_v[INDEX["addone|n2618"]])}
    for name, value in b.items():
        row[name] = float(value)
        for k, nv in null_vs.items():
            x = stats(nv)[name]
            lo, mid, hi = q5_50_95(x)
            row.update({f"{name}|{k}_p5": lo, f"{name}|{k}_median": mid, f"{name}|{k}_p95": hi})
            if np.isfinite(value):
                row[f"{name}|{k}_p_high"] = mc_p_high(float(value), x)
                row[f"{name}|{k}_p_low"] = mc_p_high(-float(value), -x)
    return row


def _hist_rows(tf: str, cell: str, btc_H: np.ndarray, null_Hs: dict[str, np.ndarray]) -> list[dict]:
    rows = []
    fit, test = [0, 1, 2], 3
    for hi_, key in enumerate(HIST_KEYS):
        h = btc_H[hi_].astype(float)
        row = {"tf": tf, "scale": cell, "key": key, "n": int(h.sum()), "n_test": int(h[test].sum())}
        full = h.sum(axis=0)
        for k, H_all in null_Hs.items():
            H = H_all[:, hi_].astype(float)
            pooled = H.sum(axis=(0, 1))
            pool = pooled / max(pooled.sum(), 1)
            shares = H.sum(axis=1) / np.maximum(H.sum(axis=(1, 2), keepdims=False)[:, None], 1)
            ks_b = np.abs(np.cumsum(full / max(full.sum(), 1)) - np.cumsum(pool)).max() if full.sum() else float("nan")
            ks_n = np.abs(np.cumsum(shares, axis=1) - np.cumsum(pool)).max(axis=1)
            row.update({f"{k}_ks": float(ks_b), f"{k}_ks_p": mc_p_high(ks_b, ks_n) if full.sum() else float("nan")})
            # Learnability, smoothed: a histogram fitted on the earlier eras against the null's pool of 2022-2026.
            test_pool = H[:, test].sum(axis=0) + 0.5
            f_null = test_pool / test_pool.sum()

            def gain(train: np.ndarray, t: np.ndarray) -> float:
                f = train + 0.5
                f = f / f.sum()
                return float((t * (np.log(f) - np.log(f_null))).sum() / t.sum()) if t.sum() else float("nan")

            if h[test].sum() >= 5:
                g_b = gain(h[fit].sum(axis=0), h[test])
                g_n = np.array([gain(H[j, fit].sum(axis=0), H[j, test]) for j in range(H.shape[0])])
                row.update({f"{k}_gain": g_b, f"{k}_gain_null_median": float(np.nanmedian(g_n)), f"{k}_gain_p": mc_p_high(g_b, g_n)})
                # Fewer parameters: the bands between Fibonacci levels only.
                cb = np.searchsorted(COARSE, np.exp((BINS[:-1] + BINS[1:]) / 2), side="right") - 1

                def bands(a: np.ndarray) -> np.ndarray:
                    return np.stack([a[..., cb == x].sum(axis=-1) for x in range(COARSE.size - 1)], axis=-1)

                fn = bands(H[:, test]).sum(axis=0) + 0.5
                fn = fn / fn.sum()
                tr = bands(H[:, fit].sum(axis=1)) + 0.5
                tr = tr / tr.sum(axis=1, keepdims=True)
                te = bands(H[:, test])
                with np.errstate(invalid="ignore", divide="ignore"):
                    g_cn = (te * (np.log(tr) - np.log(fn))).sum(axis=1) / np.maximum(te.sum(axis=1), 1)
                tb = bands(h[fit].sum(axis=0)) + 0.5
                tb = tb / tb.sum()
                tt = bands(h[test])
                g_cb = float((tt * (np.log(tb) - np.log(fn))).sum() / tt.sum())
                row.update({f"{k}_coarse_gain": g_cb, f"{k}_coarse_gain_null_median": float(np.median(g_cn)), f"{k}_coarse_gain_p": mc_p_high(g_cb, g_cn)})
            for si, (era, _, _) in enumerate(SPANS):
                if era == "before_2014" or h[si].sum() < 5:
                    continue
                pool_e = H[:, si].sum(axis=0)
                share_e = pool_e / max(pool_e.sum(), 1)
                ks_be = np.abs(np.cumsum(h[si] / h[si].sum()) - np.cumsum(share_e)).max()
                s_ = H[:, si] / np.maximum(H[:, si].sum(axis=1, keepdims=True), 1)
                ks_ne = np.abs(np.cumsum(s_, axis=1) - np.cumsum(share_e)).max(axis=1)
                row[f"{k}_ks_p_{era}"] = mc_p_high(ks_be, ks_ne)
        rows.append(row)
    return rows


def report() -> None:
    window_rows, excess_rows, derived_rows, hist_rows = [], [], [], []
    stores = {}
    for tf in BARS_PER_DAY:
        path = OUT / f"b2_{tf}.npz"
        if path.exists():
            stores[tf] = dict(np.load(path))
    per_cell_null = {}
    per_cell_btc = {}
    for tf, d in stores.items():
        cells = [str(c) for c in d["cells"]]
        min_paths = min(d[f"v_{k}"].shape[0] for k in KINDS)
        for ci, cell in enumerate(cells):
            per_cell_btc[cell] = d["btc_v"][ci]
            per_cell_null[cell] = {k: d[f"v_{k}"][:min_paths, ci] for k in KINDS}
            nulls = per_cell_null[cell]
            window_rows += _stat_rows(cell, d["btc_v"][ci], nulls)
            excess_rows += _excess_rows(cell, d["btc_v"][ci], nulls)
            derived_rows.append(_derived(cell, d["btc_v"][ci], nulls))
            hist_rows += _hist_rows(tf, cell, d["btc_H"][ci], {k: d[f"H_{k}"][:min_paths, ci] for k in KINDS})
        # Pool of a timeframe: cells share each null path except in the block family, whose cells are drawn apart.
        pool_b = d["btc_v"].sum(axis=0)
        pool_n = {k: d[f"v_{k}"][:min_paths].sum(axis=1) for k in KINDS}
        window_rows += _stat_rows(f"pool_{tf}", pool_b, pool_n)
        excess_rows += _excess_rows(f"pool_{tf}", pool_b, pool_n)
        derived_rows.append(_derived(f"pool_{tf}", pool_b, pool_n))
    for ladder, cells in LADDERS.items():
        have = [c for c in cells if c in per_cell_btc]
        if len(have) < 2:
            continue
        paths = min(per_cell_null[c][KINDS[0]].shape[0] for c in have)
        pool_b = np.sum([per_cell_btc[c] for c in have], axis=0)
        pool_n = {k: np.sum([per_cell_null[c][k][:paths] for c in have], axis=0) for k in KINDS}
        window_rows += _stat_rows(ladder, pool_b, pool_n)
        excess_rows += _excess_rows(ladder, pool_b, pool_n)
        derived_rows.append(_derived(ladder, pool_b, pool_n))
    # Two-sided p and BH over all windows of the primary slice per null family.
    primary = [r for r in window_rows if r["slice"] == "all" and r["price"] == "log" and r["n"] > 0 and not r["group"].startswith(("pool", "ladder"))]
    summary: dict = {"windows_primary": len(primary)}
    for k in KINDS:
        ps = np.array([min(1.0, 2 * min(r[f"{k}_p_high"], r[f"{k}_p_low"])) for r in primary])
        qs = bh_qvalues(ps)
        for r, p, q in zip(primary, ps, qs):
            r[f"{k}_p2"] = float(p)
            r[f"{k}_q"] = float(q)
        summary[k] = {"p_under_05": int((ps < 0.05).sum()), "expected_by_chance": 0.05 * ps.size, "q_under_05": int((qs < 0.05).sum()),
                      "q_under_10": int((qs < 0.10).sum())}
    write_csv("b2_windows.csv", window_rows)
    write_csv("b2_excess.csv", excess_rows)
    write_csv("b2_derived.csv", derived_rows)
    for k in KINDS:
        for col in ("ks_p", "gain_p", "coarse_gain_p"):
            vals = [r.get(f"{k}_{col}", float("nan")) for r in hist_rows]
            qs = bh_qvalues(np.array(vals, float))
            for r, q in zip(hist_rows, qs):
                r[f"{k}_{col}_q"] = float(q)
    write_csv("b2_shape.csv", hist_rows)
    write_json("b2_summary.json", summary)
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
