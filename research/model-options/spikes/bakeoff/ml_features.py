"""Samples for the simple-ML test: one per confirmed zigzag pivot that can be read as the end of a pullback.

Setup at pivot P2, with P0 and P1 the two pivots before it (P0-P1 the last completed leg, P1-P2 the pullback):
  entry   S = close of the bar that confirmed P2. Nothing before that bar's close is used for a decision.
  target  T = P2 + s x 1.618 x |P1 - P0|, the NewWave extension of 0-1-2 (sec 1).
  origin  O = P0. A setup whose P2 already passed P0 is not a legal 0-1-2 and is left out, and counted.
  label   y = 1 if T trades before O within H bars. Timeouts are y = 0, as the brief words it.

A bar that touches both barriers is settled by which extreme came first (hl_order, from 1-minute data); when unknown,
the origin goes first. Every feature reads bars up to and including the confirming bar and pivots already confirmed by
then; check_causal.py proves it by truncating and rewriting the future.
"""
from __future__ import annotations

import math
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field

import numpy as np

from enumerator import Grammar
from rules import ED, FLAT_EXP, FLAT_REG, FLAT_RUN, IMPULSE, ZIGZAG, Point, hard, violations
from zigzag import HIGH_FIRST, LOW_FIRST, Series, atr_log, rolling_std, rsi, sma, zigzag

DAY_MS = 86_400_000
STATS_START_MS = 1_362_096_000_000  # 2013-03-01, as in rules/cycles.yaml


@dataclass(frozen=True)
class Scale:
    name: str
    tf: str
    k: float       # main zigzag, x ATR(14)
    H: int         # bars to reach the target
    vol_bars: int  # realised volatility window, 14 days
    long_bars: int # trend window, 90 days
    sub_k: float   # one degree down: k / 3


def scale(name: str, tf: str, k: float, H: int) -> Scale:
    per_day = {"4h": 6, "1h": 24}[tf]
    return Scale(name, tf, k, H, 14 * per_day, 90 * per_day, k / 3)


SCALES = {
    "4h_k4": scale("4h_k4", "4h", 4, 150),   # main: median leg 10-12 percent, sec 5's 4H move size; H = 2.236 x p90 leg bars
    "4h_k3": scale("4h_k3", "4h", 3, 90),
    "4h_k6": scale("4h_k6", "4h", 6, 300),
    "1h_k6": scale("1h_k6", "1h", 6, 300),
}

GROUPS = {
    "V": ["logit_p", "x_sig", "up_sig", "log_sigma", "vol_regime"],
    "D": ["s", "s_ret_short", "s_ret_long", "s_vs_sma", "s_sma_slope", "dd_ath", "s_dd_ath"],
    "F": ["r", "r_log", "d382", "d500", "d618", "d786", "in_500_618", "in_382_618", "near_fib", "log_time_ratio", "time_rule_ok",
          "leg01_speed", "leg12_speed", "leg01_atr", "prior_leg_ratio", "engulfs_prior", "p0_extreme_100"],
    "T": ["rsi_t_a", "rsi_p1_a", "rsi_p2_a", "p2_in_zone", "p1_through_70", "p2_buy_territory", "hdiv_p0_p2", "rdiv_at_p0", "rsi_band_a",
          "rsi_signal_a", "p1_outside_band"],
    "R": ["prior_opposite_5", "as_w4", "as_c_zigzag", "as_c_flat", "n_w4_readings", "n_w2_origins", "n_sub_01", "n_sub_12",
          "w1_nested_motive", "w1_leaf", "w2_nested_corrective", "w2_leaf"],
    "C": ["d_phase", "w_phase", "y_phase", "d_in_window", "w_in_window", "d_top_pos", "w_top_pos", "d_failed", "w_failed",
          "s_d_cos", "s_w_cos", "s_y_cos", "p2_at_d_low", "p2_at_w_low", "p0_w_align", "p0_d_align"],
}
FEATURES = [f for g in GROUPS.values() for f in g]


@dataclass
class Samples:
    X: np.ndarray
    names: list[str]
    y: np.ndarray
    outcome: list[str]       # target / origin / timeout
    i_conf: np.ndarray       # bar of the decision
    i_resolve: np.ndarray    # bar where the label became known
    t_conf: np.ndarray       # ms, close of the decision bar
    t_resolve: np.ndarray    # ms, close of the resolving bar
    p_barrier: np.ndarray
    ext_max: np.ndarray      # furthest extension reached before the origin broke or H ran out
    entry: np.ndarray
    origin: np.ndarray
    p2: np.ndarray
    leg: np.ndarray
    sigma: np.ndarray
    side: np.ndarray
    counts: dict = field(default_factory=dict)


def barrier_prob(x: np.ndarray, a: np.ndarray, sig2_h: np.ndarray, terms: int = 400) -> np.ndarray:
    """P(driftless Brownian motion started at x in (0, a) hits a before 0 and before the horizon), the two-barrier series.

    u(x, T) = x/a + sum_n 2(-1)^n/(n pi) sin(n pi x/a) exp(-n^2 pi^2 sig2_h / (2 a^2)).
    """
    x = np.asarray(x, float)
    a = np.asarray(a, float)
    n = np.arange(1, terms + 1)[None, :]
    frac = (x / a)[:, None]
    decay = np.exp(-(n ** 2) * np.pi ** 2 * (sig2_h / (2 * a * a))[:, None])
    series = (2 * (-1.0) ** n / (n * np.pi)) * np.sin(n * np.pi * frac) * decay
    return np.clip(frac[:, 0] + series.sum(axis=1), 1e-4, 1 - 1e-4)


def logit(p: np.ndarray) -> np.ndarray:
    return np.log(p / (1 - p))


def day_bars(s: Series) -> tuple[list, list, list, list, list]:
    """Aggregate to UTC days. The series has no holes, so days are consecutive."""
    day = s.ts // DAY_MS
    starts = np.flatnonzero(np.diff(day, prepend=day[0] - 1))
    ends = np.append(starts[1:], len(day))
    ts = (day[starts] * DAY_MS).tolist()
    o = s.open[starts].tolist()
    c = s.close[ends - 1].tolist()
    h = [float(s.high[a:b].max()) for a, b in zip(starts, ends)]
    l = [float(s.low[a:b].min()) for a, b in zip(starts, ends)]
    return ts, o, h, l, c


def cycle_states(s: Series, rules) -> dict:
    """The live cycle state after each closed day, from the walk-forward machines in ewave.cycles. Read-only use."""
    from ewave.cycles.live import LiveEngine

    ts, o, h, l, c = day_bars(s)
    n = len(ts)
    e = LiveEngine(rules, track_zones=False)
    out = {k: np.full(n, -1, dtype=np.int32) for k in ("d_anchor", "w_anchor", "y_anchor", "d_cand", "w_cand", "d_top", "w_top")}
    failed = {k: np.zeros(n, dtype=bool) for k in ("d_failed", "w_failed")}
    tops = {"d": (-1, -1, -math.inf), "w": (-1, -1, -math.inf)}
    for i in range(n):
        e.step(ts[i], o[i], h[i], l[i], c[i])
        for tag, m in (("d", e.daily), ("w", e.weekly)):
            a = m.chain[-1] if m.chain else None
            if a is None:
                continue
            out[f"{tag}_anchor"][i] = a.i
            anchor, top_i, top = tops[tag]
            if anchor != a.i:
                seg = h[a.i:i + 1]
                top = max(seg)
                top_i = a.i + seg.index(top)
            elif h[i] > top:
                top, top_i = h[i], i
            tops[tag] = (a.i, top_i, top)
            out[f"{tag}_top"][i] = top_i
            failed[f"{tag}_failed"][i] = a.ts_failed is not None
            if m.candidate is not None:
                out[f"{tag}_cand"][i] = m.candidate.i
        y = e.fouryear.chain[-1] if e.fouryear.chain else None
        if y is not None:
            out["y_anchor"][i] = y.i
    return {**out, **failed, "first_day": ts[0] // DAY_MS, "centre_d": rules.levels["daily"].centre, "centre_w": rules.levels["weekly"].centre,
            "lo_d": rules.levels["daily"].lo, "hi_d": rules.levels["daily"].hi, "lo_w": rules.levels["weekly"].lo, "hi_w": rules.levels["weekly"].hi}


def _sub_count(subs: list, i0: int, i1: int) -> tuple[int, list[float], list[int]]:
    """Legs of the smaller zigzag strictly inside bars i0..i1, plus their prices."""
    a, b = bisect_right(subs[0], i0), bisect_left(subs[0], i1)
    return b - a + 1, subs[1][a:b], subs[0][a:b]


def build_samples(s: Series, sc: Scale, rules, *, log_target: bool = False, ext: float = 1.618, states: dict | None = None,
                  stats_start_ms: int = STATS_START_MS) -> Samples:
    n = len(s)
    tf_ms = s.tf_ms
    atr = atr_log(s)
    pivots, _ = zigzag(s, sc.k * atr, start=0)
    subs_raw, _ = zigzag(s, sc.sub_k * atr, start=0)
    subs = ([p.i for p in subs_raw], [p.price for p in subs_raw], [p.conf_i for p in subs_raw])
    close, high, low = s.close, s.high, s.low
    logc = np.log(close)
    ret = np.diff(logc, prepend=logc[0])
    cum2 = np.cumsum(ret * ret)
    rsi11 = rsi(close)
    mid31, std31, sig9 = sma(rsi11, 31), rolling_std(rsi11, 31), sma(rsi11, 9)
    sma_long = sma(logc, sc.long_bars)
    ath = np.maximum.accumulate(high)
    states = states if states is not None else cycle_states(s, rules)
    day_first = states["first_day"]
    H = sc.H

    rows: list[dict] = []
    y, outcome, i_conf, i_res, ext_max, entry, origin, p2s, legs, sigs, sides, xs, a_s = [], [], [], [], [], [], [], [], [], [], [], [], []
    counts = {"pivots": len(pivots), "skipped_origin_passed": 0, "skipped_target_passed": 0, "skipped_unresolved": 0, "skipped_warmup": 0, "ties": 0}
    prices_all = [p.price for p in pivots]
    bars_all = [p.i for p in pivots]

    for m in range(2, len(pivots)):
        P0, P1, P2 = pivots[m - 2], pivots[m - 1], pivots[m]
        t = P2.conf_i
        if s.ts[t] < stats_start_ms or t < max(sc.long_bars, sc.vol_bars) + 2:
            counts["skipped_warmup"] += 1
            continue
        side = 1 if P0.kind == "L" else -1
        if side * (P2.price - P0.price) <= 0:
            counts["skipped_origin_passed"] += 1
            continue
        leg = abs(P1.price - P0.price)
        if log_target:
            target = P2.price * math.exp(side * ext * abs(math.log(P1.price / P0.price)))
        else:
            target = P2.price + side * ext * leg
        S = float(close[t])
        if target <= 0 or side * (target - S) <= 0 or side * (S - P0.price) <= 0:
            counts["skipped_target_passed"] += 1
            continue
        seen = high[P2.i:t + 1].max() if side == 1 else low[P2.i:t + 1].min()
        if side * (seen - target) >= 0:
            counts["skipped_target_passed"] += 1
            continue

        # walk forward to the first barrier and the furthest extension
        best = side * (seen - P2.price) / leg
        res, res_i = None, None
        last = min(n - 1, t + H)
        for j in range(t + 1, last + 1):
            hj, lj, oj = high[j], low[j], s.order[j]
            fav, adv = (hj, lj) if side == 1 else (lj, hj)
            fav_first = (oj == HIGH_FIRST) if side == 1 else (oj == LOW_FIRST)
            broke = side * (adv - P0.price) <= 0
            if fav_first:
                best = max(best, side * (fav - P2.price) / leg)
                if res is None and side * (fav - target) >= 0:
                    res, res_i = "target", j
                if broke:
                    if res is None:
                        res, res_i = "origin", j
                    if res == "target" and j == res_i:
                        counts["ties"] += 1
                    break
            else:
                if broke:
                    if res is None:
                        res, res_i = "origin", j
                    if side * (fav - target) >= 0:
                        counts["ties"] += 1
                    break
                best = max(best, side * (fav - P2.price) / leg)
                if res is None and side * (fav - target) >= 0:
                    res, res_i = "target", j
        if res is None:
            if t + H > n - 1:
                counts["skipped_unresolved"] += 1
                continue
            res, res_i = "timeout", t + H

        # volatility and barrier
        w = sc.vol_bars
        sigma = math.sqrt(max((cum2[t] - cum2[t - w]) / w, 1e-10))
        sigma_long = math.sqrt(max((cum2[t] - cum2[t - sc.long_bars]) / sc.long_bars, 1e-10))
        x = abs(math.log(S / P0.price))
        a = abs(math.log(target / P0.price))

        d: dict = {}
        d["x_sig"] = x / (sigma * math.sqrt(H))
        d["up_sig"] = (a - x) / (sigma * math.sqrt(H))
        d["log_sigma"] = math.log(sigma)
        d["vol_regime"] = math.log(sigma / sigma_long)
        # trend
        d["s"] = side
        d["s_ret_short"] = side * (logc[t] - logc[t - w]) / (sigma * math.sqrt(w))
        d["s_ret_long"] = side * (logc[t] - logc[t - sc.long_bars]) / (sigma_long * math.sqrt(sc.long_bars))
        d["s_vs_sma"] = side * (logc[t] - sma_long[t]) / (sigma_long * math.sqrt(sc.long_bars))
        d["s_sma_slope"] = side * (sma_long[t] - sma_long[t - w]) / (sigma_long * math.sqrt(w))
        d["dd_ath"] = logc[t] - math.log(ath[t])
        d["s_dd_ath"] = side * d["dd_ath"]
        # fib and leg geometry
        bars01, bars12 = max(1, P1.i - P0.i), max(1, P2.i - P1.i)
        r = abs(P2.price - P1.price) / leg
        rl = abs(math.log(P2.price / P1.price)) / abs(math.log(P1.price / P0.price))
        d["r"], d["r_log"] = r, rl
        for name, lv in (("d382", .382), ("d500", .5), ("d618", .618), ("d786", .786)):
            d[name] = abs(r - lv)
        d["in_500_618"] = float(.5 <= r <= .618)
        d["in_382_618"] = float(.382 <= r <= .618)
        d["near_fib"] = float(min(abs(r - lv) for lv in (.236, .382, .5, .618, .786)) <= .02)
        tr = bars12 / bars01
        d["log_time_ratio"] = math.log(tr)
        d["time_rule_ok"] = float(.25 <= tr <= 1)
        atr_t = atr[t]
        d["leg01_speed"] = abs(math.log(P1.price / P0.price)) / (sigma * math.sqrt(bars01))
        d["leg12_speed"] = abs(math.log(P2.price / P1.price)) / (sigma * math.sqrt(bars12))
        d["leg01_atr"] = abs(math.log(P1.price / P0.price)) / atr_t
        if m >= 3:
            Pm1 = pivots[m - 3]
            d["prior_leg_ratio"] = math.log(max(abs(P0.price - Pm1.price), 1e-9) / leg)
            d["engulfs_prior"] = float(side * (P1.price - Pm1.price) > 0)
        else:
            d["prior_leg_ratio"], d["engulfs_prior"] = float("nan"), float("nan")
        lb = max(0, P0.i - 100)
        ref = low[lb:P0.i + 1].min() if side == 1 else high[lb:P0.i + 1].max()
        d["p0_extreme_100"] = float(side * (P0.price - ref) <= 0)
        # TDI
        rt, r1, r2, r0 = rsi11[t], rsi11[P1.i], rsi11[P2.i], rsi11[P0.i]
        al = lambda v: 50 + side * (v - 50)
        d["rsi_t_a"], d["rsi_p1_a"], d["rsi_p2_a"] = al(rt), al(r1), al(r2)
        d["p2_in_zone"] = float(40 <= r2 <= 50) if side == 1 else float(60 <= r2 <= 70)
        d["p1_through_70"] = float(r1 > 70) if side == 1 else float(r1 < 40)
        d["p2_buy_territory"] = float(r2 < 40) if side == 1 else float(r2 > 70)
        d["hdiv_p0_p2"] = float(side * (r2 - r0) < 0)  # P2 holds above P0 while RSI goes past: hidden divergence
        if m >= 4:
            Pm2 = pivots[m - 4]
            d["rdiv_at_p0"] = float(side * (P0.price - Pm2.price) < 0 and side * (r0 - rsi11[Pm2.i]) > 0)
        else:
            d["rdiv_at_p0"] = float("nan")
        band = 1.6185 * std31[t]
        d["rsi_band_a"] = side * (rt - mid31[t]) / band if band > 0 else float("nan")
        d["rsi_signal_a"] = side * (rt - sig9[t])
        band1 = 1.6185 * std31[P1.i]
        d["p1_outside_band"] = float(side * (r1 - mid31[P1.i]) > band1) if band1 > 0 else float("nan")
        # rule-legality flags: one degree, what the checker can see
        dir_s = "up" if side == 1 else "down"
        opp = "down" if side == 1 else "up"
        d["prior_opposite_5"] = 0.0
        if m >= 7:
            ps = pivots[m - 7:m - 1]  # ends at P0
            lab = {k: Point(p.i, p.price) for k, p in zip(("0", "1", "2", "3", "4", "5"), ps)}
            d["prior_opposite_5"] = float(not hard(violations(IMPULSE, opp, lab)) or not hard(violations(ED, opp, lab)))
        d["as_w4"] = 0.0
        if m >= 4:
            ps = pivots[m - 4:m + 1]
            lab = {k: Point(p.i, p.price) for k, p in zip(("0", "1", "2", "3", "4"), ps)}
            d["as_w4"] = float(not hard(violations(IMPULSE, dir_s, lab)))
        d["as_c_zigzag"], d["as_c_flat"] = 0.0, 0.0
        if m >= 3:
            ps = pivots[m - 3:m + 1]
            lab = {k: Point(p.i, p.price) for k, p in zip(("0", "A", "B", "C"), ps)}
            d["as_c_zigzag"] = float(not hard(violations(ZIGZAG, opp, lab)))
            d["as_c_flat"] = float(any(not hard(violations(f, opp, lab)) for f in (FLAT_REG, FLAT_RUN, FLAT_EXP)))
        # how many ways can P2 be a wave 4 or a wave 2 over the last 12 pivots
        lo_m = max(0, m - 12)
        n_w4 = 0
        for i2 in range(m - 2, lo_m - 1, -2):
            for i1 in range(i2 - 1, lo_m - 1, -2):
                for i0 in range(i1 - 1, lo_m - 1, -2):
                    if i0 < 0:
                        continue
                    lab = {"0": Point(bars_all[i0], prices_all[i0]), "1": Point(bars_all[i1], prices_all[i1]), "2": Point(bars_all[i2], prices_all[i2]),
                           "3": Point(P1.i, P1.price), "4": Point(P2.i, P2.price)}
                    if not hard(violations(IMPULSE, dir_s, lab)):
                        n_w4 += 1
        d["n_w4_readings"] = float(n_w4)
        n_w2 = 0
        for i0 in range(m - 2, lo_m - 1, -2):
            if side * (P2.price - prices_all[i0]) > 0 and side * (P1.price - prices_all[i0]) > 0:
                n_w2 += 1
        d["n_w2_origins"] = float(n_w2)
        # the inside of each leg, one degree down
        n01, px01, ix01 = _sub_count(subs, P0.i, P1.i)
        n12, px12, ix12 = _sub_count(subs, P1.i, P2.i)
        d["n_sub_01"], d["n_sub_12"] = float(n01), float(n12)
        d["w1_leaf"], d["w2_leaf"] = float(n01 == 1), float(n12 == 1)
        d["w1_nested_motive"], d["w2_nested_corrective"] = 0.0, 0.0
        if 3 <= n01 <= 15 and n01 % 2 == 1:
            d["w1_nested_motive"] = float(Grammar([P0.price, *px01, P1.price], [P0.i, *ix01, P1.i]).motive(0, n01) > 0)
        if 3 <= n12 <= 15 and n12 % 2 == 1:
            d["w2_nested_corrective"] = float(Grammar([P1.price, *px12, P2.price], [P1.i, *ix12, P2.i]).corrective(0, n12) > 0)
        # cycles: state after the last day closed by the decision bar
        j_day = int((s.ts[t] + tf_ms) // DAY_MS) - 1 - day_first
        cd, cw = states["centre_d"], states["centre_w"]
        da, wa, ya = states["d_anchor"][j_day], states["w_anchor"][j_day], states["y_anchor"][j_day]
        nan = float("nan")
        day_of = lambda i: int(s.ts[i] // DAY_MS) - day_first
        dd = j_day - da if da >= 0 else None
        dw = j_day - wa if wa >= 0 else None
        d["d_phase"] = dd / cd if dd is not None else nan
        d["w_phase"] = dw / cw if dw is not None else nan
        d["y_phase"] = (j_day - ya) / 1434 if ya >= 0 else nan
        d["d_in_window"] = float(states["lo_d"] <= dd <= states["hi_d"]) if dd is not None else nan
        d["w_in_window"] = float(states["lo_w"] <= dw <= states["hi_w"]) if dw is not None else nan
        d["d_top_pos"] = (states["d_top"][j_day] - da) / cd if da >= 0 else nan
        d["w_top_pos"] = (states["w_top"][j_day] - wa) / cw if wa >= 0 else nan
        d["d_failed"] = float(states["d_failed"][j_day]) if da >= 0 else nan
        d["w_failed"] = float(states["w_failed"][j_day]) if wa >= 0 else nan
        d["s_d_cos"] = side * math.cos(2 * math.pi * d["d_phase"]) if dd is not None else nan
        d["s_w_cos"] = side * math.cos(2 * math.pi * d["w_phase"]) if dw is not None else nan
        d["s_y_cos"] = side * math.cos(2 * math.pi * d["y_phase"]) if ya >= 0 else nan
        p2_day, p0_day = day_of(P2.i), day_of(P0.i)
        dc, wc = states["d_cand"][j_day], states["w_cand"][j_day]
        d["p2_at_d_low"] = float((da >= 0 and abs(p2_day - da) <= 3) or (dc >= 0 and abs(p2_day - dc) <= 3)) if side == 1 else 0.0
        d["p2_at_w_low"] = float((wa >= 0 and abs(p2_day - wa) <= 7) or (wc >= 0 and abs(p2_day - wc) <= 7)) if side == 1 else 0.0
        d["p0_w_align"] = side * math.cos(2 * math.pi * (p0_day - wa) / cw) if wa >= 0 else nan
        d["p0_d_align"] = side * math.cos(2 * math.pi * (p0_day - da) / cd) if da >= 0 else nan

        rows.append(d)
        y.append(1 if res == "target" else 0)
        outcome.append(res)
        i_conf.append(t)
        i_res.append(res_i)
        ext_max.append(best)
        entry.append(S)
        origin.append(P0.price)
        p2s.append(P2.price)
        legs.append(leg)
        sigs.append(sigma)
        sides.append(side)
        xs.append(x)
        a_s.append(a)

    i_conf_a, i_res_a = np.array(i_conf, dtype=np.int64), np.array(i_res, dtype=np.int64)
    p_b = barrier_prob(np.array(xs), np.array(a_s), np.array(sigs) ** 2 * H)
    names = FEATURES
    X = np.full((len(rows), len(names)), np.nan)
    for r_i, d in enumerate(rows):
        d["logit_p"] = float(logit(p_b[r_i]))
        for c_i, f in enumerate(names):
            X[r_i, c_i] = d[f]
    counts["samples"] = len(rows)
    return Samples(X, names, np.array(y), outcome, i_conf_a, i_res_a, s.ts[i_conf_a] + tf_ms, s.ts[i_res_a] + tf_ms, p_b, np.array(ext_max), np.array(entry),
                   np.array(origin), np.array(p2s), np.array(legs), np.array(sigs), np.array(sides), counts)


def null_series(s: Series, first: int, kind: str, block_days: int, rng: np.random.Generator) -> Series:
    """Bars before `first` as they were, then this series' own bars in a new order, OHLC relative to the previous close.
    `shuffled` destroys all time order; `block` keeps runs of block_days, on day boundaries, so volatility clustering
    and the time-of-day pattern survive but anything longer does not. The same idea as ewave.cycles.evaluate.null_path."""
    per_day = int(DAY_MS // s.tf_ms)
    # the bars from `first` on, as whole days where possible
    m = len(s) - first
    pc = s.close[first - 1:-1]
    rel = np.column_stack([s.open[first:] / pc, s.high[first:] / pc, s.low[first:] / pc, s.close[first:] / pc])
    if kind == "shuffled":
        order = rng.permutation(m)
    elif kind == "block":
        blk = block_days * per_day
        starts = rng.integers(0, max(1, (m // per_day)), size=m // blk + 2) * per_day
        idx = (starts[:, None] + np.arange(blk)[None, :]).ravel() % m
        order = idx[:m]
    else:
        raise ValueError(kind)
    cum = s.close[first - 1] * np.cumprod(rel[order, 3])
    prev = np.concatenate([[s.close[first - 1]], cum[:-1]])
    o, h, l, c = s.open.copy(), s.high.copy(), s.low.copy(), s.close.copy()
    hl = s.order.copy()
    o[first:] = prev * rel[order, 0]
    h[first:] = prev * rel[order, 1]
    l[first:] = prev * rel[order, 2]
    c[first:] = cum
    hl[first:] = s.order[first:][order]
    return Series(s.ts, o, h, l, c, hl, s.tf_ms)


__all__ = ["Scale", "SCALES", "GROUPS", "FEATURES", "Samples", "build_samples", "cycle_states", "null_series", "barrier_prob", "logit", "STATS_START_MS", "DAY_MS"]
