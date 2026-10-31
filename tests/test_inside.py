"""Round 4: what is inside a wave is a rule. A wave that is readable and does not admit its form kills the count; a wave too
short to read, or a 3 and a 5 too close to tell, is held; a running wave is never killed; the search goes down the frames before
judging; a verdict reads no later bars and comes back the same from the cache. The time minimum only ranks. No network, no real
data."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ewave.counts.export import payload, verdict_word
from ewave.counts.frames import LOW_FIRST, HIGH_FIRST, TF_MS, Frame, Frames
from ewave.counts.inside import EITHER, FAIL, FIVE, HOLD, PASS, RUNNING, THREE, THREES, Cache, Insides, closed_at, form_of, open_cache
from ewave.counts.nest import Builder
from ewave.counts.pivots import Pivot, locate
from ewave.counts.report import render
from ewave.counts.rules import COMBO, ED, FLAT, IMPULSE, LD, TRIANGLE, WAVES, ZIGZAG, Checker
from ewave.counts.state import Count, describe

from .test_counts import CFG, DAY, JUDGE, START, frames_from, from_polyline, pts, random_frames, resample

FOUR_H = TF_MS["4h"]
Q = TF_MS["15m"]
W3 = ("impulse",)
ABOVE = (ZIGZAG, FLAT, COMBO)


def reader(fr: Frames, cfg=CFG, cache: Cache | None = None) -> Insides:
    fr.wire_time(cfg.frames)
    return Insides(fr, cfg, JUDGE, cache)


def on(fr: Frames, prices: list[float], bars: list[int], tf: str = "4h") -> list[Pivot]:
    """The corners of a polyline as pivots on a frame, each on the bar that holds it."""
    f = fr[tf]
    fine = fr["15m"]
    out, at = [], 0
    for n, price in enumerate(prices):
        kind = ("L" if price < prices[n + 1] else "H") if n < len(prices) - 1 else ("L" if price < prices[n - 1] else "H")
        i = min(at, len(fine.ts) - 1)
        side = fine.low if kind == "L" else fine.high
        best = min(range(max(0, i - 1), min(len(fine.ts), i + 2)), key=lambda t: abs(side[t] - price))
        ts = f.ts[f.bar_at(fine.ts[best])]
        bar = f.bar_at(ts)
        p = f.low[bar] if kind == "L" else f.high[bar]
        out.append(Pivot(ts, kind, p, ts + f.tf_ms))
        if n < len(bars):
            at += bars[n]
    return out


# An impulse whose W3 is a clear 3 (up, down, up, each straight), with plain legs around it.
CLEAR_THREE = ([100.0, 120.0, 110.0, 150.0, 138.0, 180.0, 170.0, 200.0], [96, 48, 96, 48, 96, 48, 96])
# A wave whose small corrections stay under every threshold on 4H and show on 1H and 15m.
HIDDEN_FIVE = ([100.0, 120.0, 118.2, 150.0, 147.8, 170.0], [160, 4, 200, 4, 140])


def minute_bars(closes: list[float], start: int = START) -> Frame:
    """1m bars the way the collector stores them, indicators filled as `minute_loader` does."""
    ts, o, h, l, order = [], [], [], [], []
    prev = closes[0]
    for n, x in enumerate(closes):
        ts.append(start + n * 60_000)
        o.append(prev)
        h.append(max(prev, x) * 1.00002)
        l.append(min(prev, x) * 0.99998)
        order.append(LOW_FIRST if x >= prev else HIGH_FIRST)
        prev = x
    f = Frame("1m", ts, o, h, l, list(closes), order, [1.0] * len(closes))
    f.indicators(14, 11)
    return f


def clear_three_frames() -> Frames:
    prices, bars = CLEAR_THREE
    return frames_from(from_polyline(prices, bars))


class TestTable:
    @pytest.mark.parametrize(("pattern", "wave", "want"), [
        (IMPULSE, "1", FIVE), (IMPULSE, "2", THREE), (IMPULSE, "3", FIVE), (IMPULSE, "4", THREE), (IMPULSE, "5", FIVE),
        (ZIGZAG, "A", FIVE), (ZIGZAG, "B", THREE), (ZIGZAG, "C", FIVE),
        (FLAT, "A", THREE), (FLAT, "B", THREE), (FLAT, "C", FIVE),
        (TRIANGLE, "A", THREE), (TRIANGLE, "E", THREE),
        (COMBO, "W", THREE), (COMBO, "X", THREE), (COMBO, "Y", THREE),
        (LD, "1", EITHER), (LD, "2", THREE), (LD, "3", EITHER), (ED, "1", THREE), (ED, "5", THREE),
    ])
    def test_every_wave_asks_for_what_the_book_says(self, pattern, wave, want):
        assert form_of(CFG.grammar[pattern][wave]) == want

    def test_w3_may_only_be_an_impulse(self):
        assert CFG.grammar[IMPULSE]["3"] == [IMPULSE]
        assert LD not in CFG.grammar[IMPULSE]["5"] and ED not in CFG.grammar[IMPULSE]["1"]
        assert LD not in CFG.grammar[ZIGZAG]["C"] and "triangle" not in CFG.grammar[IMPULSE]["2"]


class TestTheRule:
    def _w3(self):
        fr = clear_three_frames()
        prices, bars = CLEAR_THREE
        pv = on(fr, prices, bars)
        return fr, pv, Count("4h", IMPULSE, 1, ("0", "1", "2", "3", "4", "5"), (pv[0], pv[1], pv[2], pv[5], pv[6], pv[7]), 8.0)

    def test_a_w3_that_is_a_clear_3_fails(self):
        fr, pv, c = self._w3()
        v = reader(fr).check("4h", c.pts[2], c.pts[3], W3)
        assert v.state == FAIL and v.required == FIVE and v.found == THREE and "no legal impulse" in v.note

    def test_and_the_count_dies(self):
        fr, pv, c = self._w3()
        b = Builder(fr, CFG)
        st = describe(c, fr["4h"], CFG)
        assert b._read_insides([(c, st)], "4h") == []
        stat = b.inside_rule["4h"]
        assert stat["killed"] == stat["read"] == 1 and stat["by"] == {"W3 holds no 5": 1}

    def test_the_same_three_may_be_a_flat_or_zigzag_wave(self):
        """Nothing about those bars is wrong: a 3 is fine where the label allows one."""
        fr, pv, c = self._w3()
        assert reader(fr).check("4h", c.pts[2], c.pts[3], ABOVE).state in (PASS, HOLD)

    def test_a_textbook_impulse_passes_at_a_finer_frame_where_the_coarse_one_cannot_see_it(self):
        prices, bars = HIDDEN_FIVE
        fr = frames_from(from_polyline(prices, bars))
        pv = on(fr, prices, bars)
        ins = reader(fr)
        f = fr["4h"]
        a, b = locate(f, FOUR_H, pv[0]), locate(f, FOUR_H, pv[5])
        for k in CFG.inside["ks"]:
            got = closed_at(f, k, a, b, f.bar_at(b.ts))
            assert got is None or len(got) - 1 < 5, f"4H should not show it, threshold {k}"
        v = ins.check("4h", pv[0], pv[5], W3)
        assert v.state == PASS and v.pattern == IMPULSE and v.tf in ("1h", "15m") and v.required == v.found == FIVE

    def test_a_short_wave_is_held(self):
        prices, bars = [100.0, 104.0, 102.0, 106.0], [6, 2, 3]  # under the floor on every frame there is
        fr = frames_from(from_polyline([90.0, *prices, 100.0], [96, *bars, 96]))
        pv = on(fr, [90.0, *prices, 100.0], [96, *bars, 96], "15m")
        v = reader(fr).check("15m", pv[1], pv[4], W3)
        assert v.state == HOLD and v.found == "?" and "too short" in v.note

    def test_a_straight_leg_is_held(self):
        """One leg at every threshold on every frame: nothing says it is not a 5."""
        fr = frames_from(from_polyline([100.0, 200.0, 150.0], [400, 200]))
        pv = on(fr, [100.0, 200.0, 150.0], [400, 200])
        v = reader(fr).check("4h", pv[0], pv[1], W3)
        assert v.state == HOLD and "no structure" in v.note

    def test_one_minute_bars_read_what_15m_cannot(self):
        """Six 15m bars are under the floor. With the collector's minutes the same wave reads as a 5, and no later bar is asked for."""
        warm = [92.0 + 8.0 * t / 1440 for t in range(1440)]
        down = [100.0 - 3.0 * t / 60 for t in range(1, 61)]
        wave = [97.0 + 6.0 * t / 40 for t in range(1, 41)] + [103.0 - 1.5 * t / 10 for t in range(1, 11)] + [101.5 + 4.5 * t / 20 for t in range(1, 21)] \
            + [106.0 - 1.0 * t / 5 for t in range(1, 6)] + [105.0 + 3.0 * t / 14 for t in range(1, 15)]
        closes = [*warm, *down, *wave, *[108.0 - 0.002 * t for t in range(1, 1441)]]
        m = minute_bars(closes)
        fr = frames_from(resample(m, "15m"))
        f = fr["15m"]
        i, j = len(warm) + len(down) - 1, len(warm) + len(down) - 1 + len(wave)
        a = Pivot(f.ts[f.bar_at(m.ts[i])], "L", m.low[i], 0)
        b = Pivot(f.ts[f.bar_at(m.ts[j])], "H", max(m.high[i : j + 1]), 0)
        assert f.bar_at(b.ts) - f.bar_at(a.ts) < CFG.inside["min_bars"]
        none = reader(fr).check("15m", a, b, W3)
        assert none.state == HOLD and "too short" in none.note
        asked = []

        def load(start, end):
            asked.append(end)
            return minute_bars(closes[: (end - START) // 60_000])

        v = reader(Frames(fr.venue, fr.by_tf, fr.as_of_ms, load)).check("15m", a, b, W3)
        assert v.state == PASS and v.tf == "1m" and v.pattern == IMPULSE
        assert [round(p.price, 1) for p in v.count.pts] == [97.0, 103.0, 101.5, 106.0, 105.0, 108.0]
        assert asked and max(asked) <= b.ts + Q, "nothing past the wave's last bar is asked for"


class TestClearFive:
    def _leg(self):
        from .test_premise import ramp_five

        prices = [300.0, *ramp_five(100.0), 180.0]
        days = [20, 6, 3, 10, 3, 6, 6]
        fr = frames_from(from_polyline(prices, [d * 96 for d in days]))
        fr.wire_time(CFG.frames)
        f = fr["4h"]
        lo = f.bar_at(START + 20 * DAY)
        i = min(range(lo - 2, lo + 3), key=lambda t: f.low[t])
        j = max(range(i, len(f.high)), key=lambda t: f.high[t])
        return fr, Pivot(f.ts[i], "L", f.low[i], f.ts[i]), Pivot(f.ts[j], "H", f.high[j], f.ts[j])

    def test_the_margin_decides_between_clear_and_hold(self):
        """Inside the margin both are held (sec 0). Past it, a corrective label on a clear 5 dies: his words on r2's node."""
        fr, a, b = self._leg()
        ins = reader(fr)
        five, three = ins.best("4h", a, b, (IMPULSE,)), ins.best("4h", a, b, THREES)
        assert five is not None and three is not None
        gap = five[1].score - three[1].score
        assert gap > 0, "the planted five must read better as a 5"
        tight = reader(fr, CFG.replaced(inside={"clear_margin": gap / 2})).check("4h", a, b, ABOVE)
        wide = reader(fr, CFG.replaced(inside={"clear_margin": gap * 2})).check("4h", a, b, ABOVE)
        assert tight.state == FAIL and tight.found == FIVE and tight.pattern == IMPULSE
        assert wide.state == HOLD and wide.found == EITHER

    def test_the_same_leg_is_fine_where_a_5_belongs(self):
        fr, a, b = self._leg()
        v = reader(fr).check("4h", a, b, (IMPULSE, LD))
        assert v.state == PASS and v.pattern == IMPULSE

    def test_a_5_that_does_not_end_at_its_own_extreme_is_not_clear(self):
        """A truncation, or a wick past the end inside the wave: his macro W2 ends at 24,853 with 24,201 printed inside it."""
        prices = [100.0, 120.0, 110.0, 150.0, 130.0, 145.0, 120.0]
        fr = frames_from(from_polyline(prices, [96, 48, 96, 48, 96, 96]))
        pv = on(fr, prices, [96, 48, 96, 48, 96, 96])
        ins = reader(fr)
        assert ins._ends_short(Count("4h", IMPULSE, 1, tuple("012345"), tuple(pv[:6]), 4.0))
        clean = [100.0, 120.0, 110.0, 150.0, 130.0, 170.0, 120.0]
        fr2 = frames_from(from_polyline(clean, [96, 48, 96, 48, 96, 96]))
        assert not reader(fr2)._ends_short(Count("4h", IMPULSE, 1, tuple("012345"), tuple(on(fr2, clean, [96, 48, 96, 48, 96, 96])[:6]), 4.0))


class TestDepth:
    def test_a_5_whose_largest_wave_is_a_clear_3_does_not_count_at_depth_2(self):
        """FND-8, FND-9: labelling 1-5 on visible swings without checking inside is the beginner's error. Here the largest wave,
        105 to 170 or 135 to 170 however it is cut, is up, down, up and nothing else."""
        prices = [100.0, 110.0, 105.0, 135.0, 125.0, 160.0, 152.0, 158.0, 170.0]
        bars = [64, 32, 96, 48, 96, 32, 16, 32]
        fr = frames_from(from_polyline(prices, bars))
        pv = on(fr, prices, bars)
        assert reader(fr).check("4h", pv[0], pv[8], W3, depth=1).state == PASS
        two = reader(fr).check("4h", pv[0], pv[8], W3, depth=2)
        assert two.state == FAIL and two.found == THREE

    def test_a_clean_5_inside_a_5_passes_at_depth_2(self):
        prices = [100.0, 108.0, 104.0, 140.0, 125.0, 175.0, 168.0, 190.0]
        bars = [48, 24, 96, 48, 96, 24, 48]
        fr = frames_from(from_polyline(prices, bars))
        pv = on(fr, prices, bars)
        assert reader(fr).check("4h", pv[0], pv[7], W3, depth=2).state == PASS


class TestRunning:
    def test_a_running_wave_is_never_killed_by_its_inside(self):
        """The W3 that dies once finished, while it is still the running wave: provisional, held."""
        prices, bars = CLEAR_THREE
        fr = frames_from(from_polyline(prices[:6], bars[:5]))
        pv = on(fr, prices[:6], bars[:5])
        c = Count("4h", IMPULSE, 1, ("0", "1", "2"), (pv[0], pv[1], pv[2]), 8.0)
        st = describe(c, fr["4h"], CFG)
        assert st.wave == "3"
        b = Builder(fr, CFG)
        assert b._read_insides([(c, st)], "4h") == [(c, st)]
        rows = b.insides.checks(c, st)
        assert rows[-1].wave == "W3" and rows[-1].state == RUNNING
        assert "running" in verdict_word(rows[-1])
        assert all(v.state != FAIL for v in rows)


class TestCausal:
    def test_a_verdict_reads_nothing_after_the_waves_end(self):
        fr = random_frames(seed=11, days=60)
        b = Builder(fr, CFG)
        rows = b.root_candidates("1d") or b.child_candidates("4h", Pivot(fr["4h"].ts[20], "L", fr["4h"].low[20], fr["4h"].ts[21]), (IMPULSE, ZIGZAG, FLAT))
        seen = 0
        for c, _, _ in rows[:6]:
            for n, w in enumerate(WAVES[c.pattern][: c.done]):
                kinds = tuple(CFG.grammar[c.pattern][w])
                a, z = c.pts[n], c.pts[n + 1]
                full = Insides(fr, CFG, JUDGE).check(c.tf, a, z, kinds)
                cut = fr.upto(z.ts + TF_MS[c.tf])
                cut.wire_time(CFG.frames)
                short = Insides(cut, CFG, JUDGE).check(c.tf, a, z, kinds)
                assert (full.state, full.found, full.tf, full.k, full.pattern) == (short.state, short.found, short.tf, short.k, short.pattern)
                seen += 1
        assert seen

    def test_a_different_future_does_not_change_it(self):
        prices, bars = CLEAR_THREE
        one = frames_from(from_polyline(prices, bars))
        other = [*prices[:6], 120.0, 260.0]  # the same wave, then another path: 180 is a high in both
        two = frames_from(from_polyline(other, [*bars[:5], 200, 300]))
        pa, pb = on(one, prices, bars), on(two, other, [*bars[:5], 200, 300])
        a = reader(one).check("4h", pa[2], pa[5], W3)
        b = reader(two).check("4h", pb[2], pb[5], W3)
        assert (a.state, a.found, a.tf, a.k) == (b.state, b.found, b.tf, b.k)


def strip(obj: dict) -> dict:
    return {k: v for k, v in obj.items() if k != "generated_at_ms"}


class TestCache:
    def test_it_gives_identical_results_cold_warm_and_with_none(self, tmp_path):
        fr = random_frames(seed=3, days=90)
        plain = payload(fr, CFG, 1)
        path = tmp_path / "inside.sqlite"
        cold = Cache(path)
        first = payload(fr, CFG, 1, None, cold)
        assert cold.misses > 0 and cold.hits == 0 or cold.misses > cold.hits
        cold.close()
        warm = Cache(path)
        second = payload(fr, CFG, 1, None, warm)
        assert warm.misses == 0 and warm.hits > 0, "a second run reads nothing again"
        warm.close()
        assert json.dumps(strip(first), sort_keys=True) == json.dumps(strip(second), sort_keys=True) == json.dumps(strip(plain), sort_keys=True)

    def test_a_kept_verdict_comes_back_as_it_was(self, tmp_path):
        prices, bars = CLEAR_THREE
        fr = frames_from(from_polyline(prices, bars))
        pv = on(fr, prices, bars)
        path = tmp_path / "inside.sqlite"
        one = Cache(path)
        a = reader(fr, CFG, one).check("4h", pv[2], pv[5], W3)
        one.close()
        two = Cache(path)
        b = reader(fr, CFG, two).check("4h", pv[2], pv[5], W3)
        two.close()
        assert a == b and two.hits >= 1 and a.count == b.count

    def test_the_file_name_holds_rules_and_code_and_old_files_go(self, tmp_path):
        for n in range(5):
            (tmp_path / f"inside-old{n}.sqlite").write_bytes(b"")
        got = open_cache(CFG, tmp_path)
        assert CFG.digest in got.path.name
        assert len(list(tmp_path.glob("inside-*.sqlite"))) == 3
        got.close()

    def test_the_folder_is_ignored(self):
        root = Path(__file__).parent.parent
        assert ".cache/" in (root / ".gitignore").read_text()

    def test_a_damaged_file_is_read_again_not_a_crash(self, tmp_path):
        got = open_cache(CFG, tmp_path)
        path = got.path
        got.close()
        path.write_bytes(b"this is not a database, not even close" * 100)
        again = open_cache(CFG, tmp_path)
        assert again.get("nothing") is None
        again.close()


class TestOutput:
    def test_each_node_says_what_each_wave_holds_and_the_tree_how_many_died(self):
        obj = payload(random_frames(seed=3, days=90), CFG, 1)
        seen = 0
        for tree in obj["trees"].values():
            for lv in tree["levels"]:
                assert lv["stats"]["inside"] is None or {"read", "killed", "by"} <= set(lv["stats"]["inside"])
                for n in lv["nodes"]:
                    assert isinstance(n["inside_line"], str)
                    assert all(v["state"] != FAIL for v in n["inside_rule"]), "a kept count has no failing wave"
                    seen += len(n["inside_rule"])
        assert seen
        text = render(obj)
        assert "Inside rule, readings killed per frame:" in text and "inside rule:" in text

    @pytest.mark.parametrize(("state", "found", "tf", "want"), [
        (PASS, FIVE, "1h", "W1 5 ok (1H)"), (HOLD, "?", None, "W1 5 unreadable"), (HOLD, EITHER, "4h", "W1 3 or 5 held"), (RUNNING, "?", None, "W1 running"),
    ])
    def test_the_compact_words(self, state, found, tf, want):
        from ewave.counts.inside import Verdict

        assert verdict_word(Verdict("W1", FIVE, found, state, tf, 4.0, IMPULSE, "", "")) == want


class TestTimeMinimum:
    def test_it_is_no_rule(self):
        checker = Checker(CFG.rules)
        fast = {"0": (0, 100), "1": (10, 120), "2": (10.5, 108), "3": (40, 170), "4": (40.5, 150), "5": (70, 200)}
        assert not checker.violations(IMPULSE, 1, pts(fast))

    def test_it_ranks_graded_and_a_pass_says_nothing(self):
        spec = CFG.fit["items"]["min_time"]
        assert spec["credit"] == "penalty" and spec["w"] > 1
        fine = frames_from(from_polyline([100.0, 130.0, 118.0, 180.0, 160.0, 200.0], [96 * d for d in (10, 5, 20, 10, 10)]))
        fine.wire_time(CFG.frames)
        f = fine["15m"]

        def fit(w4_days: float):
            ts = [f.ts[0], f.ts[960], f.ts[1440], f.ts[3360]]
            kinds, prices = "LHLH", (100.0, 130.0, 118.0, 180.0)
            pv = [Pivot(t, k, p, t) for t, k, p in zip(ts, kinds, prices)]
            pv.append(Pivot(ts[3] + int(w4_days * DAY), "L", 160.0, ts[3]))
            return JUDGE._min_time(Count("15m", IMPULSE, 1, ("0", "1", "2", "3", "4"), tuple(pv), 4.0), f)

        ok, short, worse = fit(10), fit(2.5), fit(0.5)
        assert ok[1] == 1.0 and 0 < worse[1] < short[1] < 1
        assert "kills nothing" in short[2]
