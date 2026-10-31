"""Section A: how many swings, how many rule-legal impulses, how many independent structures, on BTC and on null paths.

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/a_census.py [--paths 200]

Writes census_btc.csv (every scale, all three venues), census_null.csv (null medians and ranges, Bitstamp), census_stages.csv
(what a growing count predicts, one leg at a time), census_eras.csv (the legal rate per era) and census_summary.json to the
scratch folder. About 8 minutes at 1000 paths per null.

The block null uses a block equal to the median leg duration of the scale under test (at least 3 bars), so that adjacent
legs rarely fall in one block; shuffle and signflip paths are shared by all scales of a timeframe. Reported per scale: legs, legs a year, median leg duration, median leg size, windows of six
pivots, rule-legal up and down impulses, truncated, diagonal candidates, which rule kills first, non-overlapping count.
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from common import (ANALYSIS_VENUE, BARS_PER_DAY, ERAS, SCALES, VENUES, bh_qvalues, load_series, mc_p_high, q5_50_95, to_ms,
                    write_csv, write_json)
from impulse import RULE_NAMES, STAGES, check, first_broken, non_overlapping, stages, threes
from nulls import KINDS, null_bars, to_rel
from zigzag import pivots, zigzag_raw


def block_for(series, scale) -> int:
    """Median leg duration (bars) at this scale, at least 3."""
    p = pivots(series, scale)
    return max(3, int(round(float(np.median(np.diff(p.i)))))) if len(p) > 2 else 3


def measure(p, c, years: float, per_day: int, with_detail: bool = True) -> dict:
    legs = len(p) - 1
    legal, trunc, diag = c.legal, c.truncated, c.diagonal
    up = c.direction == 1
    out = {
        "legs": legs,
        "legs_per_year": legs / years if years else 0.0,
        "windows": len(c),
        "legal": int(legal.sum()),
        "legal_up": int((legal & up).sum()),
        "legal_down": int((legal & ~up).sum()),
        "legal_rate": float(legal.mean()) if len(c) else float("nan"),
        "truncated": int(trunc.sum()),
        "diagonal": int(diag.sum()),
        "independent": non_overlapping(c.subset(legal)),
    }
    if with_detail:
        d = np.diff(p.i) / per_day
        size = np.abs(np.diff(p.x))
        out.update({
            "median_leg_days": float(np.median(d)) if legs else float("nan"),
            "median_leg_size": float(np.median(np.expm1(size))) if legs else float("nan"),
            "legal_linear_r3": int((c.legal | (((c.flags & 15) == 4) & ((c.flags & 16) == 0) & ~c.r3_linear)).sum() -
                                   (c.legal & c.r3_linear).sum()) if len(c) else 0,
        })
        for name, count in first_broken(c.flags).items():
            out[f"killed_{name[:2]}"] = count
        t = threes(p)
        out["threes"] = t.start.size
        out["threes_zigzag_legal"] = int(t.legal.sum())
        out["threes_any_legal"] = int(t.legal_any.sum())
    return out


def stage_rates(p) -> dict[str, float]:
    """Pass rate and n of each stage: all directions, then up and down."""
    out: dict[str, float] = {}
    for name, arr in stages(p).items():
        for label, mask in (("all", np.ones(arr.shape[1], bool)), ("up", arr[0] == 1), ("down", arr[0] == -1)):
            hits = arr[1][mask]
            out[f"{name}|{label}|n"] = float(hits.size)
            out[f"{name}|{label}|rate"] = float(hits.mean()) if hits.size else float("nan")
    return out


def era_rates(c, bar_edges: list[tuple[int, int]]) -> dict[str, float]:
    """Legal rate and count per era, a window belonging to the era of its first pivot."""
    out: dict[str, float] = {}
    for (name, _, _), (a, b) in zip(ERAS, bar_edges):
        mask = (c.i[:, 0] >= a) & (c.i[:, 0] < b)
        n = int(mask.sum())
        out[f"{name}|windows"] = n
        out[f"{name}|legal"] = int(c.legal[mask].sum())
        out[f"{name}|rate"] = float(c.legal[mask].mean()) if n else float("nan")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261030)
    args = ap.parse_args()
    t0 = time.time()

    rows = []
    for venue in VENUES:
        for tf, per_day in BARS_PER_DAY.items():
            s = load_series(venue, tf)
            for scale in [x for x in SCALES if x.tf == tf]:
                p = pivots(s, scale)
                c = check(p)
                rows.append({"venue": venue, "tf": tf, "scale": scale.name, "bars": len(s), "years": s.years,
                             **measure(p, c, s.years, per_day)})
    write_csv("census_btc.csv", rows)
    print(f"BTC census done, {time.time() - t0:.0f}s")

    rng = np.random.default_rng(args.seed)
    null_rows, stage_rows, era_rows, summary = [], [], [], {}
    btc_index = {r["scale"]: r for r in rows if r["venue"] == ANALYSIS_VENUE}
    for tf, per_day in BARS_PER_DAY.items():
        s = load_series(ANALYSIS_VENUE, tf)
        edges = [(int(np.searchsorted(s.ts, to_ms(a))), int(np.searchsorted(s.ts, to_ms(b)))) for _, a, b in ERAS]
        tf_scales = [x for x in SCALES if x.tf == tf]
        blocks = {sc.name: block_for(s, sc) for sc in tf_scales}
        summary[tf] = {"block_bars": blocks}
        rel = to_rel(s.o, s.h, s.l, s.c, s.high_first, per_day)
        btc_piv = {sc.name: pivots(s, sc) for sc in tf_scales}
        btc_stage = {k: stage_rates(p) for k, p in btc_piv.items()}
        btc_era = {k: era_rates(check(p), edges) for k, p in btc_piv.items()}
        store = {(k, sc.name): [] for k in KINDS for sc in tf_scales}
        store_stage = {(k, sc.name): [] for k in KINDS for sc in tf_scales}
        store_era = {(k, sc.name): [] for k in KINDS for sc in tf_scales}

        def one(kind, sc, h, l, c_, hf):
            p = zigzag_raw(h, l, c_, hf, sc)
            c = check(p)
            store[(kind, sc.name)].append(measure(p, c, s.years, per_day, with_detail=False))
            store_stage[(kind, sc.name)].append(stage_rates(p))
            store_era[(kind, sc.name)].append(era_rates(c, edges))

        for _ in range(args.paths):
            for kind in ("shuffle", "signflip", "trendflip"):
                o, h, l, c_, hf = null_bars(rel, kind, rng)
                for sc in tf_scales:
                    one(kind, sc, h, l, c_, hf)
            for sc in tf_scales:
                o, h, l, c_, hf = null_bars(rel, "block", rng, block=blocks[sc.name])
                one("block", sc, h, l, c_, hf)

        for sc in tf_scales:
            btc = btc_index[sc.name]
            for kind in KINDS:
                runs = store[(kind, sc.name)]
                row = {"tf": tf, "scale": sc.name, "null": kind, "paths": len(runs)}
                for key in ("legs", "legal", "legal_up", "legal_down", "legal_rate", "truncated", "diagonal", "independent"):
                    values = np.array([r[key] for r in runs], float)
                    lo, mid, hi = q5_50_95(values)
                    row.update({f"{key}_p5": lo, f"{key}_median": mid, f"{key}_p95": hi})
                    row[f"{key}_btc"] = btc[key]
                    row[f"{key}_p_high"] = mc_p_high(float(btc[key]), values)
                    row[f"{key}_p_low"] = mc_p_high(-float(btc[key]), -values)
                null_rows.append(row)

                for stage in STAGES:
                    for label in ("all", "up", "down"):
                        key = f"{stage}|{label}"
                        values = np.array([r[f"{key}|rate"] for r in store_stage[(kind, sc.name)]], float)
                        v = btc_stage[sc.name][f"{key}|rate"]
                        lo, mid, hi = q5_50_95(values)
                        stage_rows.append({"tf": tf, "scale": sc.name, "null": kind, "stage": stage, "direction": label,
                                           "n": btc_stage[sc.name][f"{key}|n"], "btc": v, "null_p5": lo, "null_median": mid,
                                           "null_p95": hi, "p_high": mc_p_high(v, values) if np.isfinite(v) else float("nan"),
                                           "p_low": mc_p_high(-v, -values) if np.isfinite(v) else float("nan")})
                for era, _, _ in ERAS:
                    values = np.array([r[f"{era}|rate"] for r in store_era[(kind, sc.name)]], float)
                    v = btc_era[sc.name][f"{era}|rate"]
                    lo, mid, hi = q5_50_95(values)
                    era_rows.append({"tf": tf, "scale": sc.name, "null": kind, "era": era,
                                     "windows": btc_era[sc.name][f"{era}|windows"], "legal": btc_era[sc.name][f"{era}|legal"],
                                     "btc": v, "null_p5": lo, "null_median": mid, "null_p95": hi,
                                     "p_high": mc_p_high(v, values) if np.isfinite(v) else float("nan")})
        print(f"{tf} nulls done, blocks {blocks}, {time.time() - t0:.0f}s", flush=True)
    for kind in KINDS:
        chosen = [r for r in null_rows if r["null"] == kind]
        for r, q in zip(chosen, bh_qvalues(np.array([r["legal_rate_p_high"] for r in chosen]))):
            r["legal_rate_q_high"] = float(q)
    write_csv("census_stages.csv", stage_rows)
    write_csv("census_eras.csv", era_rows)
    write_csv("census_null.csv", null_rows)
    write_json("census_summary.json", {"paths": args.paths, "seed": args.seed, "tf": summary,
                                       "rule_names": list(RULE_NAMES.values()), "since": to_ms("2013-03-01")})
    print(f"done {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
