"""The weekly-window flag on top of the plain volatility models, on BTC, walk-forward. Companion to ml_leads.py, whose
null comparison adds the flag to volatility + trend.

    uv run --with numpy --with scikit-learn --with lightgbm python research/model-options/spikes/bakeoff/ml_flag_on_volatility.py
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import brier_score_loss, roc_auc_score

from ewave.cycles.config import load_rules
from ml_features import GROUPS, SCALES, build_samples
from ml_run import FIRST_TEST_YEAR, MIN_TRAIN, VENUE, fit_lr, jan1, year_of
from zigzag import load_series


def main() -> None:
    rules = load_rules()
    print("| scale | raw barrier | barrier recalibrated | + flag | logistic volatility | + flag |")
    print("|---|---|---|---|---|---|")
    for key in ("4h_k4", "4h_k3", "4h_k6", "1h_k6"):
        sc = SCALES[key]
        sm = build_samples(load_series(VENUE, sc.tf), sc, rules)
        vol = [sm.names.index(f) for f in GROUPS["V"]]
        flag = sm.names.index("w_in_window")
        years = year_of(sm.t_conf)
        n = len(sm.y)
        lr_v, lr_vf, cal, cal_f = (np.full(n, np.nan) for _ in range(4))
        lp = np.log(sm.p_barrier / (1 - sm.p_barrier))[:, None]
        for yr in range(FIRST_TEST_YEAR, int(years.max()) + 1):
            te, tr = np.flatnonzero(years == yr), np.flatnonzero(sm.t_resolve < jan1(yr))
            if len(te) == 0 or len(tr) < MIN_TRAIN:
                continue
            lr_v[te] = fit_lr(sm.X[np.ix_(tr, vol)], sm.y[tr], sm.X[np.ix_(te, vol)])
            lr_vf[te] = fit_lr(np.column_stack([sm.X[np.ix_(tr, vol)], sm.X[tr, flag]]), sm.y[tr], np.column_stack([sm.X[np.ix_(te, vol)], sm.X[te, flag]]))
            cal[te] = fit_lr(lp[tr], sm.y[tr], lp[te], C=100.0)
            cal_f[te] = fit_lr(np.column_stack([lp[tr], sm.X[tr, flag]]), sm.y[tr], np.column_stack([lp[te], sm.X[te, flag]]), C=100.0)
        m = ~np.isnan(lr_v)
        y = sm.y[m]
        cell = lambda p: f"{brier_score_loss(y, p[m]):.4f}, AUC {roc_auc_score(y, p[m]):.3f}"
        print(f"| {key} | {cell(sm.p_barrier)} | {cell(cal)} | {cell(cal_f)} | {cell(lr_v)} | {cell(lr_vf)} |")


if __name__ == "__main__":
    main()
