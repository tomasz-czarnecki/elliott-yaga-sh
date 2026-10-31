"""Cycle marking: constraints, planted troughs, causality of the live layer, determinism of the zones."""
from __future__ import annotations

import json
import random
from math import exp, log, pi, sin

import pytest

from ewave.cycles.chain import best_chain, chain_between, swing_lows
from ewave.cycles.config import DAY_MS, load_rules
from ewave.cycles.cycle import LT, MT, RT, classify, make_cycle
from ewave.cycles.evaluate import null_path, path_metrics
from ewave.cycles.export import payload
from ewave.cycles.fouryear import completed_troughs, running_bear
from ewave.cycles.hindsight import build
from ewave.cycles.live import LiveEngine, replay
from ewave.cycles.series import Bars, to_ms
from ewave.cycles.zones import overlaps

RULES = load_rules()
START = to_ms("2013-03-04")  # a Monday, after stats_start
DAILY = RULES.levels["daily"]


def from_closes(closes: list[float], start: int = START, wick: float = 0.01) -> Bars:
    """Day bars around a close series: each opens at the previous close, wicks a little past both ends."""
    ts = [start + i * DAY_MS for i in range(len(closes))]
    opens = [closes[0], *closes[:-1]]
    highs = [max(o, c) * (1 + wick) for o, c in zip(opens, closes)]
    lows = [min(o, c) * (1 - wick) for o, c in zip(opens, closes)]
    return Bars(ts, opens, highs, lows, closes)


def seasonal(n: int, period: int, drift: float = 0.0, amp: float = 0.25, seed: int = 1) -> Bars:
    rng = random.Random(seed)
    closes = [100 * exp(drift * i + amp * sin(2 * pi * i / period - pi / 2) + rng.gauss(0, 0.004)) for i in range(n)]
    return from_closes(closes)


def noisy(n: int, seed: int = 3, vol: float = 0.03, drift: float = 0.0006, start: int = START) -> Bars:
    rng = random.Random(seed)
    closes, p = [], 100.0
    for _ in range(n):
        p *= exp(rng.gauss(drift, vol))
        closes.append(p)
    return from_closes(closes, start=start)


def planted_bears() -> tuple[Bars, list[int]]:
    """Three deep, long bears in an uptrend, each followed by a new high; the troughs are the answer."""
    log_path: list[float] = []
    level = log(100.0)
    troughs: list[int] = []
    for rise_days, rise, fall_days, fall in [(300, 2.0, 400, 1.6), (900, 3.5, 370, 1.5), (900, 3.0, 380, 1.4)]:
        for _ in range(rise_days):
            level += rise / rise_days
            log_path.append(level)
        for _ in range(fall_days):
            level -= fall / fall_days
            log_path.append(level)
        troughs.append(len(log_path) - 1)
    for _ in range(900):
        level += 3.0 / 900
        log_path.append(level)
    return from_closes([exp(x) for x in log_path], start=to_ms("2011-08-18"), wick=0.002), troughs


# --- the DP ---------------------------------------------------------------------------------------------------------

def test_dp_finds_planted_lows_and_respects_window():
    bars = seasonal(800, 60)
    lows = chain_between(bars, DAILY, RULES.dp, None, None, 0, len(bars) - 1)
    gaps = [b - a for a, b in zip(lows, lows[1:])]
    assert len(lows) >= 12
    assert all(DAILY.lo_tol <= g <= DAILY.hi_tol for g in gaps)
    troughs = [i for i in range(60, 780, 60)]
    assert all(any(abs(i - j) <= 6 for j in lows) for i in troughs)


def test_dp_fixed_ends_stay_in_the_chain():
    bars = seasonal(400, 60)
    lows = swing_lows(bars, DAILY.swing_k, 0, len(bars) - 1)
    a, b = lows[0], lows[-1]
    chain = chain_between(bars, DAILY, RULES.dp, a, b, a + 1, b - 1)
    assert chain[0] == a and chain[-1] == b and chain == sorted(set(chain))


@pytest.mark.parametrize("seed", range(5))
def test_dp_on_noise_keeps_gaps_near_the_window(seed):
    """Random data: the penalty is soft, so gaps may leave the window, but most stay in and order is strict."""
    bars = noisy(1500, seed=seed)
    lows = chain_between(bars, DAILY, RULES.dp, None, None, 0, len(bars) - 1)
    gaps = [b - a for a, b in zip(lows, lows[1:])]
    assert all(g > 0 for g in gaps)
    assert sum(DAILY.lo_tol <= g <= DAILY.hi_tol for g in gaps) / len(gaps) > 0.5


def test_dp_score_outside_window_costs_more():
    """A low the window forbids is taken only if it is worth the penalty."""
    closes = [100.0] * 200
    for centre, depth in ((60, 0.3), (75, 0.05), (120, 0.3)):
        for j in range(-5, 6):
            closes[centre + j] = min(closes[centre + j], 100 * exp(-depth * (1 - abs(j) / 6)))
    bars = from_closes(closes, wick=0.001)
    nodes = [60, 75, 120]
    chain = best_chain(bars, nodes, DAILY, RULES.dp, fixed_start=True, fixed_end=True, span_start=60, span_end=120)
    assert chain == [60, 120]


def test_hindsight_nests_levels():
    bars = planted_bears()[0]
    h = build(bars, RULES)
    weekly, daily = set(h.lows["weekly"]), set(h.lows["daily"])
    assert set(h.lows["fouryear"]) <= weekly
    assert weekly <= daily


# --- the 4-year detector --------------------------------------------------------------------------------------------

def test_fouryear_finds_planted_troughs():
    bars, troughs = planted_bears()
    found = [b.low_i for b in completed_troughs(bars, RULES.fouryear)]
    assert len(found) == 3
    assert all(abs(a - b) <= 1 for a, b in zip(found, troughs))


def test_fouryear_ignores_short_or_shallow_bears():
    cfg = RULES.fouryear
    shallow = from_closes([100 * exp(0.002 * i) for i in range(400)] + [222 * exp(-0.5 * i / 400) for i in range(400)]
                          + [135 * exp(0.005 * i) for i in range(400)])
    assert completed_troughs(shallow, cfg) == []
    short = from_closes([100 * exp(0.002 * i) for i in range(400)] + [222 * exp(-1.6 * i / 100) for i in range(100)]
                        + [45 * exp(0.005 * i) for i in range(500)])
    assert completed_troughs(short, cfg) == []


def test_fouryear_running_bear_is_not_a_low():
    bars, troughs = planted_bears()
    cut = bars.upto(troughs[-1] + 30)
    found = completed_troughs(cut, RULES.fouryear)
    assert len(found) == 2
    assert running_bear(cut).low_i == troughs[-1]


# --- cycle measurements ---------------------------------------------------------------------------------------------

def test_translation_bands():
    band = RULES.cycle["mid_band"]
    assert classify(0.2, band) == LT
    assert classify(0.5, band) == MT
    assert classify(0.8, band) == RT


def test_cycle_failed_and_hcl():
    closes = [100, 110, 120, 110, 95, 90, 100, 112, 105, 80, 85, 90]
    bars = from_closes([float(x) for x in closes], wick=0.0)
    c = make_cycle("daily", bars, 0, 9, RULES)
    assert c.failed and c.failed_ts == bars.ts[4]
    assert c.top_price == 120.0 and c.translation == LT
    assert c.lower_end and c.drop_log == pytest.approx(log(120 / 80))


# --- causality ------------------------------------------------------------------------------------------------------

def _bars_for_causality() -> Bars:
    return noisy(1400, seed=11, start=to_ms("2013-03-04"))


def _jsonable(state: dict) -> str:
    return json.dumps(state, sort_keys=True)


@pytest.mark.parametrize("seed", [11, 12])
def test_live_state_at_t_equals_truncated_run(seed):
    """The state reached while walking forward through all bars equals a fresh run on the bars up to t."""
    bars = noisy(1400, seed=seed)
    engine = LiveEngine(RULES)
    checks = set(random.Random(seed).sample(range(60, len(bars)), 60)) | {len(bars) - 1}
    for t in range(len(bars)):
        engine.step(bars.ts[t], bars.open[t], bars.high[t], bars.low[t], bars.close[t])
        if t in checks:
            fresh = replay(bars.upto(t + 1), RULES)
            assert _jsonable(fresh.state()) == _jsonable(engine.state()), f"state differs at bar {t}"
            assert _jsonable(fresh.zones()) == _jsonable(engine.zones()), f"zones differ at bar {t}"


def test_live_state_ignores_a_changed_future():
    """Rewrite everything after t: nothing known at t may change."""
    bars = _bars_for_causality()
    t = 900
    other = noisy(len(bars) - t - 1, seed=99, start=bars.ts[t + 1], vol=0.08)
    changed = Bars(bars.ts[:t + 1] + other.ts, bars.open[:t + 1] + other.open, bars.high[:t + 1] + other.high,
                   bars.low[:t + 1] + other.low, bars.close[:t + 1] + other.close)
    a, b = LiveEngine(RULES), LiveEngine(RULES)
    for i in range(t + 1):
        a.step(bars.ts[i], bars.open[i], bars.high[i], bars.low[i], bars.close[i])
        b.step(changed.ts[i], changed.open[i], changed.high[i], changed.low[i], changed.close[i])
    assert _jsonable(a.state()) == _jsonable(b.state())
    assert _jsonable(a.zones()) == _jsonable(b.zones())


def test_confirmed_low_is_only_known_after_its_signal():
    bars = noisy(2500, seed=5, drift=0.001)
    e = replay(bars, RULES)
    for machine in (e.daily, e.weekly, e.fouryear):
        for low in machine.log:
            assert low.ts_confirmed >= low.ts_signal_bar + DAY_MS  # the signal bar has closed
            assert low.ts_confirmed > low.ts_low + DAY_MS - 1
            assert low.ts_signal_bar > low.ts_low or machine is not e.daily
    assert e.daily.log and e.weekly.log


def test_a_low_never_confirms_on_its_own_bar():
    """A huge wick whose close is far above the SMA: the signal must still come from a later bar."""
    closes = [200 * exp(-0.01 * i) for i in range(121)]
    bars = from_closes(closes, wick=0.002)
    ts = bars.ts + [bars.ts[-1] + (i + 1) * DAY_MS for i in range(31)]
    o = bars.open + [closes[-1]] + [closes[-1] * 1.3] * 30
    h = bars.high + [closes[-1] * 1.3] + [closes[-1] * 1.31] * 30
    l = bars.low + [closes[-1] * 0.6] + [closes[-1] * 1.29] * 30
    c = closes + [closes[-1] * 1.3] * 31
    e = replay(Bars(ts, o, h, l, c), RULES)
    low = e.daily.log[0]
    assert low.i == 121 and low.price == pytest.approx(closes[-1] * 0.6)
    assert low.ts_signal_bar == low.ts_low + DAY_MS and low.ts_confirmed == low.ts_low + 2 * DAY_MS


def test_weekly_level_moves_only_when_a_week_closes():
    bars = noisy(800, seed=7)
    e = replay(bars, RULES)
    for low in e.weekly.log:
        # A week closes on Sunday, so it is known at Monday 00:00 UTC.
        assert ((low.ts_confirmed // DAY_MS) + 3) % 7 == 0


def test_revised_low_stays_in_the_log():
    bars = noisy(2500, seed=5)
    e = replay(bars, RULES)
    revised = [x for x in e.daily.log if x.status == "revised"]
    assert revised and len(revised) == len(e.daily.revisions)
    chain = {id(x) for x in e.daily.chain}
    assert all(id(x) not in chain for x in revised)
    assert all(x.ts_revised >= x.ts_confirmed for x in revised)


def test_undercut_soon_revises_later_fails():
    """A low undercut within revise_days is revised; undercut later, it stands and its cycle has failed."""
    # Fall into a low at bar 120, rally, then fall back through it.
    def path(back_after: int) -> Bars:
        down = [200 * exp(-0.01 * i) for i in range(121)]
        up = [down[-1] * exp(0.01 * i) for i in range(1, back_after // 2 + 1)]
        fall = [up[-1] * exp(-0.03 * i) for i in range(1, 60)]
        return from_closes(down + up + fall, wick=0.002)

    level = RULES.levels["daily"]
    soon = replay(path(level.revise_days), RULES)
    assert any(x.status == "revised" and abs(x.i - 120) <= 3 for x in soon.daily.log)
    late = replay(path(level.revise_days * 3), RULES)
    low = next(x for x in late.daily.log if abs(x.i - 120) <= 3)
    assert low.status == "confirmed" and low.ts_undercut is not None


# --- zones and export -----------------------------------------------------------------------------------------------

def test_zones_are_deterministic():
    bars = noisy(2500, seed=21, drift=0.001)
    a, b = replay(bars, RULES).zones(), replay(bars, RULES).zones()
    assert a and _jsonable(a) == _jsonable(b)
    p1, p2 = payload(bars, RULES, 0), payload(bars, RULES, 0)
    assert json.dumps(p1) == json.dumps(p2)
    assert p1["rules_version"] == RULES.version


def test_zone_box_is_measured_and_sided():
    bars = noisy(3000, seed=23, drift=0.001)
    e = LiveEngine(RULES)
    seen = {"failed": 0, "rt": 0}
    for i in range(len(bars)):
        e.step(bars.ts[i], bars.open[i], bars.high[i], bars.low[i], bars.close[i])
        if i % 7 or i < 500:
            continue
        for z in e.zones():
            if z["level"] == "fouryear" or z["p_lo"] is None:
                continue
            assert z["t_from"] < z["t_to"]
            assert 0 < z["p_lo"] <= z["p_hi"]
            if z["failed"]:
                seen["failed"] += 1
                assert z["p_hi"] <= z["anchor_price"] + 1e-9
            elif z["translation"] == RT:
                seen["rt"] += 1
                assert z["p_lo"] >= z["anchor_price"] - 1e-9
    assert seen["failed"] and seen["rt"]


def test_overlaps_are_real_intersections():
    a = {"level": "daily", "t_from": 10, "t_to": 20}
    b = {"level": "weekly", "t_from": 15, "t_to": 40}
    c = {"level": "fouryear", "t_from": 30, "t_to": 50}
    assert overlaps([a, b, c]) == [{"levels": ["daily", "weekly"], "t_from": 15, "t_to": 20},
                                   {"levels": ["weekly", "fouryear"], "t_from": 30, "t_to": 40}]


def test_fouryear_zone_uses_measured_gaps():
    bars, troughs = planted_bears()
    cut = bars.upto(troughs[-1] + 950)
    falling = from_closes([cut.close[-1] * exp(-0.002 * i) for i in range(1, 101)], start=cut.ts[-1] + DAY_MS, wick=0.002)
    all_bars = Bars(cut.ts + falling.ts, cut.open + falling.open, cut.high + falling.high, cut.low + falling.low, cut.close + falling.close)
    e = replay(all_bars, RULES)
    z = next(x for x in e.zones() if x["level"] == "fouryear")
    assert z["n_bears"] == 3 and z["n_gaps"] == 2
    assert z["gaps_days"] == [troughs[1] - troughs[0], troughs[2] - troughs[1]] or abs(z["gaps_days"][0] - (troughs[1] - troughs[0])) <= 1
    assert z["p_lo"] < z["p_hi"] < z["ath_price"]


# --- null models ----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["shuffled", "block"])
def test_null_path_keeps_the_days_and_the_total_return(kind):
    bars = noisy(1000, seed=31)
    path = null_path(bars, 200, kind, 20, random.Random(1))
    assert path.ts == bars.ts and path.close[:200] == bars.close[:200]
    if kind == "shuffled":
        assert path.close[-1] == pytest.approx(bars.close[-1])
    assert all(path.low[i] <= min(path.open[i], path.close[i]) + 1e-9 for i in range(len(path)))
    assert all(path.high[i] >= max(path.open[i], path.close[i]) - 1e-9 for i in range(len(path)))


def test_null_paths_are_reproducible_and_run_through_the_pipeline():
    bars = noisy(2000, seed=33, drift=0.001)
    a = path_metrics(null_path(bars, 100, "block", 20, random.Random(5)), RULES)
    b = path_metrics(null_path(bars, 100, "block", 20, random.Random(5)), RULES)
    assert a == b
    assert a["daily.hind.n"] > 0
