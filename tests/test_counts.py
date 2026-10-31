"""Count board: the rule checker kills illegal counts, the enumerator finds planted patterns, nesting respects the
parent's running wave, nothing reads the future, and the same input gives the same output. No network, no real data."""
from __future__ import annotations

import json
import random
from math import exp, log

import pytest

from ewave.counts.config import load_config
from ewave.counts.enumerate import Scan, unbroken_anchors
from ewave.counts.export import default_path, payload
from ewave.counts.frames import HIGH_FIRST, LOW_FIRST, TF_MS, Frame, Frames, atr_log, from_lists, resample_12h, rsi, to_ms
from ewave.counts.nest import Builder
from ewave.counts.odds import barrier_prob, first_target, horizons, odds_row
from ewave.counts.pivots import Pivot, dated, locate, zigzag
from ewave.counts.rules import COMBO, ED, FLAT, IMPULSE, LD, TRIANGLE, ZIGZAG, Checker, Point
from ewave.counts.score import Judge, partner_filter
from ewave.counts.state import AFTER, Count, Kill, Level, advance, alive, crosshairs, describe

CFG = load_config()
CHECK = Checker(CFG.rules)
JUDGE = Judge(CFG)
START = to_ms("2024-01-01")
FIFTEEN = TF_MS["15m"]


def resample(fine: Frame, tf: str) -> Frame:
    """Coarser bars from finer ones, the way the collector builds them."""
    size = TF_MS[tf]
    out = Frame(tf, [], [], [], [], [], [], [])
    i, n = 0, len(fine.ts)
    while i < n:
        bucket = fine.ts[i] - fine.ts[i] % size
        j, hi, lo = i, i, i
        while j < n and fine.ts[j] < bucket + size:
            hi = j if fine.high[j] > fine.high[hi] else hi
            lo = j if fine.low[j] < fine.low[lo] else lo
            j += 1
        if bucket + size > fine.ts[-1] + fine.tf_ms:
            break
        order = HIGH_FIRST if hi < lo else LOW_FIRST if lo < hi else fine.order[hi]
        out.ts.append(bucket)
        out.open.append(fine.open[i])
        out.high.append(fine.high[hi])
        out.low.append(fine.low[lo])
        out.close.append(fine.close[j - 1])
        out.order.append(order)
        out.volume.append(sum(fine.volume[i:j]))
        i = j
    return out


def frames_from(fine: Frame, venue: str = "test") -> Frames:
    h1 = resample(fine, "1h")
    return from_lists(venue, {"15m": fine, "1h": h1, "4h": resample(fine, "4h"), "12h": resample_12h(h1), "1d": resample(fine, "1d")})


def bars_from_closes(closes: list[float], start: int = START, wick: float = 0.0005) -> Frame:
    ts, o, h, l, c, order, vol = [], [], [], [], [], [], []
    prev = closes[0]
    for i, x in enumerate(closes):
        up = x >= prev
        ts.append(start + i * FIFTEEN)
        o.append(prev)
        h.append(max(prev, x) * (1 + wick))
        l.append(min(prev, x) * (1 - wick))
        c.append(x)
        order.append(LOW_FIRST if up else HIGH_FIRST)
        vol.append(1.0)
        prev = x
    return Frame("15m", ts, o, h, l, c, order, vol)


def from_polyline(prices: list[float], bars_per_leg, start: int = START) -> Frame:
    """A path through these prices, log-linear in between. bars_per_leg: one number, or one per leg."""
    legs = len(prices) - 1
    counts = [bars_per_leg] * legs if isinstance(bars_per_leg, int) else bars_per_leg
    closes = [prices[0]]
    for a, b, n in zip(prices, prices[1:], counts):
        closes += [a * exp(log(b / a) * t / n) for t in range(1, n + 1)]
    return bars_from_closes(closes, start)


def random_frames(seed: int = 7, days: int = 150, vol: float = 0.004) -> Frames:
    rng = random.Random(seed)
    closes, p = [], 50_000.0
    for _ in range(days * 96):
        p *= exp(rng.gauss(0, vol))
        closes.append(p)
    return frames_from(bars_from_closes(closes))


def resolved(f: Frame, bars: float) -> Frame:
    """The same bars with a measuring candle of this many bars: only `resolution` is read from it."""
    class Measured(Frame):
        @property
        def resolution(self) -> float:
            return bars
    return Measured(f.tf, f.ts, f.open, f.high, f.low, f.close, f.order, f.volume)


def pts(labels: dict[str, tuple[float, float]]) -> dict[str, Point]:
    return {k: Point(*v) for k, v in labels.items()}


def rules_broken(pattern: str, s: int, labels: dict[str, tuple[float, float]]) -> set[str]:
    return {v.rule for v in CHECK.violations(pattern, s, pts(labels))}


GOOD_IMPULSE = {"0": (0, 100), "1": (10, 120), "2": (16, 108), "3": (40, 170), "4": (50, 150), "5": (70, 200)}


class TestRules:
    def test_textbook_impulse_is_legal(self):
        assert rules_broken(IMPULSE, 1, GOOD_IMPULSE) == set()

    @pytest.mark.parametrize(("change", "rule"), [
        ({"2": (16, 99)}, "I1_w2_beyond_start"),
        ({"4": (50, 118)}, "I4_w4_into_w1"),
        ({"1": (10, 150), "2": (16, 120), "3": (40, 151), "4": (50, 145), "5": (70, 200)}, "I3_w3_shortest"),
        ({"5": (70, 155)}, "I7_truncation_too_deep"),
    ])
    def test_impulse_breaks(self, change, rule):
        assert rule in rules_broken(IMPULSE, 1, {**GOOD_IMPULSE, **change})

    def test_w3_must_pass_w1(self):
        partial = {"0": (0, 100), "1": (10, 120), "2": (16, 108), "3": (40, 119)}
        assert "I2_w3_not_beyond_w1" in rules_broken(IMPULSE, 1, partial)

    def test_mirror_down(self):
        down = {k: (b, 40000 / p) for k, (b, p) in GOOD_IMPULSE.items()}
        assert rules_broken(IMPULSE, -1, down) == set()
        assert "I4_w4_into_w1" in rules_broken(IMPULSE, -1, {**down, "4": (50, 40000 / 118)})

    def test_labels_out_of_order(self):
        assert "S1_time_order" in rules_broken(IMPULSE, 1, {"0": (10, 100), "1": (5, 120)})
        assert "S2_wave_direction" in rules_broken(IMPULSE, 1, {"0": (0, 100), "1": (5, 90)})
        assert "S0_labels_skipped" in rules_broken(IMPULSE, 1, {"0": (0, 100), "2": (5, 90)})

    def test_zigzag(self):
        good = {"0": (0, 100), "A": (10, 80), "B": (20, 92), "C": (35, 70)}
        assert rules_broken(ZIGZAG, -1, good) == set()
        assert "Z1_b_beyond_start" in rules_broken(ZIGZAG, -1, {**good, "B": (20, 101)})
        assert "C2_c_short" in rules_broken(ZIGZAG, -1, {**good, "C": (35, 85)})

    def test_flat(self):
        good = {"0": (0, 100), "A": (10, 90), "B": (20, 99), "C": (35, 88)}
        assert rules_broken(FLAT, -1, good) == set()
        assert "F1_b_too_long" in rules_broken(FLAT, -1, {**good, "B": (20, 107)})
        assert "C2_c_short" in rules_broken(FLAT, -1, {**good, "C": (35, 95)})

    def test_diagonal(self):
        good = {"0": (0, 100), "1": (10, 130), "2": (16, 112), "3": (30, 135), "4": (36, 122), "5": (45, 140)}
        assert rules_broken(ED, 1, good) == set()
        assert "D4_w4_beyond_w2" in rules_broken(ED, 1, {**good, "4": (36, 111)})
        assert "D5_no_overlap" in rules_broken(ED, 1, {**good, "4": (36, 131)})
        assert "D6_shape" in rules_broken(ED, 1, {**good, "5": (45, 160)})
        assert "D8_ld_w5_not_past_w3" in rules_broken(LD, 1, {**good, "5": (45, 134)})

    def test_triangle(self):
        good = {"0": (0, 100), "A": (10, 80), "B": (20, 95), "C": (30, 83), "D": (40, 92), "E": (50, 86)}
        assert rules_broken(TRIANGLE, -1, good) == set()
        assert "T1_c_beyond_a" in rules_broken(TRIANGLE, -1, {**good, "C": (30, 79)})
        assert "T2_d_beyond_b" in rules_broken(TRIANGLE, -1, {**good, "D": (40, 96)})
        assert "T3_e_beyond_c" in rules_broken(TRIANGLE, -1, {**good, "E": (50, 82)})
        assert "T4_e_short" in rules_broken(TRIANGLE, -1, {**good, "E": (50, 91)})

    def test_combination(self):
        good = {"0": (0, 100), "W": (10, 80), "X": (20, 92), "Y": (35, 72)}
        assert rules_broken(COMBO, -1, good) == set()
        assert "W2_y_short" in rules_broken(COMBO, -1, {**good, "Y": (35, 85)})
        assert "W5_x_too_long" in rules_broken(COMBO, -1, {**good, "X": (20, 115)})


def scan_of(prices: list[float], bars_per_leg, k: float = 3.0) -> Scan:
    """A scan whose pivots are exactly the planted turning points; the last price is the running leg."""
    fine = from_polyline(prices, bars_per_leg)
    frames = frames_from(fine)
    f = frames["15m"]
    legs = len(prices) - 1
    counts = [bars_per_leg] * legs if isinstance(bars_per_leg, int) else bars_per_leg
    pivots, bar = [], 0
    for i in range(len(prices) - 1):
        kind = "L" if prices[i] < prices[i + 1] else "H"
        pivots.append(Pivot(f.ts[bar], kind, f.low[bar] if kind == "L" else f.high[bar], f.ts[min(bar + 2, len(f.ts) - 1)]))
        bar += counts[i]
    return Scan(f, k, pivots, None, CFG)


def found(scan: Scan, a: int, patterns: tuple[str, ...]) -> list[tuple[Count, object]]:
    return scan.counts_from(a, patterns)


class TestEnumerator:
    def test_finds_planted_impulse(self):
        # 5 waves up, then the correction after them is running
        scan = scan_of([100, 130, 112, 190, 165, 230, 215], [40, 20, 80, 30, 50, 10])
        got = found(scan, 0, (IMPULSE,))
        full = [c for c, st in got if c.done == 5 and st.wave == AFTER]
        assert full, "the planted five is not among the counts"
        assert [p.price for p in full[0].pts] == pytest.approx([p.price for p in scan.pivots[:6]])

    def test_illegal_impulse_is_not_found(self):
        # the planted "W4" dips into W1: no impulse may label those pivots as 1-2-3-4
        scan = scan_of([100, 130, 112, 190, 125, 230, 215], [40, 20, 80, 30, 50, 10])
        for c, st in found(scan, 0, (IMPULSE,)):
            if c.done >= 4:
                assert [p.ts for p in c.pts[:5]] != [p.ts for p in scan.pivots[:5]]

    def test_finds_planted_zigzag(self):
        scan = scan_of([100, 70, 88, 55, 62], [40, 25, 40, 10])
        got = found(scan, 0, (ZIGZAG,))
        assert any(c.done == 3 and st.wave == AFTER and c.s == -1 for c, st in got)

    def test_finds_planted_flats(self):
        regular = scan_of([100, 85, 99, 83, 90], [40, 30, 35, 10])
        assert any(c.done == 3 and st.wave == AFTER for c, st in found(regular, 0, (FLAT,)))
        expanded = scan_of([100, 85, 106, 78, 84], [40, 30, 35, 10])
        hit = [c for c, st in found(expanded, 0, (FLAT,)) if c.done == 3]
        assert hit, "an expanded flat, with B past the start, must be found"

    def test_b_at_the_ceiling_is_not_a_flat(self):
        scan = scan_of([100, 90, 118, 88, 95], [40, 30, 35, 10])
        assert not [c for c, st in found(scan, 0, (FLAT,)) if c.done >= 2]

    def test_killed_running_wave_is_dropped(self):
        # W4 is running and has gone below the end of W1
        scan = scan_of([100, 130, 112, 190, 150, 125], [40, 20, 80, 30, 30])
        for c, st in found(scan, 0, (IMPULSE,)):
            assert not (c.done == 3 and st.wave == "4" and st.start.price == pytest.approx(scan.pivots[3].price, rel=1e-3))

    def test_motive_wave_must_end_at_its_extreme(self):
        # a "5" whose inner high stands far above its end is not a truncation
        scan = scan_of([100, 110, 104, 180, 120, 130, 125], [20, 10, 40, 30, 10, 5])
        assert not scan.parse(IMPULSE, 0, 5)

    def test_running_wave_state(self):
        scan = scan_of([100, 130, 112, 190, 165], [40, 20, 80, 30])
        rows = {st.wave: (c, st) for c, st in found(scan, 0, (IMPULSE,))}
        c, st = rows["4"]
        assert st.d == -1 and st.invalidation.rule == "I4_w4_into_w1"
        assert st.invalidation.price == pytest.approx(c.pts[1].price)
        assert "triangle" in st.kinds
        rows2 = {st.wave: st for _, st in found(scan_of([100, 130, 112, 125], [40, 20, 30]), 0, (IMPULSE,))}
        assert "triangle" not in rows2["2"].kinds, "never in W2 (sec 3)"
        assert rows2["3"].kinds == ("impulse",), "W3 is an impulse (sec 1)"

    def test_a_limit_under_zero_is_no_kill(self):
        """A deep bear: W1 far longer than W3 puts the W3-shortest limit under zero, and a level there cannot be crossed."""
        f = from_polyline([1000, 300, 500, 200, 230, 180], 60)
        p = [Pivot(f.ts[60 * i], "H" if i % 2 == 0 else "L", x, f.ts[60 * i + 1]) for i, x in enumerate([1000, 300, 500, 200, 230])]
        fr = frames_from(f)
        st = describe(Count("15m", IMPULSE, -1, ("0", "1", "2", "3", "4"), tuple(p), 4.0), fr["15m"], CFG)
        assert st.wave == "5" and all(k.price > 0 for k in st.kills)

    def test_unbroken_anchors(self):
        scan = scan_of([100, 130, 90, 150, 120, 140], [30, 30, 30, 30, 30])
        got = unbroken_anchors(scan.f, scan.pivots, 0)
        assert 0 not in got and 2 in got and 3 in got


class TestPivots:
    def test_confirmation_comes_after_the_extreme(self):
        fr = random_frames()
        f = fr["1h"]
        pivots, running = zigzag(f, 4)
        assert pivots
        for p in pivots:
            assert p.conf_ts > p.ts
            assert p.price == (f.high[f.bar_at(p.ts)] if p.kind == "H" else f.low[f.bar_at(p.ts)])
        assert all(a.kind != b.kind for a, b in zip(pivots, pivots[1:]))
        assert running is not None

    def test_walk_forward_matches(self):
        """The pivots known at t are exactly the full run's pivots confirmed by t."""
        fr = random_frames()
        f = fr["1h"]
        full, _ = zigzag(f, 4)
        for cut in range(300, len(f.ts), 400):
            as_of = f.ts[cut - 1] + f.tf_ms
            part, _ = zigzag(f.upto(as_of), 4)
            assert part == [p for p in full if p.conf_ts <= as_of]

    def test_locate_keeps_the_price(self):
        fr = random_frames()
        d = fr["1d"]
        pivots, _ = zigzag(d, 2)
        for p in pivots:
            fine = locate(fr["1h"], d.tf_ms, p)
            assert fine.price == p.price
            assert p.ts <= fine.ts < p.ts + d.tf_ms
            i = fr["1h"].bar_at(fine.ts)
            assert (fr["1h"].high[i] if p.kind == "H" else fr["1h"].low[i]) == pytest.approx(p.price)


def walk(tree):
    for lv in tree.levels:
        yield from lv.nodes


@pytest.fixture(scope="module")
def built():
    fr = random_frames()
    return fr, {root: Builder(fr, CFG).build(root) for root in CFG.tree["roots"]}


class TestNesting:
    def test_tree_has_all_levels_within_limits(self, built):
        _, trees = built
        for root, tree in trees.items():
            assert [lv.tf for lv in tree.levels] == [root, "4h", "1h", "15m"]
            for lv, cap in zip(tree.levels, CFG.tree["max_nodes"]):
                assert len(lv.nodes) <= cap
            assert tree.levels[0].nodes, "no root counts"

    def test_child_respects_the_parent(self, built):
        fr, trees = built
        for tree in trees.values():
            for n in walk(tree):
                if n.parent is None:
                    continue
                p = n.parent
                # same start, same price, inside the parent's bar; same direction; a pattern the parent's wave allows
                start = n.count.pts[0]
                assert start.price == p.state.start.price
                assert p.state.start.ts <= start.ts < p.state.start.ts + TF_MS[p.tf]
                assert n.count.s == p.state.d
                allowed = set(p.state.kinds)
                assert n.count.pattern in allowed or n.count.done == 0

    def test_closed_child_hands_over_within_the_parent_rules(self):
        """A finished child ends the parent's running wave only where the parent's own rules allow it."""
        f = from_polyline([100, 130, 112, 190, 165, 175], [40, 20, 80, 30, 10])
        tf_ms = f.tf_ms
        p = [Pivot(f.ts[0], "L", 100.0, f.ts[1]), Pivot(f.ts[40], "H", 130.0, f.ts[41]), Pivot(f.ts[60], "L", 112.0, f.ts[61]), Pivot(f.ts[140], "H", 190.0, f.ts[141])]
        parent = Count("15m", IMPULSE, 1, ("0", "1", "2", "3"), tuple(p), 4.0)
        ok = advance(parent, Pivot(f.ts[170], "L", 165.0, f.ts[171]), CHECK, tf_ms)
        assert ok is not None and ok.labs[-1] == "4"
        assert advance(parent, Pivot(f.ts[170], "L", 125.0, f.ts[171]), CHECK, tf_ms) is None, "W4 into W1 territory"
        assert advance(parent, Pivot(f.ts[141], "L", 165.0, f.ts[142]), CHECK, tf_ms) is not None, "a W4 under the minimum time ranks lower, since r4"
        done = Count("15m", ZIGZAG, 1, ("0", "A", "B", "C"), tuple(p), 4.0)
        assert advance(done, Pivot(f.ts[170], "L", 165.0, f.ts[171]), CHECK, tf_ms) is None, "a finished parent has no next wave"

    def test_candidates_fill_only_what_the_parent_allows(self, built):
        fr, trees = built
        n = trees["1d"].levels[0].nodes[0]
        start = locate(fr["1h"], TF_MS[n.tf], n.state.start)
        got = Builder(fr, CFG).child_candidates("1h", start, (IMPULSE,))
        assert got and all(c.pattern == IMPULSE and c.pts[0].price == start.price and c.pts[0].ts == start.ts for c, _, _ in got)

    def test_parent_in_w4_means_a_correction_from_the_w3_end(self):
        """The brief's case: a parent in W4 of an up move makes the child a correction, down, that starts at the W3 end."""
        fine = from_polyline([100, 130, 112, 190, 170, 182, 165], [800, 400, 1600, 320, 200, 240])
        fr = frames_from(fine)
        f = fr["4h"]
        tops = zigzag(f, 3)[0]
        w3_end = max(tops, key=lambda p: p.price)
        kinds = tuple(CFG.grammar[IMPULSE]["4"])
        got = Builder(fr, CFG).child_candidates("1h", locate(fr["1h"], f.tf_ms, w3_end), kinds)
        assert got
        for c, st, _ in got:
            assert c.s == -1 and c.pts[0].price == w3_end.price and c.pattern in kinds

    def test_nodes_are_alive_and_report_what_was_asked(self, built):
        fr, trees = built
        for tree in trees.values():
            for n in walk(tree):
                assert alive(n.count, n.state, fr[n.tf]) is None
                assert 0.0 <= n.fit.score <= 1.0
                assert n.state.kills
                for o in n.odds:
                    assert 0.0 <= o.p_h <= 1.0 and o.p_h <= o.p_geo + 1e-9
                    assert o.rr >= 0 and (o.h_src == "window" or o.h_bars == CFG.frames[n.tf]["horizon_bars"])

    def test_shares_leave_room_for_other(self, built):
        _, trees = built
        for tree in trees.values():
            nodes = tree.levels[0].nodes
            assert sum(n.share for n in nodes) + tree.levels[0].crossroads["other_share"] == pytest.approx(1.0)
            assert tree.levels[0].crossroads["other_share"] >= CFG.fit["other_floor"]

    def test_labels_only_on_confirmed_pivots(self, built):
        fr, trees = built
        for tree in trees.values():
            for n in walk(tree):
                for pt in n.count.pts:
                    assert pt.conf_ts <= fr.as_of_ms


class TestCausality:
    def _json(self, fr: Frames) -> str:
        obj = payload(fr, CFG, 0)
        return json.dumps(obj, sort_keys=True)

    def test_truncated_data_gives_the_same_tree(self):
        """A run on data cut at t, a run on the walk-forward frames at t, and a run with the future rewritten must agree."""
        full = random_frames(seed=11)
        t = full["15m"].ts[9000] + FIFTEEN
        walk_forward = self._json(full.upto(t))

        fine = full["15m"]
        n = 9001
        only_past = Frame("15m", fine.ts[:n], fine.open[:n], fine.high[:n], fine.low[:n], fine.close[:n], fine.order[:n], fine.volume[:n])
        assert self._json(frames_from(only_past)) == walk_forward

        rng = random.Random(99)
        closes = fine.close[:n] + [fine.close[n - 1] * exp(0.002 * (i + 1) + rng.gauss(0, 0.01)) for i in range(len(fine.ts) - n)]
        rewritten = bars_from_closes(closes)
        # bars_from_closes rebuilds the wicks from the closes, so rebuild the past from them too
        same_past = bars_from_closes(closes[:n])
        assert self._json(frames_from(rewritten).upto(t)) == self._json(frames_from(same_past))

    def test_indicators_of_the_cut_equal_a_fresh_computation(self):
        full = random_frames(seed=5, days=40)
        f = full["1h"]
        cut = f.upto(f.ts[300] + f.tf_ms)
        assert cut.atr[14:] == atr_log(cut.high, cut.low, cut.close, 14)[14:]
        assert cut.rsi[12:] == rsi(cut.close, 11)[12:]

    def test_a_kill_shows_before_the_bar_closes(self):
        """The 1D frame's last bar is yesterday's, but a break today, on 15m bars, must already kill a 1D count."""
        fine = from_polyline([100, 130, 112, 190, 165, 120], [960, 480, 1920, 720, 90])
        fr = frames_from(fine)
        d = fr["1d"]
        assert d.tail_low < 125
        c = Count("1d", IMPULSE, 1, ("0", "1", "2", "3"),
                  (Pivot(d.ts[0], "L", d.low[0], d.ts[1]), Pivot(d.ts[10], "H", 130.0, d.ts[11]), Pivot(d.ts[15], "L", 112.0, d.ts[16]), Pivot(d.ts[35], "H", 190.0, d.ts[36])), 4.0)
        st = describe(c, d, CFG)
        assert alive(c, st, d) is not None


class TestDeterminism:
    def test_same_input_same_output(self):
        a = json.dumps(payload(random_frames(seed=3), CFG, 123), sort_keys=True)
        b = json.dumps(payload(random_frames(seed=3), CFG, 123), sort_keys=True)
        assert a == b

    def test_version_in_output_and_private_path(self):
        obj = payload(random_frames(seed=3, days=60), CFG, 1)
        assert obj["rules_version"] == CFG.version and obj["rules_digest"] == CFG.digest
        assert obj["format"] == "ewave-counts-4"
        parts = default_path().parts
        assert parts[-3:] == ("data", "local", "counts.json")
        assert "win chance" in obj["note"]

    def test_no_em_dash_anywhere(self):
        text = json.dumps(payload(random_frames(seed=3, days=60), CFG, 1), ensure_ascii=False)
        assert chr(0x2014) not in text


class TestOdds:
    def test_no_time_limit_is_geometry(self):
        assert barrier_prob(0.2, 1.0, 1e6) == pytest.approx(0.2, abs=1e-6)
        assert barrier_prob(0.5, 1.0, 1e6) == pytest.approx(0.5, abs=1e-6)

    def test_no_time_means_no_hit(self):
        assert barrier_prob(0.5, 1.0, 1e-6) == pytest.approx(0.0, abs=1e-3)

    def test_more_time_never_lowers_it(self):
        ps = [barrier_prob(0.3, 1.0, v) for v in (0.01, 0.05, 0.2, 1.0, 5.0)]
        assert ps == sorted(ps)

    def test_monte_carlo(self):
        rng = random.Random(1)
        x, a, sigma, steps = 0.03, 0.1, 0.002, 2000
        hits = 0
        paths = 1500
        for _ in range(paths):
            p = x
            for _ in range(steps):
                p += rng.gauss(0, sigma)
                if p <= 0:
                    break
                if p >= a:
                    hits += 1
                    break
        got = barrier_prob(x, a, sigma * sigma * steps)
        assert hits / paths == pytest.approx(got, abs=0.04)

    def test_row_needs_target_ahead_and_stop_behind(self):
        stop = Kill(90.0, -1, "r", "n")
        assert odds_row("leg", Level(1, 110.0, "x"), stop, 100.0, 1, 0.01, 100) is not None
        assert odds_row("leg", Level(1, 95.0, "x"), stop, 100.0, 1, 0.01, 100) is None
        assert odds_row("leg", Level(1, 110.0, "x"), Kill(101.0, -1, "r", "n"), 100.0, 1, 0.01, 100) is None
        row = odds_row("leg", Level(1, 120.0, "x"), stop, 100.0, 1, 0.01, 100)
        assert row.rr == pytest.approx(2.0)
        assert row.p_geo == pytest.approx(log(100 / 90) / log(120 / 90))

    def test_conservative_target_first(self):
        levels = [Level(1, 120.0, "a"), Level(2, 110.0, "b"), Level(3, 95.0, "c")]
        assert first_target(levels, 100.0, 1).price == 110.0
        assert first_target(levels, 100.0, -1).price == 95.0
        assert first_target(levels, 130.0, 1) is None
        assert first_target(levels, 100.0, 1, min_log=0.15).price == 120.0, "a level inside the noise is already there"


def test_resample_12h():
    fine = from_polyline([100, 120, 90, 110], 192)
    h1 = resample(fine, "1h")
    h12 = resample_12h(h1)
    assert all(t % TF_MS["12h"] == 0 for t in h12.ts)
    assert h12.high[0] == max(h1.high[:12]) and h12.low[0] == min(h1.low[:12])
    assert h12.open[0] == h1.open[0] and h12.close[0] == h1.close[11]
    # a period not yet over gives no bar
    cut = Frame("1h", h1.ts[:18], h1.open[:18], h1.high[:18], h1.low[:18], h1.close[:18], h1.order[:18], h1.volume[:18])
    assert len(resample_12h(cut)) == 1


# --- round 2: Fibonacci time ------------------------------------------------------------------------------------------

DAY = 86_400_000


def day_frame(prices: list[float], days: list[int]) -> tuple[Frames, Frame, list[Pivot]]:
    """A path through these prices with these leg lengths in days, and its pivots on the 15m frame, dated to the bar."""
    fine = from_polyline(prices, [d * 96 for d in days])
    fr = frames_from(fine)
    fr.wire_time(CFG.frames)
    f = fr["15m"]
    out, bar = [], 0
    for i, price in enumerate(prices):
        kind = ("L" if price < prices[i + 1] else "H") if i < len(prices) - 1 else ("L" if price < prices[i - 1] else "H")
        out.append(Pivot(f.ts[min(bar, len(f.ts) - 1)], kind, price, f.ts[min(bar + 2, len(f.ts) - 1)]))
        if i < len(days):
            bar += days[i] * 96
    return fr, f, out


def judged(pattern: str, s: int, labs: tuple[str, ...], prices: list[float], days: list[int], tail: list[float] | None = None, tail_days: list[int] | None = None):
    """A count over this path, with the path running on after its last label. What the judge said, by item."""
    fr, f, pv = day_frame(prices + (tail or []), days + (tail_days or []))
    c = Count("15m", pattern, s, labs, tuple(pv[: len(labs)]), 4.0, pv[len(labs)] if len(pv) > len(labs) else None)
    st = describe(c, f, CFG)
    items = {i: (g, note) for i, g, note in JUDGE.fit(c, st, f)}
    return c, st, f, items


class TestAxes:
    def test_every_item_has_an_axis(self):
        for name, spec in CFG.fit["items"].items():
            assert spec["axis"] in ("price", "time", "structure"), name

    def test_main_time_items_weigh_as_much_as_price_items(self):
        it = CFG.fit["items"]
        for name in ("w2_time", "w3_time", "w4_time", "w5_time", "ac_time"):
            assert it[name]["w"] == it["w2_ret"]["w"], name

    def test_a_clear_failure_on_one_axis_is_not_bought_back(self):
        """Perfect price and structure, time failed outright, against a count that is only middling on all three."""
        price = [("w2_ret", 1.0, ""), ("w3_ext", 1.0, ""), ("w4_ret", 1.0, ""), ("w5_ext", 1.0, ""), ("zz_b", 1.0, ""), ("zz_c", 1.0, "")]
        structure = [("subwaves", 1.0, ""), ("channel", 1.0, ""), ("line_24", 1.0, ""), ("anchor_major", 1.0, ""), ("tdi_35_div", 1.0, "")]
        fails = JUDGE.finish(price + structure + [("w3_time", 0.0, ""), ("w5_time", 0.0, ""), ("w2_time", 0.0, "")])
        middling = JUDGE.finish([(i, 0.6, n) for i, _, n in price] + [(i, 0.6, n) for i, _, n in structure]
                                + [("w3_time", 0.6, ""), ("w5_time", 0.6, ""), ("w2_time", 0.6, "")])
        assert fails.axes["price"] > middling.axes["price"] and fails.axes["time"] < 0.25
        assert fails.score < middling.score

    def test_fit_is_the_geometric_mean_of_the_axes(self):
        fit = JUDGE.finish([("w2_ret", 0.9, ""), ("w3_time", 0.5, ""), ("subwaves", 0.7, "")])
        assert fit.score == pytest.approx((fit.axes["price"] * fit.axes["time"] * fit.axes["structure"]) ** (1 / 3))

    def test_a_failed_check_costs_its_weight_and_caps_nothing(self):
        """Rules eliminate, guidelines rank (sec 0). r2 capped the axis at 0.2 here; one fast W5 could sink a textbook impulse."""
        passes = [(i, 1.0, "") for i in ("w3_time", "w5_time", "w4_time", "crosshair", "retrace_time")]
        clean = JUDGE.finish(passes)
        fit = JUDGE.finish([*passes, ("w2_time", 0.0, "")])
        weight = sum(CFG.fit["items"][i]["w"] for i, _, _ in passes)
        want = (weight + CFG.fit["evidence"] * CFG.fit["prior"]) / (weight + CFG.fit["items"]["w2_time"]["w"] + CFG.fit["evidence"])
        assert fit.axes["time"] == pytest.approx(want) and fit.axes["time"] < clean.axes["time"]
        assert fit.axes["time"] > 0.5 and fit.fails == ["w2_time"]

    def test_nothing_in_the_config_can_cap_a_count(self):
        assert "veto_cap" not in CFG.fit and not any("veto" in spec for spec in CFG.fit["items"].values())

    def test_little_to_judge_does_not_outrank_a_well_labelled_count(self):
        """R1's lesson: a passing "has not failed yet" is no evidence, and few items stay near the prior."""
        bare = JUDGE.finish([("running_depth", 1.0, ""), ("running_time", 1.0, ""), ("tf_move", 1.0, ""), ("corrective_tiebreak", 1.0, "")])
        full = JUDGE.finish([(i, 0.75, "") for i in ("w2_ret", "w3_ext", "w4_ret", "w5_ext", "w2_time", "w3_time", "w4_time", "w5_time", "subwaves", "channel", "line_24", "tdi_w3")])
        assert bare.score < full.score

    def test_penalty_and_bonus_items(self):
        assert JUDGE.finish([("running_time", 1.0, "")]).axes["time"] == pytest.approx(CFG.fit["prior"])
        assert JUDGE.finish([("running_time", 0.5, "")]).axes["time"] != pytest.approx(CFG.fit["prior"])
        assert JUDGE.finish([("crosshair", 0.0, "")]).axes["time"] == pytest.approx(CFG.fit["prior"])
        assert JUDGE.finish([("crosshair", 1.0, "")]).axes["time"] > CFG.fit["prior"]


class TestExactTime:
    def test_a_daily_pivot_is_dated_from_the_hour_that_holds_it(self):
        fr = random_frames(seed=11, days=120)
        fr.wire_time(CFG.frames)
        d = fr["1d"]
        pivots, _ = zigzag(d, 2)
        assert pivots
        for p in pivots:
            assert p.at is not None and p.ts <= p.at < p.ts + DAY
            i = fr["1h"].bar_at(p.at)
            assert (fr["1h"].high[i] if p.kind == "H" else fr["1h"].low[i]) == pytest.approx(p.price)
            assert dated(d, p) == p

    def test_without_a_time_frame_the_bar_is_the_time(self):
        f = bars_from_closes([100.0, 101.0, 102.0])
        p = Pivot(f.ts[1], "H", f.high[1], f.ts[2])
        assert dated(f, p).t == f.ts[1] and p.t == f.ts[1]

    def test_the_minimum_tolerance_comes_from_the_measuring_candle(self):
        """W1 8 days, W2 1.9 days: under the 0.25 minimum by 2.4 hours. A whole daily bar of tolerance passes it, an hour does not."""
        fr, f, pv = day_frame([100.0, 120.0, 110.0, 130.0], [8, 2, 8])
        c = Count("15m", IMPULSE, 1, ("0", "1", "2"), (pv[0], pv[1], Pivot(pv[1].ts + int(1.9 * DAY), "L", 110.0, pv[2].conf_ts)), 4.0)
        hour = JUDGE._min_time(c, resolved(f, 4.0))
        day = JUDGE._min_time(c, resolved(f, 96.0))
        assert day[1] == 1.0 and 0.8 < hour[1] < 1.0


class TestTimeItems:
    PRICES = [100.0, 120.0, 108.0, 170.0, 150.0, 200.0]

    def test_w2_outlasting_w1_fails_as_that_label(self):
        *_, ok = judged(IMPULSE, 1, ("0", "1", "2"), self.PRICES[:3], [8, 8], [130.0], [4])
        *_, bad = judged(IMPULSE, 1, ("0", "1", "2"), self.PRICES[:3], [8, 34], [130.0], [4])
        assert ok["w2_time"][0] == 1.0
        assert bad["w2_time"][0] == 0.0 and "corrective wave" in bad["w2_time"][1]

    def test_w4_outlasting_w3_fails_as_that_label(self):
        *_, bad = judged(IMPULSE, 1, ("0", "1", "2", "3", "4"), self.PRICES[:5], [8, 4, 13, 34], [190.0], [4])
        assert bad["w4_time"][0] == 0.0

    def test_w3_on_and_off_its_template(self):
        for days, want in ((13, 1.0), (64, 0.0)):
            *_, items = judged(IMPULSE, 1, ("0", "1", "2", "3"), self.PRICES[:4], [8, 4, days], [150.0], [4])
            assert items["w3_time"][0] == want, days

    def test_a_truncated_w5_is_not_judged_on_time(self):
        """IMP-T5: truncation is the book's exception to W1 about equal to W5."""
        *_, items = judged(IMPULSE, 1, ("0", "1", "2", "3", "4", "5"), [100.0, 120.0, 108.0, 170.0, 150.0, 165.0], [8, 4, 13, 4, 40], [150.0], [4])
        assert "w5_time" not in items

    def test_a_tiny_w1_still_fails_on_time_without_degree_mix(self):
        """The 1d.1 case of r1, a 4-day W1 under a 102-day W3. r2 had an item of its own for this; the book's own templates
        are enough, and a speed that high does not excuse it, because the slow leg is the long one."""
        *_, items = judged(IMPULSE, 1, ("0", "1", "2", "3"), self.PRICES[:4], [4, 17, 102], [150.0], [4])
        assert items["w2_time"][0] == 0.0 and items["w3_time"][0] == 0.0 and "degree_mix" not in items

    def test_c_at_365_percent_of_a_fails(self):
        """The 1d.3 case of r1."""
        *_, bad = judged(ZIGZAG, -1, ("0", "A", "B", "C"), [126.0, 80.0, 98.0, 58.0], [46, 54, 168], [70.0], [5])
        assert bad["ac_time"][0] == 0.0
        *_, ok = judged(ZIGZAG, 1, ("0", "A", "B", "C"), [15.0, 74.0, 49.0, 126.0], [478, 144, 428], [90.0], [50])
        assert ok["ac_time"][0] > 0.5 and ok["b_time"][0] == 1.0

    def test_b_may_take_four_times_a_and_no_more(self):
        *_, ok = judged(ZIGZAG, 1, ("0", "A", "B"), [100.0, 120.0, 110.0], [10, 39], [115.0], [2])
        *_, bad = judged(ZIGZAG, 1, ("0", "A", "B"), [100.0, 120.0, 110.0], [10, 70], [115.0], [2])
        assert ok["b_time"][0] == 1.0 and bad["b_time"][0] == 0.0

    def test_fib_time_on_x_and_y(self):
        *_, items = judged(COMBO, 1, ("0", "W", "X", "Y"), [100.0, 120.0, 110.0, 130.0], [10, 8, 10], [115.0], [2])
        assert items["x_time"][0] == 1.0 and items["wy_time"][0] == 1.0

    def test_a_fifth_retraced_in_its_own_time_counts(self):
        *_, items = judged(IMPULSE, 1, ("0", "1", "2", "3", "4", "5"), self.PRICES, [8, 4, 13, 4, 8], [140.0], [5])
        assert items["retrace_time"][0] == 1.0

    def test_a_fifth_not_retraced_past_its_own_time_loses_credit(self):
        *_, items = judged(IMPULSE, 1, ("0", "1", "2", "3", "4", "5"), self.PRICES, [8, 4, 13, 4, 8], [180.0], [30])
        assert items["retrace_time"][0] == 0.0 and "not retraced" in items["retrace_time"][1]

    def test_a_fifth_not_retraced_inside_its_own_time_is_not_judged(self):
        *_, items = judged(IMPULSE, 1, ("0", "1", "2", "3", "4", "5"), self.PRICES, [8, 4, 13, 4, 8], [180.0], [5])
        assert "retrace_time" not in items

    def test_past_end_fails_a_b_that_runs_far_past_a(self):
        *_, clean = judged(ZIGZAG, -1, ("0", "A", "B"), [126.0, 60.0, 87.0], [100, 100], [76.0], [10])
        assert clean.get("past_end", (1.0,))[0] == 1.0  # the wick of the turning bar is nothing
        fr, f, pv = day_frame([126.0, 65.0, 75.0, 57.0, 87.0, 76.0], [100, 20, 30, 50, 10])
        c = Count("15m", ZIGZAG, -1, ("0", "A", "B"), (pv[0], pv[1], pv[4]), 4.0, pv[5])
        bad = {i: g for i, g, _ in JUDGE.fit(c, describe(c, f, CFG), f)}
        assert bad["past_end"] == 0.0

    def test_whole_correction_against_the_wave_it_corrects(self):
        fr, f, pv = day_frame([100.0, 200.0, 120.0, 160.0, 110.0, 150.0], [100, 20, 10, 20, 10])
        short = Count("15m", ZIGZAG, -1, ("0", "A", "B", "C"), tuple(pv[1:5]), 4.0, pv[5])
        got = JUDGE.whole_time(short, describe(short, f, CFG), f)
        assert got and got[1] == CFG.time["whole"]["shallow_f"]  # 50 days against 100
        running = Count("15m", ZIGZAG, -1, ("0", "A", "B"), tuple(pv[1:4]), 4.0, pv[4])
        assert JUDGE.whole_time(running, describe(running, f, CFG), f) is None


class TestWindows:
    def test_the_right_tool_for_each_wave(self):
        _, f, pv = day_frame([100.0, 120.0, 108.0, 170.0, 150.0, 200.0, 180.0], [10, 5, 20, 5, 10, 3])
        c = Count("15m", IMPULSE, 1, ("0", "1"), tuple(pv[:2]), 4.0, pv[2])
        w = describe(c, f, CFG).window
        assert w.tool == "Fib Time Zone" and w.base == "W1"
        assert w.lo_ts == pv[1].t + int(0.25 * 10 * DAY) and w.hi_ts == pv[1].t + 10 * DAY
        c = Count("15m", IMPULSE, 1, ("0", "1", "2"), tuple(pv[:3]), 4.0, pv[3])
        w = describe(c, f, CFG).window
        assert w.tool == "Trend-Based Fib Time" and w.lo_ts == pv[2].t + 10 * DAY and w.hi_ts == pv[2].t + int(2.236 * 10 * DAY)
        c = Count("15m", IMPULSE, 1, ("0", "1", "2", "3"), tuple(pv[:4]), 4.0, pv[4])
        w = describe(c, f, CFG).window
        assert w.tool == "Fib Time Zone" and w.base == "W3" and w.hi_ts == pv[3].t + 20 * DAY
        c = Count("15m", IMPULSE, 1, ("0", "1", "2", "3", "4"), tuple(pv[:5]), 4.0, pv[5])
        w = describe(c, f, CFG).window
        assert w.tool == "Trend-Based Fib Time" and w.lo_ts == pv[4].t + int(0.618 * 10 * DAY) and w.hi_ts == pv[4].t + 10 * DAY
        c = Count("15m", IMPULSE, 1, ("0", "1", "2", "3", "4", "5"), tuple(pv[:6]), 4.0, pv[6])
        assert describe(c, f, CFG).window.hi_ts == pv[5].t + 50 * DAY

    def test_corrections(self):
        _, f, pv = day_frame([100.0, 120.0, 110.0, 130.0, 115.0], [10, 5, 10, 3])
        c = Count("15m", ZIGZAG, 1, ("0", "A"), tuple(pv[:2]), 4.0, pv[2])
        assert describe(c, f, CFG).window.hi_ts == pv[1].t + 40 * DAY
        c = Count("15m", COMBO, 1, ("0", "W", "X"), tuple(pv[:3]), 4.0, pv[3])
        w = describe(c, f, CFG).window
        assert w.hi_ts == pv[2].t + 10 * DAY and w.lo_ts == pv[2].t + int(0.618 * 10 * DAY)

    def test_no_base_no_window(self):
        _, f, pv = day_frame([100.0, 120.0, 110.0], [10, 5])
        assert describe(Count("15m", IMPULSE, 1, ("0",), tuple(pv[:1]), 4.0, pv[1]), f, CFG).window is None
        assert describe(Count("15m", TRIANGLE, 1, ("0", "A"), tuple(pv[:2]), 4.0, pv[2]), f, CFG).window is None

    def test_a_running_wave_past_its_window_loses_credit(self):
        *_, inside = judged(IMPULSE, 1, ("0", "1", "2", "3", "4"), [100.0, 120.0, 108.0, 170.0, 150.0], [10, 5, 20, 5], [160.0], [5])
        *_, past = judged(IMPULSE, 1, ("0", "1", "2", "3", "4"), [100.0, 120.0, 108.0, 170.0, 150.0], [10, 5, 20, 5], [160.0], [30])
        assert inside["running_time"][0] == 1.0 and past["running_time"][0] == 0.0

    def test_crosshairs_only_ahead(self):
        c, st, f, _ = judged(IMPULSE, 1, ("0", "1", "2"), [100.0, 120.0, 108.0], [10, 5], [114.0], [1])
        now = f.ts[-1] + f.tf_ms
        got = crosshairs(st, now, 99)
        assert got and all(x.ts >= now and st.d * (x.price - st.extreme) > 0 for x in got)
        assert len(got) == len([t for t in st.window.levels if t.ts >= now]) * len(st.zone)
        assert crosshairs(st, st.window.hi_ts + 1, 99) == []
        assert len(crosshairs(st, now, 2)) == 2

    def test_the_odds_horizon_comes_from_the_window(self):
        c, st, f, _ = judged(IMPULSE, 1, ("0", "1", "2"), [100.0, 120.0, 108.0], [10, 5], [114.0], [1])
        now = f.ts[-1] + f.tf_ms
        leg, leg_src, nxt, nxt_src = horizons(st, 150, now, f.tf_ms, 5)
        assert leg_src == "window" and leg * f.tf_ms >= st.window.hi_ts - now > (leg - 1) * f.tf_ms
        assert nxt_src == "fixed"  # the fourth wave's base is W3, not finished yet
        # past the window, or nearly at its end: the frame's horizon
        assert horizons(st, 150, st.window.hi_ts + DAY, f.tf_ms, 5)[:2] == (150, "fixed")
        assert horizons(st, 150, st.window.hi_ts - f.tf_ms, f.tf_ms, 5)[:2] == (150, "fixed")
        # a correction leads to a next wave with a known base: its horizon runs past the window
        c2, st2, f2, _ = judged(IMPULSE, 1, ("0", "1"), [100.0, 120.0], [10], [114.0], [1])
        leg2, _, nxt2, src2 = horizons(st2, 150, f2.ts[-1] + f2.tf_ms, f2.tf_ms, 5)
        assert src2 == "window" and nxt2 > leg2


class TestPartners:
    def _item(self, c: Count, f: Frame, score: float):
        st = describe(c, f, CFG)
        return (c, st, JUDGE.finish(JUDGE.fit(c, st, f)))

    def test_a_pairing_beaten_on_both_goes(self):
        """Same origin, same end, two ways to pair A and C: one has C about A in price and time, the other misses both."""
        fr, f, pv = day_frame([100.0, 80.0, 90.0, 70.0, 85.0, 62.0, 75.0], [10, 10, 30, 10, 12, 5])
        good = Count("15m", ZIGZAG, -1, ("0", "A", "B", "C"), (pv[0], pv[1], pv[4], pv[5]), 4.0, pv[6])
        bad = Count("15m", ZIGZAG, -1, ("0", "A", "B", "C"), (pv[0], pv[3], pv[4], pv[5]), 4.0, pv[6])
        g, b = JUDGE.partner(good, f), JUDGE.partner(bad, f)
        assert g[0] >= b[0] + 0.1 and g[1] >= b[1] + 0.1
        rows = [self._item(bad, f, 0), self._item(good, f, 0)]
        kept, dropped = partner_filter(rows, JUDGE, f, CFG.time["partner_margin"])
        assert dropped == 1 and kept[0][0] is good

    def test_it_changes_which_reading_survives_even_against_a_higher_fit(self):
        fr, f, pv = day_frame([100.0, 80.0, 90.0, 70.0, 85.0, 62.0, 75.0], [10, 10, 30, 10, 12, 5])
        good = Count("15m", ZIGZAG, -1, ("0", "A", "B", "C"), (pv[0], pv[1], pv[4], pv[5]), 4.0, pv[6])
        bad = Count("15m", ZIGZAG, -1, ("0", "A", "B", "C"), (pv[0], pv[3], pv[4], pv[5]), 4.0, pv[6])
        low, high = self._item(good, f, 0), self._item(bad, f, 0)
        high = (high[0], high[1], JUDGE.finish([("subwaves", 1.0, ""), ("anchor_major", 1.0, ""), ("w2_ret", 1.0, ""), ("w3_ext", 1.0, ""), ("w3_time", 1.0, "")]))
        assert high[2].score > low[2].score
        kept, _ = partner_filter([high, low], JUDGE, f, CFG.time["partner_margin"])
        assert [i[0] for i in kept] == [good]

    def test_better_on_one_and_worse_on_the_other_stays(self):
        fr, f, pv = day_frame([100.0, 80.0, 90.0, 70.0, 85.0, 62.0, 75.0], [10, 10, 30, 10, 12, 5])
        a = Count("15m", ZIGZAG, -1, ("0", "A", "B", "C"), (pv[0], pv[3], pv[4], pv[5]), 4.0, pv[6])
        b = Count("15m", ZIGZAG, -1, ("0", "A", "B", "C"), (pv[0], pv[1], pv[4], pv[5]), 4.0, pv[6])
        rows = [self._item(a, f, 0), self._item(b, f, 0)]
        kept, dropped = partner_filter(rows, JUDGE, f, 2.0)  # no margin can be met
        assert dropped == 0 and len(kept) == 2

    def test_no_pair_yet_is_not_compared(self):
        fr, f, pv = day_frame([100.0, 80.0, 90.0, 70.0], [10, 10, 30])
        c = Count("15m", ZIGZAG, -1, ("0", "A"), (pv[0], pv[1]), 4.0, pv[2])
        assert JUDGE.partner(c, f) is None


class TestNestingTime:
    def _parent(self, prices, days, labs, pattern=IMPULSE):
        fr, f, pv = day_frame(prices, days)
        c = Count("15m", pattern, 1, labs, tuple(pv[: len(labs)]), 4.0, pv[len(labs)])
        st = describe(c, f, CFG)
        b = Builder(fr, CFG)
        from ewave.counts.nest import Node
        fit = JUDGE.finish(JUDGE.fit(c, st, f))
        return b, f, pv, Node("p", "15m", 0, c, st, st, fit, 0.1, [], False, fit.score)

    def test_a_child_that_ends_inside_the_parents_window_passes(self):
        b, f, pv, parent = self._parent([100.0, 120.0, 110.0, 170.0, 150.0, 165.0], [10, 5, 20, 8, 5], ("0", "1", "2", "3"))
        child = Count("15m", ZIGZAG, -1, ("0", "A", "B", "C"), (pv[3], Pivot(pv[3].t + 2 * DAY, "L", 160.0, pv[3].t + 3 * DAY), Pivot(pv[3].t + 4 * DAY, "H", 165.0, pv[3].t + 5 * DAY), pv[4]), 4.0, pv[5])
        st = describe(child, f, CFG)
        got = dict((i, g) for i, g, _ in b._nest_time(child, st, parent))
        assert got["nest_time"] == 1.0

    def test_a_child_due_after_the_parents_window_closes_loses_credit(self):
        b, f, pv, parent = self._parent([100.0, 120.0, 110.0, 170.0, 150.0, 165.0], [10, 5, 20, 8, 5], ("0", "1", "2", "3"))
        # the parent's W4 window is 5 to 20 days; a child whose own Y is due 60 days out does not fit
        child = Count("15m", COMBO, -1, ("0", "W", "X"), (pv[3], Pivot(pv[3].t + 100 * DAY, "L", 160.0, pv[3].t + 101 * DAY), Pivot(pv[3].t + 110 * DAY, "H", 165.0, pv[3].t + 111 * DAY)), 4.0, pv[5])
        st = describe(child, f, CFG)
        got = dict((i, g) for i, g, _ in b._nest_time(child, st, parent))
        assert got["nest_time"] < 1.0

    def test_sub_wave_2_may_not_outlast_the_primary_w2(self):
        """STR-C8. The parent is in W3, its W2 took 5 days. The child is W3's own impulse."""
        b, f, pv, parent = self._parent([100.0, 120.0, 110.0, 150.0, 140.0], [10, 5, 10, 12], ("0", "1", "2"))
        short = Count("15m", IMPULSE, 1, ("0", "1", "2"), (pv[2], pv[3], Pivot(pv[3].t + 2 * DAY, "L", 145.0, pv[3].t + 3 * DAY)), 4.0, None)
        long_ = Count("15m", IMPULSE, 1, ("0", "1", "2"), (pv[2], pv[3], pv[4]), 4.0, None)
        tie = Count("15m", IMPULSE, 1, ("0", "1", "2"), (pv[2], pv[3], Pivot(pv[3].t + 5 * DAY, "L", 145.0, pv[3].t + 6 * DAY)), 4.0, None)
        got = lambda c: b._sub_w2(c, describe(c, f, CFG), parent)[1]
        assert got(short) == 1.0
        assert got(tie) == CFG.time["sub_w2"]["tie"]
        assert got(long_) == 0.0


class TestRound2Output:
    def test_payload_has_axes_windows_legs(self):
        obj = payload(random_frames(seed=3, days=90), CFG, 1)
        seen_window = 0
        for tree in obj["trees"].values():
            for lv in tree["levels"]:
                for n in lv["nodes"]:
                    assert set(n["fit"]["axes"]) == {"price", "time", "structure"}
                    assert n["fit"]["score"] == pytest.approx(
                        (n["fit"]["axes"]["price"] * n["fit"]["axes"]["time"] * n["fit"]["axes"]["structure"]) ** (1 / 3), abs=0.01)
                    assert len(n["legs"]) == len(n["labels"]) - 1
                    if n["window"]:
                        seen_window += 1
                        assert n["window"]["lo"] <= n["window"]["hi"] and n["window"]["levels"]
                        assert n["window"]["status"] in ("early", "inside", "past")
                    assert n["window_text"]
        assert seen_window

    def test_short_title_and_exact_times_are_additions(self):
        """The panel's one-line title, and each pivot's exact minute inside its bar: new fields, the old ones stay."""
        obj = payload(random_frames(seed=3, days=90), CFG, 1)
        for tree in obj["trees"].values():
            for lv in tree["levels"]:
                for n in lv["nodes"]:
                    assert n["short"]
                    assert n["short"].startswith(n["pattern_name"]) or n["short"].startswith("First leg")
                    if " · done " in n["short"]:
                        assert "finished at" in n["title"]
                    for mark in [*n["labels"], n["wave"]["start"]]:
                        assert mark["t"] <= mark["at"]

    def test_time_window_and_exact_times_do_not_read_the_future(self):
        """Cut the data at a moment: the tree of the cut equals the tree of the shorter data, windows included."""
        fr = random_frames(seed=5, days=110)
        cut_ms = fr.as_of_ms - 15 * DAY
        fine = fr["15m"].upto(cut_ms)
        short = frames_from(Frame("15m", fine.ts, fine.open, fine.high, fine.low, fine.close, fine.order, fine.volume))
        a = payload(fr.upto(cut_ms), CFG, 1)
        b = payload(short, CFG, 1)
        strip = lambda o: json.dumps({k: v for k, v in o.items() if k in ("trees", "as_of", "price")}, sort_keys=True)
        assert strip(a) == strip(b)
