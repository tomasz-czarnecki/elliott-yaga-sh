"""Section B1, follow-up: the level summary of b1 left one Fibonacci hit standing after correction: extensions in linear price near
1.618, on 1H and above. It was found among hundreds of tests and the b1 p value is too kind, since its null paths are independent
across timeframes and BTC's are not. Two honest checks.

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/b1d_scan.py --paths 300

1. Level scan. The same statistic on a dense grid of levels instead of a list of famous ones: mean z across the 18 scales on 1h, 4h
   and 1d, for levels 0.2 to 5 in steps of 1 percent. If 1.618 is special it is a peak; if 1.55 and 1.75 score the same it is not.
   Null paths are built on 1h bars and aggregated to 4h and 1d, so one path is one market at all three timeframes, as BTC is. Each
   path's largest scan value gives a family-wise p for the whole scan.
2. Replication. The hit on eras it could not have been fitted to, and on the other venues: extension, linear, 1.618, +-4 percent,
   counts summed over the scales of 1h, 4h and 1d.

Writes b1d_scan.csv, b1d_top.csv, b1d_replicate.csv to the scratch folder. About 6 minutes.
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from common import ANALYSIS_VENUE, ERAS, FIB_LEVELS, SCALES, load_series, mc_p_high, q5_50_95, to_ms, write_csv
from nulls import null_bars, to_rel
from zigzag import Pivots, zigzag_raw

SEED = 20261042
W = 0.04
GRID = np.exp(np.arange(np.log(0.2), np.log(5.0), 0.01))
CELLS = [x for x in SCALES if x.tf in ("1h", "4h", "1d")]
FACTOR = {"1h": 1, "4h": 4, "1d": 24}
RATIOS = (("ret", "log"), ("ret", "lin"), ("ext", "log"), ("ext", "lin"))
PERIODS = (("all", "2013-01-01", "2027-01-01"), ("before_2018", "2013-01-01", "2018-01-01"), *ERAS[1:])


def aggregate(o, h, l, c, hf, k: int):
    if k == 1:
        return o, h, l, c, hf
    n = o.size // k
    O, H, L, C = o[:n * k].reshape(n, k), h[:n * k].reshape(n, k), l[:n * k].reshape(n, k), c[:n * k].reshape(n, k)
    H_, L_ = H.max(axis=1), L.min(axis=1)
    hi_at, lo_at = H.argmax(axis=1), L.argmin(axis=1)
    same = hf[:n * k].reshape(n, k)[np.arange(n), hi_at]
    return O[:, 0], H_, L_, C[:, -1], np.where(hi_at == lo_at, same, hi_at < lo_at)


def ln_ratios(p: Pivots) -> dict[tuple[str, str], tuple[np.ndarray, np.ndarray]]:
    out = {}
    if len(p) < 5:
        e = np.empty(0)
        return {key: (e, np.empty(0, np.int64)) for key in RATIOS}
    for price in ("log", "lin"):
        x = p.x if price == "log" else np.exp(p.x)
        legs = np.abs(np.diff(x))
        ret = np.log(legs[1:] / legs[:-1])
        out[("ret", price)] = (ret, p.confirmed[2:])
        keep = legs[1:-1] < legs[:-2]
        out[("ext", price)] = (np.log(legs[2:][keep] / legs[:-2][keep]), p.confirmed[3:][keep])
    return out


_GRID_LN = np.log(GRID)
_E = np.stack([_GRID_LN - 4 * W, _GRID_LN - W, _GRID_LN + W, _GRID_LN + 4 * W])


def excess_grid(values: np.ndarray) -> np.ndarray:
    a = np.sort(values)
    pos = np.searchsorted(a, _E)
    band = pos[2] - pos[1]
    shoulders = pos[3] - pos[0] - band
    return (band + 0.5) / ((shoulders + 1.5) / 3)


def scan_path(o, h, l, c, hf) -> np.ndarray:
    """(ratio kinds, cells, grid) of excess for one market given on 1h bars."""
    out = np.empty((len(RATIOS), len(CELLS), GRID.size), np.float32)
    views = {tf: aggregate(o, h, l, c, hf, k) for tf, k in FACTOR.items()}
    for ci, sc in enumerate(CELLS):
        _, hh, ll, cc, ff = views[sc.tf]
        r = ln_ratios(zigzag_raw(hh, ll, cc, ff, sc))
        for ri, key in enumerate(RATIOS):
            out[ri, ci] = excess_grid(r[key][0])
    return out


def band_counts(p: Pivots, level: float, period_edges) -> np.ndarray:
    """(periods, 2): in-band and shoulder counts of the linear extension at this level, by the bar confirming the ratio."""
    out = np.zeros((len(period_edges), 2))
    r, conf = ln_ratios(p)[("ext", "lin")]
    if r.size == 0:
        return out
    d = np.abs(r - np.log(level))
    for k, (a, b) in enumerate(period_edges):
        m = (conf >= a) & (conf < b)
        band = int((d[m] <= W).sum())
        out[k] = band, int((d[m] <= 4 * W).sum()) - band
    return out


def replicate(venue: str, paths: int, rows: list, seed_extra: int) -> None:
    s = load_series(venue, "1h")
    first = int(np.argmax(s.ts % 86_400_000 == 0))  # start on a UTC day, so that aggregates match the venue's 4h and 1d bars
    o0, h0, l0, c0, hf0, ts0 = s.o[first:], s.h[first:], s.l[first:], s.c[first:], s.high_first[first:], s.ts[first:]
    edges_ms = [(to_ms(a), to_ms(b)) for _, a, b in PERIODS]
    views = {tf: aggregate(o0, h0, l0, c0, hf0, k) for tf, k in FACTOR.items()}
    ts = {tf: ts0[::k][:views[tf][1].size] for tf, k in FACTOR.items()}
    period_edges = {tf: [(int(np.searchsorted(ts[tf], a)), int(np.searchsorted(ts[tf], b))) for a, b in edges_ms] for tf in FACTOR}
    btc = np.zeros((len(PERIODS), 2))
    for sc in CELLS:
        _, hh, ll, cc, ff = views[sc.tf]
        btc += band_counts(zigzag_raw(hh, ll, cc, ff, sc), 1.618, period_edges[sc.tf])
    rel = to_rel(o0, h0, l0, c0, hf0, 24)
    for kind_i, kind in enumerate(("signflip", "trendflip")):
        rng = np.random.default_rng([SEED, seed_extra, kind_i])
        sims = np.zeros((paths, len(PERIODS), 2))
        for n in range(paths):
            o, h, l, c, hf = null_bars(rel, kind, rng)
            v = {tf: aggregate(o, h, l, c, hf, k) for tf, k in FACTOR.items()}
            for sc in CELLS:
                _, hh, ll, cc, ff = v[sc.tf]
                sims[n] += band_counts(zigzag_raw(hh, ll, cc, ff, sc), 1.618, period_edges[sc.tf])
        x_b = (btc[:, 0] + 0.5) / ((btc[:, 1] + 1.5) / 3)
        x_n = (sims[:, :, 0] + 0.5) / ((sims[:, :, 1] + 1.5) / 3)
        for k, (period, _, _) in enumerate(PERIODS):
            lo, mid, hi = q5_50_95(x_n[:, k])
            rows.append({"venue": venue, "null": kind, "period": period, "in_band": int(btc[k, 0]), "shoulders": int(btc[k, 1]), "excess": float(x_b[k]),
                         "null_median": mid, "null_p5": lo, "null_p95": hi, "p_high": mc_p_high(float(x_b[k]), x_n[:, k])})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=300)
    args = ap.parse_args()
    t0 = time.time()
    s = load_series(ANALYSIS_VENUE, "1h")
    rel = to_rel(s.o, s.h, s.l, s.c, s.high_first, 24)
    btc = scan_path(s.o, s.h, s.l, s.c, s.high_first)
    rows, top_rows = [], []
    for kind_i, kind in enumerate(("signflip", "trendflip")):
        rng = np.random.default_rng([SEED, kind_i])
        sims = np.empty((args.paths, *btc.shape), np.float32)
        for n in range(args.paths):
            sims[n] = scan_path(*null_bars(rel, kind, rng))
            if (n + 1) % 100 == 0:
                print(kind, n + 1, f"{time.time() - t0:.0f}s", flush=True)
        mean, sd = sims.mean(axis=0), sims.std(axis=0)
        sd = np.where(sd > 0, sd, np.nan)
        z_b = np.nanmean((btc - mean) / sd, axis=1)  # (ratio kinds, grid)
        z_n = np.nanmean((sims - mean) / sd, axis=2)  # (paths, ratio kinds, grid)
        for ri, (rtype, price) in enumerate(RATIOS):
            sd_grid = np.nanstd(z_n[:, ri], axis=0)
            stand = z_b[ri] / sd_grid
            stand_n = z_n[:, ri] / sd_grid
            mx = np.nanmax(stand_n, axis=1)
            mn = np.nanmax(-stand_n, axis=1)
            for gi, level in enumerate(GRID):
                rows.append({"null": kind, "type": rtype, "price": price, "level": float(level), "mean_z": float(z_b[ri, gi]), "standardised": float(stand[gi]),
                             "p_high": mc_p_high(float(stand[gi]), stand_n[:, gi]), "scan_familywise_p": mc_p_high(float(stand[gi]), mx), "scan_familywise_p_low": mc_p_high(float(-stand[gi]), mn)})
            order = np.argsort(-stand)[:300]
            kept: list[float] = []
            for gi in order:
                if all(abs(np.log(GRID[gi] / other)) > 2 * W for other in kept):
                    kept.append(float(GRID[gi]))
                    near_fib = min(FIB_LEVELS, key=lambda f: abs(np.log(f / GRID[gi])))
                    top_rows.append({"null": kind, "type": rtype, "price": price, "rank": len(kept), "level": float(GRID[gi]), "standardised": float(stand[gi]),
                                     "scan_familywise_p": mc_p_high(float(stand[gi]), mx), "nearest_fib": near_fib, "distance_pct": float(abs(GRID[gi] / near_fib - 1) * 100)})
                if len(kept) == 8:
                    break
    write_csv("b1d_scan.csv", rows)
    write_csv("b1d_top.csv", top_rows)
    print(f"scan done {time.time() - t0:.0f}s", flush=True)
    rep: list = []
    for i, venue in enumerate(("bitstamp_btcusd", "binance_btcusdt", "bybit_btcusdt_perp")):
        replicate(venue, args.paths, rep, i)
        print(venue, f"{time.time() - t0:.0f}s", flush=True)
    write_csv("b1d_replicate.csv", rep)
    print("done")


if __name__ == "__main__":
    main()
