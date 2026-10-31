"""Section B1, follow-up: the one place BTC's swing ratios clearly differ from every null is around 1.0, not at a Fibonacci level.
A leg stops just short of the previous pivot more often than chance, and a leg that passes it rarely stops just beyond it.

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/b1b_barrier.py --paths 300

This pattern was found by looking at the density table of b1_fib_unconditional.py, so it is a hypothesis here, not a discovery. It
gets tested on what could still refute it: each era alone, and the other venues. Measured on all consecutive leg pairs, r = |leg2|/|leg1|:
  asymmetry   share of r in 0.786-1.0 minus share in 1.0-1.272. The law on a random walk is symmetric around 1, so about 0.
  spike       excess in +-1.5 percent around 1.0, against shoulders, as in b1.
  overshoot   for pairs with r > 1: how far leg2 ran beyond the start of leg1, in units of the reversal threshold.
              On a memoryless walk this is Exp(1): mean 1, P(under 0.25) = 22 percent.
  run-on      mean overshoot minus 1. If you bought the moment a swing extreme broke and left when the zigzag reversed, the result is
              overshoot minus the threshold, so this is a gross expectancy in units of the threshold, before costs and gaps.
              It uses the threshold known at the confirming bar. A causal trade: the old pivot is long confirmed when price reaches it.
  ties        share of pairs where the two pivots are the same price to the cent: resting orders or thin trading.

Writes b1b_barrier.csv, b1b_fine.csv to the scratch folder. About 6 minutes.
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from common import BARS_PER_DAY, SCALES, VENUES, bh_qvalues, load_series, mc_p_high, q5_50_95, to_ms, write_csv
from nulls import null_bars, to_rel
from zigzag import Pivots, pivots, thresholds, zigzag_raw

SEED = 20261038
PERIODS = {"bitstamp_btcusd": (("all", "2013-01-01", "2027-01-01"), ("2014-2017", "2014-01-01", "2018-01-01"), ("2018-2021", "2018-01-01", "2022-01-01"), ("2022-2026", "2022-01-01", "2027-01-01")),
           "binance_btcusdt": (("all", "2013-01-01", "2027-01-01"), ("2018-2021", "2018-01-01", "2022-01-01"), ("2022-2026", "2022-01-01", "2027-01-01")),
           "bybit_btcusdt_perp": (("all", "2013-01-01", "2027-01-01"), ("2020-2021", "2020-01-01", "2022-01-01"), ("2022-2026", "2022-01-01", "2027-01-01"))}
FINE_CELLS = ("15m_pct2", "1h_pct4", "4h_pct8", "1d_pct16")
FINE_EDGES = np.array([-0.40, -0.20, -0.10, -0.05, -0.03, -0.015, 0.0, 0.015, 0.03, 0.05, 0.10, 0.20, 0.40])
NAMES = ("n", "asymmetry", "spike", "overshoot_n", "overshoot_mean", "overshoot_median", "share_overshoot_under_025", "run_on")


def measure(p: Pivots, thr: np.ndarray, bar_edges) -> np.ndarray:
    """(periods, metrics). A pair belongs to the period of the bar that confirms its last pivot."""
    out = np.full((len(bar_edges), len(NAMES)), np.nan)
    if len(p) < 4:
        return out
    legs = np.abs(np.diff(p.x))
    r = legs[1:] / legs[:-1]
    ln_r = np.log(r)
    conf = p.confirmed[2:]
    theta = thr[conf]
    over = (legs[1:] - legs[:-1]) / theta
    for k, (a, b) in enumerate(bar_edges):
        m = (conf >= a) & (conf < b) & np.isfinite(theta)
        n = int(m.sum())
        out[k, 0] = n
        if n < 20:
            continue
        rr, ll = r[m], ln_r[m]
        out[k, 1] = np.mean((rr >= 0.786) & (rr < 1.0)) - np.mean((rr >= 1.0) & (rr < 1.272))
        band = np.sum(np.abs(ll) <= 0.015)
        shoulders = np.sum(np.abs(ll) <= 0.06) - band
        out[k, 2] = (band + 0.5) / ((shoulders + 1.5) / 3)
        o = over[m]
        o = o[o > 0]
        out[k, 3] = o.size
        if o.size >= 10:
            out[k, 4] = o.mean()
            out[k, 5] = np.median(o)
            out[k, 6] = np.mean(o < 0.25)
            out[k, 7] = o.mean() - 1.0
    return out


def fine_hist(p: Pivots) -> np.ndarray:
    legs = np.abs(np.diff(p.x))
    ln_r = np.log(legs[1:] / legs[:-1])
    h = np.histogram(ln_r, bins=FINE_EDGES)[0].astype(float)
    return h / max(ln_r.size, 1)


def ties(p: Pivots) -> float:
    if len(p) < 3:
        return float("nan")
    return float(np.mean(np.abs(np.exp(p.x[2:]) - np.exp(p.x[:-2])) < 0.005))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=300)
    args = ap.parse_args()
    t0 = time.time()
    rows, fine_rows = [], []
    for vi, venue in enumerate(VENUES):
        for tf_i, (tf, per_day) in enumerate(BARS_PER_DAY.items()):
            s = load_series(venue, tf)
            periods = PERIODS[venue]
            edges = [(int(np.searchsorted(s.ts, to_ms(a))), int(np.searchsorted(s.ts, to_ms(b)))) for _, a, b in periods]
            cells = [x for x in SCALES if x.tf == tf]
            btc = {}
            btc_ties = {}
            btc_fine = {}
            for sc in cells:
                p = pivots(s, sc)
                btc[sc.name] = measure(p, thresholds(sc, s.h, s.l, s.c), edges)
                btc_ties[sc.name] = ties(p)
                btc_fine[sc.name] = fine_hist(p)
            rel = to_rel(s.o, s.h, s.l, s.c, s.high_first, per_day)
            for kind_i, kind in enumerate(("signflip", "trendflip")):
                rng = np.random.default_rng([SEED, vi, tf_i, kind_i])
                store = {sc.name: [] for sc in cells}
                store_fine = {sc.name: [] for sc in cells}
                for _ in range(args.paths):
                    o, h, l, c, hf = null_bars(rel, kind, rng)
                    for sc in cells:
                        q = zigzag_raw(h, l, c, hf, sc)
                        store[sc.name].append(measure(q, thresholds(sc, h, l, c), edges))
                        if venue == "bitstamp_btcusd" and sc.name in FINE_CELLS:
                            store_fine[sc.name].append(fine_hist(q))
                for sc in cells:
                    arr = np.array(store[sc.name])  # (paths, periods, metrics)
                    for k, (period, _, _) in enumerate(periods):
                        row = {"venue": venue, "scale": sc.name, "null": kind, "period": period, "ties_btc": btc_ties[sc.name] if period == "all" else ""}
                        for mi, name in enumerate(NAMES):
                            v = float(btc[sc.name][k, mi])
                            lo, mid, hi = q5_50_95(arr[:, k, mi])
                            row[name] = v
                            row[f"{name}_median"] = mid
                            row[f"{name}_p5"] = lo
                            row[f"{name}_p95"] = hi
                            if name in ("asymmetry", "spike", "run_on", "overshoot_mean", "overshoot_median") and np.isfinite(v):
                                row[f"{name}_p_high"] = mc_p_high(v, arr[:, k, mi])
                                row[f"{name}_p_low"] = mc_p_high(-v, -arr[:, k, mi])
                        rows.append(row)
                    if venue == "bitstamp_btcusd" and sc.name in FINE_CELLS:
                        f = np.array(store_fine[sc.name])
                        for b in range(FINE_EDGES.size - 1):
                            lo, mid, hi = q5_50_95(f[:, b])
                            fine_rows.append({"scale": sc.name, "null": kind, "from": FINE_EDGES[b], "to": FINE_EDGES[b + 1], "btc": float(btc_fine[sc.name][b]), "null_median": mid, "null_p5": lo, "null_p95": hi})
                print(f"{venue} {tf} {kind} {time.time() - t0:.0f}s", flush=True)
    for name in ("asymmetry", "spike", "run_on"):
        chosen = [r for r in rows if f"{name}_p_high" in r]
        qs = bh_qvalues(np.array([min(1.0, 2 * min(r[f"{name}_p_high"], r[f"{name}_p_low"])) for r in chosen]))
        for r, q in zip(chosen, qs):
            r[f"{name}_q"] = float(q)
    write_csv("b1b_barrier.csv", rows)
    write_csv("b1b_fine.csv", fine_rows)
    print(f"done {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
