"""Round 3: his premise fixes the root, rules kill and guidelines rank, a fast market softens time with the book as its
basis, what is inside a wave is read, and a triple combination exists. No network, no real data."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ewave.counts.enumerate import Scan
from ewave.counts.export import payload
from ewave.counts.frames import TF_MS, Frame, stamp
from ewave.counts.gold import load_gold
from ewave.counts.inside import Insides
from ewave.counts.nest import Builder, _best_per_state, _without_open_twins
from ewave.counts.pivots import Pivot, zigzag
from ewave.counts.premise import BROKEN, DEAD, HOLDS, REVIEW, Mark, Premise, applies, given_on, load_premise, status
from ewave.counts.report import render
from ewave.counts.rules import CORRECTIVE, IMPULSE, TRIPLE, ZIGZAG, Checker
from ewave.counts.score import tf_move
from ewave.counts.state import AFTER, Count, describe

from .test_counts import CFG, DAY, JUDGE, START, day_frame, frames_from, from_polyline, judged, pts, random_frames, rules_broken

FIVE = [100.0, 160.0, 130.0, 300.0, 240.0, 400.0]
FIVE_DAYS = [30, 15, 60, 20, 40]


def premise_over(frames_start: int = START) -> Premise:
    marks, at = [], frames_start
    for n, price in enumerate(FIVE):
        marks.append(Mark(str(n), at, price, ()))
        if n < len(FIVE_DAYS):
            at += FIVE_DAYS[n] * DAY
    return Premise("premise-test", "Tomasz", "5 up ended 400 on a test day; counting the correction since", "above the 1D root", "test", tuple(marks), "abc")


def framed(after: list[float], days: list[int]):
    """His five, then this path after its top."""
    fine = from_polyline(FIVE + after, [d * 96 for d in FIVE_DAYS + days])
    return frames_from(fine)


CORRECTION = ([240.0, 300.0, 180.0, 260.0, 220.0], [40, 30, 60, 30, 10])


def exact_top(pm: Premise, fr) -> Premise:
    """The same premise with its top on the bars' own high: a test path's wick sits a hair above the polyline's corner."""
    f = fr["1h"]
    high = max(f.high[: f.bar_at(pm.top.ms) + 3])
    top = Mark(pm.top.label, pm.top.ms, high, ())
    return Premise(pm.version, pm.owner, pm.statement, pm.degree, pm.venue, (*pm.marks[:-1], top), pm.digest)


class TestPremiseFile:
    def test_his_file_loads_and_says_what_he_said(self):
        pm = load_premise()
        assert pm.owner == "Tomasz" and "126,150" in pm.statement and "2025-10-06" in pm.statement
        assert [m.label for m in pm.marks] == ["0", "1", "2", "3", "4", "5"]
        assert pm.origin.price == 15440.0 and pm.top.price == 126150.0
        assert stamp(pm.top.ms)[:10] == "2025-10-06"
        assert all(m.alts for m in pm.marks if m.label in "123") and pm.digest

    def test_switching_it_off_is_his_too(self, tmp_path):
        p = tmp_path / "premise.yaml"
        p.write_text(Path(__file__).parent.parent.joinpath("rules/premise.yaml").read_text().replace("active: true", "active: false"))
        assert load_premise(p) is None
        assert load_premise(tmp_path / "nothing.yaml") is None


class TestRoot:
    def test_it_counts_only_what_came_after_the_top(self):
        fr = framed(*CORRECTION)
        pm = premise_over()
        b = Builder(fr, CFG, pm)
        rows = b.root_candidates("1d")
        assert rows
        for c, st, fit in rows:
            assert c.pattern in CORRECTIVE and c.s == -1
            assert c.pts[0].price == 400.0 and c.pts[0].ts >= pm.top.ms - DAY
        tree = b.build("1d")
        assert 0 < len(tree.levels[0].nodes) <= CFG.tree["keep_root"]
        assert all(len(n.children) <= CFG.tree["keep_child"] for lv in tree.levels for n in lv.nodes)

    def test_without_it_the_root_is_searched_as_before(self):
        fr = framed(*CORRECTION)
        rows = Builder(fr, CFG).root_candidates("1d")
        assert any(c.pattern == IMPULSE and c.s > 0 for c, _, _ in rows) or any(c.pts[0].price != 400.0 for c, _, _ in rows)

    def test_a_run_cut_before_the_red_line_knows_nothing_of_it(self):
        fr = framed(*CORRECTION)
        pm = premise_over()
        assert applies(pm, fr)
        before = fr.upto(pm.top.ms - DAY)
        assert not applies(pm, before)
        assert Builder(before, CFG, pm).premise is None
        other = Premise(pm.version, pm.owner, pm.statement, pm.degree, "another_venue", pm.marks, pm.digest)
        assert not applies(other, fr)

    def test_a_finished_correction_under_the_minimum_of_the_five_ranks_lower_and_stays(self):
        """FIB-T3 is a strong guideline since r4: short means wrong pivots or unfinished, and it kills nothing."""
        fr = framed([240.0, 300.0, 200.0, 360.0], [10, 10, 15, 60])  # 35 days to the low, the five took 165
        rows = Builder(fr, CFG, premise_over()).root_candidates("1d")
        floor = CFG.time["minimum"]["share"] * 165 * DAY
        short = [(c, fit) for c, st, fit in rows if st.wave == AFTER and c.pts[-1].t - c.pts[0].t < floor]
        assert short, "it stays on the board"
        for c, fit in short:
            item = next(r for r in fit.reasons if r.item == "premise_time")
            assert item.f == 0.0 and "kills nothing" in item.note

    def test_the_correction_is_judged_against_the_five(self):
        fr = framed(*CORRECTION)
        pm = premise_over()
        g = given_on(pm, fr, "1d", CFG)
        f = fr["1d"]
        pivots, running = zigzag(f, 4.0, g.top)
        low = next(p for p in pivots if p.kind == "L")
        c = Count("1d", ZIGZAG, -1, ("0", "A", "B", "C"), (g.top, low, low, low), 4.0)
        items = {i: (x, n) for i, x, n in JUDGE.premise_items(c, describe(c, f, CFG), g.top, g.origin, f)}
        assert set(items) == {"premise_time", "premise_ret"}
        running_count = Count("1d", ZIGZAG, -1, ("0", "A"), (g.top, low), 4.0)
        got = {i for i, _, _ in JUDGE.premise_items(running_count, describe(running_count, f, CFG), g.top, g.origin, f)}
        assert got == {"premise_time"}

    def test_cutting_the_data_gives_the_same_tree(self):
        fr = framed(*CORRECTION)
        pm = premise_over()
        cut = fr.as_of_ms - 12 * DAY
        fine = fr["15m"].upto(cut)
        short = frames_from(Frame("15m", fine.ts, fine.open, fine.high, fine.low, fine.close, fine.order, fine.volume))
        strip = lambda o: json.dumps({k: v for k, v in o.items() if k in ("trees", "as_of", "price", "premise")}, sort_keys=True)
        assert strip(payload(fr.upto(cut), CFG, 1, pm)) == strip(payload(short, CFG, 1, pm))


class TestItsOwnLevels:
    def test_it_holds_under_the_top_and_over_the_origin(self):
        fr = framed(*CORRECTION)
        st = status(exact_top(premise_over(), fr), fr, CFG)
        assert st["state"] == HOLDS

    def test_below_the_origin_it_is_dead(self):
        """Sec 0, UNSPOKEN R1: a finished 5 back to its origin. The tree goes back to searching every root, and says so."""
        fr = framed([200.0, 300.0, 90.0, 120.0], [40, 30, 60, 30])
        pm = premise_over()
        assert status(pm, fr, CFG)["state"] == DEAD
        b = Builder(fr, CFG, pm)
        assert b.premise is None and b.premise_status["state"] == DEAD
        obj = payload(fr, CFG, 1, pm)
        assert obj["premise"]["applied"] is False and "origin" in obj["premise"]["status_note"]

    def test_a_new_high_is_only_a_review_while_under_the_flat_ceiling(self):
        """A B of an expanded flat, or an extended fifth. The readings that cannot survive it die by their own rules; a flat
        or a combination whose middle leg went past the origin stays."""
        fr = framed([280.0, 340.0, 300.0, 430.0, 380.0], [40, 30, 20, 40, 15])
        pm = premise_over()
        st = status(pm, fr, CFG)
        assert st["state"] == REVIEW and st["ceiling"] > st["high"] > 400.0
        b = Builder(fr, CFG, pm)
        assert b.premise is pm
        rows = b.root_candidates("1d")
        assert rows and all(c.pattern != ZIGZAG for c, _, _ in rows)
        assert any(c.done >= 1 for c, _, _ in rows)

    def test_past_the_flat_ceiling_it_is_broken(self):
        fr = framed([350.0, 700.0, 620.0], [20, 60, 15])
        pm = premise_over()
        assert status(pm, fr, CFG)["state"] == BROKEN
        assert Builder(fr, CFG, pm).premise is None

    def test_the_payload_carries_them(self):
        fr = framed(*CORRECTION)
        pm = exact_top(premise_over(), fr)
        obj = payload(fr, CFG, 1, pm)["premise"]
        assert obj["applied"] and obj["status"] == HOLDS and obj["owner"] == "Tomasz"
        assert obj["invalid_below"]["p"] == 100.0 and obj["review_above"]["p"] == pm.top.price and obj["broken_above"]["p"] > pm.top.price
        assert [x["k"] for x in obj["pulls"]] == CFG.levels["next_degree_ret"]
        assert obj["window"]["lo"] < obj["window"]["hi"] and obj["window"]["levels"]
        assert [x["l"] for x in obj["labels"]] == ["0", "1", "2", "3", "4", "5"]

    def test_it_heads_the_report(self):
        pm = premise_over()
        text = render(payload(framed(*CORRECTION), CFG, 1, pm))
        assert "Premise (Tomasz): " + pm.statement in text.splitlines()[1]

    def test_a_rule_his_labels_break_is_told_and_kills_nothing(self):
        """W4 of 5 days against a W3 of 60: under the minimum. It is his count: the tree still uses it, and says so."""
        marks, at = [], START
        days = [30, 15, 60, 5, 40]
        for n, price in enumerate(FIVE):
            marks.append(Mark(str(n), at, price, ()))
            at += days[n] * DAY if n < 5 else 0
        pm = Premise("p", "Tomasz", "s", "d", "test", tuple(marks), "x")
        fr = frames_from(from_polyline(FIVE + CORRECTION[0], [d * 96 for d in days + CORRECTION[1]]))
        obj = payload(fr, CFG, 1, pm)["premise"]
        assert obj["applied"] and not [v for row in obj["rule_notes"] for v in row["broken"]], "time is no hard rule since r4"
        assert any(n.startswith("W4") and "under the 0.25 minimum" in n for n in obj["time_notes"])
        assert Builder(fr, CFG, pm).root_candidates("1d")


class TestFastMarket:
    """Fib time is a convention the course itself softens: IMP-T1 "1.0 in a fast market", FIB-T1 "a violent move in price is
    paid for in sideways time", E5-5 a fifth "squeezes up fast". His own impulse needs this: a 6-day W5 against a 20-day W1."""
    PRICES = [100.0, 120.0, 110.0, 170.0, 150.0, 200.0]

    def test_a_fast_fifth_shorter_than_the_corrections_keeps_part_credit(self):
        *_, fast = judged(IMPULSE, 1, ("0", "1", "2", "3", "4", "5"), self.PRICES, [20, 10, 30, 12, 6], [190.0], [2])
        assert fast["w5_time"][0] == pytest.approx(CFG.time["fast"]["credit"]) and "E5-5" in fast["w5_time"][1]

    def test_a_slow_short_fifth_does_not(self):
        *_, slow = judged(IMPULSE, 1, ("0", "1", "2", "3", "4", "5"), [100.0, 120.0, 110.0, 170.0, 150.0, 151.0], [20, 10, 30, 12, 6], [150.5], [2])
        assert slow.get("w5_time", (1.0,))[0] < CFG.time["fast"]["credit"] or "w5_time" not in slow

    def test_a_fast_fifth_longer_than_a_correction_does_not(self):
        """E5-5's own limit: no more time than any correction before it."""
        *_, long_ = judged(IMPULSE, 1, ("0", "1", "2", "3", "4", "5"), self.PRICES, [20, 3, 30, 3, 6], [190.0], [2])
        assert long_["w5_time"][0] < CFG.time["fast"]["credit"]

    def test_a_vertical_w3_may_be_fast(self):
        *_, items = judged(IMPULSE, 1, ("0", "1", "2", "3"), [100.0, 110.0, 105.0, 200.0], [20, 5, 13], [190.0], [2])
        assert items["w3_time"][0] == pytest.approx(CFG.time["fast"]["credit"]) and "IMP-T1" in items["w3_time"][1]
        *_, slow = judged(IMPULSE, 1, ("0", "1", "2", "3"), [100.0, 130.0, 115.0, 135.0], [20, 5, 13], [130.0], [2])
        assert slow["w3_time"][0] < CFG.time["fast"]["credit"]

    def test_the_w4_after_it_may_be_long(self):
        """FIB-T1, on the variant of his count with 3 = Aug 28: W4 1.39 x W3 after a W3 at 2.7 x W1's speed."""
        *_, after_fast = judged(IMPULSE, 1, ("0", "1", "2", "3", "4"), [100.0, 110.0, 105.0, 200.0, 170.0], [20, 5, 13, 18], [180.0], [2])
        assert after_fast["w4_time"][0] == 1.0 and "FIB-T1" in after_fast["w4_time"][1]
        *_, past = judged(IMPULSE, 1, ("0", "1", "2", "3", "4"), [100.0, 110.0, 105.0, 200.0, 170.0], [20, 5, 13, 40], [180.0], [2])
        assert past["w4_time"][0] == 0.0
        *_, after_slow = judged(IMPULSE, 1, ("0", "1", "2", "3", "4"), [100.0, 130.0, 115.0, 150.0, 135.0], [20, 5, 13, 18], [140.0], [2])
        assert after_slow["w4_time"][0] < 1.0

    def test_fast_does_not_excuse_a_w2_that_outlasts_w1(self):
        """r1's 1d.1, W2 at 3.98 x W1: the book softens W3, W4 and W5 only, and he rejected this one."""
        *_, items = judged(IMPULSE, 1, ("0", "1", "2"), [100.0, 150.0, 120.0], [4, 16], [130.0], [1])
        assert items["w2_time"][0] == 0.0


class TestPivots:
    @pytest.mark.parametrize("k", [3.0, 5.0, 8.0])
    def test_each_pivot_is_the_real_extreme_of_its_leg(self, k):
        """A threshold that shrinks while price waits can confirm a swing long after the leg's real extreme. r2 then took the
        confirming bar's low as the start of the next leg's extreme: 62,676 for a low that was 62,505 two days before."""
        fr = random_frames(seed=9, days=200)
        f = fr["4h"]
        pivots, _ = zigzag(f, k)
        for a, b in zip(pivots, pivots[1:]):
            i, j = f.bar_at(a.ts), f.bar_at(b.ts)
            inner = range(i + 1, j)
            if b.kind == "L":
                assert all(f.low[t] >= b.price for t in inner)
            else:
                assert all(f.high[t] <= b.price for t in inner)


class TestTriple:
    GOOD = {"0": (0, 100), "W": (10, 80), "X": (20, 92), "Y": (40, 70), "X2": (50, 82), "Z": (70, 60)}

    def test_legal(self):
        assert not rules_broken(TRIPLE, -1, self.GOOD)

    def test_second_x_beyond_the_first(self):
        assert "W6_x2_beyond_x" in rules_broken(TRIPLE, -1, {**self.GOOD, "X2": (50, 95)})

    def test_second_x_under_the_minimum_time_is_no_rule_since_r4(self):
        assert not rules_broken(TRIPLE, -1, {**self.GOOD, "X2": (41, 82)})

    def test_it_only_shows_once_it_has_a_y(self):
        """Until then it is a double three, and the double three says it."""
        fine = from_polyline([100.0, 80.0, 92.0, 70.0, 82.0, 60.0, 66.0], [960] * 6)
        fr = frames_from(fine)
        f = fr["15m"]
        pivots, running = zigzag(f, 3.0)
        scan = Scan(f, 3.0, pivots, running, CFG)
        a = next(i for i, p in enumerate(pivots) if p.price >= 99.0 and p.kind == "H")
        rows = scan.counts_from(a, (TRIPLE,))
        assert rows and all(c.done >= 3 for c, _ in rows)

    def test_its_running_waves_have_levels_and_kills(self):
        _, f, pv = day_frame([100.0, 80.0, 92.0, 70.0, 82.0, 60.0, 66.0], [10, 10, 20, 10, 20, 3])
        for n, lab in ((3, "X2"), (4, "Z"), (5, AFTER)):
            c = Count("15m", TRIPLE, -1, ("0", "W", "X", "Y", "X2", "Z")[: n + 1], tuple(pv[: n + 1]), 3.0, pv[n + 1])
            st = describe(c, f, CFG)
            assert st.wave == lab and st.zone and st.kills
        items = {i for i, _, _ in JUDGE.shape(Count("15m", TRIPLE, -1, ("0", "W", "X", "Y"), tuple(pv[:4]), 3.0), f)}
        assert "triple_rare" in items


def ramp_five(lo: float = 100.0) -> list[float]:
    return [lo, lo * 1.3, lo * 1.15, lo * 1.9, lo * 1.65, lo * 2.3]


class TestInside:
    def _frames(self):
        prices = [300.0, *ramp_five(100.0)[0:], 180.0]
        days = [20, 6, 3, 10, 3, 6, 6]
        return frames_from(from_polyline(prices, [d * 96 for d in days]))

    def test_a_planted_five_is_read_inside_one_leg(self):
        fr = self._frames()
        fr.wire_time(CFG.frames)
        f = fr["4h"]
        lo = f.bar_at(START + 20 * DAY)
        hi = f.bar_at(START + 54 * DAY)
        i = min(range(lo - 2, lo + 3), key=lambda t: f.low[t])
        j = max(range(i, len(f.high)), key=lambda t: f.high[t])
        ins = Insides(fr, CFG, JUDGE)
        a, b = Pivot(f.ts[i], "L", f.low[i], f.ts[i]), Pivot(f.ts[j], "H", f.high[j], f.ts[j])
        got = ins.best("4h", a, b, (IMPULSE,))
        assert got is not None and got[0].labs == ("0", "1", "2", "3", "4", "5") and got[0].pts[-1].price == b.price

    def test_a_corrective_label_on_a_clear_five_loses_credit_and_a_motive_one_does_not(self):
        """His words on r2's node: "it is clearly 5 waves". A B may not be a 5; a zigzag's A must be."""
        fr = self._frames()
        fr.wire_time(CFG.frames)
        f = fr["4h"]
        lo = f.bar_at(START + 20 * DAY)
        i = min(range(lo - 2, lo + 3), key=lambda t: f.low[t])
        j = max(range(i, len(f.high)), key=lambda t: f.high[t])
        start = Pivot(f.ts[0], "H", 300.0, f.ts[1])
        low, high = Pivot(f.ts[i], "L", f.low[i], f.ts[i]), Pivot(f.ts[j], "H", f.high[j], f.ts[j])
        ins = Insides(fr, CFG, JUDGE)
        five = ins.best("4h", low, high, (IMPULSE,))
        three = ins.best("4h", low, high, ("zigzag", "flat", "combination"))
        as_b = {i: (x, n) for i, x, n in ins.judge_legs(Count("4h", ZIGZAG, -1, ("0", "A", "B"), (start, low, high), 8.0))}
        as_a = {i: (x, n) for i, x, n in ins.judge_legs(Count("4h", ZIGZAG, 1, ("0", "A"), (low, high), 8.0))}
        assert five is not None
        if three is None or five[1].score > three[1].score + CFG.fit["leg_form"]["margin"]:
            assert "inside_price" in as_a and as_a["leg_form"][0] == 1.0
            assert as_b["leg_form"][0] < 1.0 and "B reads as a 5" in as_b["leg_form"][1]

    def test_the_tree_carries_it(self):
        fr = random_frames(seed=3, days=90)
        obj = payload(fr, CFG, 1)
        for tree in obj["trees"].values():
            for lv in tree["levels"]:
                for n in lv["nodes"]:
                    assert isinstance(n["inside"], list) and isinstance(n["alike"], list)


class TestSmall:
    def test_a_finished_structure_is_measured_against_what_runs_now(self):
        """r2 measured a finished five by the wave after next: 60% away, "wrong frame", a false miss on every finished 5."""
        fr, f, pv = day_frame([100.0, 120.0, 110.0, 170.0, 150.0, 200.0, 180.0], [10, 5, 20, 5, 10, 3])
        fr.wire_time(CFG.frames)
        c = Count("4h", IMPULSE, 1, ("0", "1", "2", "3", "4", "5"), tuple(pv[:6]), 4.0, pv[6])
        st = describe(c, fr["4h"], CFG)
        got = tf_move("4h", st, 180.0, CFG)
        nearest = min(abs(lv.price / 180.0 - 1) for lv in st.zone if lv.price < 180.0)
        assert f"{nearest:.1%}" in got[2]

    def test_a_running_last_wave_gives_way_to_its_finished_twin(self):
        _, f, pv = day_frame([100.0, 120.0, 110.0, 170.0, 150.0, 200.0, 180.0], [10, 5, 20, 5, 10, 3])
        open_ = (Count("15m", IMPULSE, 1, ("0", "1", "2", "3", "4"), tuple(pv[:5]), 4.0, pv[5]), None, None)
        closed = (Count("15m", IMPULSE, 1, ("0", "1", "2", "3", "4", "5"), tuple(pv[:6]), 4.0, pv[6]), None, None)
        assert _without_open_twins([open_, closed]) == [closed]
        assert _without_open_twins([open_]) == [open_]  # past that pivot the finished one is dead, and this one is what is left

    def test_gold_file_loads_and_lists_both_variants(self):
        rows = {e.id: e for e in load_gold()}
        four = rows["4h-impulse-2026-07-to-09"]
        assert four.tf == "4h" and four.pattern == IMPULSE and four.s == 1
        assert len(list(four.variants())) == 4 and "5 waves" in four.note
        macro = rows["1d-impulse-2022-to-2025"]
        assert macro.tf == "1d" and len(list(macro.variants())) == 4 and macro.checks == ("kept", "inside")

    def test_no_em_dash_in_his_files(self):
        root = Path(__file__).parent.parent
        for name in ("rules/premise.yaml", "gold/counts.yaml", "rules/counts.yaml", "site/counts.js", "src/ewave/counts/premise.py", "src/ewave/counts/gold.py", "src/ewave/counts/inside.py", "src/ewave/counts/export.py", "src/ewave/counts/nest.py", "src/ewave/counts/score.py"):
            assert chr(0x2014) not in (root / name).read_text(), name
