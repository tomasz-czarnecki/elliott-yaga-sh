"""Are rule-legal wave structures more common on BTC than on random paths? And how many readings does a window have?

For each path, on one zigzag scale, from 2013-03 on:
  - the share of runs of 6 consecutive pivots that form a legal impulse or diagonal, and of 4 that form a legal zigzag or flat;
  - for a window of the last 12 pivots, sampled every 5th pivot: how many legal readings end on its last pivot.

    uv run --with numpy python research/model-options/spikes/bakeoff/ambiguity_null.py --paths 20 --workers 2
"""
from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from enumerator import readings
from ewave.cycles.config import load_rules
from ml_features import SCALES, STATS_START_MS, null_series
from rules import ED, FLAT_EXP, FLAT_REG, FLAT_RUN, IMPULSE, LD, ZIGZAG, Point, hard, violations
from zigzag import load_series, threshold, zigzag

OUT = Path(os.environ.get("BAKE_OUT", "/opt/data/cache/scratch/elliott_research_r1/bake"))
VENUE = "bitstamp_btcusd"
LAB5 = ("0", "1", "2", "3", "4", "5")
LAB3 = ("0", "A", "B", "C")


def legal(pattern: str, labs: tuple, ps: list) -> bool:
    d = "up" if ps[1].price > ps[0].price else "down"
    return not hard(violations(pattern, d, {k: Point(p.i, p.price) for k, p in zip(labs, ps)}))


def measure(s, first: int, scale_name: str) -> dict:
    sc = SCALES[scale_name]
    piv, _ = zigzag(s, threshold(s, sc.k), start=0)
    piv = [p for p in piv if p.i >= first]
    imp, diag, zz, flat = [], [], [], []
    for m in range(len(piv) - 5):
        ps = piv[m:m + 6]
        imp.append(legal(IMPULSE, LAB5, ps))
        diag.append(legal(ED, LAB5, ps) or legal(LD, LAB5, ps))
    for m in range(len(piv) - 3):
        ps = piv[m:m + 4]
        zz.append(legal(ZIGZAG, LAB3, ps))
        flat.append(any(legal(f, LAB3, ps) for f in (FLAT_REG, FLAT_RUN, FLAT_EXP)))
    strict, loose, states = [], [], []
    for m in range(12, len(piv), 5):
        ps = piv[m - 12:m]
        pr, br = [p.price for p in ps], [p.i for p in ps]
        rs = readings(pr, br)
        strict.append(len(rs))
        loose.append(len(readings(pr, br, hidden_sub=True)))
        states.append(len({(r.pattern, r.labels[-1][0]) for r in rs}))
    return {"pivots": len(piv), "impulse": float(np.mean(imp)), "diagonal": float(np.mean(diag)), "zigzag": float(np.mean(zz)), "flat": float(np.mean(flat)),
            "strict_median": float(np.median(strict)), "loose_median": float(np.median(loose)), "states_median": float(np.median(states)), "windows": len(strict)}


def _job(job: tuple) -> dict:
    scale_name, kind, seed = job
    s = load_series(VENUE, SCALES[scale_name].tf)
    rules = load_rules()
    first = int(np.searchsorted(s.ts, STATS_START_MS))
    ns = null_series(s, first, kind, rules.null["block_days"], np.random.default_rng(seed))
    return {"kind": kind, **measure(ns, first, scale_name)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="4h_k4")
    ap.add_argument("--paths", type=int, default=20)
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    s = load_series(VENUE, SCALES[args.scale].tf)
    first = int(np.searchsorted(s.ts, STATS_START_MS))
    btc = measure(s, first, args.scale)
    jobs = [(args.scale, kind, 700_000 + (0 if kind == "shuffled" else 50_000) + i) for kind in ("shuffled", "block") for i in range(args.paths)]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        nulls = list(pool.map(_job, jobs, chunksize=2))
    (OUT / "ml" / f"ambiguity_{args.scale}.json").write_text(json.dumps({"btc": btc, "nulls": nulls}))
    print(f"\n### {args.scale}: legal structures on BTC against random paths ({args.paths} paths each)\n")
    print("| measure | BTC | shuffled, median (5 to 95) | block, median (5 to 95) |")
    print("|---|---|---|---|")
    names = {"pivots": "pivots", "impulse": "6-pivot runs that are a legal impulse", "diagonal": "6-pivot runs that are a legal diagonal", "zigzag": "4-pivot runs that are a legal zigzag", "flat": "4-pivot runs that are a legal flat",
             "strict_median": "legal readings of a 12-pivot window, strict, median", "loose_median": "same, loose, median", "states_median": "distinct states among them, median"}
    for key, name in names.items():
        row = [name, f"{btc[key]:.3f}" if btc[key] < 1 else f"{btc[key]:.0f}"]
        for kind in ("shuffled", "block"):
            v = [r[key] for r in nulls if r["kind"] == kind]
            lo, md, hi = np.percentile(v, [5, 50, 95])
            row.append(f"{md:.3f} ({lo:.3f} to {hi:.3f})" if md < 1 else f"{md:.0f} ({lo:.0f} to {hi:.0f})")
        print("| " + " | ".join(row) + " |")


if __name__ == "__main__":
    main()
