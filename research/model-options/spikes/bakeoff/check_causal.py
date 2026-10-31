"""Lookahead checks for the ML samples and the zigzag. Run from the repo root:

    uv run --with numpy --with scipy --with scikit-learn --with lightgbm python research/model-options/spikes/bakeoff/check_causal.py

1. Truncation: features of every setup decided before a cut are identical when the data stops at the cut.
2. Rewriting the future: replacing all bars after the cut with garbage changes no feature of those setups.
3. The label of a setup never reads a bar at or before its decision bar (checked through i_resolve).
4. Planted bug: a feature that peeks at the future must light up the same pipeline (positive control).
"""
from __future__ import annotations

import sys

import numpy as np

from ewave.cycles.config import load_rules
from ml_features import SCALES, STATS_START_MS, build_samples
from ml_run import walk_forward, score
from zigzag import Series, load_series

VENUE = "bitstamp_btcusd"


def same(a: np.ndarray, b: np.ndarray) -> bool:
    return bool(((a == b) | (np.isnan(a) & np.isnan(b))).all())


def main() -> int:
    rules = load_rules()
    s = load_series(VENUE, "4h")
    sc = SCALES["4h_k4"]
    full = build_samples(s, sc, rules)
    first = int(np.searchsorted(s.ts, STATS_START_MS))
    fails = 0
    rng = np.random.default_rng(3)
    cuts = sorted(rng.integers(first + 2000, len(s) - 200, size=6).tolist())
    for cut in cuts:
        trunc = build_samples(s.slice(0, cut), sc, rules)
        # setups decided by the cut and already resolved inside it exist in both runs
        keep_full = np.flatnonzero((full.i_conf < cut) & (full.i_resolve < cut))
        keep_trunc = np.flatnonzero(trunc.i_resolve < cut)
        a = {int(i): k for k, i in enumerate(full.i_conf[keep_full])}
        b = {int(i): k for k, i in enumerate(trunc.i_conf[keep_trunc])}
        common = sorted(set(a) & set(b))
        same_x = same(full.X[keep_full][[a[i] for i in common]], trunc.X[keep_trunc][[b[i] for i in common]])
        same_y = (full.y[keep_full][[a[i] for i in common]] == trunc.y[keep_trunc][[b[i] for i in common]]).all()
        missing = set(a) ^ set(b)
        ok = same_x and same_y and not missing
        print(f"truncate at {cut} ({len(common)} setups): features same {same_x}, labels same {same_y}, setups only on one side {len(missing)}")
        fails += not ok

        # garbage future
        h, l, c, o = s.high.copy(), s.low.copy(), s.close.copy(), s.open.copy()
        noise = np.exp(np.cumsum(rng.normal(0, .05, len(s) - cut)))
        c[cut:], o[cut:] = c[cut - 1] * noise, c[cut - 1] * noise
        h[cut:], l[cut:] = c[cut:] * 1.02, c[cut:] * .98
        junk = build_samples(Series(s.ts, o, h, l, c, s.order, s.tf_ms), sc, rules)
        ja = {int(i): k for k, i in enumerate(junk.i_conf)}
        before = [i for i in common if i in ja]
        same_junk = same(full.X[keep_full][[a[i] for i in before]], junk.X[[ja[i] for i in before]])
        lost = len(common) - len(before)
        print(f"   rewrite after the cut: features same {same_junk}, setups lost {lost}")
        fails += not (same_junk and lost == 0)

    bad_label = int((full.i_resolve <= full.i_conf).sum())
    print(f"labels resolved at or before their decision bar: {bad_label}")
    fails += bad_label > 0

    # positive control: a peeking feature must show up as an enormous gain
    y = full.y.astype(float)
    planted = full.X.copy()
    planted[:, full.names.index("near_fib")] = y + rng.normal(0, .3, len(y))
    from dataclasses import replace
    wf = walk_forward(replace(full, X=planted), sets={"VD": "VD", "VDF": "VDF"})
    sc2 = score(replace(full, X=planted), wf)
    print(f"planted future feature: AUC lr_VD {sc2['lr_VD']['auc']:.3f} -> lr_VDF {sc2['lr_VDF']['auc']:.3f}, gbm_VDF {sc2['gbm_VDF']['auc']:.3f}")
    fails += sc2["lr_VDF"]["auc"] < .9
    print("ALL CHECKS PASS" if not fails else f"{fails} CHECKS FAILED")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
