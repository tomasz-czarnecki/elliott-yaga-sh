"""Section A, follow-up: rule-legal impulses are more common on BTC than on random paths at 1H and up. Is that wave structure,
or just bull and bear regimes? Family-wise test, sensitivity to the trend window, and the other venues.

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/a2_legal_excess.py --paths 500

For each null family: legal rate per scale on BTC against null paths, z, Monte Carlo p, Westfall-Young family-wise p over the
24 scales. The trendflip null is run with a drift window of +-30, +-60 and +-120 days: if the excess fades as the null keeps
more of BTC's local drift, the excess is regimes. Binance and Bybit run only to rule out a Bitstamp artefact: they cover the same
market, so they are not independent evidence.

Writes a2_legal.csv and a2_familywise.csv to the scratch folder. About 8 minutes.
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from common import ANALYSIS_VENUE, BARS_PER_DAY, SCALES, VENUES, load_series, mc_p_high, q5_50_95, write_csv
from impulse import check
from nulls import null_bars, to_rel
from zigzag import pivots, zigzag_raw

SEED = 20261034
FAMILIES = (("shuffle", 60), ("signflip", 60), ("trendflip", 30), ("trendflip", 60), ("trendflip", 120))
SHORT = ("15m", "1h", "4h", "1d")


def rate(p) -> tuple[float, int, int]:
    c = check(p)
    if not len(c):
        return float("nan"), 0, 0
    return float(c.legal.mean()), int(c.legal.sum()), len(c)


def run_venue(venue: str, families, paths: int, seed_extra: int, rows: list, fw: list) -> None:
    t0 = time.time()
    for fam_i, (kind, days) in enumerate(families):
        zs_btc, zs_null, names = [], [], []
        for tf_i, (tf, per_day) in enumerate(BARS_PER_DAY.items()):
            s = load_series(venue, tf)
            cells = [x for x in SCALES if x.tf == tf]
            rel = to_rel(s.o, s.h, s.l, s.c, s.high_first, per_day, trend_days=days)
            rng = np.random.default_rng([SEED, seed_extra, fam_i, tf_i])
            store = np.empty((paths, len(cells)))
            pooled_legal = np.empty(paths)
            pooled_windows = np.empty(paths)
            for n in range(paths):
                o, h, l, c, hf = null_bars(rel, kind, rng)
                tl, tw = 0, 0
                for ci, sc in enumerate(cells):
                    r, lg, w = rate(zigzag_raw(h, l, c, hf, sc))
                    store[n, ci] = r
                    tl += lg
                    tw += w
                pooled_legal[n], pooled_windows[n] = tl, tw
            btc_tl, btc_tw = 0, 0
            btc_rates = []
            for ci, sc in enumerate(cells):
                r, lg, w = rate(pivots(s, sc))
                btc_rates.append(r)
                btc_tl += lg
                btc_tw += w
                lo, mid, hi = q5_50_95(store[:, ci])
                sd = float(np.nanstd(store[:, ci]))
                rows.append({"venue": venue, "null": kind, "trend_days": days if kind == "trendflip" else "", "scale": sc.name, "legal": lg, "windows": w,
                             "btc": r, "null_p5": lo, "null_median": mid, "null_p95": hi, "ratio_to_null": r / mid if mid else float("nan"),
                             "z": (r - float(np.nanmean(store[:, ci]))) / sd if sd else float("nan"), "p_high": mc_p_high(r, store[:, ci])})
                names.append(sc.name)
            pooled = pooled_legal / pooled_windows
            lo, mid, hi = q5_50_95(pooled)
            rows.append({"venue": venue, "null": kind, "trend_days": days if kind == "trendflip" else "", "scale": f"pool_{tf}", "legal": btc_tl, "windows": btc_tw,
                         "btc": btc_tl / btc_tw, "null_p5": lo, "null_median": mid, "null_p95": hi, "ratio_to_null": btc_tl / btc_tw / mid,
                         "z": (btc_tl / btc_tw - float(np.mean(pooled))) / float(np.std(pooled)), "p_high": mc_p_high(btc_tl / btc_tw, pooled)})
            mean, sd = np.nanmean(store, axis=0), np.nanstd(store, axis=0)
            zs_btc.append((np.array(btc_rates) - mean) / sd)
            zs_null.append((store - mean) / sd)
        zb = np.concatenate(zs_btc)
        zn = np.concatenate(zs_null, axis=1)
        mx = np.nanmax(zn, axis=1)
        for name, z in zip(names, zb):
            fw.append({"venue": venue, "null": kind, "trend_days": days if kind == "trendflip" else "", "scale": name, "z": float(z),
                       "familywise_p": mc_p_high(float(z), mx)})
        print(f"{venue} {kind} {days}: max z {np.nanmax(zb):.2f}, cells z>1.645: {int(np.nansum(zb > 1.645))} of {zb.size}, null median of that count {np.median(np.nansum(zn > 1.645, axis=1)):.0f}, {time.time() - t0:.0f}s", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=500)
    ap.add_argument("--venue-paths", type=int, default=200)
    args = ap.parse_args()
    rows: list = []
    fw: list = []
    run_venue(ANALYSIS_VENUE, FAMILIES, args.paths, 0, rows, fw)
    for i, venue in enumerate(VENUES):
        if venue != ANALYSIS_VENUE:
            run_venue(venue, (("signflip", 60), ("trendflip", 60)), args.venue_paths, i + 1, rows, fw)
    write_csv("a2_legal.csv", rows)
    write_csv("a2_familywise.csv", fw)


if __name__ == "__main__":
    main()
