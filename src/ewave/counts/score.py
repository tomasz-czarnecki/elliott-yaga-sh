"""Rulebook fit: how well a legal count follows the book on price, on time and on structure. A ranking, not a win chance.

Rules kill (rules.py); everything here only ranks, and nothing here can cap or remove a count: the book's own sentence is
"rules eliminate, guidelines rank" (sec 0, FND-4). Each item is judged from 0 to 1 only where it can be judged, and carries
its weight, axis and section from rules/counts.yaml. Each axis stays near its prior until enough has been judged, so that a
count with little to judge does not outrank one that passed many tests. Fit is the geometric mean of the axes, so that a
clear failure on one cannot be bought back by the others. Ratios of price are read on both log and linear and the better one counts (sec 4 allows either on wide ranges).
Durations come from each pivot's exact time (FIB-T6), and a template is met to within the candle that measured it.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, log

from .config import Config
from .frames import Frame
from .pivots import Pivot, dated, locate, zigzag
from .enumerate import Scan
from .rules import CORRECTIVE, ED, FAMILY, FLAT, IMPULSE, LD, TRIANGLE, TRIPLE, ZIGZAG, COMBO, flat_kind
from .state import AFTER, Count, State

AXES = ("price", "time", "structure")


@dataclass(frozen=True)
class Reason:
    item: str
    f: float
    note: str
    sec: str
    w: float
    axis: str
    counted: bool = True   # False: a penalty item that passed, or a bonus item that missed. Shown, not scored


@dataclass
class Fit:
    score: float
    axes: dict[str, float]
    reasons: list[Reason]
    fails: list[str]       # the named checks it fails outright: shown to the reader, and no cap on anything


def ratios(a0: float, a1: float, b0: float, b1: float) -> tuple[float, float]:
    """len(b) / len(a), linear and log."""
    la, lb = abs(a1 - a0), abs(b1 - b0)
    ga, gb = abs(log(a1 / a0)), abs(log(b1 / b0))
    return (lb / la if la else 0.0, gb / ga if ga else 0.0)


def _span(ms: float) -> str:
    """A duration the way a chart reader says it."""
    days = ms / 86_400_000
    if days >= 2:
        return f"{days:.0f}d"
    hours = ms / 3_600_000
    return f"{hours:.0f}h" if hours >= 2 else f"{ms / 60_000:.0f}m"


class Judge:
    def __init__(self, cfg: Config):
        self.items = cfg.fit["items"]
        self.tol = cfg.fit["near_tol"]
        self.fade = cfg.fit["near_fade"]
        self.prior = cfg.fit["prior"]
        self.evidence = cfg.fit["evidence"]
        self.fail_at = cfg.fit["fail_at"]
        self.th = cfg.fit["thresholds"]
        self.time = cfg.time
        self.win = cfg.time["windows"]
        self.fast = cfg.time["fast"]

    def near(self, r: float, levels, tol: float | None = None) -> float:
        """1 within the tolerance of any level, fading to 0."""
        tol = self.tol if tol is None else tol
        fade = max(self.fade, tol * 2)
        best = 0.0
        for lv in levels:
            gap = abs(r - lv) / lv
            if gap <= tol:
                return 1.0
            if gap < fade:
                best = max(best, (fade - gap) / (fade - tol))
        return best

    def inside(self, r: float, lo: float, hi: float) -> float:
        if lo <= r <= hi:
            return 1.0
        return max(self.near(r, (lo,)), self.near(r, (hi,)))

    # --- time ------------------------------------------------------------------------------------------------------

    def t_tol(self, base_bars: float, res: float) -> float:
        """FIB-T6: a template is met to within what the measuring candle can tell, and never tighter than the price rule."""
        return max(self.tol, self.time["resolution_slack"] * res / max(base_bars, res))

    def band(self, t: float, levels, tol: float, fade: float | None = None) -> float:
        """A Fib time template: full on a level, part credit inside its range, fading to 0 outside it, straight in log."""
        hit = self.near(t, levels, tol)
        lo, hi = min(levels), max(levels)
        inner = self.time["band_inner"]
        if lo <= t <= hi:
            return max(hit, inner)
        edge = hi if t > hi else lo
        gap = abs(log(max(t, 1e-9) / edge)) / log(fade or self.time["band_fade"])
        return max(hit, inner * max(0.0, 1 - gap))

    def fast_credit(self, t: float, speed: float, low: float) -> float:
        """FIB-T1, IMP-T1, E5-5: a wave much faster than its base covers the ground in less time, so a shortfall in time is
        no miss. Graded, and never the credit of landing on a level: how much time it would have taken at its base's speed
        must still reach the template's low edge. 0 when the wave is not fast."""
        if speed < self.fast["speed"]:
            return 0.0
        return self.fast["credit"] * min(1.0, t * speed / low)

    @staticmethod
    def limit(x: float, at: float, zero: float) -> float:
        """1 up to the limit, 0 from `zero`, straight in log between."""
        if x <= at:
            return 1.0
        if x >= zero:
            return 0.0
        return 1 - log(x / at) / log(zero / at)

    def fit(self, c: Count, st: State, f: Frame) -> list[tuple[str, float, str]]:
        """(item, 0 to 1, note) for everything that can be judged on this count."""
        out = self.shape(c, f)
        self._running(c, st, {lab: pt.price for lab, pt in zip(c.labs, c.pts)}, dict(zip(c.labs, c.pts)), f, out)
        return out

    def shape(self, c: Count, f: Frame) -> list[tuple[str, float, str]]:
        """What can be judged from the labels alone, with nothing about what price did after them."""
        p = {lab: pt.price for lab, pt in zip(c.labs, c.pts)}
        q = dict(zip(c.labs, c.pts))
        tf_ms = f.tf_ms
        res = f.resolution
        bars = lambda a, b: max((q[b].t - q[a].t) / tf_ms, res)
        out: list[tuple[str, float, str]] = []
        if c.pattern == IMPULSE:
            self._impulse(c, p, q, bars, f, out)
        elif c.pattern in (LD, ED):
            self._diagonal(c, p, q, bars, f, out)
        elif c.pattern == ZIGZAG:
            self._zigzag(c, p, q, bars, f, out)
        elif c.pattern == FLAT:
            self._flat(c, p, q, bars, f, out)
        elif c.pattern == TRIANGLE:
            self._triangle(p, out)
        elif c.pattern in (COMBO, TRIPLE):
            self._combo(p, q, bars, f, out)
            if c.pattern == TRIPLE:
                out.append(("triple_rare", 0.0, "a triple three is rare; the book keeps it simple first (sec 3)"))
        got = self._past_end(c, f)
        if got:
            out.append(got)
        got = self._min_time(c, f)
        if got:
            out.append(got)
        if c.pattern in CORRECTIVE:
            out.append(("corrective_tiebreak", 1.0, ""))
        elif "corrective_tiebreak" in self.items:
            out.append(("corrective_tiebreak", 0.0, ""))
        return out

    def _past_end(self, c: Count, f: Frame) -> tuple[str, float, str] | None:
        """How far the inside of a correction went past the end of the wave it corrects. An expanded B may (sec 3), but the
        further it goes, the less that wave looks finished: an A that ends at 64,936 with 57,756 printed inside its B."""
        worst, name = 0.0, ""
        labs = dict(zip(c.labs, range(len(c.labs))))
        for first, second in (("1", "2"), ("3", "4"), ("A", "B"), ("W", "X")):
            if first not in labs or c.pattern == TRIANGLE:
                continue
            i = labs[first]
            a, end = c.pts[i - 1], c.pts[i]
            i0, i1 = f.bar_at(end.ts) + 1, (f.bar_at(c.pts[i + 1].ts) if i + 1 < len(c.pts) else len(f.ts))
            if i1 <= i0:
                continue
            beyond = min(f.low[i0:i1]) if end.kind == "L" else max(f.high[i0:i1])
            d = 1 if end.kind == "H" else -1
            if d * (beyond - end.price) <= 0:
                continue
            x = abs(log(beyond / end.price)) / abs(log(end.price / a.price))
            if x > worst:
                worst, name = x, f"W{first}" if first.isdigit() else first
        if not name:
            return None
        spec = self.time["past_end"]
        return ("past_end", self.limit(worst, spec["limit"], spec["zero"]), f"price went {worst:.2f} of {name} past the end of {name}: it may not have been over")

    def _min_time(self, c: Count, f: Frame) -> tuple[str, float, str] | None:
        """FIB-T3: a correction takes at least a quarter of the wave it corrects, to within a candle (FIB-T6). Short means the
        pivots are wrong or it is unfinished, says the book, so it ranks and kills nothing. The worst correction sets the item."""
        labs = dict(zip(c.labs, c.pts))
        spec = self.time["minimum"]
        tol = spec["tolerance_bars"] * f.resolution * f.tf_ms
        worst, name, base = None, "", ""
        for start, first, second, of in (("0", "1", "2", "W1"), ("2", "3", "4", "W3"), ("0", "A", "B", "A"), ("0", "W", "X", "W"), ("X", "Y", "X2", "Y")):
            if second not in labs:
                continue
            x = (labs[second].t - labs[first].t + tol) / max(labs[first].t - labs[start].t, 1)
            if worst is None or x < worst:
                worst, base = x, of
                name = {"2": "W2", "4": "W4", "X2": "the second X"}.get(second, second)
        if worst is None:
            return None
        ratio = worst / spec["share"]
        if ratio >= 1:
            return ("min_time", 1.0, f"{name}, the shortest correction, took {worst:.2f} x {base}: over the {spec['share']} minimum")
        return ("min_time", ratio * ratio, f"{name} took {worst:.2f} x {base} in time, under the {spec['share']} minimum: the pivots are wrong or it is unfinished (FIB-T3), ranks lower, kills nothing")

    def _crosshair(self, marks: list[tuple[str, float, float]], out) -> None:
        """FIB-T9, on what has printed: how many of the finished pivots sit on a price level and a time level at once."""
        if not marks:
            return
        got = [min(a, b) for _, a, b in marks]
        hits = [name for (name, a, b) in marks if min(a, b) >= 0.7]
        verb = "sits" if len(hits) == 1 else "sit"
        note = f"{', '.join(hits)} {verb} on a crosshair of price and time" if hits else "no finished pivot sits on a crosshair of price and time"
        out.append(("crosshair", sum(got) / len(got), note))

    def _impulse(self, c, p, q, bars, f, out) -> None:
        s = c.s
        res = f.resolution
        marks: list[tuple[str, float, float]] = []
        ftz = self.win["w2"]["levels"]
        if "2" in p:
            r = ratios(p["0"], p["1"], p["1"], p["2"])
            g = max(self.inside(x, 0.5, 0.618) for x in r)
            if s > 0:  # sec 7: 0.382 in a strong BTC uptrend
                g = max(g, 0.6 * max(self.near(x, (0.382,)) for x in r))
            out.append(("w2_ret", g, f"W2 is {r[0]:.3f} of W1, template 0.5-0.618"))
            t = bars("1", "2") / bars("0", "1")
            tol = self.t_tol(bars("0", "1"), res)
            verdict = "should not outlast it" if t <= 1 + tol else ("it outlasts W1" if t < self.win["w2"]["zero"] else "it outlasts W1: read it as a corrective wave, not a W2")
            out.append(("w2_time", self.limit(t, 1 + tol, self.win["w2"]["zero"]), f"W2 took {t:.2f} x W1 in time, {verdict}"))
            marks.append(("W2", g, self.near(t, ftz, tol)))
        if "3" in p:
            r = ratios(p["0"], p["1"], p["2"], p["3"])
            g = max(self.near(x, (1.618, 2.618, 3.236)) for x in r)
            out.append(("w3_ext", g, f"W3 is {r[0]:.3f} of W1, template 1.618 or 2.618"))
            t = bars("2", "3") / bars("0", "1")
            levels = self.win["w3"]["levels"]
            tol = self.t_tol(bars("0", "1"), res)
            v1 = abs(log(p["1"] / p["0"])) / bars("0", "1")
            v3 = abs(log(p["3"] / p["2"])) / bars("2", "3")
            got = self.band(t, levels, tol)
            soft = self.fast_credit(t, v3 / v1, levels[0])
            aside = f"; a fast market at {v3 / v1:.1f} x W1's speed (IMP-T1, FIB-T1)" if soft > got else ""
            out.append(("w3_time", max(got, soft), f"W3 took {t:.2f} x W1 in time, template 1, 1.618, 2.236{aside}"))
            marks.append(("W3", g, self.near(t, levels, tol)))
            out.append(("w3_steepest", 1.0 if v3 >= v1 else max(0.0, v3 / v1), f"W3 speed is {v3 / v1:.2f} x W1"))
            self._tdi_impulse(c, q, f, out)
        if "4" in p:
            r = ratios(p["2"], p["3"], p["3"], p["4"])
            g = max(max(self.inside(x, 0.236, 0.382) for x in r), 0.7 * max(self.near(x, (0.5,)) for x in r))
            out.append(("w4_ret", g, f"W4 is {r[0]:.3f} of W3, template 0.236-0.382"))
            t = bars("3", "4") / bars("2", "3")
            tol = self.t_tol(bars("2", "3"), res)
            if abs(log(p["3"] / p["2"])) / bars("2", "3") >= self.fast["speed"] * abs(log(p["1"] / p["0"])) / bars("0", "1"):
                # FIB-T1: a violent W3 is paid for in sideways time, so its W4 may run longer than it did
                out.append(("w4_time", self.limit(t, self.fast["w4_limit"] * (1 + tol), self.fast["w4_zero"]), f"W4 took {t:.2f} x W3 in time, after a fast W3 it may run to {self.fast['w4_limit']} x (FIB-T1)"))
            else:
                verdict = "should not outlast it" if t <= 1 + tol else ("it outlasts W3" if t < self.win["w4"]["zero"] else "it outlasts W3: read it as a corrective wave, not a W4")
                out.append(("w4_time", self.limit(t, 1 + tol, self.win["w4"]["zero"]), f"W4 took {t:.2f} x W3 in time, {verdict}"))
            marks.append(("W4", g, self.near(t, self.win["w4"]["levels"], tol)))
            # K: alternation (a clearly different depth) or equality (about the same time). Both count; only the muddle in
            # between does not. How far apart the two may be in time is w4_w2_time.
            t24 = bars("3", "4") / bars("1", "2")
            d2 = ratios(p["0"], p["1"], p["1"], p["2"])[0]
            d4 = ratios(p["2"], p["3"], p["3"], p["4"])[0]
            equal = 0.8 <= t24 <= 1.25
            out.append(("alternation", 1.0 if equal or abs(d2 - d4) >= 0.2 else 0.3, f"W4 took {t24:.2f} x W2 in time; depths {d2:.2f} and {d4:.2f}"))
            sym = self.time["w4_w2"]
            over = max(t24 / sym["high"], sym["low"] / t24)
            out.append(("w4_w2_time", self.limit(over, 1.0, sym["fade"]), f"W4 took {t24:.2f} x W2 in time, {sym['low']} to {sym['high']} is no drastic asymmetry"))
        if "5" in p:
            r3 = abs(p["3"] - p["2"]) / abs(p["1"] - p["0"])
            rows = {1.618: 2.236, 2.618: 3.236, 3.236: 4.236}
            k = 2.236
            for hit, w5 in sorted(rows.items()):
                if r3 >= hit * 0.97:
                    k = w5
            a = ratios(p["0"], p["1"], p["2"], p["5"])
            b = ratios(p["0"], p["1"], p["4"], p["5"])
            g = max(max(self.near(x, (k,)) for x in a), max(self.near(x, (1.0, 0.618)) for x in b))
            out.append(("w5_ext", g, f"W5 is {a[0]:.3f} of 0-1-2 (template {k}) and {b[0]:.3f} of 0-1-4 (template 1 or 0.618)"))
            t = bars("4", "5") / bars("0", "1")
            levels = self.win["w5"]["levels"]
            tol = self.t_tol(bars("0", "1"), res)
            if s * (p["5"] - p["3"]) >= 0:  # IMP-T5: a truncated fifth is the book's exception
                got = self.band(t, levels, tol)
                # E5-5: a fifth may squeeze up fast, taking no more time than any correction before it
                v = (abs(log(p["5"] / p["4"])) / bars("4", "5")) / (abs(log(p["1"] / p["0"])) / bars("0", "1"))
                soft = self.fast_credit(t, v, levels[0]) if bars("4", "5") <= min(bars("1", "2"), bars("3", "4")) else 0.0
                aside = f"; a fast fifth at {v:.1f} x W1's speed, shorter than W2 and W4 (E5-5, FIB-T1)" if soft > got else ""
                out.append(("w5_time", max(got, soft), f"W5 took {t:.2f} x W1 in time, template 1 or 0.618{aside}"))
                marks.append(("W5", g, self.near(t, levels, tol)))
            past = s * (p["5"] - p["3"]) > 0
            out.append(("w5_past_w3", 1.0 if past else 0.0, "W5 passes the end of W3" if past else "W5 stops short of W3: a truncation, possible and not the rule"))
            whole = bars("0", "5")
            out.append(("w4_split", self.near(bars("0", "4") / whole, (0.618, 0.382)), f"W4 ends {bars('0', '4') / whole:.2f} of the way through the impulse in time"))
            w1, w3, w5 = abs(log(p["1"] / p["0"])), abs(log(p["3"] / p["2"])), abs(log(p["5"] / p["4"]))
            out.append(("w1_not_longest", 0.0 if w1 > w3 and w1 > w5 else 1.0, "W1 is the longest" if w1 > w3 and w1 > w5 else "W1 is not the longest"))
            # the 2-4 line, carried to W5's time, against the parallel through W3 (sec 1)
            t24 = q["4"].ts - q["2"].ts
            if t24 > 0:
                slope = (p["4"] - p["2"]) / t24
                channel = p["3"] + slope * (q["5"].ts - q["3"].ts)
                gap = abs(p["5"] - channel) / abs(p["5"] - p["4"])
                tol = self.th["channel_tol"]
                out.append(("channel", 1.0 if gap <= tol else max(0.0, 1 - (gap - tol) / (3 * tol)), f"W5 ends {gap:.2f} of its length from the channel line"))
            self._line_24(c, q, p, f, out)
        self._crosshair(marks, out)

    def _line_24(self, c, q, p, f: Frame, out) -> None:
        """The 2-4 line must not cut through price between 2 and 4 (sec 1)."""
        t2, t4 = q["2"].ts, q["4"].ts
        if t4 <= t2:
            return
        a, b = f.bar_at(t2), f.bar_at(t4)
        slope = (p["4"] - p["2"]) / (t4 - t2)
        cuts = 0
        for i in range(a + 1, b):
            line = p["2"] + slope * (f.ts[i] - t2)
            if (c.s > 0 and f.low[i] < line) or (c.s < 0 and f.high[i] > line):
                cuts += 1
        share = cuts / max(1, b - a - 1)
        out.append(("line_24", 1.0 if share == 0 else max(0.0, 1 - 5 * share), f"{share:.0%} of bars between 2 and 4 cut the 2-4 line"))

    def _rsi_at(self, f: Frame, pt: Pivot) -> float | None:
        i = f.bar_at(pt.ts)
        if i >= len(f.rsi) or f.rsi[i] != f.rsi[i]:
            return None
        return f.rsi[i]

    def _tdi_impulse(self, c, q, f: Frame, out) -> None:
        """Sec 5 wave map. Close-based RSI(11) read at the pivot bar: the same crutch the book warns of. Mirrored down."""
        s = c.s
        r1, r3 = self._rsi_at(f, q["1"]), self._rsi_at(f, q["3"])
        if r1 is None or r3 is None:
            return
        out.append(("tdi_w3", 1.0 if s * (r3 - r1) > 0 else 0.0, f"RSI {r3:.0f} at W3 against {r1:.0f} at W1"))
        lim = self.th["tdi_w3_70"] if s > 0 else 100 - self.th["tdi_w3_70"]
        out.append(("tdi_w3_70", 1.0 if s * (r3 - lim) >= 0 else 0.0, f"RSI {r3:.0f} at W3, line at {lim:.0f}"))
        r2 = self._rsi_at(f, q["2"])
        if r2 is not None:
            hold = self.th["tdi_w2_hold"] if s > 0 else 100 - self.th["tdi_w2_hold"]
            out.append(("tdi_w2_zone", 1.0 if s * (r2 - hold) >= 0 else 0.0, f"RSI {r2:.0f} at W2, line at {hold:.0f}"))
        if "5" in q:
            r5 = self._rsi_at(f, q["5"])
            if r5 is not None:
                new_extreme = s * (q["5"].price - q["3"].price) > 0
                div = new_extreme and s * (r3 - r5) > 0
                out.append(("tdi_35_div", 1.0 if div else 0.0, f"RSI {r5:.0f} at W5 against {r3:.0f} at W3, {'with' if new_extreme else 'without'} a new extreme"))

    def _diagonal(self, c, p, q, bars, f, out) -> None:
        s = c.s
        if "3" in p:
            r = ratios(p["0"], p["1"], p["2"], p["3"])
            out.append(("diag_w3", max(self.near(x, (0.618, 0.786, 1.0, 1.236, 1.382)) for x in r), f"W3 is {r[0]:.3f} of W1"))
        if "4" in p:
            t = bars("3", "4") / bars("1", "2")
            contract = abs(p["3"] - p["4"]) < abs(p["1"] - p["2"])
            out.append(("diag_time", 1.0 if (contract and t < 1) or (not contract and t > 1) else 0.3, f"W4 took {t:.2f} x W2 in time"))
        if "5" in p:
            r = ratios(p["0"], p["1"], p["4"], p["5"])
            out.append(("diag_w5", max(self.near(x, (0.618, 1.0, 1.236, 1.618)) for x in r), f"W5 is {r[0]:.3f} of W1"))
            r3, r5 = self._rsi_at(f, q["3"]), self._rsi_at(f, q["5"])
            if r3 is not None and r5 is not None:
                new_extreme = s * (q["5"].price - q["3"].price) > 0
                out.append(("diag_tdi", 1.0 if new_extreme and s * (r3 - r5) > 0 else 0.0, f"RSI {r5:.0f} at W5 against {r3:.0f} at W3"))
        small = c.tf == "15m"
        out.append(("diag_frame", 1.0 if small else 0.3, "a diagonal on 15m" if small else f"a diagonal on {c.tf}: less common there"))

    def _b_time(self, name: str, base: str, t: float, tol: float, out) -> None:
        """FIB-T5, CPX-G6: B and X can take up to four times the wave before them."""
        spec = self.win[name.lower()]
        out.append((f"{name.lower()}_time", self.limit(t, max(spec["levels"]) * (1 + tol), spec["zero"]), f"{name} took {t:.2f} x {base} in time, up to 4 is fine"))

    def _zigzag(self, c, p, q, bars, f, out) -> None:
        s = c.s
        marks: list[tuple[str, float, float]] = []
        if "B" in p:
            r = ratios(p["0"], p["A"], p["A"], p["B"])
            g = max(self.inside(x, 0.382, 0.786) for x in r)
            out.append(("zz_b", g, f"B is {r[0]:.3f} of A, range 0.382-0.786"))
            t = bars("A", "B") / bars("0", "A")
            tol = self.t_tol(bars("0", "A"), f.resolution)
            self._b_time("B", "A", t, tol, out)
            marks.append(("B", g, self.near(t, self.win["b"]["levels"], tol)))
        if "C" in p:
            r = ratios(p["0"], p["A"], p["B"], p["C"])
            g = max(self.near(x, (0.618, 1.0, 1.236, 1.382, 1.618)) for x in r)
            out.append(("zz_c", g, f"C is {r[0]:.3f} of A, template 0.618, 1, 1.236"))
            past = s * (p["C"] - p["A"]) > 0
            out.append(("zz_c_past_a", 1.0 if past else 0.0, "C passes the end of A" if past else "C stops short of A"))
            over = min(r)
            ceiling = self.time["ceiling"]
            if over >= ceiling:
                out.append(("past_ceiling", 0.0, f"C is {over:.2f} x A at the least: past {ceiling}, double-check impulsive (sec 3)"))
            self._ac(p, bars, f, g, marks, out)
        self._crosshair(marks, out)

    def _flat(self, c, p, q, bars, f, out) -> None:
        s = c.s
        marks: list[tuple[str, float, float]] = []
        if "B" in p:
            r = ratios(p["0"], p["A"], p["A"], p["B"])
            g = max(max(self.inside(x, 0.786, 1.05) for x in r), max(self.inside(x, 1.236, 1.382) for x in r),
                    0.7 * max(self.inside(x, 1.05, 1.236) for x in r), 0.4 * max(self.inside(x, 0.382, 0.786) for x in r))
            out.append(("flat_b", g, f"B is {r[0]:.3f} of A: {flat_kind(s, p)}"))
            t = bars("A", "B") / bars("0", "A")
            tol = self.t_tol(bars("0", "A"), f.resolution)
            self._b_time("B", "A", t, tol, out)
            marks.append(("B", g, self.near(t, self.win["b"]["levels"], tol)))
        if "C" in p:
            kind = flat_kind(s, p)
            levels = {"expanded": (1.618, 2.236), "running": (0.618, 1.0)}.get(kind, (1.0,))
            r = ratios(p["0"], p["A"], p["B"], p["C"])
            g = max(self.near(x, levels) for x in r)
            out.append(("flat_c", g, f"C is {r[0]:.3f} of A, {kind} template {levels}"))
            self._ac(p, bars, f, g, marks, out)
        self._crosshair(marks, out)

    def _ac(self, p, bars, f, price_f, marks, out) -> None:
        t = bars("B", "C") / bars("0", "A")
        levels = self.win["c"]["levels"]
        tol = self.t_tol(bars("0", "A"), f.resolution)
        got = self.band(t, levels, tol, self.time["ac_fade"])
        verdict = "" if got > 0 else ": this C is not partner to this A"
        out.append(("ac_time", got, f"C took {t:.2f} x A in time, template 0.618 or 1{verdict}"))
        marks.append(("C", price_f, self.near(t, levels, tol)))
        va = abs(log(p["A"] / p["0"])) / bars("0", "A")
        vc = abs(log(p["C"] / p["B"])) / bars("B", "C")
        ratio = vc / va if va else 0.0
        spec = self.time["ac_speed"]
        out.append(("ac_speed", self.limit(max(ratio, 1 / ratio) if ratio else float("inf"), spec["limit"], spec["zero"]), f"C speed is {ratio:.2f} x A"))

    def _triangle(self, p, out) -> None:
        got = []
        if "B" in p:
            got.append(max(self.near(x, (0.786, 1.236)) for x in ratios(p["0"], p["A"], p["A"], p["B"])))
        if "C" in p:
            got.append(max(self.near(x, (0.786,)) for x in ratios(p["A"], p["B"], p["B"], p["C"])))
        if "E" in p:
            got.append(max(self.near(x, (0.618,)) for x in ratios(p["B"], p["C"], p["D"], p["E"])))
        if got:
            out.append(("tri_legs", sum(got) / len(got), f"{len(got)} legs near their templates on average {sum(got) / len(got):.2f}"))

    def _combo(self, p, q, bars, f, out) -> None:
        marks: list[tuple[str, float, float]] = []
        if "X" in p:
            r = ratios(p["0"], p["W"], p["W"], p["X"])
            g = max(max(self.inside(x, 0.5, 0.618) for x in r), 0.7 * max(self.inside(x, 0.618, 0.786) for x in r))
            out.append(("x_ret", g, f"X is {r[0]:.3f} of W"))
            t = bars("W", "X") / bars("0", "W")
            tol = self.t_tol(bars("0", "W"), f.resolution)
            self._b_time("X", "W", t, tol, out)
            marks.append(("X", g, self.near(t, self.win["x"]["levels"], tol)))
        if "Y" in p:
            r = ratios(p["0"], p["W"], p["X"], p["Y"])
            g = max(self.near(x, (0.618, 1.0, 1.236)) for x in r)
            out.append(("y_ext", g, f"Y is {r[0]:.3f} of W"))
            over = min(r)
            ceiling = self.time["ceiling"]
            if over >= ceiling:
                out.append(("past_ceiling", 0.0, f"Y is {over:.2f} x W at the least: past {ceiling} a W3 or a C is more likely (sec 3)"))
            t = bars("X", "Y") / bars("0", "W")
            levels = self.win["y"]["levels"]
            tol = self.t_tol(bars("0", "W"), f.resolution)
            out.append(("wy_time", self.band(t, levels, tol, self.time["ac_fade"]), f"Y took {t:.2f} x W in time, template 0.618 or 1"))
            marks.append(("Y", g, self.near(t, levels, tol)))
        if "X2" in p:
            r = ratios(p["0"], p["Y"], p["Y"], p["X2"])
            g = max(max(self.inside(x, 0.5, 0.618) for x in r), 0.7 * max(self.inside(x, 0.618, 0.786) for x in r))
            out.append(("x_ret", g, f"the second X is {r[0]:.3f} of 0-Y"))
            t = bars("Y", "X2") / bars("X", "Y")
            tol = self.t_tol(bars("X", "Y"), f.resolution)
            self._b_time("X", "Y", t, tol, out)
        if "Z" in p:
            r = ratios(p["0"], p["W"], p["X2"], p["Z"])
            out.append(("z_ext", max(self.near(x, self.time["z_ext"]) for x in r), f"Z is {r[0]:.3f} of W, template 1.236 to 1.382, ceiling 1.618"))
            t = bars("X2", "Z") / bars("0", "W")
            tol = self.t_tol(bars("0", "W"), f.resolution)
            out.append(("wy_time", self.band(t, self.win["y"]["levels"], tol, self.time["ac_fade"]), f"Z took {t:.2f} x W in time, template 0.618 or 1"))
        self._crosshair(marks, out)

    def _running(self, c, st: State, p, q, f: Frame, out) -> None:
        """What the running wave has done so far. An item here can only be judged against what has already printed."""
        start = st.start.price
        wave = st.wave
        if st.zone and st.extreme != start:
            far = max(abs(log(lv.price / start)) for lv in st.zone)
            x = abs(log(st.extreme / start)) / far if far else 0.0
            out.append(("running_depth", 1.0 if x <= 1 else max(0.0, 2 - x), f"{_wave_name(wave)} has gone {x:.2f} of the way to the far edge of its zone"))
        if not f.ts:
            return
        now = f.ts[-1] + f.tf_ms
        win = st.window
        if win is not None:
            x = win.x(now)
            hi = win.levels[-1].k
            spec = self.win[win.key]
            zero = spec["zero"]
            out.append(("running_time", self.limit(x, hi, zero), f"{_wave_name(wave)} has taken {x:.2f} x {win.base} so far, its window ends at {hi:g}"))
        self._retrace(c, st, p, q, f, now, out)

    def _retrace(self, c, st: State, p, q, f: Frame, now: int, out) -> None:
        """IMP-T6, STR-C8: a finished fifth or C is retraced in about its own time or less. Holding past that, it may not
        have been the end. "Retraced" here means back to where that wave started."""
        if st.wave != AFTER:
            return
        names = {IMPULSE: ("4", "5"), LD: ("4", "5"), ED: ("4", "5"), ZIGZAG: ("B", "C"), FLAT: ("B", "C")}.get(c.pattern)
        if names is None:
            return
        a, b = q[names[0]], q[names[1]]
        own = max(b.t - a.t, f.tf_ms)
        crossed = f.first_cross(b.ts, a.price, 1 if a.price > b.price else -1)
        zero = self.time["retrace"]["zero"]
        name = f"W{names[1]}" if names[1].isdigit() else names[1]
        if crossed is not None:
            x = (crossed - b.t) / own
            out.append(("retrace_time", self.limit(x, 1.0, zero), f"{name} was retraced in {x:.2f} x its own time ({_span(crossed - b.t)} against {_span(own)})"))
            return
        x = (now - b.t) / own
        if x > 1:
            out.append(("retrace_time", self.limit(x, 1.0, zero), f"{name} still not retraced after {x:.2f} x its own time: it may not have been the end"))

    def whole_time(self, c: Count, st: State, f: Frame) -> tuple[str, float, str] | None:
        """FIB-T3/T5 on a finished correction at the root, against the wave it corrects: the move from the opposite extreme
        of the lookback before it. Finding that wave is ours; the numbers are the book's. A running correction is not
        judged here: it may simply be unfinished."""
        if c.pattern not in CORRECTIVE or st.wave != AFTER:
            return None
        spec = self.time["whole"]
        a, end = c.pts[0], c.pts[-1]
        i = f.bar_at(a.ts)
        i0 = max(0, f.bar_at(a.ts - spec["lookback_days"] * 86_400_000))
        if i - i0 < spec["min_bars"]:
            return None
        if a.kind == "H":
            j = min(range(i0, i), key=lambda t: f.low[t])
            prior_ts, prior_p = f.ts[j], f.low[j]
        else:
            j = max(range(i0, i), key=lambda t: f.high[t])
            prior_ts, prior_p = f.ts[j], f.high[j]
        base = max(a.t - prior_ts, f.tf_ms)
        t = (end.t - a.t) / base
        if t < spec["minimum"]:
            g, note = 0.0, "short of the 1.25 minimum: unfinished or a lower degree"
        elif t < spec["pocket"]:
            g, note = spec["pocket_f"], "only just reaches the 1.25 to 1.33 minimum"
        elif t < spec["w2_low"]:
            g, note = spec["shallow_f"], "over the minimum, under the usual 0.618"
        elif t <= spec["w2_high"]:
            g, note = 1.0, "within the wave it corrects"
        elif t <= spec["b_max"]:
            g, note = spec["long_f"], "longer than the wave it corrects: fine for a B or X, not for a W2 or W4"
        else:
            g, note = spec["long_f"] * self.limit(t, spec["b_max"], spec["zero"]), "past the 4 x of a B or X"
        return ("whole_time", g, f"the whole correction took {t:.2f} x the {_span(base)} move from {prior_p:,.0f} before it: {note}")

    def premise_items(self, c: Count, st: State, top: Pivot, origin: Pivot, f: Frame) -> list[tuple[str, float, str]]:
        """The correction against the impulse he gave (sec 1 C next-degree W2, FIB-T3, FIB-T5). A running one can only be
        judged on how long it has already taken; a finished one also on how far it pulled 0-5 and in how much time."""
        out: list[tuple[str, float, str]] = []
        spec = self.time["whole"]
        span = max(top.t - origin.t, f.tf_ms)
        if st.wave != AFTER:
            now = f.ts[-1] + f.tf_ms if f.ts else top.t
            x = (now - top.t) / span
            out.append(("premise_time", self.limit(x, spec["b_max"], spec["zero"]), f"the correction has taken {x:.2f} x the five so far"))
            return out
        end = c.pts[-1]
        t = (end.t - top.t) / span
        if t < spec["minimum"]:
            g, note = 0.0, "short of the 1.25 minimum: unfinished or a lower degree (FIB-T3), ranks lower, kills nothing"
        elif t < spec["pocket"]:
            g, note = spec["pocket_f"], "only just reaches the 1.25 to 1.33 minimum"
        elif t < spec["w2_low"]:
            g, note = spec["shallow_f"], "over the minimum, under the usual 0.618"
        elif t <= spec["w2_high"]:
            g, note = 1.0, "within the five it corrects"
        elif t <= spec["b_max"]:
            g, note = spec["long_f"], "longer than the five: fine for a B or X, not for a next-degree W2"
        else:
            g, note = spec["long_f"] * self.limit(t, spec["b_max"], spec["zero"]), "past the 4 x of a B or X"
        out.append(("premise_time", g, f"the whole correction took {t:.2f} x the five: {note}"))
        r = ratios(origin.price, top.price, top.price, end.price)
        ret = max(self.inside(x, 0.5, 0.618) for x in r)
        out.append(("premise_ret", ret, f"it pulled {r[0]:.3f} of 0-5 (log {r[1]:.3f}), next-degree template 0.5 to 0.618"))
        return out

    def partner(self, c: Count, f: Frame) -> tuple[float, float] | None:
        """FIB-T8: how well the partner legs agree, on time and on price. None when no pair has printed yet."""
        p = {lab: pt.price for lab, pt in zip(c.labs, c.pts)}
        q = dict(zip(c.labs, c.pts))
        res = f.resolution
        bars = lambda a, b: max((q[b].t - q[a].t) / f.tf_ms, res)
        pairs: list[tuple[float, float]] = []
        if c.pattern == IMPULSE and "3" in p:
            tol = self.t_tol(bars("0", "1"), res)
            pairs.append((self.band(bars("2", "3") / bars("0", "1"), self.win["w3"]["levels"], tol),
                          max(self.near(x, (1.618, 2.618, 3.236)) for x in ratios(p["0"], p["1"], p["2"], p["3"]))))
            if "5" in p:
                pairs.append((self.band(bars("4", "5") / bars("0", "1"), self.win["w5"]["levels"], tol),
                              max(self.near(x, (1.0, 0.618)) for x in ratios(p["0"], p["1"], p["4"], p["5"]))))
        elif c.pattern in (ZIGZAG, FLAT) and "C" in p:
            tol = self.t_tol(bars("0", "A"), res)
            levels = (0.618, 1.0, 1.236, 1.382, 1.618) if c.pattern == ZIGZAG else (0.618, 1.0, 1.618, 2.236)
            pairs.append((self.band(bars("B", "C") / bars("0", "A"), self.win["c"]["levels"], tol, self.time["ac_fade"]),
                          max(self.near(x, levels) for x in ratios(p["0"], p["A"], p["B"], p["C"]))))
        elif c.pattern == COMBO and "Y" in p:
            tol = self.t_tol(bars("0", "W"), res)
            pairs.append((self.band(bars("X", "Y") / bars("0", "W"), self.win["y"]["levels"], tol, self.time["ac_fade"]),
                          max(self.near(x, (0.618, 1.0, 1.236)) for x in ratios(p["0"], p["W"], p["X"], p["Y"]))))
        if not pairs:
            return None
        return (sum(a for a, _ in pairs) / len(pairs), sum(b for _, b in pairs) / len(pairs))

    def finish(self, judged: list[tuple[str, float, str]]) -> Fit:
        totals = {a: [0.0, 0.0] for a in AXES}
        fails: dict[str, list[str]] = {a: [] for a in AXES}
        reasons = []
        for item, g, note in judged:
            spec = self.items[item]
            axis, w = spec["axis"], spec["w"]
            credit = spec.get("credit", "both")
            counted = not ((credit == "penalty" and g >= 1.0) or (credit == "bonus" and g < self.prior))
            if counted:
                totals[axis][0] += w * g
                totals[axis][1] += w
            if spec.get("named") and g <= self.fail_at:
                fails[axis].append(item)
            reasons.append(Reason(item, round(g, 3), note, spec["sec"], w, axis, counted))
        axes = {a: (got + self.evidence * self.prior) / (weight + self.evidence) for a, (got, weight) in totals.items()}
        score = 1.0
        for a in AXES:
            score *= axes[a]
        return Fit(score ** (1 / len(AXES)), axes, sorted(reasons, key=lambda r: (-r.f * r.w, r.item)), fails["time"] + fails["price"] + fails["structure"])


def partner_filter(ranked: list, judge: Judge, f: Frame, margin: float) -> tuple[list, int]:
    """FIB-T8: where the same reading can be labelled with its legs paired in more than one way, the pairing beaten on both
    time and price goes. A pairing better on one and worse on the other stays: the book's test decides only when both agree.
    Readings with no pair yet are not comparable and stay. `ranked` keeps its order."""
    groups: dict[tuple, list] = {}
    for item in ranked:
        c, st, _ = item
        got = judge.partner(c, f)
        if got is not None:
            # the same reading's legs paired differently: a different origin is a different count, not another pairing
            groups.setdefault((FAMILY[c.pattern], c.s, c.pts[0].ts, st.wave, st.start.ts), []).append((item, got))
    gone: set[int] = set()
    for rows in groups.values():
        for item, (t, pr) in rows:
            if any(t2 >= t + margin and p2 >= pr + margin for _, (t2, p2) in rows):
                gone.add(id(item))
    return [i for i in ranked if id(i) not in gone], len(gone)


def _wave_name(w: str) -> str:
    return f"W{w}" if w.isdigit() else ("the wave" if w == AFTER else w)


class Subwaves:
    """Can a labelled wave be seen to subdivide one frame down? (sec 0: the largest wave subdivides visibly; sec 6: verify
    sub-waves.) Motive waves should show 5 or more legs, corrective ones 3 or more."""

    def __init__(self, frames, cfg: Config):
        self.frames = frames
        self.cfg = cfg
        self.memo: dict[tuple, bool | None] = {}

    def check(self, tf: str, a: Pivot, b: Pivot, kinds: tuple[str, ...], need: int) -> bool | None:
        """True or False, or None when the wave is too small to judge on that frame."""
        key = (tf, a.ts, b.ts, kinds)
        if key in self.memo:
            return self.memo[key]
        sub_tf = self.cfg.frames[tf]["sub"]
        sub = self.frames[sub_tf]
        tf_ms = self.frames[tf].tf_ms
        got = self._check(sub, tf_ms, a, b, kinds, need)
        self.memo[key] = got
        return got

    def _check(self, sub: Frame, tf_ms: int, a: Pivot, b: Pivot, kinds, need: int) -> bool | None:
        start = locate(sub, tf_ms, a)
        end_pivot = locate(sub, tf_ms, b)
        i, j = sub.bar_at(start.ts), sub.bar_at(end_pivot.ts)
        if j - i < 12:
            return None
        ks = self.cfg.frames[sub.tf]["k"]
        cap = self.cfg.pivots["max_pivots"]
        for k in ks:
            pivots, running = zigzag(sub, k, start, j + 1)
            if running is None or len(pivots) > cap:
                continue
            legs = len(pivots) if running.kind != pivots[-1].kind else len(pivots) - 1
            if legs < need:
                continue
            closed = [*pivots, dated(sub, Pivot(running.ts, running.kind, running.price, end_pivot.conf_ts))]
            scan = Scan(sub, k, closed, None, self.cfg)
            if any(scan.parse(kind, 0, len(closed) - 1) for kind in kinds):
                return True
        return False

    def judge(self, c: Count, grammar: dict) -> tuple[str, float, str] | None:
        from .rules import WAVES

        waves = WAVES[c.pattern]
        seen, total = 0, 0
        names = []
        for n, wave in enumerate(waves[: c.done]):
            kinds = tuple(k for k in grammar[c.pattern][wave])
            motive = all(k in (IMPULSE, LD, ED) for k in kinds)
            got = self.check(c.tf, c.pts[n], c.pts[n + 1], kinds, 5 if motive else 3)
            if got is None:
                continue
            total += 1
            seen += bool(got)
            names.append(f"{wave}{'+' if got else '-'}")
        if not total:
            return None
        return ("subwaves", seen / total, f"visible one frame down: {' '.join(names)}")


def anchor_major(c: Count, f: Frame, from_ts: int) -> tuple[str, float, str]:
    """Does the root start at the highest high or lowest low of its lookback?"""
    a = c.pts[0]
    i = f.bar_at(from_ts)
    if a.kind == "L":
        major = a.price <= min(f.low[i:])
    else:
        major = a.price >= max(f.high[i:])
    return ("anchor_major", 1.0 if major else 0.0, "starts at the extreme of the lookback" if major else "starts inside the lookback's range")


def tf_move(tf: str, st: State, price: float, cfg: Config) -> tuple[str, float, str] | None:
    """Sec 5: a target too big for the frame means a wrong frame."""
    table = cfg.frames[tf].get("move_table")
    if not table:
        return None
    # a finished structure's running wave is what follows it now: its zone, not the wave after that
    levels, d = (st.targets, st.next_d) if st.next_first and st.wave != AFTER else (st.zone, st.d)
    ahead = [lv.price for lv in levels if d and d * (lv.price - price) > 0]
    if not ahead:
        return None
    move = min(abs(x / price - 1) for x in ahead)
    lo, hi = table
    g = 1.0 if move <= hi * 1.5 else max(0.0, 1 - (move - hi * 1.5) / (hi * 1.5))
    return ("tf_move", g, f"first target is {move:.1%} away, this frame's move is {lo:.0%}-{hi:.0%}")


def shares(fits: list[float], kept: int, cfg: Config) -> tuple[list[float], float]:
    """Fit share of the first `kept` states and what is left for other/unclear. Not a probability of anything."""
    beta, floor = cfg.fit["share_beta"], cfg.fit["other_floor"]
    w = [exp(beta * x) for x in fits]
    total = sum(w)
    if not total:
        return [0.0] * kept, 1.0
    top = [(x / total) * (1 - floor) for x in w[:kept]]
    return top, 1 - sum(top)
