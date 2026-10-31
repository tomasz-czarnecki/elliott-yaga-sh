"""Section C: Tomasz's hypothesis. "Very often the Elliott Wave structure finishes on the weekly cycles. Very often the
weekly cycle is a low or something and the middle of the weekly cycle is a top of something."

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/c_weekly_cycles.py --paths 1000

Weekly cycle: the 24-42 week low-to-low cycle of ewave.cycles (Camel Finance), hindsight marks and live machine, imported and
not modified. Structures come from the zigzag and the rule checker alone, with no cycle input. The cycle DP picks swing lows
by construction, so "a cycle low is a pivot low" proves nothing; every number here is therefore also computed by the identical
pipeline on null paths, and only the difference counts. Null paths use whole days as the unit (nulls.null_days), so a path's 1D
view and 4H view are the same market and the marks and the structures can be compared on it. Bars before 2013-03-01 stay as
they were, as in cycles-r1.

Tests:
  C1 Top position: where the highest high of each weekly cycle sits as a fraction of the cycle. Uniform, null, BTC.
  C2 Local tops: all pivot highs of an independent zigzag, by cycle phase, and where the biggest pullback inside each cycle starts.
     A "top of something" need not be the cycle's top. Camel's book puts a half-cycle LOW near the middle, so pivot lows are measured too.
  C3 Structure ends: do legal down-structures end near weekly lows, and legal up-structures in the middle of the cycle, more
     often than the same detector and the same marks give on null paths? Also an odds ratio inside the path: among pivot lows,
     is one that ends a legal down-structure more often at a weekly low than one that does not? That controls for the plain
     fact that big lows are big lows.
  C4 Causal: after a live-confirmed weekly low, is the next structure more often a legal up impulse than after other pivot lows
     or random dates, and does a 2R barrier from the confirmation close do better than on nulls?
  C5 Confluence for a trader: a legal down-structure confirmed with the live weekly window open, against one with it closed:
     does it reach the start of its last leg before undercutting its end more often? On BTC and, as a difference, on nulls.
  C6 Rhythm: spectral power of daily returns at 168-294 day periods against nulls. No marks involved.
  C7 Other reading: "weekly" as day of the week. Pivots by weekday, against nulls.

Primary settings fixed before any outcome was looked at (they come from the census only): scales 4h_pct8 and 1d_pct16, whose
median leg size (15 and 33 percent) matches the rulebook's expected move for 4h and D signals; tolerance +-14 days, the weekly
level's own swing_k_days; mid band 0.4-0.6. Everything else is reported as sensitivity.

Writes c_metrics.csv, c_positions.csv, c_lows_btc.csv, c_summary.json to the scratch folder. About 5 minutes at 1000 paths.
"""
from __future__ import annotations

import argparse
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from common import ANALYSIS_VENUE, Scale, bh_qvalues, day_str, load_series, mc_p_high, q5_50_95, to_ms, write_csv, write_json
from ewave.cycles.config import DAY_MS, load_rules
from ewave.cycles.hindsight import build
from ewave.cycles.live import replay
from ewave.cycles.series import Bars, load_daily
from impulse import check, threes
from nulls import KINDS, null_days, to_day_rel
from zigzag import Pivots, zigzag_raw

try:
    from numba import njit
except ImportError:
    def njit(f):
        return f

PER_DAY = 6
SEED = 20261032
PRIMARY = ("4h_pct8", "1d_pct16")
C_SCALES = (Scale("4h", "pct", 8), Scale("1d", "pct", 16), Scale("4h", "pct", 4), Scale("1d", "pct", 8),
            Scale("4h", "atr", 4), Scale("1d", "atr", 2))
TOLERANCES = (7, 14, 21)
MID_BANDS = ((0.45, 0.55), (0.4, 0.6), (0.35, 0.65))
BLOCK_DAYS = 20


class View:
    """One market, as both layers need it. All day indices are positions in `bars` (whole history)."""

    def __init__(self, bars: Bars, first: int, o4, h4, l4, c4, hf4):
        self.bars, self.first = bars, first
        self.h4, self.l4, self.c4, self.hf4 = h4, l4, c4, hf4
        days = h4.size // PER_DAY
        H, L = h4.reshape(days, PER_DAY), l4.reshape(days, PER_DAY)
        self.h1, self.l1 = H.max(axis=1), L.min(axis=1)
        self.c1 = c4[PER_DAY - 1::PER_DAY]
        hi_at, lo_at = H.argmax(axis=1), L.argmin(axis=1)
        same = hf4.reshape(days, PER_DAY)[np.arange(days), hi_at]
        self.hf1 = np.where(hi_at == lo_at, same, hi_at < lo_at)

    def zigzag(self, scale: Scale) -> Pivots:
        if scale.tf == "1d":
            return zigzag_raw(self.h1, self.l1, self.c1, self.hf1, scale)
        return zigzag_raw(self.h4, self.l4, self.c4, self.hf4, scale)

    def day_of(self, scale: Scale, bars_i: np.ndarray) -> np.ndarray:
        """Absolute day index of bar positions on this scale's timeframe."""
        return self.first + (bars_i if scale.tf == "1d" else bars_i // PER_DAY)


def load_market() -> tuple[Bars, int, tuple, np.ndarray]:
    rules = load_rules()
    bars = load_daily(ANALYSIS_VENUE)
    first = bars.index_of(to_ms(rules.series["stats_start"]))
    s = load_series(ANALYSIS_VENUE, "4h", rules.series["stats_start"])
    days = min((len(bars) - first), len(s) // PER_DAY)
    m = days * PER_DAY
    if s.ts[0] != bars.ts[first] or np.any(np.diff(s.ts[:m]) != 4 * 3_600_000):
        raise ValueError("4h bars must be a full grid starting on the first statistics day")
    bars = bars.upto(first + days)
    return bars, first, (s.o[:m], s.h[:m], s.l[:m], s.c[:m], s.high_first[:m]), s.ts[:m]


def view_of(bars: Bars, first: int, arrays: tuple) -> View:
    o, h, l, c, hf = arrays
    days = h.size // PER_DAY
    O = np.exp(o[::PER_DAY]).tolist()
    H = np.exp(h.reshape(days, PER_DAY).max(axis=1)).tolist()
    L = np.exp(l.reshape(days, PER_DAY).min(axis=1)).tolist()
    C = np.exp(c[PER_DAY - 1::PER_DAY]).tolist()
    path = Bars(bars.ts, bars.open[:first] + O, bars.high[:first] + H, bars.low[:first] + L, bars.close[:first] + C)
    return View(path, first, o, h, l, c, hf)


@njit
def _first_touch(hi, lo, start, up, down):
    """From bar `start` on: +1 if up is touched first, -1 if down, 0 neither. A bar touching both counts as down."""
    for t in range(start, hi.size):
        if lo[t] <= down:
            return -1
        if hi[t] >= up:
            return 1
    return 0


def _nearest(events: np.ndarray, anchors: np.ndarray) -> np.ndarray:
    pos = np.searchsorted(anchors, events)
    left = anchors[np.clip(pos - 1, 0, anchors.size - 1)]
    right = anchors[np.clip(pos, 0, anchors.size - 1)]
    return np.minimum(np.abs(events - left), np.abs(events - right))


def _phase(days: np.ndarray, lows: np.ndarray) -> np.ndarray:
    """Fraction of the cycle for events between the first and the last low; NaN outside."""
    out = np.full(days.size, np.nan)
    k = np.searchsorted(lows, days, side="right") - 1
    ok = (k >= 0) & (k < lows.size - 1)
    out[ok] = (days[ok] - lows[k[ok]]) / (lows[k[ok] + 1] - lows[k[ok]])
    return out


def _odds_ratio(a: int, b: int, c: int, d: int) -> float:
    return ((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5))


def path_metrics(view: View, rules) -> tuple[dict, dict]:
    """Every number of sections C1 to C5 for one path. Second value: raw lists kept for pooled histograms."""
    m: dict[str, float] = {}
    raw: dict[str, list] = {}
    h = build(view.bars, rules)
    e = replay(view.bars, rules, track_zones=False)
    hind_cycles = [c for c in h.cycles["weekly"] if c.length is not None]
    live_cycles = list(e.weekly.cycles)
    marks = {"hind": np.array(h.lows["weekly"], np.int64), "live": np.array([x.i for x in e.weekly.chain], np.int64)}
    first = view.first

    # C1: top position.
    for tag, cycles in (("hind", hind_cycles), ("live", live_cycles)):
        pos = np.array([c.top_pos for c in cycles], float)
        raw[f"top_pos|{tag}"] = pos.tolist()
        m[f"c1|{tag}|n_cycles"] = pos.size
        if pos.size == 0:
            continue
        for half in (0.05, 0.10, 0.15):
            m[f"c1|{tag}|share_top_within_{half:.2f}_of_mid"] = float(np.mean(np.abs(pos - 0.5) <= half))
        m[f"c1|{tag}|share_top_left_of_mid"] = float(np.mean(pos < 0.5))
        m[f"c1|{tag}|mean_abs_distance_from_mid"] = float(np.mean(np.abs(pos - 0.5)))
        m[f"c1|{tag}|median_top_pos"] = float(np.median(pos))

    weekly = rules.levels["weekly"]
    union: dict[str, list[np.ndarray]] = {"down|impulse": [], "up|impulse": [], "down|both": [], "up|both": []}
    for scale in C_SCALES:
        piv = view.zigzag(scale)
        name = scale.name
        day = view.day_of(scale, piv.i)
        cand = check(piv)
        legal = cand.legal if len(cand) else np.zeros(0, bool)
        th = threes(piv)
        hi_mask, lo_mask = piv.kind == 1, piv.kind == -1
        # Structure ends, as positions in the pivot list.
        ends: dict[str, np.ndarray] = {}
        up_imp = cand.start[legal & (cand.direction == 1)] + 5 if len(cand) else np.empty(0, np.int64)
        dn_imp = cand.start[legal & (cand.direction == -1)] + 5 if len(cand) else np.empty(0, np.int64)
        up_abc = th.start[th.legal & (th.direction == 1)] + 3
        dn_abc = th.start[th.legal & (th.direction == -1)] + 3
        ends["down|impulse"], ends["up|impulse"] = dn_imp, up_imp
        ends["down|abc"], ends["up|abc"] = dn_abc, up_abc
        ends["down|both"], ends["up|both"] = np.union1d(dn_imp, dn_abc), np.union1d(up_imp, up_abc)
        for key, value in ends.items():
            m[f"count|{name}|{key}"] = value.size
            if key in union:
                union[key].append(day[value])

        for tag, lows in marks.items():
            if lows.size < 3:
                continue
            # C2: every pivot high and low, by phase.
            ph_hi = _phase(day[hi_mask], lows)
            ph_lo = _phase(day[lo_mask], lows)
            raw[f"phase_hi|{tag}|{name}"] = ph_hi[np.isfinite(ph_hi)].tolist()
            raw[f"phase_lo|{tag}|{name}"] = ph_lo[np.isfinite(ph_lo)].tolist()
            for a, b in MID_BANDS:
                band = f"{a:.2f}-{b:.2f}"
                inner = ph_hi[np.isfinite(ph_hi)]
                if inner.size:
                    m[f"c2|{tag}|{name}|share_pivot_highs_in_{band}"] = float(np.mean((inner >= a) & (inner <= b)))
                inner_lo = ph_lo[np.isfinite(ph_lo)]
                if inner_lo.size:
                    m[f"c2|{tag}|{name}|share_pivot_lows_in_{band}"] = float(np.mean((inner_lo >= a) & (inner_lo <= b)))
                # Cycles with at least one pivot high in the band.
                hit = 0
                for s_, e_ in zip(lows[:-1], lows[1:]):
                    lo_d, hi_d = s_ + a * (e_ - s_), s_ + b * (e_ - s_)
                    hit += int(np.any((day[hi_mask] >= lo_d) & (day[hi_mask] <= hi_d)))
                m[f"c2|{tag}|{name}|share_cycles_with_pivot_high_in_{band}"] = hit / (lows.size - 1)

            # C2: the top of the biggest pullback inside each cycle: a different reading of "a top of something".
            big = []
            for s_, e_ in zip(lows[:-1], lows[1:]):
                inside = np.flatnonzero((day >= s_) & (day <= e_))
                if inside.size < 2:
                    continue
                drops = piv.x[inside[:-1]] - piv.x[inside[1:]]
                j = int(np.argmax(drops))
                if drops[j] > 0:
                    big.append((day[inside[j]] - s_) / (e_ - s_))
            raw[f"bigdrop|{tag}|{name}"] = big
            if big:
                m[f"c2|{tag}|{name}|biggest_pullback_starts_in_0.40-0.60"] = float(np.mean([0.4 <= b <= 0.6 for b in big]))
                m[f"c2|{tag}|{name}|biggest_pullback_start_median"] = float(np.median(big))

            # C3: structure ends near lows and in the middle.
            all_lo, all_hi = np.flatnonzero(lo_mask), np.flatnonzero(hi_mask)
            for struct in ("impulse", "abc", "both"):
                down = ends[f"down|{struct}"]
                up = ends[f"up|{struct}"]
                d_days = day[down]
                u_days = day[up]
                for x in TOLERANCES:
                    tol = f"{x}d"
                    usable = d_days[(d_days >= lows[0] - x) & (d_days <= lows[-1] + x)]
                    if usable.size:
                        m[f"c3|{tag}|{name}|{struct}|down_ends_near_low|{tol}"] = float(np.mean(_nearest(usable, lows) <= x))
                    if d_days.size:
                        all_days = np.arange(lows[0], lows[-1] + 1)
                        m[f"c3|{tag}|{name}|{struct}|lows_with_down_end|{tol}"] = float(np.mean(_nearest(lows, np.sort(d_days)) <= x))
                        m[f"c3|{tag}|{name}|{struct}|days_with_down_end|{tol}"] = float(np.mean(_nearest(all_days, np.sort(d_days)) <= x))
                    else:
                        m[f"c3|{tag}|{name}|{struct}|lows_with_down_end|{tol}"] = 0.0
                        m[f"c3|{tag}|{name}|{struct}|days_with_down_end|{tol}"] = 0.0
                    if u_days.size:
                        m[f"c3|{tag}|{name}|{struct}|lows_with_up_end|{tol}"] = float(np.mean(_nearest(lows, np.sort(u_days)) <= x))
                    # Odds ratio inside the path: among pivot lows, ends of a legal down-structure against the others.
                    other = np.setdiff1d(all_lo, down, assume_unique=False)
                    near_end = (_nearest(day[down], lows) <= x)
                    near_other = (_nearest(day[other], lows) <= x)
                    m[f"c3|{tag}|{name}|{struct}|odds_ratio_low|{tol}"] = _odds_ratio(int(near_end.sum()), int((~near_end).sum()),
                                                                                  int(near_other.sum()), int((~near_other).sum()))
                for a, b in MID_BANDS:
                    band = f"{a:.2f}-{b:.2f}"
                    ph = _phase(u_days, lows)
                    ph = ph[np.isfinite(ph)]
                    if ph.size:
                        m[f"c3|{tag}|{name}|{struct}|up_ends_in_mid|{band}"] = float(np.mean((ph >= a) & (ph <= b)))
                    hit = 0
                    for s_, e_ in zip(lows[:-1], lows[1:]):
                        lo_d, hi_d = s_ + a * (e_ - s_), s_ + b * (e_ - s_)
                        hit += int(np.any((u_days >= lo_d) & (u_days <= hi_d)))
                    m[f"c3|{tag}|{name}|{struct}|cycles_with_up_end_in_mid|{band}"] = hit / (lows.size - 1)
                    other = np.setdiff1d(all_hi, up)
                    ph_o = _phase(day[other], lows)
                    ph_o = ph_o[np.isfinite(ph_o)]
                    a_ = int(((ph >= a) & (ph <= b)).sum())
                    c_ = int(((ph_o >= a) & (ph_o <= b)).sum())
                    m[f"c3|{tag}|{name}|{struct}|odds_ratio_mid|{band}"] = _odds_ratio(a_, ph.size - a_, c_, ph_o.size - c_)

        # C4: causal, from live-confirmed lows, including the ones revised later.
        log = e.weekly.log
        low_days = np.array([x.i for x in log], np.int64)
        conf_days = np.array([x.ts_confirmed // DAY_MS - view.bars.ts[0] // DAY_MS for x in log], np.int64)  # first day after the signal bar closes
        if low_days.size and lo_mask.any():
            lows_pos = np.flatnonzero(lo_mask)
            lows_day = day[lows_pos]
            # A pivot low of this scale within 7 days of the weekly low: did a legal up impulse start from it?
            near = _nearest(lows_day, np.sort(low_days)) <= 7
            legal_up_starts = set(cand.start[legal & (cand.direction == 1)].tolist()) if len(cand) else set()
            resolved = lows_pos + 5 < len(piv)
            at_low = lows_pos[near & resolved]
            other_lows = lows_pos[~near & resolved]
            r_at = np.array([p in legal_up_starts for p in at_low], bool)
            r_other = np.array([p in legal_up_starts for p in other_lows], bool)
            m[f"c4|{name}|n_pivot_lows_at_live_low"] = at_low.size
            if at_low.size:
                m[f"c4|{name}|up_impulse_from_live_low"] = float(r_at.mean())
            if other_lows.size:
                m[f"c4|{name}|up_impulse_from_other_pivot_low"] = float(r_other.mean())
            if at_low.size and other_lows.size:
                m[f"c4|{name}|up_impulse_difference"] = float(r_at.mean() - r_other.mean())
            # The first legal impulse completing after the confirmation: which way?
            if len(cand) and legal.any():
                c_days = np.sort(view.day_of(scale, cand.confirmed_p5[legal]))
                order = np.argsort(view.day_of(scale, cand.confirmed_p5[legal]))
                dirs = cand.direction[legal][order]
                after = np.searchsorted(c_days, conf_days, side="right")
                ok = after < c_days.size
                if ok.any():
                    m[f"c4|{name}|next_impulse_up_after_live_low"] = float(np.mean(dirs[after[ok]] == 1))
                m[f"c4|{name}|share_up_among_all_impulses"] = float(np.mean(dirs == 1))

    # C3, any degree: how a person counts. A structure at any of the six scales is accepted.
    for tag, lows in marks.items():
        if lows.size < 3:
            continue
        for struct in ("impulse", "both"):
            d_days = np.unique(np.concatenate(union[f"down|{struct}"]))
            u_days = np.unique(np.concatenate(union[f"up|{struct}"]))
            if d_days.size:
                all_days = np.arange(lows[0], lows[-1] + 1)
                m[f"c3|{tag}|any_scale|{struct}|lows_with_down_end|14d"] = float(np.mean(_nearest(lows, d_days) <= 14))
                m[f"c3|{tag}|any_scale|{struct}|days_with_down_end|14d"] = float(np.mean(_nearest(all_days, d_days) <= 14))
            hit = 0
            for s_, e_ in zip(lows[:-1], lows[1:]):
                hit += int(np.any((u_days >= s_ + 0.4 * (e_ - s_)) & (u_days <= s_ + 0.6 * (e_ - s_))))
            m[f"c3|{tag}|any_scale|{struct}|cycles_with_up_end_in_mid|0.40-0.60"] = hit / (lows.size - 1)

    # C4 without a zigzag: the 2R barrier and the forward return from the confirmation close.
    log = e.weekly.log
    wins = []
    forward = {30: [], 60: [], 90: []}
    for x in log:
        d = (x.ts_confirmed - view.bars.ts[0]) // DAY_MS  # the bar after the signal bar's close
        k = d - first
        if k <= 0 or k >= view.h1.size:
            continue
        entry = view.c1[k - 1]
        risk = entry - np.log(x.price)
        if risk <= 0:
            continue
        wins.append(_first_touch(view.h1, view.l1, k, entry + 2 * risk, np.log(x.price)))
        for days_, values in forward.items():
            if k - 1 + days_ < view.c1.size:
                values.append(view.c1[k - 1 + days_] - entry)
    wins_ = np.array(wins)
    resolved = wins_[wins_ != 0]
    m["c4|barrier_2r_from_live_low|n"] = resolved.size
    if resolved.size:
        m["c4|barrier_2r_from_live_low|win_rate"] = float(np.mean(resolved == 1))
    for days_, values in forward.items():
        if values:
            m[f"c4|forward_{days_}d_mean_log_return"] = float(np.mean(values))
            m[f"c4|forward_{days_}d_share_positive"] = float(np.mean(np.array(values) > 0))
            m[f"c4|forward_{days_}d_n"] = len(values)

    # C5: confluence, causal. For each legal down-structure at its confirmation: was the live weekly window open then?
    known = sorted(((x.ts_confirmed, x.i, x.ts_revised) for x in log), key=lambda r: r[0])
    t0 = view.bars.ts[0]
    for scale in (C_SCALES[0], C_SCALES[1]):
        piv = view.zigzag(scale)
        name = scale.name
        cand = check(piv)
        th = threes(piv)
        per_bar = 1 if scale.tf == "1d" else PER_DAY
        hi, lo = (view.h1, view.l1) if scale.tf == "1d" else (view.h4, view.l4)
        rows = []
        if len(cand):
            for s0, conf in zip(cand.start[cand.legal & (cand.direction == -1)], cand.confirmed_p5[cand.legal & (cand.direction == -1)]):
                rows.append((conf, piv.x[s0 + 4], piv.x[s0 + 5]))
        for s0, conf in zip(th.start[th.legal & (th.direction == -1)], th.confirmed_end[th.legal & (th.direction == -1)]):
            rows.append((conf, piv.x[s0 + 2], piv.x[s0 + 3]))
        outcome = {"open": [], "closed": []}
        for conf, level_up, level_end in rows:
            start = conf + 1
            if start >= hi.size:
                continue
            day_i = first + conf // per_bar
            ts_now = t0 + (day_i + 1) * DAY_MS
            standing = None
            for ts_c, low_i, ts_r in known:
                if ts_c > ts_now:
                    break
                if ts_r is None or ts_r > ts_now:
                    standing = low_i
            if standing is None:
                continue
            elapsed = day_i - standing
            state = "open" if weekly.lo_tol <= elapsed <= weekly.hi_tol else "closed"
            r = _first_touch(hi, lo, start, level_up, level_end)
            if r != 0:
                outcome[state].append(r == 1)
        for state, values in outcome.items():
            m[f"c5|{name}|n_window_{state}"] = len(values)
            if values:
                m[f"c5|{name}|reaches_start_of_last_leg|window_{state}"] = float(np.mean(values))
        if outcome["open"] and outcome["closed"]:
            m[f"c5|{name}|difference_open_minus_closed"] = float(np.mean(outcome["open"]) - np.mean(outcome["closed"]))

    # C6: spectral power of daily returns.
    r = np.diff(view.c1)
    r = r - r.mean()
    power = np.abs(np.fft.rfft(r)) ** 2
    freq = np.fft.rfftfreq(r.size, 1.0)
    with np.errstate(divide="ignore"):
        period = np.where(freq > 0, 1 / np.where(freq > 0, freq, 1), np.inf)
    band = (period >= 168) & (period <= 294)
    near_band = ((period >= 100) & (period < 168)) | ((period > 294) & (period <= 500))
    m["c6|power_share_168_294d"] = float(power[band].sum() / power[1:].sum())
    m["c6|power_ratio_to_neighbours"] = float(power[band].mean() / power[near_band].mean())
    return m, raw


_STATE: dict = {}


def _run(job: tuple) -> tuple[str, dict, dict]:
    kind, seed = job
    rng = np.random.default_rng(seed)
    arrays = null_days(_STATE["day_rel"], kind, rng, block=BLOCK_DAYS)
    return kind, *path_metrics(view_of(_STATE["bars"], _STATE["first"], arrays), _STATE["rules"])


def _init() -> None:
    bars, first, arrays, _ = load_market()
    _STATE.update({"bars": bars, "first": first, "rules": load_rules(),
                   "day_rel": to_day_rel(*arrays, PER_DAY)})


def weekday_test(paths: int) -> list[dict]:
    """C7: pivots of 1h and 4h zigzags by UTC weekday, against shuffle and signflip paths. Chi-square style distance to flat."""
    from nulls import null_bars, to_rel
    rows = []
    for tf, per_day, scales in (("4h", 6, (Scale("4h", "pct", 4), Scale("4h", "atr", 4))), ("1h", 24, (Scale("1h", "pct", 4), Scale("1h", "atr", 4)))):
        s = load_series(ANALYSIS_VENUE, tf)
        weekday = ((s.ts // DAY_MS + 3) % 7).astype(int)  # 0 Monday
        rel = to_rel(s.o, s.h, s.l, s.c, s.high_first, per_day)
        rng = np.random.default_rng([SEED, per_day])
        for scale in scales:
            p = zigzag_raw(s.h, s.l, s.c, s.high_first, scale)
            for kind_name, mask in (("low", p.kind == -1), ("high", p.kind == 1)):
                counts = np.bincount(weekday[p.i[mask]], minlength=7).astype(float)
                row = {"scale": scale.name, "pivot": kind_name, "n": int(counts.sum()),
                       **{f"d{d}": float(counts[d] / counts.sum()) for d in range(7)}}
                rows.append(row)
            for kind in ("shuffle", "signflip"):
                shares = {"low": [], "high": []}
                for _ in range(paths):
                    o, h, l, c, hf = null_bars(rel, kind, rng)
                    q = zigzag_raw(h, l, c, hf, scale)
                    for kind_name, mask in (("low", q.kind == -1), ("high", q.kind == 1)):
                        cnt = np.bincount(weekday[q.i[mask]], minlength=7).astype(float)
                        shares[kind_name].append(cnt / cnt.sum())
                for r in rows[-2:]:
                    k_ = r["pivot"]
                    arr = np.array(shares[k_])
                    mean = arr.mean(axis=0)
                    btc = np.array([r[f"d{d}"] for d in range(7)])
                    dist_b = float(((btc - mean) ** 2 / mean).sum())
                    dist_n = ((arr - mean) ** 2 / mean).sum(axis=1)
                    r[f"{kind}_p"] = mc_p_high(dist_b, dist_n)
                    r[f"{kind}_mean_d0"] = float(mean[0])
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--weekday-paths", type=int, default=200)
    args = ap.parse_args()
    t0 = time.time()
    bars, first, arrays, ts4 = load_market()
    rules = load_rules()
    view = View(bars, first, *arrays)
    # The 1D bars aggregated from the 4H bars must be the 1D bars the cycle code reads.
    assert np.allclose(np.exp(view.h1), np.array(bars.high[first:]), rtol=1e-9)
    assert np.allclose(np.exp(view.l1), np.array(bars.low[first:]), rtol=1e-9)
    btc, btc_raw = path_metrics(view, rules)
    print(f"BTC metrics: {len(btc)} numbers, {time.time() - t0:.1f}s", flush=True)

    jobs = [(kind, np.random.SeedSequence([SEED, i, n]).generate_state(1)[0].item()) for i, kind in enumerate(KINDS) for n in range(args.paths)]
    results: dict[str, list[dict]] = {k: [] for k in KINDS}
    pooled: dict[str, dict[str, list]] = {k: {} for k in KINDS}
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init) as pool:
        for done, (kind, metrics, raw) in enumerate(pool.map(_run, jobs, chunksize=8)):
            results[kind].append(metrics)
            for key, values in raw.items():
                pooled[kind].setdefault(key, []).extend(values)
            if (done + 1) % 400 == 0:
                print(f"{done + 1}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)

    rows = []
    for key, value in sorted(btc.items()):
        row = {"metric": key, "btc": value,
               "primary": (any(p in key for p in PRIMARY) and ("|14d" in key or "0.40-0.60" in key or key.startswith(("c4", "c5"))))
               or "share_top_within_0.10" in key or key == "c6|power_ratio_to_neighbours" or key == "c4|barrier_2r_from_live_low|win_rate"}
        for kind in KINDS:
            values = np.array([r.get(key, np.nan) for r in results[kind]], float)
            lo, mid, hi = q5_50_95(values)
            row.update({f"{kind}_p5": lo, f"{kind}_median": mid, f"{kind}_p95": hi, f"{kind}_n_paths": int(np.isfinite(values).sum()),
                        f"{kind}_p_high": mc_p_high(float(value), values), f"{kind}_p_low": mc_p_high(-float(value), -values)})
        rows.append(row)
    for kind in KINDS:
        ps = np.array([min(1.0, 2 * min(r[f"{kind}_p_high"], r[f"{kind}_p_low"])) for r in rows])
        qs = bh_qvalues(ps)
        prim = [i for i, r in enumerate(rows) if r["primary"]]
        qp = bh_qvalues(ps[prim])
        for r, p, q in zip(rows, ps, qs):
            r[f"{kind}_p2"] = float(p)
            r[f"{kind}_q_all"] = float(q)
        for i, q in zip(prim, qp):
            rows[i][f"{kind}_q_primary"] = float(q)
    write_csv("c_metrics.csv", rows)

    # Position histograms, pooled over null cycles: is there a hump at the middle in random paths?
    pos_rows = []
    edges = np.linspace(0, 1, 11)
    for key in sorted(btc_raw):
        b = np.array(btc_raw[key], float)
        row = {"key": key, "n_btc": b.size}
        hist_b = np.histogram(b, bins=edges)[0] / max(b.size, 1)
        for i in range(10):
            row[f"btc_{i}"] = float(hist_b[i])
        for kind in KINDS:
            v = np.array(pooled[kind].get(key, []), float)
            hist = np.histogram(v, bins=edges)[0] / max(v.size, 1)
            for i in range(10):
                row[f"{kind}_{i}"] = float(hist[i])
            row[f"{kind}_n"] = v.size
        pos_rows.append(row)
    write_csv("c_positions.csv", pos_rows)

    # BTC detail: each weekly low, with the nearest structure ends, so the reader can check the dates.
    detail = []
    h = build(bars, rules)
    hind = np.array(h.lows["weekly"], np.int64)
    ends_by = {}
    for scale in C_SCALES[:2]:
        piv = view.zigzag(scale)
        cand = check(piv)
        th = threes(piv)
        day = view.day_of(scale, piv.i)
        ends_by[f"{scale.name}|impulse"] = np.sort(day[cand.start[cand.legal & (cand.direction == -1)] + 5])
        ends_by[f"{scale.name}|abc"] = np.sort(day[th.start[th.legal & (th.direction == -1)] + 3])
    for i in hind:
        row = {"low": day_str(bars.ts[i]), "price": bars.low[i]}
        for key, ends in ends_by.items():
            if ends.size:
                near = ends[np.argmin(np.abs(ends - i))]
                row[f"nearest_down_{key}"] = int(near - i)
        detail.append(row)
    write_csv("c_lows_btc.csv", detail)

    tops = [{"start": day_str(bars.ts[c.start_i]), "end": day_str(bars.ts[c.end_i]), "length": c.length, "top": day_str(bars.ts[c.top_i]), "top_pos": c.top_pos,
             "translation": c.translation, "failed": c.failed} for c in h.cycles["weekly"] if c.length is not None]
    write_csv("c_cycles_btc.csv", tops)

    wd = weekday_test(args.weekday_paths) if args.weekday_paths else []
    write_csv("c_weekday.csv", wd)
    write_json("c_summary.json", {"paths": args.paths, "kinds": KINDS, "primary": PRIMARY, "tolerances": TOLERANCES, "mid_bands": MID_BANDS,
                                  "null_cycles_check": {k: {"weekly_cycles_hind_median": float(np.median([r["c1|hind|n_cycles"] for r in results[k]]))} for k in KINDS}})
    print(f"done {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
