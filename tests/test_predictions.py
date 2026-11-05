"""Round 6: predictions. A planted count projects at the stated ratios, a child's target outside its parent's box is ranked down and
kept, clusters merge and weigh, clarity tells a clean 3 from a barely-there one, an event needs N exports, the forward log dedupes,
scoring reads nothing before the as-of time and nothing the bar cannot say, and choosing a count moves nothing. No network, no real
data."""
from __future__ import annotations

import json
import re
from math import log
from pathlib import Path

import pytest

from ewave.counts import events as events_mod
from ewave.counts import forward as forward_mod
from ewave.counts.backtest import flip_after, resample_bars, weekly_dates
from ewave.counts.clarity import Clarities
from ewave.counts.clock import load_windows, tag
from ewave.counts.confluence import Source, cluster_of, clusters_payload, merge
from ewave.counts.export import payload
from ewave.counts.forward import NEITHER, OPEN, STOP, TARGET, append_log, brier, dedupe, resolve, resolved_rows, row_hash, walk_forward
from ewave.counts.frames import TF_MS, Frame, Frames
from ewave.counts.inside import Cache, FIVE, THREE
from ewave.counts.odds import rows_for
from ewave.counts.pivots import Pivot
from ewave.counts.project import AFTER_ROLE, BEYOND, INNER, INSIDE, LATE, NO_PARENT, ON_WAY, REMAINING, RUNNING, SHORT, Leg, Target, apply_nest, inner_legs, judge_target, own_legs
from ewave.counts.rules import COMBO, FLAT, IMPULSE, ZIGZAG
from ewave.counts.state import AFTER, Count, describe

from .test_counts import CFG, FIFTEEN, JUDGE, START, bars_from_closes, frames_from, from_polyline, random_frames
from .test_inside import on, reader

SPEC = CFG.projection
FOUR_H = TF_MS["4h"]
DAY = 86_400_000


def pivots(*rows) -> tuple[Pivot, ...]:
    """(bar index on the 15m frame, kind, price)"""
    return tuple(Pivot(START + i * FIFTEEN, k, p, START + (i + 1) * FIFTEEN) for i, k, p in rows)


def planted_zigzag() -> tuple[Frames, Count]:
    """A zigzag down, A and B printed, C just started: 100 to 80, back to 90, now 88."""
    fr = frames_from(from_polyline([100.0, 80.0, 90.0, 88.0], [96, 48, 8]))
    pts = pivots((0, "H", 100.0), (96, "L", 80.0), (144, "H", 90.0))
    return fr, Count("15m", ZIGZAG, -1, ("0", "A", "B"), pts, 8.0)


def legs_of(fr: Frames, c: Count, st, widen: float = 1.0) -> list[Leg]:
    return own_legs(c, st, fr[c.tf], CFG, fr.as_of_ms, fr.price, widen)


class TestProjection:
    def test_planted_zigzag_projects_c_at_the_stated_ratios(self):
        fr, c = planted_zigzag()
        st = describe(c, fr["15m"], CFG)
        legs = legs_of(fr, c, st)
        c_leg = legs[0]
        assert (c_leg.wave, c_leg.role, c_leg.d) == ("C", RUNNING, -1)
        # 15m is linear (rules: frames.15m.log_fib): C = B - k x |A|, k from levels.c_ext_zigzag
        want = {k: 90.0 - k * 20.0 for k in CFG.levels["c_ext_zigzag"]}
        got = {t.k: t.price for t in c_leg.targets}
        assert got == pytest.approx(want)
        # the most likely point is A = C (ZZ-G1), the box runs across all the levels, and the source is cited
        assert c_leg.p == pytest.approx(70.0)
        assert c_leg.p_lo == pytest.approx(want[1.618]) and c_leg.p_hi == pytest.approx(want[0.618])
        assert "ZZ-G1" in c_leg.src
        # time: Trend-Based Fib Time of A from B, 1.0 x A most likely (COR-4), window 0.618 to 1.0
        base = 96 * FIFTEEN
        start = START + 144 * FIFTEEN
        assert c_leg.t == start + base and c_leg.t_lo == start + int(0.618 * base) and c_leg.t_hi == start + base

    def test_one_step_after_it_is_secondary_and_says_so(self):
        fr, c = planted_zigzag()
        legs = legs_of(fr, c, describe(c, fr["15m"], CFG))
        assert [x.role for x in legs] == [RUNNING, AFTER_ROLE]
        after = legs[-1]
        assert after.d == 1 and after.wave == AFTER
        # retraced from the path's own end, not from the extreme so far: 0.618 and 1.0 of 0-C with C at 70
        assert after.p == pytest.approx(70.0 + 0.618 * 30.0)

    def test_the_move_after_is_never_the_main_plan_while_a_correction_runs(self):
        fr = frames_from(from_polyline([100.0, 70.0, 90.0, 88.0], [192, 192, 8]))
        pts = pivots((0, "H", 100.0), (192, "L", 70.0), (384, "H", 90.0))
        st = describe(Count("15m", COMBO, -1, ("0", "W", "X"), pts, 8.0), fr["15m"], CFG)
        assert not st.motive_running
        rows = rows_for(st, fr.price, 0.002, 150)
        assert [r.name for r in rows][:1] == ["leg"] and rows[0].d == -1

    def test_impulse_projects_what_is_left_of_it(self):
        fr = frames_from(from_polyline([100.0, 120.0, 110.0, 118.0], [96, 48, 16]))
        pts = pivots((0, "L", 100.0), (96, "H", 120.0), (144, "L", 110.0))
        c = Count("15m", IMPULSE, 1, ("0", "1", "2"), pts, 8.0)
        legs = legs_of(fr, c, describe(c, fr["15m"], CFG))
        assert [(x.wave, x.role) for x in legs] == [("3", RUNNING), ("4", REMAINING), ("5", REMAINING), (AFTER, AFTER_ROLE)]
        w3, w4, w5 = legs[0].p, legs[1].p, legs[2].p
        assert w3 == pytest.approx(110.0 + 1.618 * 20.0)                # IMP-F4
        assert w4 == pytest.approx(w3 - 0.382 * (w3 - 110.0))           # IMP-F2, on the projected W3
        assert w5 == pytest.approx(w4 + 20.0)                           # IMP-F6, W5 = W1
        assert legs[0].t < legs[1].t < legs[2].t < legs[3].t

    def test_a_level_a_rule_forbids_is_not_the_path(self):
        fr = frames_from(from_polyline([100.0, 120.0, 110.0, 150.0, 125.0], [96, 48, 96, 16]))
        pts = pivots((0, "L", 100.0), (96, "H", 120.0), (144, "L", 110.0), (240, "H", 150.0))
        c = Count("15m", IMPULSE, 1, ("0", "1", "2", "3"), pts, 8.0)
        st = describe(c, fr["15m"], CFG)
        leg = legs_of(fr, c, st)[0]
        # W4 at 0.5 of 2-3 would be 130 and legal; price at 125 is already past all of them: nothing ahead, so it reads as reached
        assert leg.wave == "4" and leg.reached

    def test_combination_y_runs_as_a_3_inside_and_lands_on_its_point(self):
        fr = frames_from(from_polyline([100.0, 70.0, 90.0, 88.0], [192, 192, 8]))
        pts = pivots((0, "H", 100.0), (192, "L", 70.0), (384, "H", 90.0))
        c = Count("15m", COMBO, -1, ("0", "W", "X"), pts, 8.0)
        st = describe(c, fr["15m"], CFG)
        legs = legs_of(fr, c, st)
        got = inner_legs(c, st, legs[0], "flat", fr["15m"], CFG, fr.as_of_ms, fr.price, st.start.t)
        assert [x.wave for x in got] == ["A", "B", "C"] and all(x.role == INNER for x in got)
        assert got[-1].p == pytest.approx(legs[0].p)
        assert got[0].d == -1 and got[1].d == 1 and got[2].d == -1
        # B retraces A by the template's 0.618 in log, against A measured from X
        a, b = log(got[0].p / 90.0), log(got[1].p / got[0].p)
        assert -b / a == pytest.approx(0.618, abs=0.02)
        assert got[0].t < got[1].t < got[2].t

    def test_a_low_clarity_count_draws_a_wider_box(self):
        fr, c = planted_zigzag()
        st = describe(c, fr["15m"], CFG)
        narrow, wide = legs_of(fr, c, st)[0], legs_of(fr, c, st, widen=2.0)[0]
        assert log(wide.p_hi / wide.p_lo) == pytest.approx(2 * log(narrow.p_hi / narrow.p_lo))
        assert wide.p == narrow.p  # the point does not move

    def test_projecting_does_not_read_the_bars(self):
        """Same labels and same price on another past: the path is the same. It is arithmetic on the labels."""
        fr, c = planted_zigzag()
        st = describe(c, fr["15m"], CFG)
        a = legs_of(fr, c, st)
        b = own_legs(c, st, fr["15m"], CFG, fr.as_of_ms, fr.price, 1.0)
        assert [(x.p, x.t) for x in a] == [(x.p, x.t) for x in b]


def parent_leg(start: float, lo: float, hi: float, d: int = -1, t_hi: int = 10_000) -> Leg:
    return Leg("Y", RUNNING, d, start, start, 0, lo, t_hi, lo, hi, 0, t_hi, [], [], "", "")


class TestNesting:
    def test_a_child_target_outside_the_parent_box_is_ranked_down_not_removed(self):
        env = parent_leg(100.0, 50.0, 60.0)
        child = Leg("C", RUNNING, -1, 100.0, 100.0, 0, 55.0, 100, 40.0, 75.0, 0, 100,
                    [Target(0.618, 75.0, "near, short"), Target(1.0, 55.0, "inside"), Target(1.618, 40.0, "past it")], [], "", "")
        status, f = apply_nest([child], [env], SPEC, 0)
        by = {t.pull: t for t in child.targets}
        assert len(child.targets) == 3  # none is removed
        assert by["inside"].status == INSIDE and by["inside"].nest_f == 1.0
        assert by["past it"].status == BEYOND and by["past it"].nest_f < 1.0
        assert by["near, short"].status == SHORT and by["near, short"].nest_f < 1.0
        assert child.targets[0].pull == "inside"  # ranked first
        assert (status, f) == (INSIDE, 1.0)

    def test_short_counts_only_for_the_level_that_would_end_the_child(self):
        env = parent_leg(100.0, 50.0, 60.0)
        assert judge_target(80.0, 5, env, True, SPEC, 0)[0] == SHORT
        assert judge_target(80.0, 5, env, False, SPEC, 0) == (ON_WAY, 1.0)

    def test_the_penalty_grows_with_distance_and_has_a_floor(self):
        env = parent_leg(100.0, 50.0, 60.0)
        near = judge_target(48.0, 5, env, True, SPEC, 0)[1]
        far = judge_target(30.0, 5, env, True, SPEC, 0)[1]
        floor = judge_target(1.0, 5, env, True, SPEC, 0)[1]
        assert 1.0 > near > far > floor == SPEC["nest_floor"]

    def test_landing_after_the_parent_window_is_outside_too(self):
        env = parent_leg(100.0, 50.0, 60.0, t_hi=1_000)
        status, f = judge_target(55.0, 1_400, env, True, SPEC, 0)
        assert status == LATE and f < 1.0

    def test_no_parent_no_penalty(self):
        child = Leg("C", RUNNING, -1, 100.0, 100.0, 0, 55.0, 100, 40.0, 75.0, 0, 100, [Target(1.0, 55.0, "x")], [], "", "")
        assert apply_nest([child], [], SPEC, 0) == (NO_PARENT, 1.0)

    def test_the_tree_keeps_a_penalised_child(self):
        obj = payload(random_frames(seed=5, days=90), CFG, 1)
        nodes = [n for lv in obj["trees"]["1d"]["levels"] for n in lv["nodes"]]
        assert nodes
        for n in nodes:
            assert n["projection"]["legs"]
            for leg in n["projection"]["legs"]:
                assert len(leg["targets"]) == len({(t["k"], t["pull"]) for t in leg["targets"]})
                assert all(0 < t["nest_f"] <= 1 for t in leg["targets"])


def src(price: float, weight: float, reading: str, node: str = "n", tf: str = "1h", role: str = "running") -> Source:
    return Source(price, weight, reading, node, tf, "x", "ret", role)


class TestClusters:
    def test_near_levels_merge_and_far_ones_do_not(self):
        got = merge([src(100.0, 0.5, "a"), src(100.3, 0.4, "b"), src(120.0, 0.6, "c")], 0.01)
        assert len(got) == 2
        two = next(c for c in got if c.readings == 2)
        assert two.lo == 100.0 and two.hi == 100.3 and two.weight == pytest.approx(0.9)

    def test_the_cluster_is_sorted_by_weight_and_its_center_leans_to_the_heavier_level(self):
        got = merge([src(100.0, 0.9, "a"), src(100.4, 0.1, "b"), src(120.0, 0.6, "c")], 0.01)
        assert got[0].weight == pytest.approx(1.0)
        assert 100.0 < got[0].center < 100.2

    def test_one_reading_counts_once_however_many_roots_show_it(self):
        got = merge([src(100.0, 0.5, "a", "1d.1.1"), src(100.1, 0.5, "a", "1d.2.1"), src(100.2, 0.3, "a", "1d.3.1")], 0.01)
        assert len(got) == 1 and got[0].readings == 1 and got[0].weight == pytest.approx(0.5)
        assert len(got[0].sources) == 3  # the panel still names each one

    def test_a_run_of_near_levels_does_not_chain_across_a_wide_range(self):
        prices = [100.0 * 1.006 ** i for i in range(20)]
        got = merge([src(p, 0.5, str(i)) for i, p in enumerate(prices)], 0.01)
        assert len(got) > 1
        assert all(log(c.hi / c.lo) <= 0.02 + 1e-9 for c in got)

    def test_distance_scales_with_volatility(self):
        spec = CFG.raw["clusters"]
        n = {"id": "1", "tf": "1h", "pattern": "zigzag", "dir": "up", "labels": [{"t": 1}], "pattern_name": "Zigzag", "fit": {"score": 0.5},
             "projection": {"legs": [{"role": "running", "name": "C", "targets": [{"p": 100.0, "reached": False, "nest_f": 1.0, "pull": "a", "status": ""}, {"p": 101.0, "reached": False, "nest_f": 1.0, "pull": "b", "status": ""}]}]}}
        calm = clusters_payload([n], 90.0, 0.005, spec)
        wild = clusters_payload([n], 90.0, 0.05, spec)
        assert len(calm["rows"]) == 2 and len(wild["rows"]) == 1

    def test_a_penalised_level_weighs_less_and_stays(self):
        spec = CFG.raw["clusters"]
        leg = {"role": "running", "name": "C", "targets": [{"p": 100.0, "reached": False, "nest_f": 0.25, "pull": "a", "status": BEYOND}, {"p": 80.0, "reached": False, "nest_f": 1.0, "pull": "b", "status": INSIDE}, {"p": 60.0, "reached": True, "nest_f": 1.0, "pull": "c", "status": INSIDE}]}
        n = {"id": "1", "tf": "1h", "pattern": "zigzag", "dir": "up", "labels": [{"t": 1}], "pattern_name": "Zigzag", "fit": {"score": 0.4}, "projection": {"legs": [leg]}}
        rows = clusters_payload([n], 90.0, 0.01, spec)["rows"]
        assert [r["p"] for r in rows] == [80.0, 100.0]  # the level already reached is gone, the penalised one is last and still there
        assert rows[1]["weight"] == pytest.approx(0.1)

    def test_the_move_after_counts_for_less(self):
        spec = CFG.raw["clusters"]
        target = {"p": 100.0, "reached": False, "nest_f": 1.0, "pull": "a", "status": ""}
        n = {"id": "1", "tf": "1h", "pattern": "zigzag", "dir": "up", "labels": [{"t": 1}], "pattern_name": "Zigzag", "fit": {"score": 0.4}, "projection": {"legs": [{"role": "after", "name": "after", "targets": [target]}]}}
        assert clusters_payload([n], 90.0, 0.01, spec)["rows"][0]["weight"] == pytest.approx(0.4 * spec["after_weight"])

    def test_a_target_finds_its_cluster(self):
        rows = [{"id": "m1", "lo": 100.0, "hi": 101.0}, {"id": "m2", "lo": 120.0, "hi": 120.0}]
        assert cluster_of(100.5, rows, 0.001)["id"] == "m1"
        assert cluster_of(120.1, rows, 0.01)["id"] == "m2"
        assert cluster_of(110.0, rows, 0.01) is None


class TestCacheLock:
    def test_a_locked_cache_file_does_not_stop_an_export(self, tmp_path):
        """The 15-minute export must survive another run holding the file: it carries on in memory."""
        path = tmp_path / "c.sqlite"
        first = Cache(path)
        first.put("k", {"a": 1})
        second = Cache(path)
        second.db.execute("PRAGMA busy_timeout = 1")
        second.put("k2", {"b": 2})  # the first run holds the write lock
        assert second.db is None and second.get("k2") is None
        second.commit()
        second.close()
        first.close()


class TestClarity:
    ABOVE = (ZIGZAG, FLAT, COMBO)

    def test_a_clean_3_scores_higher_than_one_found_only_at_the_finest_step(self):
        clean = frames_from(from_polyline([100.0, 130.0, 112.0, 145.0], [160, 80, 160]))
        faint = frames_from(from_polyline([100.0, 130.0, 129.4, 145.0], [190, 20, 190]))
        got = {}
        for name, fr in (("clean", clean), ("faint", faint)):
            ins = reader(fr)
            a, b = on(fr, [100.0, 145.0], [400])
            got[name] = Clarities(ins, CFG).grade("4h", a, b, self.ABOVE)
        assert got["clean"].required == THREE and got["clean"].rungs and got["faint"].rungs
        assert got["clean"].value > got["faint"].value
        assert got["clean"].share > got["faint"].share
        assert got["clean"].first is not None

    def test_a_straight_leg_counts_against_a_3_and_says_nothing_about_a_5(self):
        fr = frames_from(from_polyline([100.0, 145.0], [400]))
        ins = reader(fr)
        a, b = on(fr, [100.0, 145.0], [400])
        cl = Clarities(ins, CFG)
        three = cl.grade("4h", a, b, self.ABOVE)
        five = cl.grade("4h", a, b, (IMPULSE,))
        assert three.rungs > 0 and three.found == 0 and three.value == 0.0 and three.word == "very weak"
        assert five.required == FIVE and five.rungs == 0  # no rung sees anything but one leg: too short to say

    def test_low_clarity_ranks_and_never_kills(self):
        fr = frames_from(from_polyline([100.0, 130.0, 129.4, 145.0, 120.0, 118.0, 110.0], [190, 20, 190, 60, 8, 60]))
        ins = reader(fr)
        cl = Clarities(ins, CFG)
        pts = on(fr, [100.0, 145.0, 120.0], [400, 80])
        c = Count("4h", COMBO, 1, ("0", "W", "X"), tuple(pts), 8.0)
        rows = cl.count(c)
        assert rows
        item = cl.judge(c)
        assert item[0] == "clarity" and 0 <= item[1] <= 1
        assert CFG.fit["items"]["clarity"]["credit"] == "penalty"
        assert cl.widen([]) == 1.0
        assert cl.widen(rows) >= 1.0

    def test_grade_is_cached_with_the_verdicts_and_comes_back_the_same(self, tmp_path):
        fr = frames_from(from_polyline([100.0, 130.0, 112.0, 145.0], [160, 80, 160]))
        a, b = on(fr, [100.0, 145.0], [400])
        path = tmp_path / "c.sqlite"
        cold = Cache(path)
        first = Clarities(reader(fr, CFG, cold), CFG).grade("4h", a, b, self.ABOVE)
        cold.close()
        warm = Cache(path)
        second = Clarities(reader(fr, CFG, warm), CFG).grade("4h", a, b, self.ABOVE)
        assert first == second and warm.hits > 0
        warm.close()

    def test_a_grade_reads_nothing_after_the_wave(self):
        shared = from_polyline([100.0, 130.0, 112.0, 145.0, 135.0], [160, 80, 160, 48]).close
        a_path = shared + [135.0 + i * 0.5 for i in range(1, 80)]
        b_path = shared + [135.0 - i * 0.5 for i in range(1, 80)]
        fa, fb = frames_from(bars_from_closes(a_path)), frames_from(bars_from_closes(b_path))
        a, b = on(fa, [100.0, 145.0], [400])
        ga = Clarities(reader(fa), CFG).grade("4h", a, b, self.ABOVE)
        gb = Clarities(reader(fb), CFG).grade("4h", a, b, self.ABOVE)
        assert ga.rungs and (ga.rungs, ga.found, ga.opposite) == (gb.rungs, gb.found, gb.opposite)


def node(nid: str, tf: str, sig: int, inv: float, side: str, box=(90.0, 95.0), win: str = "early") -> dict:
    return {"id": nid, "tf": tf, "pattern": "zigzag", "dir": "down", "labels": [{"t": sig}], "short": f"Count {sig}", "invalidation": {"p": inv, "side": side}, "wave": {"name": "C"},
            "projection": {"legs": [{"targets": [{"p": box[0], "reached": False}, {"p": box[1], "reached": False}]}]},
            "window": {"status": win, "lo_str": "2026-01-01", "hi_str": "2026-02-01"}}


def export_of(as_of: int, top: int, digest: str = "d", bars=None, kept=None, clusters=None) -> dict:
    nodes = [node("1d.1", "4h", top, 120.0, "above")] + (kept or [])
    return {"as_of": as_of, "rules_digest": digest, "price": 100.0, "recent_bars": {"15m": bars if bars is not None else [[as_of - 900, 100, 101, 99, 100, 1]]},
            "trees": {"1d": {"levels": [{"tf": "4h", "nodes": nodes}], "clusters": {"rows": clusters or []}}}}


SPEC_EV = {**CFG.raw["events"], "confirm": {**CFG.raw["events"]["confirm"], "4h": 3}}


class TestEvents:
    def run(self, seq, folder):
        return [[e["kind"] for e in events_mod.run(obj, SPEC_EV, folder)] for obj in seq]

    def test_the_first_export_is_a_baseline(self, tmp_path):
        assert self.run([export_of(1000, 1)], tmp_path) == [[]]

    def test_a_new_top_needs_n_exports_in_a_row(self, tmp_path):
        seq = [export_of(1000, 1), export_of(2000, 2), export_of(3000, 2), export_of(4000, 2), export_of(5000, 2)]
        out = self.run(seq, tmp_path)
        assert out == [[], [], [], ["top"], []]

    def test_a_flicker_resets_the_count(self, tmp_path):
        seq = [export_of(1000, 1), export_of(2000, 2), export_of(3000, 2), export_of(4000, 1), export_of(5000, 2), export_of(6000, 2)]
        assert all(not x for x in self.run(seq, tmp_path))

    def test_another_challenger_starts_over(self, tmp_path):
        seq = [export_of(1000, 1), export_of(2000, 2), export_of(3000, 2), export_of(4000, 3), export_of(5000, 3)]
        assert all(not x for x in self.run(seq, tmp_path))

    def test_the_same_bar_exported_twice_counts_once(self, tmp_path):
        seq = [export_of(1000, 1), export_of(2000, 2), export_of(2000, 2), export_of(2000, 2)]
        assert all(not x for x in self.run(seq, tmp_path))

    def test_new_rules_start_a_new_baseline(self, tmp_path):
        seq = [export_of(1000, 1), export_of(2000, 2), export_of(3000, 2), export_of(4000, 2, digest="other")]
        assert all(not x for x in self.run(seq, tmp_path))

    def test_invalidation_crossed_between_exports_fires_once(self, tmp_path):
        a = export_of(1000, 1, kept=[node("1d.2", "1h", 9, 110.0, "above")])
        b = export_of(2000, 1, bars=[[1100, 100, 112, 99, 100, 1]], kept=[node("1d.2", "1h", 9, 110.0, "above")])
        c = export_of(3000, 1, bars=[[2100, 100, 113, 99, 100, 1]], kept=[node("1d.2", "1h", 9, 110.0, "above")])
        out = self.run([a, b, c], tmp_path)
        assert out[0] == [] and out[1] == ["invalid"] and "invalid" in out[1]
        assert out[2].count("invalid") <= 1

    def test_entering_a_box_fires_on_the_way_in(self, tmp_path):
        keep = [node("1d.2", "1h", 9, 80.0, "below", box=(101.0, 103.0))]
        a = export_of(1000, 1, kept=keep)
        b = export_of(2000, 1, bars=[[1100, 100, 102, 99, 100, 1]], kept=keep)
        c = export_of(3000, 1, bars=[[2100, 100, 102, 99, 100, 1]], kept=keep)
        d = export_of(4000, 1, bars=[[3100, 100, 100.5, 99, 100, 1]], kept=keep)
        e = export_of(5000, 1, bars=[[4100, 100, 102, 99, 100, 1]], kept=keep)
        assert self.run([a, b, c, d, e], tmp_path) == [[], ["box"], [], [], ["box"]]

    def test_a_window_opening_and_closing(self, tmp_path):
        mk = lambda w: [node("1d.2", "1h", 9, 80.0, "below", box=(200.0, 210.0), win=w)]
        out = self.run([export_of(1000, 1, kept=mk("early")), export_of(2000, 1, kept=mk("inside")), export_of(3000, 1, kept=mk("past"))], tmp_path)
        assert out == [[], ["window"], ["window"]]

    def test_new_prints_once_and_marks_seen(self, tmp_path):
        self.run([export_of(1000, 1), export_of(2000, 2), export_of(3000, 2), export_of(4000, 2)], tmp_path)
        first = events_mod.read_new(tmp_path)
        assert len(first) == 1 and "top count changed" in first[0]["msg"]
        assert "\n" not in first[0]["msg"] and "\u2014" not in first[0]["msg"]
        assert events_mod.read_new(tmp_path) == []

    def test_a_damaged_state_file_is_a_new_baseline(self, tmp_path):
        (tmp_path / "state.json").write_text("{not json")
        assert self.run([export_of(1000, 1)], tmp_path) == [[]]


def row(**kw) -> dict:
    base = {"as_of_ms": START + 10 * FIFTEEN, "as_of": "x", "rules": "r", "root": "1d", "node": "n", "tf": "15m", "reading": "a", "title": "t", "pattern": "zigzag", "wave": "C", "kind": "leg", "d": "up", "price": 100.0,
            "target": 110.0, "pull": "p", "stop": 95.0, "stop_rule": "s", "win_lo": None, "win_hi": None, "h_bars": 100, "sigma": 0.01, "p_null": 0.3, "p_geo": 0.33, "p_win": None, "rr": 2.0, "fit": 0.5, "clarity": 0.5, "nest_f": 1.0, "magnet": 0}
    base.update(kw)
    base["hash"] = row_hash(base)
    return base


def path(closes: list[float]) -> Frame:
    return bars_from_closes(closes, START, wick=0.0)


class TestForward:
    def test_the_log_dedupes_by_content(self, tmp_path):
        p = tmp_path / "f.jsonl"
        assert append_log([row()], p) == 1
        assert append_log([row(as_of_ms=START + 99 * FIFTEEN, p_null=0.9, price=101.0)], p) == 0  # same prediction, later
        assert append_log([row(target=111.0)], p) == 1                                         # another target
        assert append_log([row(rules="other")], p) == 1                                        # another engine
        assert len(forward_mod.read_log(p)) == 3

    def test_one_run_with_the_same_row_twice_writes_one(self, tmp_path):
        p = tmp_path / "f.jsonl"
        assert append_log([row(), row(node="other")], p) == 1

    def test_a_line_cut_short_is_skipped(self, tmp_path):
        p = tmp_path / "f.jsonl"
        append_log([row()], p)
        with p.open("a") as fh:
            fh.write('{"hash":"cut')
        assert len(forward_mod.read_log(p)) == 1

    def test_nothing_before_the_as_of_time_counts(self):
        # target touched at bar 5, before the as-of time at bar 10; afterwards price only falls to the stop
        closes = [100.0] * 5 + [111.0] + [100.0] * 5 + [99.0, 97.0, 94.0] + [94.0] * 20
        assert resolve(row(), path(closes)).outcome == STOP

    def test_target_first_then_stop_is_a_hit(self):
        closes = [100.0] * 11 + [105.0, 111.0, 94.0] + [94.0] * 10
        o = resolve(row(), path(closes))
        assert o.outcome == TARGET and o.ts == START + 12 * FIFTEEN

    def test_one_bar_holding_both_goes_to_the_invalidation(self):
        fr = path([100.0] * 30)
        fr.high[12], fr.low[12] = 112.0, 94.0
        assert resolve(row(), fr).outcome == STOP

    def test_later_bars_do_not_change_a_resolved_row(self):
        a = path([100.0] * 11 + [111.0] + [50.0] * 30)
        b = path([100.0] * 11 + [111.0] + [500.0] * 30)
        assert resolve(row(), a) == resolve(row(), b)

    def test_open_until_the_horizon_has_passed(self):
        assert resolve(row(h_bars=100), path([100.0] * 40)).outcome == OPEN
        assert resolve(row(h_bars=5), path([100.0] * 40)).outcome == NEITHER

    def test_the_horizon_is_in_bars_of_the_rows_frame(self):
        # 2 bars of 4H are 32 bars of 15m: a target at bar 30 is inside it, at bar 50 it is not
        hit = [100.0] * 30 + [111.0] + [100.0] * 30
        late = [100.0] * 50 + [111.0] + [100.0] * 30
        assert resolve(row(tf="4h", h_bars=2), path(hit)).outcome == TARGET
        assert resolve(row(tf="4h", h_bars=2), path(late)).outcome == NEITHER

    def test_inside_the_window_or_not(self):
        closes = [100.0] * 20 + [111.0] + [100.0] * 20
        t = START + 20 * FIFTEEN
        assert resolve(row(win_lo=t - FIFTEEN, win_hi=t + FIFTEEN), path(closes)).in_window is True
        assert resolve(row(win_lo=t + FIFTEEN, win_hi=t + 9 * FIFTEEN), path(closes)).in_window is False

    def test_walk_forward_uses_only_what_had_resolved(self):
        rows = [{"as_of_ms": 0, "p_null": 0.3, "y": 1, "resolved_ms": 100}, {"as_of_ms": 50, "p_null": 0.3, "y": 1, "resolved_ms": 300}, {"as_of_ms": 200, "p_null": 0.3, "y": 0, "resolved_ms": 400}]
        got = walk_forward(rows, 20)
        assert got[0] == pytest.approx(0.3)      # nothing resolved yet
        assert got[1] == pytest.approx(0.3)      # the first row resolves at 100, this one was made at 50
        assert got[2] > 0.3                      # the first row is known at 200, the second is not

    def test_walk_forward_ignores_the_row_itself(self):
        a = [{"as_of_ms": 0, "p_null": 0.3, "y": 1, "resolved_ms": 10}]
        b = [{"as_of_ms": 0, "p_null": 0.3, "y": 0, "resolved_ms": 10}]
        assert walk_forward(a, 20) == walk_forward(b, 20)

    def test_no_edge_scores_like_the_null(self):
        rows = [{"as_of_ms": i, "p_null": 0.5, "y": i % 2, "resolved_ms": i + 0.5} for i in range(2000)]
        eng = walk_forward(rows, 20)
        ys = [r["y"] for r in rows]
        assert brier(eng, ys) == pytest.approx(brier([0.5] * 2000, ys), abs=0.001)

    def test_open_rows_are_left_out_of_the_score(self):
        rows = [row(h_bars=5), row(h_bars=100, target=111.0)]
        done, still = resolved_rows(rows, path([100.0] * 40))
        assert len(done) == 1 and still == 1 and done[0]["y"] == 0

    def test_a_row_says_what_it_needs_to_be_scored(self):
        fr, c = planted_zigzag()
        obj = payload(random_frames(seed=9, days=90), CFG, 1)
        rows = forward_mod.rows_of(obj, CFG.raw["forward"])
        assert rows
        for r in rows:
            assert r["hash"] and r["rules"] == CFG.version and 0 <= r["p_null"] <= 1
            sign = 1 if r["d"] == "up" else -1
            assert sign * (r["target"] - r["price"]) > 0 and sign * (r["stop"] - r["price"]) < 0
        assert {r["kind"] for r in rows} <= {"leg", "next", "likely"}


class TestControl:
    def test_flip_keeps_the_past_and_the_sizes(self):
        fr = random_frames(seed=4, days=30)
        at = fr["15m"].ts[1500]
        got = flip_after(fr, at, seed=1)
        f, g = fr["15m"], got["15m"]
        assert f.close[:1500] == g.close[:1500] and f.high[:1500] == g.high[:1500]
        assert g.close[1500:] != f.close[1500:]
        for i in range(1500, len(f.ts)):
            assert abs(log(g.close[i] / g.open[i])) == pytest.approx(abs(log(f.close[i] / f.open[i])), abs=1e-9)
            assert g.high[i] >= max(g.open[i], g.close[i]) - 1e-9 and g.low[i] <= min(g.open[i], g.close[i]) + 1e-9

    def test_two_seeds_two_paths_one_seed_one_path(self):
        fr = random_frames(seed=4, days=30)
        at = fr["15m"].ts[1500]
        assert flip_after(fr, at, 1)["15m"].close == flip_after(fr, at, 1)["15m"].close
        assert flip_after(fr, at, 1)["15m"].close != flip_after(fr, at, 2)["15m"].close

    def test_coarse_bars_are_rebuilt_from_the_flipped_ones(self):
        fr = random_frames(seed=4, days=30)
        got = flip_after(fr, fr["15m"].ts[1500], 3)
        again = resample_bars(got["15m"], "4h")
        assert got["4h"].high == again.high and got["4h"].close == again.close

    def test_weekly_dates(self):
        got = weekly_dates("2025-10-13", 1760918400000 + 86_400_000 * 10)
        assert got[:2] == ["2025-10-13", "2025-10-20"]


class TestClock:
    WINDOWS = [{"level": "fouryear", "name": "4-year", "lo": 1000 * 86400, "hi": 1010 * 86400, "lo_str": "a", "hi_str": "b", "spacing": {"lo": 1002 * 86400, "hi": 1004 * 86400, "lo_str": "c", "hi_str": "d"}}]

    def test_a_wave_down_ending_in_the_low_window_agrees(self):
        assert tag({"lo": 1005 * 86400, "hi": 1020 * 86400}, "down", self.WINDOWS)[0]["state"] == "agrees"

    def test_a_wave_down_ending_after_it_conflicts_with_the_gap(self):
        got = tag({"lo": 1030 * 86400, "hi": 1040 * 86400}, "down", self.WINDOWS)[0]
        assert got["state"] == "conflicts" and got["gap_days"] == 20 and got["spacing_gap_days"] == 26

    def test_a_wave_up_due_to_end_in_the_low_window_conflicts(self):
        assert tag({"lo": 1005 * 86400, "hi": 1020 * 86400}, "up", self.WINDOWS)[0]["state"] == "conflicts"
        assert tag({"lo": 1030 * 86400, "hi": 1040 * 86400}, "up", self.WINDOWS)[0]["state"] == "no clash"

    def test_no_window_no_tag(self):
        assert tag(None, "down", self.WINDOWS) == []
        assert tag({"lo": 1, "hi": 2}, "down", None) == []

    def test_a_missing_file_is_not_an_error(self, tmp_path):
        assert load_windows(tmp_path / "nothing.json") is None
        (tmp_path / "bad.json").write_text("nope")
        assert load_windows(tmp_path / "bad.json") is None

    def test_a_tag_never_reaches_the_fit(self):
        items = CFG.fit["items"]
        assert not any("cycle" in k for k in items)


class TestChartRules:
    """His rule: choosing a count never moves the chart. Read off the code: the browser check is `tools/shots_counts_r6.mjs`."""
    JS = (Path(__file__).parent.parent / "site" / "counts.js").read_text()

    def body(self, name: str) -> str:
        m = re.search(rf"\n  function {name}\(", self.JS)
        rest = self.JS[m.end():]
        end = rest.index("\n  }\n")
        return rest[:end]

    def test_choosing_a_count_touches_neither_zoom_nor_timeframe(self):
        pick = self.body("pick")
        assert "zoomTo" not in pick and "setVisibleLogicalRange" not in pick and "state.tf" not in pick and "settleZoom" not in pick

    def test_the_price_scale_does_not_follow_the_count(self):
        m = re.search(r"autoscaleInfo\(from, to\) \{(.*?)\n    \}", self.JS, re.S)
        assert "selected()" not in m.group(1)

    def test_the_move_after_is_never_a_filled_box(self):
        m = re.search(r"drawBoxes\(c, n, active, hr, vr\) \{(.*?)\n    \}\n", self.JS, re.S)
        assert re.search(r"else rect\(leg, body, 0, ", m.group(1))
        assert "node.next.targets" not in self.JS
