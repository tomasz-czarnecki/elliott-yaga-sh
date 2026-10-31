"""Where a labelled count stands now: the running wave, where it should end, what comes next and what kills it.

Labels sit on confirmed pivots only. The running wave starts at the last label and everything since then, confirmed or
not, is inside it. Its levels come from the Fib pulls of sections 1 to 4. A level uses log as well as linear on the high
frames (sec 4) and takes the nearer of the two: the more conservative target goes first. Its time window comes from the
tool the book names for that wave (FIB-T2): Trend-Based Fib Time for W3, W5, C and Y, Fib Time Zone for W2, W4, B and X.
Zone and window together make the target a box: where the wave should end, and when.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log

from .config import Config
from .frames import Frame, HIGH_FIRST, LOW_FIRST
from .pivots import Pivot
from .rules import COMBO, ED, FLAT, IMPULSE, LD, MOTIVE, TRIANGLE, TRIPLE, WAVES, ZIGZAG, Checker, Point

AFTER = "after"


@dataclass(frozen=True)
class Level:
    k: float
    price: float
    pull: str


@dataclass(frozen=True)
class Kill:
    price: float
    side: int        # +1: dies above it, -1: dies below it
    rule: str
    note: str


@dataclass(frozen=True)
class TimeLevel:
    k: float
    ts: int
    pull: str


@dataclass(frozen=True)
class Window:
    """When the running wave should end. Levels are multiples of a base wave, projected from the running wave's start."""
    key: str                      # the template in rules: time.windows
    tool: str
    pull: str
    base: str                     # the base wave's name
    base_ms: int
    start_ts: int
    lo_ts: int
    hi_ts: int
    zero_ts: int                  # past this it has lost all time credit
    levels: tuple[TimeLevel, ...]

    def x(self, now_ms: int) -> float:
        """The running wave so far, in multiples of the base."""
        return (now_ms - self.start_ts) / self.base_ms

    def status(self, now_ms: int) -> str:
        return "early" if now_ms < self.lo_ts else ("inside" if now_ms <= self.hi_ts else "past")


@dataclass(frozen=True)
class Crosshair:
    """FIB-T9: a price level and a time level of the running wave meet here."""
    ts: int
    price: float
    time_k: float
    price_k: float
    pull: str


@dataclass
class Count:
    tf: str
    pattern: str
    s: int                        # direction of the first wave
    labs: tuple[str, ...]         # "0", then the finished waves
    pts: tuple[Pivot, ...]
    k: float                      # the zigzag threshold it was read at
    first_leg: Pivot | None = None  # first pivot after the last label: the running wave's printed first leg

    @property
    def done(self) -> int:
        return len(self.labs) - 1

    def points(self, tf_ms: int) -> dict[str, Point]:
        return {lab: Point(pt.t / tf_ms, pt.price) for lab, pt in zip(self.labs, self.pts)}


@dataclass
class State:
    wave: str                     # the running wave, or AFTER when the structure is finished
    kinds: tuple[str, ...]        # patterns that may fill it
    d: int                        # its direction
    start: Pivot
    extreme: float                # how far it has gone so far, in its own direction
    zone: list[Level]             # where it should end
    next_wave: str | None
    next_d: int | None
    targets: list[Level]          # where the next wave should go, measured from the extreme so far
    kills: list[Kill]             # kills[0] is the invalidation
    window: Window | None = None  # when it should end; None when the book gives no base for it
    next_span_ms: int | None = None  # the largest template duration of the next wave, for the next plan's horizon

    @property
    def invalidation(self) -> Kill:
        return self.kills[0]

    @property
    def motive_running(self) -> bool:
        return all(k in MOTIVE for k in self.kinds)

    @property
    def zone_reached(self) -> bool:
        """The running wave has already touched its zone's nearer edge, even if price has come back since."""
        if not self.zone:
            return False
        edge = min((lv.price for lv in self.zone), key=lambda x: abs(x - self.start.price))
        return self.d * (self.extreme - edge) >= 0

    @property
    def next_first(self) -> bool:
        """Which plan leads. A correction is read for what follows it; a motive wave for its own target, until reached."""
        return bool(self.targets) and (not self.motive_running or self.zone_reached)


def _ret(a: float, b: float, k: float, use_log: bool) -> float:
    """The k retracement of a-b, back from b. Nearer of linear and log."""
    lin = b - k * (b - a)
    if not use_log or lin <= 0:
        return b * (a / b) ** k if lin <= 0 else lin
    lg = b * (a / b) ** k
    return lin if abs(lin - b) <= abs(lg - b) else lg


def _ext(a: float, b: float, c: float, k: float, d: int, use_log: bool) -> float:
    """The k extension of a-b, projected from c in direction d. Nearer of linear and log."""
    lin = c + d * k * abs(b - a)
    lg = c * (max(a, b) / min(a, b)) ** (d * k)
    if lin <= 0:
        return lg
    if not use_log:
        return lin
    return lin if abs(lin - c) <= abs(lg - c) else lg


def _rets(a: float, b: float, ks, pull: str, use_log: bool) -> list[Level]:
    return [Level(k, _ret(a, b, k, use_log), f"ret {pull} {k:g}") for k in ks]


def _exts(a: float, b: float, c: float, ks, d: int, pull: str, use_log: bool) -> list[Level]:
    return [Level(k, _ext(a, b, c, k, d, use_log), f"ext {pull} {k:g}") for k in ks]


def _since(f: Frame, pt: Pivot) -> tuple[float, float]:
    """Highest high and lowest low since a pivot. Inside the pivot's bar, only what came after the extreme."""
    i = f.bar_at(pt.ts)
    if i >= len(f.ts):
        return f.tail_high, f.tail_low
    hi_from = lo_from = i
    if pt.kind == "H" and f.order[i] == LOW_FIRST:
        lo_from = i + 1
    if pt.kind == "L" and f.order[i] == HIGH_FIRST:
        hi_from = i + 1
    return max(f.hi_since(hi_from), pt.price if pt.kind == "H" else float("-inf")), min(f.lo_since(lo_from), pt.price if pt.kind == "L" else float("inf"))


# Which template and which base wave each running wave uses. The numbers live in rules: time.windows.
_AFTER_MOTIVE = ("after", "0", "5", "the whole five")
_DIAG = {"2": ("w2", "0", "1", "W1"), "4": ("diag_w4", "1", "2", "W2"), AFTER: _AFTER_MOTIVE}
_ABC = {"B": ("b", "0", "A", "A"), "C": ("c", "0", "A", "A"), AFTER: ("after", "0", "C", "the whole correction")}
TIME_PLAN = {
    IMPULSE: {"2": ("w2", "0", "1", "W1"), "3": ("w3", "0", "1", "W1"), "4": ("w4", "2", "3", "W3"), "5": ("w5", "0", "1", "W1"), AFTER: _AFTER_MOTIVE},
    LD: _DIAG,
    ED: _DIAG,
    ZIGZAG: _ABC,
    FLAT: _ABC,
    COMBO: {"X": ("x", "0", "W", "W"), "Y": ("y", "0", "W", "W"), AFTER: ("after", "0", "Y", "the whole correction")},
    TRIPLE: {"X": ("x", "0", "W", "W"), "Y": ("y", "0", "W", "W"), "X2": ("x", "X", "Y", "Y"), "Z": ("y", "0", "W", "W"), AFTER: ("after", "0", "Z", "the whole correction")},
    TRIANGLE: {},  # the book gives triangles no time numbers beyond the minimum
}
_NEXT_SPAN = {
    IMPULSE: {"2": ("w3", "0", "1"), "4": ("w5", "0", "1"), AFTER: ("w3", "0", "5")},
    ZIGZAG: {"B": ("c", "0", "A")},
    FLAT: {"B": ("c", "0", "A")},
    COMBO: {"X": ("y", "0", "W")},
    TRIPLE: {"X": ("y", "0", "W"), "X2": ("y", "0", "W")},
}


def _time_plan(c: Count, wave: str, start: Pivot, q: dict[str, Pivot], cfg: Config) -> tuple[Window | None, int | None]:
    specs = cfg.time["windows"]
    win = None
    plan = TIME_PLAN[c.pattern].get(wave)
    if plan:
        key, a, b, name = plan
        spec = specs[key]
        base = max(q[b].t - q[a].t, 1)
        pull = f"{a}-{b}"
        levels = tuple(TimeLevel(k, start.t + int(k * base), f"{spec['tool']} {pull} {k:g}") for k in spec["levels"])
        win = Window(key, spec["tool"], pull, name, base, start.t, levels[0].ts, levels[-1].ts, start.t + int(spec["zero"] * base), levels)
    span = None
    nxt = _NEXT_SPAN.get(c.pattern, {}).get(wave)
    if nxt:
        key, a, b = nxt
        span = int(max(specs[key]["levels"]) * (q[b].t - q[a].t))
    return win, span


def crosshairs(st: "State", now_ms: int, cap: int) -> list[Crosshair]:
    """Where the running wave's price levels still ahead meet its time levels still ahead (FIB-T9)."""
    if st.window is None or not st.zone:
        return []
    times = [t for t in st.window.levels if t.ts >= now_ms]
    prices = [lv for lv in st.zone if st.d * (lv.price - st.extreme) > 0]
    grid = [Crosshair(t.ts, lv.price, t.k, lv.k, f"{lv.pull} x {t.pull}") for t in times for lv in prices]
    grid.sort(key=lambda g: (g.ts, abs(g.price - st.extreme)))
    return grid[:cap]


def sits_on_crosshair(st: "State", extreme_ts: int, tol: float) -> Crosshair | None:
    """The running wave's extreme so far, if it already sits on a price level and a time level at once."""
    w = st.window
    if w is None or not st.zone or st.extreme == st.start.price:
        return None
    x = (extreme_ts - w.start_ts) / w.base_ms
    tl = min(w.levels, key=lambda t: abs(x - t.k))
    pl = min(st.zone, key=lambda lv: abs(st.extreme - lv.price))
    move = abs(st.extreme - st.start.price)
    if abs(x - tl.k) <= tol * tl.k and abs(st.extreme - pl.price) <= tol * move:
        return Crosshair(extreme_ts, st.extreme, tl.k, pl.k, f"{pl.pull} x {tl.pull}")
    return None


def _corrective_escape(c: Count, start: float, d: int, cfg: Config) -> Kill:
    """How far a running correction may go back past its own start. Once its first leg has printed, a B-type excursion
    may run up to the flat ceiling of that leg (sec 3). Before that, any new extreme says the wave before is not over."""
    if c.first_leg is None:
        return Kill(start, -d, "new_extreme", "a new extreme past the start: the wave before is not over")
    a = c.first_leg.price
    limit = _ret(start, a, cfg.rules["flat_b_max"], False)
    if limit <= 0:
        limit = a * (start / a) ** cfg.rules["flat_b_max"]
    return Kill(limit, -d, "pocket_1618", "past the flat ceiling of its first leg: not a B, the wave before is not over (sec 3)")


def describe(c: Count, f: Frame, cfg: Config) -> State:
    lv = cfg.levels
    use_log = cfg.frames[f.tf].get("log_fib", False)
    s = c.s
    p = {lab: pt.price for lab, pt in zip(c.labs, c.pts)}
    q = dict(zip(c.labs, c.pts))
    waves = WAVES[c.pattern]
    done = c.done
    start = c.pts[-1]
    wave = waves[done] if done < len(waves) else AFTER
    d = s if done % 2 == 0 else -s
    hi, lo = _since(f, start)
    e = hi if d > 0 else lo
    tf_ms = f.tf_ms
    if wave == AFTER:
        kinds = tuple(cfg.grammar["after_motive" if c.pattern in MOTIVE else "after_corrective"])
    else:
        kinds = tuple(cfg.grammar[c.pattern][wave])
    zone: list[Level] = []
    targets: list[Level] = []
    next_wave, next_d = None, None
    kills: list[Kill] = []

    if c.pattern in (IMPULSE, LD, ED):
        diagonal = c.pattern != IMPULSE
        if wave == "1":
            kills = [Kill(p["0"], -s, "origin_w1", "past the start of W1")]
            next_wave, next_d = "2", -s
            targets = _rets(p["0"], e, lv["w2_ret"], "0-1 so far", use_log)
        elif wave == "2":
            zone = _rets(p["0"], p["1"], lv["w2_ret"], "0-1", use_log)
            next_wave, next_d = "3", s
            targets = _exts(p["0"], p["1"], e, lv["w3_ext"], s, "0-1-2", use_log)
            kills = [Kill(p["0"], -s, "I1_w2_beyond_start", "W2 past the start of W1 (sec 1)"), _corrective_escape(c, p["1"], d, cfg)]
        elif wave == "3":
            zone = _exts(p["0"], p["1"], p["2"], lv["w3_ext"], s, "0-1-2", use_log)
            next_wave, next_d = "4", -s
            targets = _rets(p["2"], e, lv["w4_ret"], "2-3 so far", use_log)
            kills = [Kill(p["2"], -s, "origin_w3", "back past the end of W2: W3 has not begun (sec 0)"),
                     Kill(p["0"], -s, "I1_w2_beyond_start", "past the start of W1: the whole structure is dead (sec 1)")]
        elif wave == "4":
            next_wave, next_d = "5", s
            if diagonal:
                zone = _rets(p["2"], p["3"], lv["diag_w4_ret"], "2-3", use_log)
                targets = _exts(p["0"], p["1"], e, lv["diag_w5_ext"], s, "0-1-4", use_log)
                kills = [Kill(p["2"], -s, "D4_w4_beyond_w2", "W4 past the end of W2 (sec 2)"), _corrective_escape(c, p["3"], d, cfg)]
            else:
                zone = _rets(p["2"], p["3"], lv["w4_ret"], "2-3", use_log)
                targets = _w5_targets(p, e, s, lv, use_log)
                kills = [Kill(p["1"], -s, "I4_w4_into_w1", "W4 into W1 territory (sec 1)"), _corrective_escape(c, p["3"], d, cfg)]
        elif wave == "5":
            next_wave, next_d = "correction", -s
            targets = _rets(p["0"], e, lv["next_degree_ret"], "0-5 so far", use_log)
            if diagonal:
                zone = _exts(p["0"], p["1"], p["4"], lv["diag_w5_ext"], s, "0-1-4", use_log)
                kills = [Kill(p["4"], -s, "origin_w5", "back past the end of W4: W5 has not begun (sec 0)")]
            else:
                zone = _w5_targets(p, p["4"], s, lv, use_log)
                kills = [Kill(p["4"], -s, "origin_w5", "back past the end of W4: W5 has not begun (sec 0)")]
                w1, w3 = abs(p["1"] - p["0"]), abs(p["3"] - p["2"])
                if w1 > w3:  # sec 1 L16: with W1 longer than W3, W5 may not pass 1:1 of W3
                    kills.append(Kill(p["4"] + s * w3, s, "I3_w3_shortest", "W5 past 1:1 of W3 while W1 is longer: W3 would be the shortest (sec 1)"))
        else:
            next_wave, next_d = "next-degree 3", s
            zone = _rets(p["0"], p["5"], lv["next_degree_ret"], "0-5", use_log)
            targets = _exts(p["0"], p["5"], e, lv["w3_ext"], s, "0-5-2", use_log)
            kills = [Kill(p["0"], -s, "origin_5", "a finished 5 back to its origin: not the start of a new move (sec 0)"),
                     Kill(p["5"], s, "new_extreme", "a new extreme: the 5 is not finished")]
    elif c.pattern == TRIANGLE:
        names = waves + [AFTER]
        i = names.index(wave)
        if wave == AFTER:
            zone = _exts(p["0"], p["A"], p["E"], [1.0], -s, "height 0-A from E", use_log)
            kills = [Kill(p["E"], s, "new_extreme", "back past E: the triangle is not finished")]
        else:
            legs = ["0", *waves]
            prev, last = (legs[i - 1], legs[i]) if i >= 1 else (None, legs[0])
            if wave == "E":
                zone = _exts(p["B"], p["C"], p["D"], lv["tri_e_ext"], d, "B-C-D", use_log)
                next_wave, next_d = "thrust", -s
                targets = _exts(p["0"], p["A"], e, [1.0], -s, "height 0-A from E", use_log)
            elif prev is not None:
                zone = _rets(p[prev], p[last], lv["tri_ret"], f"{prev}-{last}", use_log)
                next_wave, next_d = names[i + 1], -d
            else:
                next_wave, next_d = names[1], -d
            if wave == "A":
                kills = [Kill(p["0"], -s, "origin_a", "past the start of the first leg")]
            elif wave == "B":
                kills = [_corrective_escape(c, p["A"], d, cfg)]
            elif wave == "C":
                kills = [Kill(p["A"], s, "T1_c_beyond_a", "C past A (sec 3)")]
            elif wave == "D":
                kills = [Kill(p["B"], -s, "T2_d_beyond_b", "D past B (sec 3)")]
            else:
                kills = [Kill(p["C"], s, "T3_e_beyond_c", "E past C (sec 3)")]
    elif c.pattern == TRIPLE:
        zone, next_wave, next_d, targets, kills = _triple_plan(c, wave, p, e, s, d, lv, use_log, cfg)
    else:  # zigzag, flat, combination
        first, mid, last = waves
        if wave == first:
            kills = [Kill(p["0"], -s, "origin_a", "past the start of the first leg")]
            next_wave, next_d = mid, -s
            first_ret = {ZIGZAG: "zz_b_ret", FLAT: "flat_b_ret"}.get(c.pattern, "x_ret")
            targets = _rets(p["0"], e, lv[first_ret], f"0-{first} so far", use_log)
        elif wave == mid:
            next_wave, next_d = last, s
            if c.pattern == ZIGZAG:
                zone = _rets(p["0"], p["A"], lv["zz_b_ret"], "0-A", use_log)
                targets = _exts(p["0"], p["A"], e, lv["c_ext_zigzag"], s, "0-A-B", use_log)
                kills = [Kill(p["0"], -s, "Z1_b_beyond_start", "B past the start of A (sec 3)"), _corrective_escape(c, p["A"], d, cfg)]
            elif last == "C":
                zone = _rets(p["0"], p["A"], lv["flat_b_ret"], "0-A", use_log)
                targets = _exts(p["0"], p["A"], e, lv["c_ext_flat"], s, "0-A-B", use_log)
                ceiling = _flat_ceiling(p["0"], p["A"], cfg)
                kills = [Kill(ceiling, -s, "F1_b_too_long", "B at the flat ceiling: not a B (sec 3)"), _corrective_escape(c, p["A"], d, cfg)]
            else:
                zone = _rets(p["0"], p["W"], lv["x_ret"], "0-W", use_log)
                targets = _exts(p["0"], p["W"], e, lv["y_ext"], s, "0-W-X", use_log)
                ceiling = _flat_ceiling(p["0"], p["W"], cfg)
                kills = [Kill(ceiling, -s, "F1_b_too_long", "X past the flat ceiling of W (sec 3)"), _corrective_escape(c, p["W"], d, cfg)]
        elif wave == last:
            next_wave, next_d = "next structure", -s
            targets = _rets(p["0"], e, lv["after_correction_ret"], f"0-{last} so far", use_log)
            if last == "C":
                zone = _exts(p["0"], p["A"], p["B"], lv["c_ext_zigzag" if c.pattern == ZIGZAG else "c_ext_flat"], s, "0-A-B", use_log)
                kills = [Kill(p["B"], -s, "origin_c", "back past the end of B: C has not begun (sec 0)")]
            else:
                zone = _exts(p["0"], p["W"], p["X"], lv["y_ext"], s, "0-W-X", use_log)
                kills = [Kill(p["X"], -s, "origin_y", "back past the end of X: Y has not begun")]
        else:
            end = p[last]
            zone = _rets(p["0"], end, lv["after_correction_ret"], f"0-{last}", use_log)
            kills = [Kill(end, s, "new_extreme", f"a new extreme: {last} is not finished")]
    kills = [k for k in kills if k.price > 0]  # a limit under zero cannot be crossed
    window, next_span = _time_plan(c, wave, start, q, cfg)
    return State(wave, kinds, d, start, e, zone, next_wave, next_d, targets, kills, window, next_span)


def _triple_plan(c: Count, wave: str, p: dict, e: float, s: int, d: int, lv: dict, use_log: bool, cfg: Config) -> tuple:
    """W-X-Y-X-Z (sec 3): the second X pulls 0-Y, Z extends 0-W from the second X and stays under 1.618 of W."""
    zone: list[Level] = []
    targets: list[Level] = []
    next_wave, next_d = None, None
    if wave == "W":
        next_wave, next_d = "X", -s
        targets = _rets(p["0"], e, lv["x_ret"], "0-W so far", use_log)
        kills = [Kill(p["0"], -s, "origin_a", "past the start of the first leg")]
    elif wave == "X":
        next_wave, next_d = "Y", s
        zone = _rets(p["0"], p["W"], lv["x_ret"], "0-W", use_log)
        targets = _exts(p["0"], p["W"], e, lv["y_ext"], s, "0-W-X", use_log)
        kills = [Kill(_flat_ceiling(p["0"], p["W"], cfg), -s, "F1_b_too_long", "X past the flat ceiling of W (sec 3)"), _corrective_escape(c, p["W"], d, cfg)]
    elif wave == "Y":
        next_wave, next_d = "X2", -s
        zone = _exts(p["0"], p["W"], p["X"], lv["y_ext"], s, "0-W-X", use_log)
        targets = _rets(p["0"], e, lv["x_ret"], "0-Y so far", use_log)
        kills = [Kill(p["X"], -s, "origin_y", "back past the end of X: Y has not begun")]
    elif wave == "X2":
        next_wave, next_d = "Z", s
        zone = _rets(p["0"], p["Y"], lv["x_ret"], "0-Y", use_log)
        targets = _exts(p["0"], p["W"], e, lv["z_ext"], s, "0-W-X", use_log)
        kills = [Kill(p["X"], -s, "W6_x2_beyond_x", "the second X beyond the first (sec 3)"), _corrective_escape(c, p["Y"], d, cfg)]
    elif wave == "Z":
        next_wave, next_d = "next structure", -s
        zone = _exts(p["0"], p["W"], p["X2"], lv["z_ext"], s, "0-W-X", use_log)
        targets = _rets(p["0"], e, lv["after_correction_ret"], "0-Z so far", use_log)
        kills = [Kill(p["X2"], -s, "origin_z", "back past the end of the second X: Z has not begun")]
    else:
        zone = _rets(p["0"], p["Z"], lv["after_correction_ret"], "0-Z", use_log)
        kills = [Kill(p["Z"], s, "new_extreme", "a new extreme: Z is not finished")]
    return zone, next_wave, next_d, targets, kills


def _flat_ceiling(zero: float, a: float, cfg: Config) -> float:
    """Where a B of 0-A reaches the flat ceiling: past the start of A by the ceiling's excess (sec 3)."""
    k = cfg.rules["flat_b_max"]
    lin = a + k * (zero - a)
    lg = a * (zero / a) ** k
    return max(lin, lg) if zero > a else (min(lin, lg) if lin > 0 else lg)


def _w5_targets(p: dict, from_price: float, s: int, lv: dict, use_log: bool) -> list[Level]:
    """W5: the add-one row of the extension W3 reached, pull 0-1-2, and 0.618 / 1.0 of W1 from W4 (sec 1)."""
    r3 = abs(p["3"] - p["2"]) / abs(p["1"] - p["0"])
    add_one = 2.236
    for hit, w5 in sorted(((float(a), b) for a, b in lv["w5_from_w3"].items())):
        if r3 >= hit * 0.97:
            add_one = w5
    out = _exts(p["0"], p["1"], p["2"], [add_one], s, "0-1-2", use_log)
    out += _exts(p["0"], p["1"], from_price, lv["w5_014"], s, "0-1-4", use_log)
    return out


def alive(c: Count, st: State, f: Frame) -> Kill | None:
    """The kill level price has already crossed since the running wave began, if any."""
    hi, lo = _since(f, st.start)
    for k in st.kills:
        if (k.side > 0 and hi > k.price) or (k.side < 0 and lo < k.price):
            return k
    return None


def advance(parent: Count, end: Pivot, checker: Checker, tf_ms: int) -> Count | None:
    """The parent with its running wave closed at `end`, when a child structure has finished. None if the parent has no
    next wave, or if closing it there breaks one of the parent's own rules: degree consistency, not decoration."""
    waves = WAVES[parent.pattern]
    if parent.done >= len(waves):
        return None
    lab = waves[parent.done]
    labs = (*parent.labs, lab)
    pts = (*parent.pts, end)
    out = Count(parent.tf, parent.pattern, parent.s, labs, pts, parent.k)
    return out if checker.legal(parent.pattern, parent.s, out.points(tf_ms)) else None


def log_dist(a: float, b: float) -> float:
    return abs(log(a / b))
