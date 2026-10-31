"""Section C, follow-ups to c_weekly_cycles.py, on the two places where BTC did stand out.

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/c2_followups.py --paths 1000

1. Up-structures in the middle of the cycle, made causal. c_weekly_cycles.py finds legal up-structures ending in the middle of live
   cycles more often than on nulls, but there the phase uses the cycle's end, not known at the time. Here each up-structure is taken at
   its confirmation, with the live low standing at that moment and the phase = days since it / 231 (the middle of the 24-42 week
   window). Is the share landing at 0.4-0.6 high? And does the top hold better there: does price reach the start of the last leg
   before making a new high, more often than for up-structures elsewhere? The driftless barrier law is reported beside it, because a
   short last leg makes that barrier easier on any path.

2. Rhythm. c_weekly_cycles.py finds extra spectral power of daily returns at 168-294 day periods against volatility-only nulls. Is that
   band special among its neighbours, and is it there in each era? Band powers of the periodogram; shuffle, block and signflip paths.
   Trendflip keeps BTC's slow path by construction, so it cannot test this.

Writes c2_midphase.csv, c2_spectrum.csv to the scratch folder. About 5 minutes at 1000 paths.
"""
from __future__ import annotations

import argparse
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from c_weekly_cycles import BLOCK_DAYS, PER_DAY, View, _first_touch, load_market, view_of
from common import ANALYSIS_VENUE, ERAS, Scale, load_series, mc_p_high, q5_50_95, to_ms, write_csv
from ewave.cycles.config import DAY_MS, load_rules
from ewave.cycles.live import replay
from impulse import check, threes
from nulls import KINDS, null_days, to_day_rel

SEED = 20261043
SCALES_F = (Scale("4h", "pct", 8), Scale("1d", "pct", 16), Scale("4h", "atr", 4), Scale("1d", "atr", 2))
BANDS = ((30, 60), (60, 100), (100, 168), (168, 294), (294, 500), (500, 1000))
SPANS = (("all", "2013-01-01", "2027-01-01"), ("2013-2017", "2013-01-01", "2018-01-01"), *ERAS[1:])
_STATE: dict = {}


def band_ratios(r: np.ndarray) -> dict[str, float]:
    """For each band: mean periodogram power against the mean over all periods of 30 to 1000 days."""
    r = r - r.mean()
    power = np.abs(np.fft.rfft(r)) ** 2
    freq = np.fft.rfftfreq(r.size, 1.0)
    with np.errstate(divide="ignore"):
        period = np.where(freq > 0, 1 / np.where(freq > 0, freq, 1), np.inf)
    base = power[(period >= 30) & (period < 1000)].mean()
    out = {}
    for a, b in BANDS:
        m = (period >= a) & (period < b)
        out[f"{a}-{b}"] = float(power[m].mean() / base) if m.any() else float("nan")
    return out


def spectrum(view: View, edges: list[tuple[int, int]]) -> dict[str, float]:
    r = np.diff(view.c1)
    m = {}
    for (name, _, _), (a, b) in zip(SPANS, edges):
        for key, value in band_ratios(r[a:max(a, b - 1)]).items():
            m[f"{name}|{key}"] = value
    return m


def midphase(view: View, rules) -> dict[str, float]:
    e = replay(view.bars, rules, track_zones=False)
    log = sorted(((x.ts_confirmed, x.i, x.ts_revised) for x in e.weekly.log), key=lambda r: r[0])
    centre = rules.levels["weekly"].centre
    t0 = view.bars.ts[0]
    first = view.first
    m: dict[str, float] = {}
    for scale in SCALES_F:
        piv = view.zigzag(scale)
        cand = check(piv)
        th = threes(piv)
        per_bar = 1 if scale.tf == "1d" else PER_DAY
        hi, lo = (view.h1, view.l1) if scale.tf == "1d" else (view.h4, view.l4)
        for struct in ("impulse", "abc"):
            if struct == "impulse":
                if not len(cand):
                    continue
                mask = cand.legal & (cand.direction == 1)
                events = [(c_, piv.x[s + 4], piv.x[s + 5]) for s, c_ in zip(cand.start[mask], cand.confirmed_p5[mask])]
            else:
                mask = th.legal & (th.direction == 1)
                events = [(c_, piv.x[s + 2], piv.x[s + 3]) for s, c_ in zip(th.start[mask], th.confirmed_end[mask])]
            groups: dict[str, list] = {"mid": [], "other": []}
            law: dict[str, list] = {"mid": [], "other": []}
            for conf, start_last, end_up in events:
                day_i = first + conf // per_bar
                ts_now = t0 + (day_i + 1) * DAY_MS
                standing = None
                for ts_c, low_i, ts_r in log:
                    if ts_c > ts_now:
                        break
                    if ts_r is None or ts_r > ts_now:
                        standing = low_i
                if standing is None or conf + 1 >= hi.size:
                    continue
                phase = (day_i - standing) / centre
                name = "mid" if 0.4 <= phase <= 0.6 else "other"
                # Mirror: the top holds if price reaches the start of the last leg before going above the end of the structure.
                r = _first_touch(-lo, -hi, conf + 1, -start_last, -end_up)
                if r != 0:
                    groups[name].append(r == 1)
                    entry = (view.c1 if scale.tf == "1d" else view.c4)[conf]
                    to_end, to_start = end_up - entry, entry - start_last
                    if to_end + to_start > 0:
                        law[name].append(to_end / (to_end + to_start))
            key = f"{scale.name}|{struct}"
            total = len(groups["mid"]) + len(groups["other"])
            m[f"{key}|n_mid"] = len(groups["mid"])
            m[f"{key}|n_other"] = len(groups["other"])
            if total:
                m[f"{key}|share_mid"] = len(groups["mid"]) / total
            for name in ("mid", "other"):
                if groups[name]:
                    m[f"{key}|top_holds_{name}"] = float(np.mean(groups[name]))
                    m[f"{key}|law_{name}"] = float(np.mean(law[name])) if law[name] else float("nan")
            if groups["mid"] and groups["other"]:
                m[f"{key}|difference"] = float(np.mean(groups["mid"]) - np.mean(groups["other"]))
                m[f"{key}|difference_minus_law"] = m[f"{key}|difference"] - (m[f"{key}|law_mid"] - m[f"{key}|law_other"])
    return m


def _init() -> None:
    bars, first, arrays, _ = load_market()
    s = load_series(ANALYSIS_VENUE, "1d", "2013-03-01")
    edges = [(int(np.searchsorted(s.ts, to_ms(a))), int(np.searchsorted(s.ts, to_ms(b)))) for _, a, b in SPANS]
    _STATE.update({"bars": bars, "first": first, "rules": load_rules(), "day_rel": to_day_rel(*arrays, PER_DAY), "edges": edges})


def _run(job: tuple) -> tuple[str, dict, dict]:
    kind, seed = job
    rng = np.random.default_rng(seed)
    view = view_of(_STATE["bars"], _STATE["first"], null_days(_STATE["day_rel"], kind, rng, block=BLOCK_DAYS))
    return kind, midphase(view, _STATE["rules"]), spectrum(view, _STATE["edges"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    t0 = time.time()
    _init()
    bars, first, arrays, _ = load_market()
    view = View(bars, first, *arrays)
    btc_mid = midphase(view, _STATE["rules"])
    btc_spec = spectrum(view, _STATE["edges"])
    jobs = [(kind, np.random.SeedSequence([SEED, i, n]).generate_state(1)[0].item()) for i, kind in enumerate(KINDS) for n in range(args.paths)]
    mids: dict[str, list[dict]] = {k: [] for k in KINDS}
    specs: dict[str, list[dict]] = {k: [] for k in KINDS}
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init) as pool:
        for done, (kind, a, b) in enumerate(pool.map(_run, jobs, chunksize=8)):
            mids[kind].append(a)
            specs[kind].append(b)
            if (done + 1) % 400 == 0:
                print(f"{done + 1}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
    for name, btc, store in (("c2_midphase.csv", btc_mid, mids), ("c2_spectrum.csv", btc_spec, specs)):
        rows = []
        for key, value in sorted(btc.items()):
            row = {"metric": key, "btc": value}
            for kind in KINDS:
                vals = np.array([r.get(key, np.nan) for r in store[kind]], float)
                lo, mid, hi = q5_50_95(vals)
                row.update({f"{kind}_p5": lo, f"{kind}_median": mid, f"{kind}_p95": hi, f"{kind}_p2": min(1.0, 2 * min(mc_p_high(float(value), vals), mc_p_high(-float(value), -vals))) if np.isfinite(value) else float("nan")})
            rows.append(row)
        write_csv(name, rows)
    print(f"done {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
