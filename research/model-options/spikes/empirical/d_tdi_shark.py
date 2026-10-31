"""Section D: the NewWave TDI "shark in the water" at 4H. Does the pattern have outcome value against a null?

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/d_tdi_shark.py --paths 500

TDI from the rulebook section 5: RSI(11), bands over 31 bars. The band width is not in the course text; 1.6185 standard
deviations is the TDI default and is assumed here [assumed]. RSI is on closes, as on the chart.

For each legal impulse (up, and mirrored for down):
  W3 outside  some close in the W3 leg has RSI outside the band on its side
  W5 inside   no close in the W5 leg does
  div         the RSI peak of the W5 leg is below the RSI peak of the W3 leg (price makes a higher high by construction)
  shark       all three; shark_z6070: the W5 peak also sits in 60-70 (mirrored 30-40)

Everything is known at the bar that confirms p5, and outcomes are read from the next bar on:
  hits_p4     price reaches the end of W4 before going beyond p5
  barrier_law what a driftless walk gives for that barrier: distance to p5 / (distance to p5 + distance to p4)
  fwd_60      log return over the next 60 bars (10 days), signed so that positive means the fifth was the end

BTC and the same pipeline on null paths. If the pattern is mechanical it appears as often on null paths; if it has value,
hits_p4 for sharks beats non-sharks by more than on nulls.

Writes d_metrics.csv to the scratch folder. About 3 minutes at 500 paths.
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from common import ANALYSIS_VENUE, Scale, bh_qvalues, load_series, mc_p_high, q5_50_95, wilson, write_csv
from impulse import check
from nulls import KINDS, null_bars, to_rel
from zigzag import pivots, zigzag_raw

try:
    from numba import njit
except ImportError:
    def njit(f):
        return f

SCALES_D = (Scale("4h", "pct", 4), Scale("4h", "atr", 2), Scale("4h", "pct", 8))
BAND_K = 1.6185
RSI_N, BAND_N = 11, 31
SEED = 20261033


@njit
def tdi(c: np.ndarray, n: int, band_n: int, k: float):
    """Wilder RSI on closes and its volatility bands; closes are log prices, so the gains are converted first."""
    size = c.size
    rsi = np.full(size, np.nan)
    up = np.full(size, np.nan)
    lo = np.full(size, np.nan)
    p = np.exp(c)
    avg_g, avg_l = 0.0, 0.0
    for t in range(1, size):
        d = p[t] - p[t - 1]
        g, l = max(d, 0.0), max(-d, 0.0)
        if t <= n:
            avg_g += g / n
            avg_l += l / n
        else:
            avg_g = (avg_g * (n - 1) + g) / n
            avg_l = (avg_l * (n - 1) + l) / n
        if t >= n:
            rsi[t] = 100.0 if avg_l == 0 else 100 - 100 / (1 + avg_g / avg_l)
        if t >= n + band_n - 1:
            w = rsi[t - band_n + 1:t + 1]
            m, sd = w.mean(), w.std()
            up[t], lo[t] = m + k * sd, m - k * sd
    return rsi, up, lo


@njit
def _classify(direction, i2, i3, i4, i5, rsi, up, lo):
    """For each candidate: W3 outside, W5 inside, divergence, peak in the 60-70 zone."""
    n = direction.size
    w3_out = np.zeros(n, np.bool_)
    w5_in = np.zeros(n, np.bool_)
    div = np.zeros(n, np.bool_)
    zone = np.zeros(n, np.bool_)
    for j in range(n):
        d = direction[j]
        peak3, peak5 = -1e9, -1e9
        out3, out5 = False, False
        for t in range(i2[j] + 1, i3[j] + 1):
            v = rsi[t] if d == 1 else 100 - rsi[t]
            if v == v:
                peak3 = max(peak3, v)
                if (d == 1 and rsi[t] > up[t]) or (d == -1 and rsi[t] < lo[t]):
                    out3 = True
        for t in range(i4[j] + 1, i5[j] + 1):
            v = rsi[t] if d == 1 else 100 - rsi[t]
            if v == v:
                peak5 = max(peak5, v)
                if (d == 1 and rsi[t] > up[t]) or (d == -1 and rsi[t] < lo[t]):
                    out5 = True
        w3_out[j] = out3
        w5_in[j] = not out5
        div[j] = peak5 < peak3
        zone[j] = 60 <= peak5 <= 70
    return w3_out, w5_in, div, zone


@njit
def _outcomes(direction, x4, x5, confirmed, hi, lo, c, fwd: int):
    n = direction.size
    hit = np.full(n, -1, np.int8)
    law = np.empty(n)
    ret = np.full(n, np.nan)
    size = hi.size
    for j in range(n):
        start = confirmed[j] + 1
        if start >= size:
            continue
        entry = c[confirmed[j]]
        d = direction[j]
        to5 = (x5[j] - entry) * d
        to4 = (entry - x4[j]) * d
        law[j] = to5 / (to5 + to4) if to5 + to4 > 0 else np.nan
        for t in range(start, size):
            if d == 1:
                if hi[t] > x5[j]:
                    hit[j] = 0
                    break
                if lo[t] <= x4[j]:
                    hit[j] = 1
                    break
            else:
                if lo[t] < x5[j]:
                    hit[j] = 0
                    break
                if hi[t] >= x4[j]:
                    hit[j] = 1
                    break
        if confirmed[j] + fwd < size:
            ret[j] = (entry - c[confirmed[j] + fwd]) * d
    return hit, law, ret


def _measure(piv, h, l, c, rsi, up, lo) -> dict[str, float]:
    cand = check(piv)
    legal = cand.subset(cand.legal) if len(cand) else cand
    n = len(legal)
    m: dict[str, float] = {"n": n}
    if n == 0:
        return m
    i = legal.i
    w3_out, w5_in, div, zone = _classify(legal.direction.astype(np.int64), i[:, 2], i[:, 3], i[:, 4], i[:, 5], rsi, up, lo)
    x4, x5 = piv.x[legal.start + 4], piv.x[legal.start + 5]
    hit, law, ret = _outcomes(legal.direction.astype(np.int64), x4, x5, legal.confirmed_p5, h, l, c, 60)
    shark = w3_out & w5_in & div
    groups = {"all": np.ones(n, bool), "shark": shark, "no_shark": ~shark, "shark_z6070": shark & zone,
              "w3_out": w3_out, "div": div, "no_div": ~div}
    m.update({"share_w3_outside": float(w3_out.mean()), "share_w5_inside": float(w5_in.mean()), "share_div": float(div.mean()),
              "share_shark": float(shark.mean()), "share_shark_z6070": float((shark & zone).mean())})
    for g, mask in groups.items():
        done = mask & (hit >= 0)
        m[f"{g}|n"] = int(done.sum())
        if done.any():
            m[f"{g}|hits_p4"] = float((hit[done] == 1).mean())
            m[f"{g}|barrier_law"] = float(np.nanmean(law[done]))
            m[f"{g}|hits_minus_law"] = m[f"{g}|hits_p4"] - m[f"{g}|barrier_law"]
        r = ret[mask]
        r = r[np.isfinite(r)]
        if r.size:
            m[f"{g}|fwd_60"] = float(r.mean())
    if "shark|hits_p4" in m and "no_shark|hits_p4" in m:
        m["shark_minus_no_shark|hits_p4"] = m["shark|hits_p4"] - m["no_shark|hits_p4"]
    if "shark|fwd_60" in m and "no_shark|fwd_60" in m:
        m["shark_minus_no_shark|fwd_60"] = m["shark|fwd_60"] - m["no_shark|fwd_60"]
    if "div|hits_p4" in m and "no_div|hits_p4" in m:
        m["div_minus_no_div|hits_p4"] = m["div|hits_p4"] - m["no_div|hits_p4"]
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=500)
    args = ap.parse_args()
    t0 = time.time()
    s = load_series(ANALYSIS_VENUE, "4h")
    rel = to_rel(s.o, s.h, s.l, s.c, s.high_first, 6)
    rsi, up, lo = tdi(s.c, RSI_N, BAND_N, BAND_K)
    btc = {sc.name: _measure(pivots(s, sc), s.h, s.l, s.c, rsi, up, lo) for sc in SCALES_D}
    blocks = {sc.name: max(3, int(round(float(np.median(np.diff(pivots(s, sc).i)))))) for sc in SCALES_D}
    results: dict[tuple[str, str], list[dict]] = {(k, sc.name): [] for k in KINDS for sc in SCALES_D}
    for i, kind in enumerate(KINDS):
        rng = np.random.default_rng([SEED, i])
        for _ in range(args.paths):
            if kind == "block":
                for sc in SCALES_D:
                    o, h, l, c, hf = null_bars(rel, kind, rng, block=blocks[sc.name])
                    r_, u_, d_ = tdi(c, RSI_N, BAND_N, BAND_K)
                    results[(kind, sc.name)].append(_measure(zigzag_raw(h, l, c, hf, sc), h, l, c, r_, u_, d_))
            else:
                o, h, l, c, hf = null_bars(rel, kind, rng)
                r_, u_, d_ = tdi(c, RSI_N, BAND_N, BAND_K)
                for sc in SCALES_D:
                    results[(kind, sc.name)].append(_measure(zigzag_raw(h, l, c, hf, sc), h, l, c, r_, u_, d_))
        print(f"{kind} done {time.time() - t0:.0f}s", flush=True)
    rows = []
    for sc in SCALES_D:
        for key, value in sorted(btc[sc.name].items()):
            row = {"scale": sc.name, "metric": key, "btc": value}
            if key.endswith("|hits_p4"):
                g = key.split("|")[0]
                n_ = btc[sc.name].get(f"{g}|n", 0)
                if n_:
                    lo_, hi_ = wilson(int(round(value * n_)), int(n_))
                    row.update({"btc_lo": lo_, "btc_hi": hi_})
            for kind in KINDS:
                vals = np.array([r.get(key, np.nan) for r in results[(kind, sc.name)]], float)
                a, b, c_ = q5_50_95(vals)
                row.update({f"{kind}_p5": a, f"{kind}_median": b, f"{kind}_p95": c_, f"{kind}_p_high": mc_p_high(float(value), vals), f"{kind}_p_low": mc_p_high(-float(value), -vals)})
            rows.append(row)
    for kind in KINDS:
        ps = np.array([min(1.0, 2 * min(r[f"{kind}_p_high"], r[f"{kind}_p_low"])) for r in rows])
        for r, p_, q in zip(rows, ps, bh_qvalues(ps)):
            r[f"{kind}_p2"] = float(p_)
            r[f"{kind}_q"] = float(q)
    write_csv("d_metrics.csv", rows)
    print(f"done {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
