"""Tables for 03-bakeoff.md from ml_run.py's outputs in $BAKE_OUT/ml/.

    uv run --with numpy python research/model-options/spikes/bakeoff/ml_report.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

OUT = Path(os.environ.get("BAKE_OUT", "/opt/data/cache/scratch/elliott_research_r1/bake")) / "ml"
MODELS = ["base", "barrier_raw", "barrier_cal", "lr_V", "lr_VD", "lr_VDF", "lr_VDT", "lr_VDR", "lr_VDC", "lr_ALL", "gbm_V", "gbm_VD", "gbm_VDF", "gbm_VDT", "gbm_VDR", "gbm_VDC", "gbm_ALL", "gbm_ALL_platt"]
NAMES = {"base": "base rate (past mean)", "barrier_raw": "volatility barrier, raw formula", "barrier_cal": "volatility barrier, recalibrated", "lr_V": "logistic, volatility", "lr_VD": "logistic, volatility + trend",
         "lr_VDF": "logistic, + Fib and legs", "lr_VDT": "logistic, + TDI", "lr_VDR": "logistic, + rule flags", "lr_VDC": "logistic, + cycles", "lr_ALL": "logistic, everything",
         "gbm_V": "LightGBM, volatility", "gbm_VD": "LightGBM, volatility + trend", "gbm_VDF": "LightGBM, + Fib and legs", "gbm_VDT": "LightGBM, + TDI", "gbm_VDR": "LightGBM, + rule flags", "gbm_VDC": "LightGBM, + cycles",
         "gbm_ALL": "LightGBM, everything", "gbm_ALL_platt": "LightGBM, everything, Platt"}
STEPS = [("lr_V", "lr_VD"), ("lr_VD", "lr_VDF"), ("lr_VD", "lr_VDT"), ("lr_VD", "lr_VDR"), ("lr_VD", "lr_VDC"), ("lr_VD", "lr_ALL"),
         ("gbm_V", "gbm_VD"), ("gbm_VD", "gbm_VDF"), ("gbm_VD", "gbm_VDT"), ("gbm_VD", "gbm_VDR"), ("gbm_VD", "gbm_VDC"), ("gbm_VD", "gbm_ALL"), ("lr_V", "gbm_ALL"), ("lr_V", "gbm_ALL_platt"), ("barrier_cal", "lr_V")]


def table(title: str, head: list[str], rows: list[list]) -> None:
    print(f"\n### {title}\n")
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for r in rows:
        print("| " + " | ".join("" if x is None else str(x) for x in r) + " |")


def q(values: list[float]) -> tuple[float, float, float]:
    return tuple(np.percentile(values, [5, 50, 95]).tolist())  # type: ignore[return-value]


def main() -> None:
    btc = json.loads((OUT / "btc.json").read_text())
    nulls = {}
    for key in btc:
        for kind in ("shuffled", "block"):
            p = OUT / f"null_{key}_{kind}.json"
            if p.exists():
                nulls[(key, kind)] = json.loads(p.read_text())

    table("Setups and outcomes", ["scale", "pivots", "origin already passed", "setups", "out of sample (2017+)", "target first", "origin first", "timeout", "base rate, all", "base rate, OOS"],
          [[k, v["counts"]["pivots"], v["counts"]["skipped_origin_passed"], v["counts"]["samples"], v["scores"]["base"]["n"], v["outcomes"]["target"], v["outcomes"]["origin"], v["outcomes"]["timeout"], f"{v['base_rate_all']:.1%}", f"{v['base_rate_oos']:.1%}"] for k, v in btc.items()])

    for key, v in btc.items():
        rows = []
        for m in MODELS:
            s = v["scores"].get(m)
            if s:
                rows.append([NAMES[m], f"{s['brier']:.4f}", f"{s['logloss']:.4f}", f"{s['auc']:.3f}", f"{s['ece']:.3f}", f"{s['slope']:.2f}"])
        table(f"{key}: out-of-sample scores", ["model", "Brier", "log loss", "AUC", "ECE", "calibration slope"], rows)

    for key, v in btc.items():
        ns, nb = nulls.get((key, "shuffled")), nulls.get((key, "block"))
        if not ns and not nb:
            continue
        rows = []
        for a, b in STEPS:
            if a not in v["scores"] or b not in v["scores"]:
                continue
            d = (v["scores"][a]["brier"] - v["scores"][b]["brier"]) * 1000
            da = v["scores"][b]["auc"] - v["scores"][a]["auc"]
            row = [f"{NAMES[a]} -> {NAMES[b]}", f"{d:+.1f}", f"{da:+.3f}"]
            flag = ""
            for tag, runs in (("S", ns), ("B", nb)):
                if not runs:
                    row += [None, None]
                    continue
                dv = [(r["scores"][a]["brier"] - r["scores"][b]["brier"]) * 1000 for r in runs if a in r["scores"] and b in r["scores"]]
                dau = [r["scores"][b]["auc"] - r["scores"][a]["auc"] for r in runs if a in r["scores"] and b in r["scores"]]
                l, m, h = q(dv)
                row.append(f"{m:+.1f} ({l:+.1f} to {h:+.1f})")
                la, ma, ha = q(dau)
                row.append(f"{ma:+.3f} ({la:+.3f} to {ha:+.3f})")
                if d > h:
                    flag += f"{tag}+ "
                if d < l:
                    flag += f"{tag}- "
                if da > ha:
                    flag += f"{tag}a+ "
                if da < la:
                    flag += f"{tag}a- "
            row.append(flag.strip())
            rows.append(row)
        table(f"{key}: what each step adds, BTC against null paths (Brier gain x 1000, positive is better). Null: median (5 to 95 percent)", ["step", "BTC gain", "BTC AUC change", "shuffled gain", "shuffled AUC change", "block gain", "block AUC change", "outside"], rows)

        rows = []
        for m in ("barrier_raw", "barrier_cal", "lr_V", "lr_VD", "lr_ALL", "gbm_V", "gbm_VD", "gbm_ALL"):
            row = [NAMES[m], f"{v['scores'][m]['auc']:.3f}", f"{v['scores'][m]['brier']:.4f}"]
            for runs in (ns, nb):
                if runs:
                    l, md, h = q([r["scores"][m]["auc"] for r in runs if m in r["scores"]])
                    l2, md2, h2 = q([r["scores"][m]["brier"] for r in runs if m in r["scores"]])
                    row += [f"{md:.3f} ({l:.3f} to {h:.3f})", f"{md2:.4f} ({l2:.4f} to {h2:.4f})"]
                else:
                    row += [None, None]
            rows.append(row)
        table(f"{key}: the same models on random paths", ["model", "BTC AUC", "BTC Brier", "shuffled AUC", "shuffled Brier", "block AUC", "block Brier"], rows)

        rows = []

        def relative(bs: list[dict]) -> list[float | None]:
            """Each bucket's excess over the barrier, minus the feature's overall excess: the barrier's own level error
            (it runs high on BTC, because the hit rate fell after 2017) is common to all buckets and says nothing."""
            tot = sum(b["n"] for b in bs if b["n"])
            overall = sum(b["excess"] * b["n"] for b in bs if b["n"]) / tot if tot else 0.0
            return [None if b["excess"] is None else (b["excess"] - overall) * 100 for b in bs]

        for f, bs in v["buckets"].items():
            rel = relative(bs)
            null_rel = {}
            for tag, runs in (("S", ns), ("B", nb)):
                null_rel[tag] = [relative(r["buckets"][f]) for r in runs] if runs else []
            for i, b in enumerate(bs):
                if not b["n"]:
                    continue
                row = [f, f"{b['lo']:.3g} to {b['hi']:.3g}", b["n"], f"{b['hit']:.0%}", f"{b['ref']:.0%}", f"{rel[i]:+.1f}"]
                flag = ""
                for tag in ("S", "B"):
                    vals = [x[i] for x in null_rel[tag] if x[i] is not None]
                    if len(vals) >= 5:
                        l, md, h = q(vals)
                        row.append(f"{md:+.1f} ({l:+.1f} to {h:+.1f})")
                        if rel[i] > h:
                            flag += f"{tag}+ "
                        if rel[i] < l:
                            flag += f"{tag}- "
                    else:
                        row.append(None)
                row.append(flag.strip())
                rows.append(row)
        table(f"{key}: hit rate by rulebook feature against the volatility barrier, each bucket relative to its feature's overall gap (out of sample, percentage points)", ["feature", "bucket", "n", "hit", "volatility said", "BTC relative excess", "shuffled", "block", "outside"], rows)
        flagged = sum(1 for r in rows if r[-1])
        both = sum(1 for r in rows if "S" in r[-1] and "B" in r[-1])
        print(f"\nBuckets outside a null range: {flagged} rows of {len(rows)}, outside both: {both}. Chance alone: about {0.19 * len(rows):.0f} rows outside at least one, and the rows of a feature are tied together.")

        rows = []
        for lv, val in v["extension"]["survival"].items():
            row = [lv, f"{val:.1%}"]
            for runs in (ns, nb):
                if runs:
                    l, md, h = q([r["extension"]["survival"][lv] for r in runs])
                    row.append(f"{md:.1%} ({l:.1%} to {h:.1%})")
                else:
                    row.append(None)
            rows.append(row)
        table(f"{key}: how far the next move ran before breaking the origin, as a multiple of the last leg", ["extension", "BTC", "shuffled", "block"], rows)
        rows = []
        for tag, name in (("fib", "within +-0.05 of 1, 1.618, 2.236, 2.618, 3.236, 4.236"), ("off", "within +-0.05 of 1.3, 1.9, 2.4, 2.9, 3.6, 4.6 (control)")):
            row = [name, f"{v['extension']['stops'][tag]:.2%}"]
            for runs in (ns, nb):
                if runs:
                    l, md, h = q([r["extension"]["stops"][tag] for r in runs])
                    row.append(f"{md:.2%} ({l:.2%} to {h:.2%})")
                else:
                    row.append(None)
            rows.append(row)
        table(f"{key}: where the moves stopped, share per level", ["level set", "BTC", "shuffled", "block"], rows)

    # the two tables the write-up leads with
    rows = []
    for key, v in btc.items():
        sc = v["scores"]
        rows.append([key, sc["base"]["n"], f"{v['base_rate_oos']:.1%}", f"{sc['base']['brier']:.4f}", f"{sc['barrier_raw']['brier']:.4f}", f"{sc['lr_V']['brier']:.4f}", f"{sc['lr_VD']['brier']:.4f}", f"{sc['lr_ALL']['brier']:.4f}", f"{sc['gbm_VD']['brier']:.4f}", f"{sc['gbm_ALL']['brier']:.4f}",
                     f"{sc['barrier_raw']['auc']:.3f}", f"{sc['lr_V']['auc']:.3f}", f"{sc['gbm_ALL']['auc']:.3f}"])
    table("Scales at a glance: out-of-sample Brier (lower is better) and AUC", ["scale", "n", "hit rate", "base rate", "vol barrier", "logistic V", "logistic V+D", "logistic all", "LightGBM V+D", "LightGBM all", "AUC barrier", "AUC logistic V", "AUC LightGBM all"], rows)
    rows = []
    n_out = n_all = 0
    for key, v in btc.items():
        ns, nb = nulls.get((key, "shuffled")), nulls.get((key, "block"))
        for fam, tag in (("lr", "logistic"), ("gbm", "LightGBM")):
            for g, name in (("VDF", "Fib and legs"), ("VDT", "TDI"), ("VDR", "rule flags"), ("VDC", "cycles"), ("ALL", "everything")):
                a, b = f"{fam}_VD", f"{fam}_{g}"
                d = (v["scores"][a]["brier"] - v["scores"][b]["brier"]) * 1000
                row = [key, tag, name, f"{d:+.1f}"]
                flag = ""
                for t, runs in (("S", ns), ("B", nb)):
                    if runs:
                        l, m, h = q([(r["scores"][a]["brier"] - r["scores"][b]["brier"]) * 1000 for r in runs])
                        row.append(f"{m:+.1f} ({l:+.1f} to {h:+.1f})")
                        n_all += 1
                        if d > h:
                            flag += f"{t}+ "
                            n_out += 1
                    else:
                        row.append(None)
                row.append(flag.strip())
                rows.append(row)
        table_rows = rows
    table("What each group adds on top of volatility + trend: Brier gain x 1000 (positive is better)", ["scale", "model", "group added", "BTC", "shuffled, median (5 to 95)", "block, median (5 to 95)", "above the null"], table_rows)
    print(f"\nAbove the null's 95th percentile: {n_out} of {n_all} comparisons; chance alone gives about {0.05 * n_all:.0f}.")

    main = btc.get("4h_k4")
    if main:
        for m in ("barrier_cal", "lr_V", "lr_ALL", "gbm_ALL"):
            rows = [[f"{b['lo']:.1f} to {b['hi']:.1f}", b["n"], f"{b['p']:.2f}", f"{b['hit']:.2f}"] for b in main["reliability"].get(m, [])] if m in main["reliability"] else []
            if rows:
                table(f"4h_k4 reliability, {NAMES[m]}", ["predicted", "n", "mean predicted", "hit rate"], rows)
        for k in ("lr_ALL", "gbm_ALL", "lr_VD"):
            rows = [[i + 1, b["n"], f"{b['p']:.2f}", f"{b['ref']:.2f}", f"{b['hit']:.2f}"] for i, b in enumerate(main["lift"][k])]
            table(f"4h_k4 by fifths of {NAMES[k]}", ["fifth", "n", "model said", "volatility said", "hit rate"], rows)
        rows = [[yr, y["n"], f"{y['hit']:.0%}", *[f"{y[m]:.3f}" for m in ("barrier_cal", "lr_VD", "lr_ALL", "gbm_VD", "gbm_ALL")]] for yr, y in main["yearly"].items()]
        table("4h_k4 Brier by year", ["year", "n", "hit", "barrier", "logistic V+D", "logistic all", "LightGBM V+D", "LightGBM all"], rows)
    for key, v in btc.items():
        pm = v.get("permutation")
        if not pm:
            continue
        table(f"{key}: permutation importance by group (log loss increase x 1000, out of sample; about zero or negative means the group does nothing)", ["group", "LightGBM all", "logistic all"], [[g, f"{x['gbm']*1000:+.1f}", f"{x['lr']*1000:+.1f}"] for g, x in pm["groups"].items()])
        top = sorted(pm["features"].items(), key=lambda kv: -kv[1]["gbm"])[:12]
        table(f"{key}: top features, permutation (log loss x 1000) and LightGBM gain share", ["feature", "LightGBM perm", "logistic perm", "gain share"], [[n, f"{x['gbm']*1000:+.1f}", f"{x['lr']*1000:+.1f}", f"{pm['gain'][n]:.1%}"] for n, x in top])

    for p in sorted(OUT.glob("power_*.json")):
        runs = json.loads(p.read_text())
        betas = sorted({r["beta"] for r in runs})
        base = [r for r in runs if r["beta"] == 0]
        rows = []
        for b in betas:
            rs = [r for r in runs if r["beta"] == b]
            row = [b, f"{np.mean([r['lift_pp'] for r in rs]):+.1f}", f"{np.mean([r['share'] for r in rs]):.0%}"]
            for m in ("lr_dbrier", "gbm_dbrier", "lr_dauc", "gbm_dauc"):
                thr = np.percentile([r[m] for r in base], 95)
                row.append(f"{np.mean([r[m] > thr for r in rs]):.0%}")
            rows.append(row)
        table(f"{p.stem}: a planted Fib effect, how often the test sees it (share of draws above the 95th percentile of beta = 0)", ["beta", "true lift in the 0.5-0.618 zone, points", "zone share", "logistic Brier", "LightGBM Brier", "logistic AUC", "LightGBM AUC"], rows)


if __name__ == "__main__":
    main()
