"""Section A, background: the plain facts any model of BTC meets first. How much is predictable at all, before waves.

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/a4_facts.py --paths 500

  F1 Autocorrelation of bar returns (direction) and of absolute returns (volatility), against shuffled bars.
  F2 Volatility forecast: next bar's log range on the trailing 20-bar mean of log range, fitted up to 2021, scored 2022-2026.
  F3 Variance ratios of daily log returns: above 1 means trending at that horizon, below 1 mean-reverting. Against shuffled days.
  F4 Time-series momentum: does the sign of the past N days predict the sign of the next N days? Non-overlapping windows.
  F5 Up legs against down legs of the zigzag: size, duration, speed. Against signflip and trendflip paths, which have no
     such asymmetry beyond volatility and the slow trend.

Writes a4_facts.json and a4_legs.csv to the scratch folder. About 3 minutes.
"""
from __future__ import annotations

import argparse

import numpy as np

from common import ANALYSIS_VENUE, BARS_PER_DAY, ERAS, Scale, load_series, mc_p_high, q5_50_95, to_ms, wilson, write_csv, write_json
from nulls import null_bars, to_rel
from zigzag import pivots, zigzag_raw

SEED = 20261036
LEG_CELLS = (Scale("15m", "pct", 2), Scale("1h", "pct", 4), Scale("4h", "pct", 8), Scale("1d", "pct", 16))


def acf(x: np.ndarray, lags) -> np.ndarray:
    x = x - x.mean()
    d = float((x * x).sum())
    return np.array([float((x[:-k] * x[k:]).sum()) / d for k in lags])


def vr(r: np.ndarray, q: int) -> float:
    r = r - r.mean()
    c = np.cumsum(np.r_[0.0, r])
    long = c[q:] - c[:-q]
    return float(long.var() / (q * r.var()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=500)
    args = ap.parse_args()
    out: dict = {}
    rng = np.random.default_rng(SEED)

    # F1
    f1 = {}
    for tf, lags in (("1h", (1, 2, 3, 6, 12, 24)), ("4h", (1, 2, 3, 6, 42)), ("1d", (1, 2, 3, 7, 30))):
        s = load_series(ANALYSIS_VENUE, tf)
        r = np.diff(s.c)
        a_r, a_abs = acf(r, lags), acf(np.abs(r), lags)
        sims_r = np.array([acf(rng.permutation(r), lags) for _ in range(200)])
        band = np.percentile(sims_r, [5, 95], axis=0)
        f1[tf] = {"lags": lags, "return_acf": a_r.tolist(), "abs_return_acf": a_abs.tolist(), "shuffle_band_5": band[0].tolist(), "shuffle_band_95": band[1].tolist()}
        for era, a, b in ERAS:
            mask = (s.ts[1:] >= to_ms(a)) & (s.ts[1:] < to_ms(b))
            f1[tf][f"return_acf_lag1_{era}"] = float(acf(r[mask], (1,))[0])
    out["f1"] = f1

    # F2
    f2 = {}
    for tf in ("1h", "4h", "1d"):
        s = load_series(ANALYSIS_VENUE, tf)
        rng_log = np.log(np.maximum(s.h - s.l, 1e-5))
        k = 20
        trail = np.convolve(rng_log, np.ones(k) / k, mode="valid")[:-1]
        target = rng_log[k:]
        ts = s.ts[k:]
        train = ts < to_ms("2022-01-01")
        b, a = np.polyfit(trail[train], target[train], 1)
        pred = a + b * trail[~train]
        ss_res = float(((target[~train] - pred) ** 2).sum())
        ss_tot = float(((target[~train] - target[train].mean()) ** 2).sum())
        f2[tf] = {"slope": float(b), "r2_oos_2022_2026": 1 - ss_res / ss_tot, "n_test": int((~train).sum())}
    out["f2"] = f2

    # F3
    s = load_series(ANALYSIS_VENUE, "1d")
    r = np.diff(s.c)
    qs = (2, 5, 10, 20, 30, 60, 90, 120, 180)
    btc = {q: vr(r, q) for q in qs}
    sims = {q: [] for q in qs}
    for _ in range(args.paths):
        p = rng.permutation(r)
        for q in qs:
            sims[q].append(vr(p, q))
    out["f3"] = {str(q): {"vr": btc[q], "shuffle_p5": float(np.percentile(sims[q], 5)), "shuffle_p95": float(np.percentile(sims[q], 95)),
                          "p_high": mc_p_high(btc[q], np.array(sims[q]))} for q in qs}
    for era, a, b in ERAS:
        mask = (s.ts[1:] >= to_ms(a)) & (s.ts[1:] < to_ms(b))
        out["f3"][era] = {str(q): vr(r[mask], q) for q in qs}

    # F4
    f4 = {}
    for n in (7, 14, 30, 60, 90, 180):
        c = s.c[::n]
        steps = np.diff(c)
        hits = (steps[1:] > 0) == (steps[:-1] > 0)
        k_, m_ = int(hits.sum()), hits.size
        up = (steps > 0).mean()
        lo, hi = wilson(k_, m_)
        # Base rate if signs were independent with this share of up windows.
        base = up * up + (1 - up) * (1 - up)
        f4[str(n)] = {"same_sign": k_ / m_, "lo": lo, "hi": hi, "n": m_, "up_share": float(up), "independent_base": float(base)}
    out["f4"] = f4
    write_json("a4_facts.json", out)

    # F5
    rows = []
    for sc in LEG_CELLS:
        s = load_series(ANALYSIS_VENUE, sc.tf)
        per_day = BARS_PER_DAY[sc.tf]

        def stats(p) -> dict[str, float]:
            legs = np.diff(p.x)
            dur = np.diff(p.i) / per_day
            up = legs > 0
            return {"up_legs": int(up.sum()), "down_legs": int((~up).sum()),
                    "median_up_size": float(np.median(np.expm1(legs[up]))), "median_down_size": float(np.median(-np.expm1(legs[~up]))),
                    "median_up_days": float(np.median(dur[up])), "median_down_days": float(np.median(dur[~up])),
                    "median_up_speed": float(np.median(legs[up] / np.maximum(dur[up], 1 / per_day))),
                    "median_down_speed": float(np.median(-legs[~up] / np.maximum(dur[~up], 1 / per_day))),
                    "down_over_up_speed": float(np.median(-legs[~up] / np.maximum(dur[~up], 1 / per_day)) / np.median(legs[up] / np.maximum(dur[up], 1 / per_day))),
                    "down_over_up_days": float(np.median(dur[~up]) / np.median(dur[up]))}

        btc = stats(pivots(s, sc))
        rel = to_rel(s.o, s.h, s.l, s.c, s.high_first, per_day)
        row = {"scale": sc.name, **btc}
        for kind in ("signflip", "trendflip"):
            rng_ = np.random.default_rng([SEED, ord(kind[0]), per_day])
            runs = []
            for _ in range(min(args.paths, 200)):
                o, h, l, c, hf = null_bars(rel, kind, rng_)
                runs.append(stats(zigzag_raw(h, l, c, hf, sc)))
            for key in ("down_over_up_speed", "down_over_up_days", "median_up_size", "median_down_size"):
                vals = np.array([r[key] for r in runs])
                lo, mid, hi = q5_50_95(vals)
                row.update({f"{key}|{kind}_p5": lo, f"{key}|{kind}_median": mid, f"{key}|{kind}_p95": hi,
                            f"{key}|{kind}_p": min(1.0, 2 * min(mc_p_high(btc[key], vals), mc_p_high(-btc[key], -vals)))})
        rows.append(row)
    write_csv("a4_legs.csv", rows)
    print("done")


if __name__ == "__main__":
    main()
