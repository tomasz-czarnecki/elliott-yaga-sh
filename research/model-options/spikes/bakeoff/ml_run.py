"""Walk-forward test of the simple-ML models, on BTC and on null paths. Same code, same fixed settings for all paths.

    uv run --with numpy --with scipy --with scikit-learn --with lightgbm python research/model-options/spikes/bakeoff/ml_run.py btc
    ... ml_run.py null --scale 4h_k4 --kind shuffled --paths 40 --workers 2
    ... ml_run.py power --paths 40

Folds: train on every setup whose label was known before 1 January of the test year (purged, so a setup still open at
the turn of the year cannot leak), test on that year, 2017 onward. Model settings are fixed in advance and never tuned
on a test year. Outputs: $BAKE_OUT/ml/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
warnings.filterwarnings("ignore", message="All-NaN slice")  # the 4-year phase has no low yet in the first folds

import lightgbm as lgb  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score  # noqa: E402

from ewave.cycles.config import load_rules  # noqa: E402
from ml_features import GROUPS, SCALES, STATS_START_MS, Samples, build_samples, logit, null_series  # noqa: E402
from zigzag import load_series  # noqa: E402

OUT = Path(os.environ.get("BAKE_OUT", "/opt/data/cache/scratch/elliott_research_r1/bake")) / "ml"
VENUE = "bitstamp_btcusd"
FIRST_TEST_YEAR = 2017
MIN_TRAIN = 80

SETS = {
    "V": "V", "VD": "VD", "VDF": "VDF", "VDT": "VDT", "VDR": "VDR", "VDC": "VDC", "VDFT": "VDFT", "VDFTR": "VDFTR", "ALL": "VDFTRC",
}
LGB_PARAMS = dict(objective="binary", learning_rate=0.03, n_estimators=200, num_leaves=7, max_depth=3, min_child_samples=25, subsample=0.8,
                  subsample_freq=1, colsample_bytree=0.7, reg_lambda=5.0, verbosity=-1, n_jobs=1, random_state=20261030)

BUCKETS = {
    "r": [0, .236, .382, .5, .618, .786, 1.0001],
    "time_rule_ok": [-.5, .5, 1.5],
    "p2_in_zone": [-.5, .5, 1.5],
    "p1_through_70": [-.5, .5, 1.5],
    "hdiv_p0_p2": [-.5, .5, 1.5],
    "rdiv_at_p0": [-.5, .5, 1.5],
    "prior_opposite_5": [-.5, .5, 1.5],
    "as_w4": [-.5, .5, 1.5],
    "as_c_flat": [-.5, .5, 1.5],
    "w1_nested_motive": [-.5, .5, 1.5],
    "w2_nested_corrective": [-.5, .5, 1.5],
    "engulfs_prior": [-.5, .5, 1.5],
    "s": [-1.5, 0, 1.5],
    "s_w_cos": [-1.01, -.5, .5, 1.01],
    "p0_w_align": [-1.01, -.5, .5, 1.01],
    "s_d_cos": [-1.01, -.5, .5, 1.01],
    "s_y_cos": [-1.01, -.5, .5, 1.01],
    "d_in_window": [-.5, .5, 1.5],
    "w_in_window": [-.5, .5, 1.5],
    "p2_at_w_low": [-.5, .5, 1.5],
    "p2_at_d_low": [-.5, .5, 1.5],
}
EXT_LEVELS = [0.618, 1.0, 1.272, 1.618, 2.0, 2.236, 2.618, 3.236, 4.236]
FIB_STOPS = [1.0, 1.618, 2.236, 2.618, 3.236, 4.236]
OFF_STOPS = [1.3, 1.9, 2.4, 2.9, 3.6, 4.6]  # same spacing, no Fibonacci meaning: the control


def cols(sm: Samples, letters: str) -> np.ndarray:
    idx = [i for g in letters for f in GROUPS[g] for i, n in enumerate(sm.names) if n == f]
    return np.array(idx)


def year_of(ms_arr: np.ndarray) -> np.ndarray:
    return np.array([dt.datetime.fromtimestamp(x / 1000, tz=dt.timezone.utc).year for x in ms_arr])


def jan1(y: int) -> int:
    return int(dt.datetime(y, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)


def fit_lr(Xtr: np.ndarray, ytr: np.ndarray, Xte: np.ndarray, C: float = 0.1) -> np.ndarray:
    med = np.nanmedian(Xtr, axis=0)
    med = np.where(np.isnan(med), 0.0, med)
    a, b = np.where(np.isnan(Xtr), med, Xtr), np.where(np.isnan(Xte), med, Xte)
    mu, sd = a.mean(axis=0), a.std(axis=0)
    sd[sd == 0] = 1.0
    m = LogisticRegression(C=C, max_iter=2000)
    m.fit((a - mu) / sd, ytr)
    return m.predict_proba((b - mu) / sd)[:, 1]


def fit_gbm(Xtr: np.ndarray, ytr: np.ndarray, Xte: np.ndarray) -> tuple[np.ndarray, lgb.LGBMClassifier]:
    m = lgb.LGBMClassifier(**LGB_PARAMS)
    m.fit(Xtr, ytr)
    return m.predict_proba(Xte)[:, 1], m


def walk_forward(sm: Samples, sets: dict = SETS, use_gbm: bool = True, y_override: np.ndarray | None = None, keep_models: bool = False) -> dict:
    """Out-of-sample probabilities per model, plus the row mask of the test years."""
    y = sm.y if y_override is None else y_override
    years = year_of(sm.t_conf)
    last = int(years.max())
    preds: dict[str, np.ndarray] = {}
    def blank(): return np.full(len(y), np.nan)
    names = ["base", "barrier_raw", "barrier_cal"]
    for key in sets:
        names.append(f"lr_{key}")
        if use_gbm:
            names.append(f"gbm_{key}")
    if use_gbm:
        names.append("gbm_ALL_platt")
    for n in names:
        preds[n] = blank()
    idx_sets = {key: cols(sm, letters) for key, letters in sets.items()}
    lp = logit(sm.p_barrier)[:, None]
    fold_models = []
    for yr in range(FIRST_TEST_YEAR, last + 1):
        te = np.flatnonzero(years == yr)
        tr = np.flatnonzero(sm.t_resolve < jan1(yr))
        if len(te) == 0 or len(tr) < MIN_TRAIN or len(set(y[tr])) < 2:
            continue
        preds["base"][te] = y[tr].mean()
        preds["barrier_raw"][te] = sm.p_barrier[te]
        preds["barrier_cal"][te] = fit_lr(lp[tr], y[tr], lp[te], C=100.0)
        for key, ix in idx_sets.items():
            preds[f"lr_{key}"][te] = fit_lr(sm.X[np.ix_(tr, ix)], y[tr], sm.X[np.ix_(te, ix)])
            if use_gbm:
                p, model = fit_gbm(sm.X[np.ix_(tr, ix)], y[tr], sm.X[np.ix_(te, ix)])
                preds[f"gbm_{key}"][te] = p
                if key == "ALL":
                    # Platt on the last quarter of the train years, fitted on a model that did not see them
                    cut = int(len(tr) * .75)
                    if cut >= MIN_TRAIN and len(set(y[tr[:cut]])) == 2 and len(set(y[tr[cut:]])) == 2:
                        p_inner, _ = fit_gbm(sm.X[np.ix_(tr[:cut], ix)], y[tr[:cut]], sm.X[np.ix_(tr[cut:], ix)])
                        lo = logit(np.clip(p_inner, 1e-4, 1 - 1e-4))[:, None]
                        lo_te = logit(np.clip(p, 1e-4, 1 - 1e-4))[:, None]
                        preds["gbm_ALL_platt"][te] = fit_lr(lo, y[tr[cut:]], lo_te, C=100.0)
                    else:
                        preds["gbm_ALL_platt"][te] = p
                    if keep_models:
                        fold_models.append((yr, te, ix, model))
    mask = ~np.isnan(preds["base"])
    return {"preds": preds, "mask": mask, "years": years, "models": fold_models}


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for a, b in zip(edges, edges[1:]):
        m = (p >= a) & (p < b) if b < 1 else (p >= a) & (p <= b)
        if m.any():
            total += m.mean() * abs(y[m].mean() - p[m].mean())
    return float(total)


def calib(y: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    """Slope and intercept of y on logit(p). A slope of 1 and intercept of 0 is perfect; under 1 means overconfident."""
    lo = logit(np.clip(p, 1e-4, 1 - 1e-4))[:, None]
    m = LogisticRegression(C=1e6, max_iter=2000).fit(lo, y)
    return float(m.coef_[0, 0]), float(m.intercept_[0])


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    p = np.clip(p, 1e-4, 1 - 1e-4)
    slope, intercept = calib(y, p)
    return {"brier": float(brier_score_loss(y, p)), "logloss": float(log_loss(y, p)), "auc": float(roc_auc_score(y, p)), "ece": ece(y, p),
            "mean_p": float(p.mean()), "mean_y": float(y.mean()), "slope": slope, "intercept": intercept, "n": int(len(y))}


def score(sm: Samples, wf: dict, y_override: np.ndarray | None = None) -> dict:
    y = sm.y if y_override is None else y_override
    m = wf["mask"]
    return {k: metrics(y[m], v[m]) for k, v in wf["preds"].items() if not np.isnan(v[m]).any()}


def bucket_tables(sm: Samples, wf: dict, ref: str = "barrier_cal") -> dict:
    """For each bucket of a rulebook feature: hit rate against what volatility alone said, out of sample only."""
    m = wf["mask"]
    y, p = sm.y[m], wf["preds"][ref][m]
    out = {}
    for f, edges in BUCKETS.items():
        col = sm.X[m, sm.names.index(f)]
        rows = []
        for a, b in zip(edges, edges[1:]):
            mask = (col >= a) & (col < b)
            rows.append({"lo": a, "hi": b, "n": int(mask.sum()), "hit": float(y[mask].mean()) if mask.any() else None,
                         "ref": float(p[mask].mean()) if mask.any() else None, "excess": float((y[mask] - p[mask]).mean()) if mask.any() else None})
        out[f] = rows
    return out


def extension_table(sm: Samples, s_vol_h: float) -> dict:
    """How far the next move ran, as a multiple of the last leg, before breaking the origin or running out of time."""
    out = {"survival": {}, "stops": {}}
    e = sm.ext_max
    for lv in EXT_LEVELS:
        out["survival"][str(lv)] = float((e >= lv).mean())
    # share of moves that stopped within +-0.05 of a Fibonacci multiple, against the same width at other multiples
    out["stops"]["fib"] = float(np.mean([np.abs(e - lv) <= .05 for lv in FIB_STOPS], axis=1).sum()) / len(FIB_STOPS)
    out["stops"]["off"] = float(np.mean([np.abs(e - lv) <= .05 for lv in OFF_STOPS], axis=1).sum()) / len(OFF_STOPS)
    return out


def lift_table(sm: Samples, wf: dict, model: str, ref: str = "barrier_cal") -> list[dict]:
    """Deciles of the model's probability: its own number, volatility's number, what happened."""
    m = wf["mask"]
    p, q, y = wf["preds"][model][m], wf["preds"][ref][m], sm.y[m]
    order = np.argsort(p)
    out = []
    for chunk in np.array_split(order, 5):
        out.append({"p": float(p[chunk].mean()), "ref": float(q[chunk].mean()), "hit": float(y[chunk].mean()), "n": int(len(chunk))})
    return out


def reliability(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict]:
    edges = np.linspace(0, 1, bins + 1)
    out = []
    for a, b in zip(edges, edges[1:]):
        m = (p >= a) & (p < b) if b < 1 else (p >= a) & (p <= b)
        if m.any():
            out.append({"lo": float(a), "hi": float(b), "n": int(m.sum()), "p": float(p[m].mean()), "hit": float(y[m].mean())})
    return out


def yearly(sm: Samples, wf: dict, names: list[str]) -> dict:
    out = {}
    y = sm.y
    for yr in sorted(set(wf["years"][wf["mask"]])):
        m = wf["mask"] & (wf["years"] == yr)
        out[int(yr)] = {"n": int(m.sum()), "hit": float(y[m].mean()),
                        **{n: float(brier_score_loss(y[m], np.clip(wf["preds"][n][m], 1e-4, 1 - 1e-4))) for n in names}}
    return out


def group_permutation(sm: Samples, wf: dict, repeats: int = 10, seed: int = 11) -> dict:
    """Out-of-sample log loss increase when one group's columns are shuffled inside each test year, for the ALL models."""
    rng = np.random.default_rng(seed)
    out: dict[str, dict] = {}
    y = sm.y
    ix = cols(sm, SETS["ALL"])
    # refit once per fold, then permute
    years = wf["years"]
    last = int(years.max())
    fold_data = []
    for yr in range(FIRST_TEST_YEAR, last + 1):
        te = np.flatnonzero(years == yr)
        tr = np.flatnonzero(sm.t_resolve < jan1(yr))
        if len(te) == 0 or len(tr) < MIN_TRAIN:
            continue
        Xtr, Xte = sm.X[np.ix_(tr, ix)], sm.X[np.ix_(te, ix)]
        gbm = lgb.LGBMClassifier(**LGB_PARAMS).fit(Xtr, y[tr])
        med = np.nanmedian(Xtr, axis=0)
        med = np.where(np.isnan(med), 0.0, med)
        a = np.where(np.isnan(Xtr), med, Xtr)
        mu, sd = a.mean(axis=0), a.std(axis=0)
        sd[sd == 0] = 1.0
        lr = LogisticRegression(C=.1, max_iter=2000).fit((a - mu) / sd, y[tr])
        fold_data.append((te, Xte, gbm, lr, med, mu, sd))
    names = [sm.names[i] for i in ix]
    pos = {n: k for k, n in enumerate(names)}

    def predict(Xte, gbm, lr, med, mu, sd):
        b = np.where(np.isnan(Xte), med, Xte)
        return gbm.predict_proba(Xte)[:, 1], lr.predict_proba((b - mu) / sd)[:, 1]

    y_all = np.concatenate([y[f[0]] for f in fold_data])
    pg = np.concatenate([predict(f[1], *f[2:])[0] for f in fold_data])
    pl = np.concatenate([predict(f[1], *f[2:])[1] for f in fold_data])
    base_g, base_l = log_loss(y_all, np.clip(pg, 1e-4, 1 - 1e-4)), log_loss(y_all, np.clip(pl, 1e-4, 1 - 1e-4))
    def run(columns: list[int]) -> tuple[float, float]:
        dg, dl = [], []
        for _ in range(repeats):
            pg2, pl2 = [], []
            for te, Xte, gbm, lr, med, mu, sd in fold_data:
                X2 = Xte.copy()
                perm = rng.permutation(len(te))
                X2[:, columns] = X2[perm][:, columns]
                a2, b2 = predict(X2, gbm, lr, med, mu, sd)
                pg2.append(a2)
                pl2.append(b2)
            dg.append(log_loss(y_all, np.clip(np.concatenate(pg2), 1e-4, 1 - 1e-4)) - base_g)
            dl.append(log_loss(y_all, np.clip(np.concatenate(pl2), 1e-4, 1 - 1e-4)) - base_l)
        return float(np.mean(dg)), float(np.mean(dl))
    for g, members in GROUPS.items():
        a, b = run([pos[n] for n in members])
        out[g] = {"gbm": a, "lr": b}
    feats = {}
    for n in names:
        a, b = run([pos[n]])
        feats[n] = {"gbm": a, "lr": b}
    gain = np.zeros(len(names))
    for f in fold_data:
        gain += f[2].booster_.feature_importance(importance_type="gain")
    gain = gain / gain.sum()
    return {"groups": out, "features": feats, "gain": {n: float(g) for n, g in zip(names, gain)}, "base_gbm": float(base_g), "base_lr": float(base_l)}


def path_result(sm: Samples, use_gbm: bool = True) -> dict:
    wf = walk_forward(sm, use_gbm=use_gbm)
    scores = score(sm, wf)
    return {"scores": {k: {f: v[f] for f in ("brier", "logloss", "auc", "ece", "slope", "n", "mean_y")} for k, v in scores.items()},
            "buckets": bucket_tables(sm, wf), "extension": extension_table(sm, 0.0), "counts": sm.counts,
            "outcomes": {k: sm.outcome.count(k) for k in ("target", "origin", "timeout")}}


def _null_job(job: tuple) -> dict:
    scale_name, kind, seed, use_gbm, log_target = job
    s = load_series(VENUE, SCALES[scale_name].tf)
    rules = load_rules()
    first = int(np.searchsorted(s.ts, STATS_START_MS))
    rng = np.random.default_rng(seed)
    ns = null_series(s, first, kind, rules.null["block_days"], rng)
    sm = build_samples(ns, SCALES[scale_name], rules, log_target=log_target)
    r = path_result(sm, use_gbm=use_gbm)
    r["kind"] = kind
    r["seed"] = seed
    return r


def cmd_btc(args) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rules = load_rules()
    series = {}
    res = {}
    variants = [(name, False) for name in args.scales] + ([("4h_k4", True)] if "4h_k4" in args.scales else [])
    for name, log_target in variants:
        t0 = time.time()
        sc = SCALES[name]
        s = series.setdefault(sc.tf, load_series(VENUE, sc.tf))
        sm = build_samples(s, sc, rules, log_target=log_target)
        wf = walk_forward(sm)
        key = name + ("_logtarget" if log_target else "")
        r = {"counts": sm.counts, "outcomes": {k: sm.outcome.count(k) for k in ("target", "origin", "timeout")},
             "scores": score(sm, wf), "buckets": bucket_tables(sm, wf), "extension": extension_table(sm, 0.0),
             "yearly": yearly(sm, wf, ["barrier_cal", "lr_VD", "lr_ALL", "gbm_VD", "gbm_ALL"]),
             "reliability": {k: reliability(sm.y[wf["mask"]], wf["preds"][k][wf["mask"]]) for k in ("barrier_raw", "barrier_cal", "lr_VD", "lr_ALL", "gbm_VD", "gbm_ALL", "gbm_ALL_platt")},
             "lift": {k: lift_table(sm, wf, k) for k in ("lr_ALL", "gbm_ALL", "lr_VD")},
             "permutation": group_permutation(sm, wf) if not log_target else None,
             "base_rate_all": float(sm.y.mean()), "base_rate_oos": float(sm.y[wf["mask"]].mean())}
        res[key] = r
        np.savez_compressed(OUT / f"btc_{key}.npz", y=sm.y, t_conf=sm.t_conf, t_resolve=sm.t_resolve, mask=wf["mask"], X=sm.X, names=np.array(sm.names),
                            **{f"p_{k}": v for k, v in wf["preds"].items()})
        print(f"{key}: {sm.counts} base {sm.y.mean():.3f} oos n {wf['mask'].sum()} ({time.time()-t0:.0f}s)", flush=True)
        for k in ("base", "barrier_raw", "barrier_cal", "lr_V", "lr_VD", "lr_VDF", "lr_VDT", "lr_VDR", "lr_VDC", "lr_ALL", "gbm_V", "gbm_VD", "gbm_VDF", "gbm_VDT", "gbm_VDR", "gbm_VDC", "gbm_ALL", "gbm_ALL_platt"):
            v = r["scores"][k]
            print(f"   {k:14} brier {v['brier']:.4f} logloss {v['logloss']:.4f} auc {v['auc']:.3f} ece {v['ece']:.3f} slope {v['slope']:.2f}", flush=True)
        (OUT / "btc.json").write_text(json.dumps(res))


def cmd_null(args) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(args.scale, args.kind, 100_000 * (1 if args.kind == "shuffled" else 2) + i + (500_000 if args.log_target else 0), not args.no_gbm, args.log_target) for i in range(args.paths)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        out = []
        for k, r in enumerate(pool.map(_null_job, jobs, chunksize=1)):
            out.append(r)
            if (k + 1) % 5 == 0:
                print(f"{args.scale} {args.kind}: {k+1}/{len(jobs)} ({time.time()-t0:.0f}s)", flush=True)
    tag = args.scale + ("_logtarget" if args.log_target else "")
    (OUT / f"null_{tag}_{args.kind}.json").write_text(json.dumps(out))
    print(f"done {tag} {args.kind} {len(out)} paths in {time.time()-t0:.0f}s", flush=True)


def _power_job(job: tuple) -> dict:
    """One draw of synthetic labels on BTC's real features, with a known effect added to the fair probability."""
    scale_name, feature_rule, beta, seed = job
    s = load_series(VENUE, SCALES[scale_name].tf)
    rules = load_rules()
    sm = build_samples(s, SCALES[scale_name], rules)
    wf0 = walk_forward(sm, sets={"VD": "VD"}, use_gbm=False)
    # the fair probability: a full-sample fit of the structure-free model, so that y* has no other structure
    ix = cols(sm, "VD")
    fair = fit_lr(sm.X[:, ix], sm.y, sm.X[:, ix])
    col = sm.X[:, sm.names.index(feature_rule[0])]
    z = ((col >= feature_rule[1]) & (col < feature_rule[2])).astype(float)
    rng = np.random.default_rng(seed)
    p = 1 / (1 + np.exp(-(logit(np.clip(fair, 1e-4, 1 - 1e-4)) + beta * z)))
    ystar = (rng.random(len(p)) < p).astype(int)
    sets = {"VD": "VD", "VDF": "VDF"}
    wf = walk_forward(sm, sets=sets, use_gbm=True, y_override=ystar)
    sc = score(sm, wf, y_override=ystar)
    m = wf0["mask"]
    return {"beta": beta, "lift_pp": float((p[z == 1] - fair[z == 1]).mean() * 100), "share": float(z[m].mean()),
            "lr_dbrier": sc["lr_VD"]["brier"] - sc["lr_VDF"]["brier"], "gbm_dbrier": sc["gbm_VD"]["brier"] - sc["gbm_VDF"]["brier"],
            "lr_dauc": sc["lr_VDF"]["auc"] - sc["lr_VD"]["auc"], "gbm_dauc": sc["gbm_VDF"]["auc"] - sc["gbm_VD"]["auc"]}


def cmd_power(args) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rule = ("r", .5, .618)
    jobs = [(args.scale, rule, b, 7000 + 1000 * i + j) for i, b in enumerate(args.betas) for j in range(args.paths)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        out = list(pool.map(_power_job, jobs, chunksize=2))
    (OUT / f"power_{args.scale}.json").write_text(json.dumps(out))
    print(f"power done {len(out)} in {time.time()-t0:.0f}s", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("btc")
    b.add_argument("--scales", nargs="*", default=list(SCALES))
    n = sub.add_parser("null")
    n.add_argument("--scale", default="4h_k4")
    n.add_argument("--kind", default="shuffled", choices=["shuffled", "block"])
    n.add_argument("--paths", type=int, default=40)
    n.add_argument("--workers", type=int, default=2)
    n.add_argument("--no-gbm", action="store_true")
    n.add_argument("--log-target", action="store_true")
    p = sub.add_parser("power")
    p.add_argument("--scale", default="4h_k4")
    p.add_argument("--paths", type=int, default=40)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--betas", nargs="*", type=float, default=[0.0, 0.25, 0.5, 0.75, 1.0])
    args = ap.parse_args()
    {"btc": cmd_btc, "null": cmd_null, "power": cmd_power}[args.cmd](args)


if __name__ == "__main__":
    main()
