"""A targeted test of one lead the bucket tables threw up: setups inside the weekly timing window of the live cycle
machine (168 to 294 days after the last weekly low) reach the 1.618 target less often than setups outside it.

It was found after looking at many buckets, so it needs a harder test than the one that found it:
  - many more null paths, for a real tail estimate;
  - 2013 to 2016 as a holdout: the out-of-sample tables start in 2017, those years were not looked at before this test
    was written down;
  - the same gap for other extension levels;
  - a plain alternative with no cycle machine: days since the lowest low of the last 294 days;
  - does the single flag improve a structure-free walk-forward model, against the same step on null paths;
  - a cluster bootstrap by weekly cycle, because setups in one cycle are not independent.

    uv run --with numpy --with scikit-learn --with lightgbm python research/model-options/spikes/bakeoff/ml_leads.py run --scale 4h_k4 --paths 300
    ... ml_leads.py run --scale 4h_k3 --paths 200 --block-days 60
    ... ml_leads.py explain --scale 4h_k4
    uv run --with numpy --with scikit-learn --with lightgbm python research/model-options/spikes/bakeoff/ml_leads.py report
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np  # noqa: E402
from sklearn.metrics import brier_score_loss, roc_auc_score  # noqa: E402

from ewave.cycles.config import load_rules  # noqa: E402
from ml_features import DAY_MS, GROUPS, SCALES, STATS_START_MS, Samples, build_samples, cycle_states, day_bars, null_series  # noqa: E402
from ml_run import FIRST_TEST_YEAR, MIN_TRAIN, VENUE, fit_lr, jan1, year_of  # noqa: E402
from zigzag import Series, load_series  # noqa: E402

OUT = Path(os.environ.get("BAKE_OUT", "/opt/data/cache/scratch/elliott_research_r1/bake")) / "ml"
EXTS = [1.0, 1.618, 2.236, 2.618]
PHASES = [0, .25, .5, .73, 1.0, 1.27, 1.6, 9]
AGE_WINDOW = 294
AGE_SPLIT = 168


def age_since_low(s: Series, first_day: int) -> np.ndarray:
    """Days since the lowest low of the trailing AGE_WINDOW days, for each day. Reads past days only."""
    _, _, _, low, _ = day_bars(s)
    out = np.zeros(len(low), dtype=np.int32)
    for j in range(len(low)):
        a = max(0, j - AGE_WINDOW)
        seg = low[a:j + 1]
        out[j] = j - (a + seg.index(min(seg)))
    return out


def gap(y: np.ndarray, flag: np.ndarray, sel: np.ndarray) -> dict:
    a, b = sel & flag, sel & ~flag
    return {"gap": float(y[a].mean() - y[b].mean()) if a.any() and b.any() else None, "in_n": int(a.sum()), "out_n": int(b.sum()),
            "in_hit": float(y[a].mean()) if a.any() else None, "out_hit": float(y[b].mean()) if b.any() else None}


def stats(s: Series, sm: Samples, states: dict) -> dict:
    """Everything measured on one path."""
    names = sm.names
    col = lambda n: sm.X[:, names.index(n)]
    years = year_of(sm.t_conf)
    oos, pre = years >= FIRST_TEST_YEAR, years < FIRST_TEST_YEAR
    inw = col("w_in_window") == 1
    phase = col("w_phase")
    out: dict = {"oos": gap(sm.y, inw, oos), "pre": gap(sm.y, inw, pre), "all": gap(sm.y, inw, oos | pre)}
    side = col("s")
    out["oos_up"] = gap(sm.y, inw, oos & (side == 1))
    out["oos_down"] = gap(sm.y, inw, oos & (side == -1))
    out["ext"] = {str(e): gap((sm.ext_max >= e).astype(int), inw, oos) for e in EXTS}
    out["phase"] = []
    for lo, hi in zip(PHASES, PHASES[1:]):
        m = oos & (phase >= lo) & (phase < hi)
        out["phase"].append({"lo": lo, "hi": hi, "n": int(m.sum()), "hit": float(sm.y[m].mean()) if m.any() else None, "barrier": float(sm.p_barrier[m].mean()) if m.any() else None})
    # a stricter reading of what the rulebook calls a W2 setup, on what one degree down can show
    leaf_or = lambda a, b: (col(a) == 1) | (col(b) == 1)
    setup = (col("in_382_618") == 1) & (col("time_rule_ok") == 1) & leaf_or("w1_nested_motive", "w1_leaf") & leaf_or("w2_nested_corrective", "w2_leaf")
    excess = sm.y.astype(float) - sm.p_barrier
    for name, flag in (("setup", setup), ("setup_engulf", setup & (col("engulfs_prior") == 1)), ("setup_after_5", setup & (col("prior_opposite_5") == 1))):
        out[name] = gap(sm.y, flag, oos)
        a, b = oos & flag, oos & ~flag
        out[name]["barrier_gap"] = float(sm.p_barrier[a].mean() - sm.p_barrier[b].mean()) if a.any() and b.any() else None
        out[name]["excess_gap"] = float(excess[a].mean() - excess[b].mean()) if a.any() and b.any() else None
    # the plain alternative
    first_day = states["first_day"]
    days = (sm.t_conf // DAY_MS).astype(np.int64) - 1 - first_day
    age = age_since_low(s, first_day)[days]
    out["age_oos"] = gap(sm.y, age >= AGE_SPLIT, oos)
    out["age_pre"] = gap(sm.y, age >= AGE_SPLIT, pre)
    both = np.column_stack([inw.astype(float), (age >= AGE_SPLIT).astype(float)])
    out["share_both"] = float(np.mean(both[oos, 0] == both[oos, 1]))
    # one flag on top of the structure-free model, walk-forward
    base_idx = [names.index(f) for g in "VD" for f in GROUPS[g]]
    flag_idx = names.index("w_in_window")
    pv, pf, pp = np.full(len(sm.y), np.nan), np.full(len(sm.y), np.nan), np.full(len(sm.y), np.nan)
    phase_x = np.nan_to_num(phase, nan=1.0)[:, None]
    for yr in range(FIRST_TEST_YEAR, int(years.max()) + 1):
        te = np.flatnonzero(years == yr)
        tr = np.flatnonzero(sm.t_resolve < jan1(yr))
        if len(te) == 0 or len(tr) < MIN_TRAIN or len(set(sm.y[tr])) < 2:
            continue
        Xtr, Xte = sm.X[np.ix_(tr, base_idx)], sm.X[np.ix_(te, base_idx)]
        pv[te] = fit_lr(Xtr, sm.y[tr], Xte)
        pf[te] = fit_lr(np.column_stack([Xtr, sm.X[tr, flag_idx]]), sm.y[tr], np.column_stack([Xte, sm.X[te, flag_idx]]))
        pp[te] = fit_lr(np.column_stack([Xtr, phase_x[tr]]), sm.y[tr], np.column_stack([Xte, phase_x[te]]))
    m = ~np.isnan(pv)
    b0 = brier_score_loss(sm.y[m], pv[m])
    out["lr_step_flag"] = {"brier_gain": float(b0 - brier_score_loss(sm.y[m], pf[m])), "auc_gain": float(roc_auc_score(sm.y[m], pf[m]) - roc_auc_score(sm.y[m], pv[m]))}
    out["lr_step_phase"] = {"brier_gain": float(b0 - brier_score_loss(sm.y[m], pp[m])), "auc_gain": float(roc_auc_score(sm.y[m], pp[m]) - roc_auc_score(sm.y[m], pv[m]))}
    return out


def cluster_ci(sm: Samples, states: dict, reps: int = 4000, seed: int = 5) -> dict:
    """Gap and its 95 percent range when whole weekly cycles are resampled."""
    years = year_of(sm.t_conf)
    oos = years >= FIRST_TEST_YEAR
    names = sm.names
    inw = sm.X[:, names.index("w_in_window")] == 1
    days = (sm.t_conf // DAY_MS).astype(np.int64) - 1 - states["first_day"]
    cycle = states["w_anchor"][days]
    ids = np.unique(cycle[oos])
    rng = np.random.default_rng(seed)
    groups = [(sm.y[oos & (cycle == c) & inw], sm.y[oos & (cycle == c) & ~inw]) for c in ids]
    vals = []
    for _ in range(reps):
        pick = rng.integers(0, len(groups), len(groups))
        a = np.concatenate([groups[i][0] for i in pick])
        b = np.concatenate([groups[i][1] for i in pick])
        if len(a) and len(b):
            vals.append(a.mean() - b.mean())
    lo, hi = np.percentile(vals, [2.5, 97.5])
    per_cycle = [{"anchor_day": int(c), "in_n": int(len(g[0])), "in_hit": float(g[0].mean()) if len(g[0]) else None, "out_n": int(len(g[1])), "out_hit": float(g[1].mean()) if len(g[1]) else None} for c, g in zip(ids, groups)]
    return {"cycles": len(ids), "p2.5": float(lo), "p97.5": float(hi), "share_negative": float(np.mean(np.array(vals) < 0)), "per_cycle": per_cycle}


def explain_stats(s: Series, sm: Samples, H: int) -> dict:
    """Why might the gap exist? What does it mean for a trade? Forward volatility against the trailing estimate, signed
    forward drift, and the R of a trade from the entry to target or origin, marked at the close when time runs out. No
    costs, no sizing: a size-of-effect figure and not a backtest."""
    names = sm.names
    inw = sm.X[:, names.index("w_in_window")] == 1
    years = year_of(sm.t_conf)
    logc = np.log(s.close)
    ret = np.diff(logc, prepend=logc[0])
    t = ((sm.t_conf - s.tf_ms - s.ts[0]) // s.tf_ms).astype(np.int64)
    # the series has no holes, so the index follows from the time
    end = np.minimum(t + H, len(s) - 1)
    vol_ratio = np.array([np.sqrt(np.mean(ret[a + 1:b + 1] ** 2)) for a, b in zip(t, end)]) / sm.sigma
    drift = sm.side * (logc[end] - logc[t]) / (sm.sigma * np.sqrt(np.maximum(end - t, 1)))
    risk = np.abs(sm.entry - sm.origin)
    target = sm.p2 + sm.side * 1.618 * sm.leg
    reward = np.abs(target - sm.entry) / risk
    outcome = np.array(sm.outcome)
    r = np.where(outcome == "target", reward, np.where(outcome == "origin", -1.0, sm.side * (s.close[end] - sm.entry) / risk))
    r = np.clip(r, -1.0, 10.0)
    out = {}
    for name, sel in (("2017+", years >= FIRST_TEST_YEAR), ("2013-2016", years < FIRST_TEST_YEAR)):
        for tag, m in (("in", sel & inw), ("out", sel & ~inw)):
            out[f"{name} {tag}"] = {"n": int(m.sum()), "fwd_vol_over_trailing": float(np.median(vol_ratio[m])), "signed_drift": float(np.mean(drift[m])), "mean_R": float(np.mean(r[m])), "median_R": float(np.median(r[m])),
                                    "win": float(np.mean(outcome[m] == "target")), "stop": float(np.mean(outcome[m] == "origin")), "timeout": float(np.mean(outcome[m] == "timeout")), "reward_median": float(np.median(reward[m]))}
    return out


def _explain_job(job: tuple) -> dict:
    scale_name, kind, seed, block_days = job
    s = load_series(VENUE, SCALES[scale_name].tf)
    rules = load_rules()
    first = int(np.searchsorted(s.ts, STATS_START_MS))
    ns = null_series(s, first, kind, block_days, np.random.default_rng(seed))
    sm = build_samples(ns, SCALES[scale_name], rules)
    return explain_stats(ns, sm, SCALES[scale_name].H)


def cmd_explain(args) -> None:
    rules = load_rules()
    sc = SCALES[args.scale]
    s = load_series(VENUE, sc.tf)
    sm = build_samples(s, sc, rules)
    btc = explain_stats(s, sm, sc.H)
    jobs = [(args.scale, kind, 800_000 + (0 if kind == "shuffled" else 100_000) + i, rules.null["block_days"]) for kind in ("shuffled", "block") for i in range(args.paths)]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        nulls = list(pool.map(_explain_job, jobs, chunksize=2))
    (OUT / f"explain_{args.scale}.json").write_text(json.dumps({"btc": btc, "nulls": nulls}))
    print(f"\n### {args.scale}: what the gap looks like (BTC; null is both kinds, {len(nulls)} paths)\n")
    print("| period, setups | n | target first | origin first | timeout | median reward:risk | mean R | null mean R, median (5 to 95) | median R | forward vol / trailing vol | signed drift, in sigma |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for key, v in btc.items():
        vals = [r[key]["mean_R"] for r in nulls if r[key]["n"]]
        lo, md, hi = np.percentile(vals, [5, 50, 95])
        print(f"| {key} | {v['n']} | {v['win']:.0%} | {v['stop']:.0%} | {v['timeout']:.0%} | {v['reward_median']:.2f} | {v['mean_R']:+.2f} | {md:+.2f} ({lo:+.2f} to {hi:+.2f}) | {v['median_R']:+.2f} | {v['fwd_vol_over_trailing']:.2f} | {v['signed_drift']:+.2f} |")


def _job(job: tuple) -> dict:
    scale_name, kind, seed, *rest = job
    s = load_series(VENUE, SCALES[scale_name].tf)
    rules = load_rules()
    first = int(np.searchsorted(s.ts, STATS_START_MS))
    block_days = rest[0] if rest else rules.null["block_days"]
    ns = null_series(s, first, kind, block_days, np.random.default_rng(seed))
    st = cycle_states(ns, rules)
    sm = build_samples(ns, SCALES[scale_name], rules, states=st)
    r = stats(ns, sm, st)
    r["kind"] = kind
    return r


def cmd_run(args) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rules = load_rules()
    sc = SCALES[args.scale]
    s = load_series(VENUE, sc.tf)
    st = cycle_states(s, rules)
    sm = build_samples(s, sc, rules, states=st)
    btc = stats(s, sm, st)
    btc["cluster"] = cluster_ci(sm, st)
    if args.block_days:
        # a longer block keeps more of the real order: does the gap need structure longer than this?
        jobs = [(args.scale, "block", 950_000 + i, args.block_days) for i in range(args.paths)]
        tag = f"_block{args.block_days}"
    else:
        jobs = [(args.scale, kind, 900_000 + (0 if kind == "shuffled" else 100_000) + i) for kind in ("shuffled", "block") for i in range(args.paths)]
        tag = ""
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        nulls = list(pool.map(_job, jobs, chunksize=4))
    (OUT / f"leads_{args.scale}{tag}.json").write_text(json.dumps({"btc": btc, "nulls": nulls}))
    print(f"{args.scale}{tag}: {len(nulls)} null paths in {time.time()-t0:.0f}s", flush=True)


def line(name: str, value: float | None, runs: list[float], lower_is_lead: bool = True) -> str:
    if value is None or not runs:
        return f"| {name} | n/a | | |"
    v = np.array(runs)
    lo, md, hi = np.percentile(v, [5, 50, 95])
    tail = np.mean(v <= value) if lower_is_lead else np.mean(v >= value)
    return f"| {name} | {value*100:+.1f} | {md*100:+.1f} ({lo*100:+.1f} to {hi*100:+.1f}) | {tail:.1%} |"


def cmd_report(args) -> None:
    for f in sorted(OUT.glob("leads_*.json")):
        d = json.loads(f.read_text())
        b, nulls = d["btc"], d["nulls"]
        print(f"\n### {f.stem}: {len(nulls)} null paths. Inside the weekly window minus outside, percentage points\n")
        print("| measure | BTC | null median (5 to 95) | share of null paths at least this extreme |")
        print("|---|---|---|---|")
        for kind in ("shuffled", "block"):
            runs = [r for r in nulls if r["kind"] == kind]
            if not runs:
                continue
            print(f"| **{kind}** | | | |")
            for name, key in (("hit gap, 2017+ (where it was found)", "oos"), ("hit gap, 2013-2016 (holdout)", "pre"), ("hit gap, up setups 2017+", "oos_up"), ("hit gap, down setups 2017+", "oos_down")):
                print(line(name, b[key]["gap"], [r[key]["gap"] for r in runs if r[key]["gap"] is not None]))
            for e in EXTS:
                print(line(f"reach {e} x leg, gap 2017+", b["ext"][str(e)]["gap"], [r["ext"][str(e)]["gap"] for r in runs if r["ext"][str(e)]["gap"] is not None]))
            for key2, name2 in (("setup", "rulebook W2 setup (0.382-0.618, time rule, legs parse), hit minus barrier, against the rest"), ("setup_engulf", "same, W1 also engulfs the prior swing"), ("setup_after_5", "same, after a legal opposite five")):
                print(line(name2, b[key2]["excess_gap"], [r[key2]["excess_gap"] for r in runs if r[key2]["excess_gap"] is not None], lower_is_lead=False))
            print(line("plain alternative: lowest low of 294 days is 168+ days old, 2017+", b["age_oos"]["gap"], [r["age_oos"]["gap"] for r in runs if r["age_oos"]["gap"] is not None]))
            print(line("plain alternative, 2013-2016", b["age_pre"]["gap"], [r["age_pre"]["gap"] for r in runs if r["age_pre"]["gap"] is not None]))
            print(line("walk-forward Brier gain x 1000, flag on top of volatility + trend", b["lr_step_flag"]["brier_gain"] * 10, [r["lr_step_flag"]["brier_gain"] * 10 for r in runs], lower_is_lead=False))
            print(line("walk-forward Brier gain x 1000, phase on top of volatility + trend", b["lr_step_phase"]["brier_gain"] * 10, [r["lr_step_phase"]["brier_gain"] * 10 for r in runs], lower_is_lead=False))
            print(line("walk-forward AUC gain x 100, flag", b["lr_step_flag"]["auc_gain"], [r["lr_step_flag"]["auc_gain"] for r in runs], lower_is_lead=False))
        print(f"\nBTC samples: 2017+ in {b['oos']['in_n']} ({b['oos']['in_hit']:.1%}), out {b['oos']['out_n']} ({b['oos']['out_hit']:.1%}); 2013-2016 in {b['pre']['in_n']} ({b['pre']['in_hit'] if b['pre']['in_hit'] is None else round(b['pre']['in_hit'],3)}), out {b['pre']['out_n']} ({round(b['pre']['out_hit'],3)}). "
              f"Flag and plain alternative agree on {b['share_both']:.0%} of setups.")
        print(f"Setups: rulebook W2 {b['setup']['in_n']} (hit {b['setup']['in_hit']:.1%}), rest {b['setup']['out_n']} (hit {b['setup']['out_hit']:.1%}); with engulf {b['setup_engulf']['in_n']} (hit {b['setup_engulf']['in_hit']}), after a five {b['setup_after_5']['in_n']} (hit {b['setup_after_5']['in_hit']}).")
        overall = lambda r: sum(x["n"] * (x["hit"] - x["barrier"]) for x in r["phase"] if x["n"]) / sum(x["n"] for x in r["phase"] if x["n"])
        print(f"Hit rate minus the raw volatility barrier, all setups with a live weekly low, 2017+: BTC {overall(b)*100:+.1f} points; " + "; ".join(
            f"{kind} median {np.median([overall(r) for r in nulls if r['kind'] == kind])*100:+.1f} (5 to 95: {np.percentile([overall(r) for r in nulls if r['kind'] == kind], 5)*100:+.1f} to {np.percentile([overall(r) for r in nulls if r['kind'] == kind], 95)*100:+.1f})" for kind in ("shuffled", "block") if any(r["kind"] == kind for r in nulls)))
        c = b["cluster"]
        print(f"Resampling whole weekly cycles ({c['cycles']} of them): gap 95 percent range {c['p2.5']*100:+.1f} to {c['p97.5']*100:+.1f}, {c['share_negative']:.1%} of resamples negative.")
        print("\n| weekly phase (days since live low / 231) | n | hit | barrier |")
        print("|---|---|---|---|")
        for p in b["phase"]:
            if p["n"]:
                print(f"| {p['lo']:.2f} to {p['hi']:.2f} | {p['n']} | {p['hit']:.0%} | {p['barrier']:.0%} |")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--scale", default="4h_k4")
    r.add_argument("--paths", type=int, default=300)
    r.add_argument("--workers", type=int, default=2)
    r.add_argument("--block-days", type=int, default=0)
    e = sub.add_parser("explain")
    e.add_argument("--scale", default="4h_k4")
    e.add_argument("--paths", type=int, default=20)
    e.add_argument("--workers", type=int, default=1)
    sub.add_parser("report")
    args = ap.parse_args()
    {"run": cmd_run, "report": cmd_report, "explain": cmd_explain}[args.cmd](args)


if __name__ == "__main__":
    main()
