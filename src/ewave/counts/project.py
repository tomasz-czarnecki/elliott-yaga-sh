"""Where a count says price goes from here: the running wave's end, what is left of its own structure, and one step of what
follows it. Every future leg gets a price x time box from the book's tools (rules/counts.yaml: levels, time.windows), and a
most likely point inside the box (rules: projection.likely). The levels come from `describe`, run on the count with its running wave
closed at that point, so a projected leg has the same pulls, kills and rule checks as a printed one (sec 1, 3, 4).

The running wave's own inside is drawn from the pattern its grammar allows, keeping the book's typical ratios between its legs
(rules: projection.inner) and landing on the running wave's point. A printed first leg, or a leg that has gone further than
the template, is kept as printed.

A child's projection lives inside its parent's running-wave box. A target outside it is ranked down and drawn dimmer, never
deleted: the parent may be the wrong one. Nothing here is evidence: Fib levels and windows are hit at random-path rates
(research/model-options/02-empirical.md B2, B3). `research/counts-r6.md` says how the forward log measures them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, log

from .config import Config
from .frames import Frame, Frames
from .pivots import Pivot
from .rules import COMBO, ED, FLAT, IMPULSE, LD, TRIANGLE, TRIPLE, WAVES, ZIGZAG, Checker
from .state import AFTER, Count, Level, State, TimeLevel, describe

RUNNING, INNER, REMAINING, AFTER_ROLE = "running", "inner", "remaining", "after"
INSIDE, ON_WAY, SHORT, BEYOND, LATE, NO_PARENT = "inside", "on the way", "short", "beyond", "late", "no parent"

_MOTIVE_TEMPLATES = {"2": "w2_ret", "3": "w3_ext", "5": "w5"}
TEMPLATE = {
    IMPULSE: {**_MOTIVE_TEMPLATES, "4": "w4_ret", AFTER: "next_degree_ret"},
    LD: {**_MOTIVE_TEMPLATES, "4": "diag_w4_ret", "5": "diag_w5_ext", AFTER: "next_degree_ret"},
    ED: {**_MOTIVE_TEMPLATES, "4": "diag_w4_ret", "5": "diag_w5_ext", AFTER: "next_degree_ret"},
    ZIGZAG: {"B": "zz_b_ret", "C": "c_ext_zigzag", AFTER: "after_correction_ret"},
    FLAT: {"B": "flat_b_ret", "C": "c_ext_flat", AFTER: "after_correction_ret"},
    COMBO: {"X": "x_ret", "Y": "y_ext", AFTER: "after_correction_ret"},
    TRIPLE: {"X": "x_ret", "Y": "y_ext", "X2": "x_ret", "Z": "z_ext", AFTER: "after_correction_ret"},
    TRIANGLE: {"B": "tri_ret", "C": "tri_ret", "D": "tri_ret", "E": "tri_e_ext", AFTER: "thrust"},
}


@dataclass
class Target:
    """One level of a leg, with what the parent says about it."""
    k: float
    price: float
    pull: str
    reached: bool = False
    status: str = NO_PARENT
    nest_f: float = 1.0        # 1 inside the parent's box, down to the floor far outside it


@dataclass
class Leg:
    wave: str
    role: str
    d: int
    start_p: float             # where the wave itself starts: a printed pivot, or the leg before's point
    p0: float                  # where this leg starts on the path
    t0: int
    p: float                   # the most likely point
    t: int
    p_lo: float | None
    p_hi: float | None
    t_lo: int | None
    t_hi: int | None
    targets: list[Target]
    times: list[TimeLevel]
    src: str                   # why that point: section ids
    t_src: str
    tool: str | None = None
    open_end: bool = False     # a first wave: the book has no pull for it until it ends
    reached: bool = False      # the running wave has already gone past every level
    late: bool = False         # its window has closed: the time is only "soon"
    status: str = NO_PARENT
    nest_f: float = 1.0


@dataclass
class Projection:
    legs: list[Leg]
    inner: list[Leg] = field(default_factory=list)
    inner_pattern: str | None = None
    inner_why: str = ""
    widen: float = 1.0
    nest_f: float = 1.0
    status: str = NO_PARENT
    note: str = ""


def _likely(levels: list[Level], key: str | None, spec: dict) -> tuple[float | None, str]:
    row = spec["likely"].get(key) if key else None
    return (row["k"], row["src"]) if row else (None, "")


def _order(levels: list[Level], k: float | None, d: int, frm: float) -> list[Level]:
    """Levels still ahead of `frm`, the most likely first, then by how near that one they are."""
    ahead = [lv for lv in levels if d * (lv.price - frm) > 0]
    if k is None:
        return sorted(ahead, key=lambda lv: abs(lv.price - frm))
    return sorted(ahead, key=lambda lv: (abs(lv.k - k), abs(lv.price - frm)))


def _box(lo: float, hi: float, widen: float, min_half: float) -> tuple[float, float]:
    """Wider by `widen` around its middle in log, and never thinner than the frame can show."""
    mid = (log(lo) + log(hi)) / 2
    half = max((log(hi) - log(lo)) / 2 * widen, min_half)
    return exp(mid - half), exp(mid + half)


def _time_point(window, spec: dict, t0: int, tf_ms: int) -> tuple[int, str, bool]:
    if window is None:
        return t0 + spec["fallback_bars"] * tf_ms, "the book gives no time for it: only the order of the legs is meant", False
    row = spec["likely_time"].get(window.key)
    k = row["k"] if row else window.levels[-1].k
    src = row["src"] if row else window.tool
    want = min(window.levels, key=lambda lv: abs(lv.k - k))
    if want.ts > t0:
        return want.ts, src, False
    later = [lv for lv in window.levels if lv.ts > t0]
    if later:
        return later[0].ts, src, False
    return t0 + max(spec["fallback_bars"] * tf_ms, window.base_ms // 10), f"past its window ({src}): only soon is meant", True


def _leg(c: Count, st: State, role: str, p0: float, t0: int, f: Frame, cfg: Config, widen: float, min_half: float, fallback: "Leg | None") -> Leg:
    spec = cfg.projection
    key = TEMPLATE.get(c.pattern, {}).get(st.wave)
    k, src = _likely(st.zone, key, spec)
    frm = st.extreme
    ahead = _order(st.zone, k, st.d, frm)
    tt, t_src, late = _time_point(st.window, spec, t0, f.tf_ms)
    open_end = not st.zone
    reached = bool(st.zone) and not ahead
    if ahead:
        p = ahead[0].price
    elif open_end and fallback is not None and fallback.d == st.d and st.d * (fallback.p - frm) > 0:
        p, src = fallback.p, f"no pull for a first wave: the parent's {fallback.wave}"  # sec 4: an extension needs three pivots
    else:
        p = frm
        if open_end:
            src = "no pull for a first wave until it ends (sec 4): drawn as if it ended at its extreme so far"
    if reached:
        src = "past every level already"
        tt, late = max(t0 + f.tf_ms, tt) if late else t0 + f.tf_ms, late
    p_lo = p_hi = None
    if st.zone:
        p_lo, p_hi = _box(min(lv.price for lv in st.zone), max(lv.price for lv in st.zone), widen, min_half)
    t_lo = t_hi = None
    if st.window is not None:
        extra = int((st.window.hi_ts - st.window.lo_ts) * (widen - 1) / 2)
        t_lo, t_hi = st.window.lo_ts - extra, st.window.hi_ts + extra
    targets = [Target(lv.k, lv.price, lv.pull, st.d * (lv.price - frm) <= 0) for lv in st.zone]
    return Leg(st.wave, role, st.d, st.start.price, p0, t0, p, max(tt, t0 + f.tf_ms), p_lo, p_hi, t_lo, t_hi, targets, list(st.window.levels) if st.window else [], src, t_src,
               st.window.tool if st.window else None, open_end, reached, late)


def _closed(c: Count, st: State, p: float, t: int, checker: Checker, tf_ms: int) -> Count | None:
    """The count with its running wave closed at this point, if no rule stops it there."""
    waves = WAVES[c.pattern]
    if c.done >= len(waves):
        return None
    kind = "H" if st.d > 0 else "L"
    end = Pivot(t, kind, p, t + tf_ms)
    out = Count(c.tf, c.pattern, c.s, (*c.labs, waves[c.done]), (*c.pts, end), c.k)
    return out if checker.legal(c.pattern, c.s, out.points(tf_ms)) else None


def own_legs(c: Count, st: State, f: Frame, cfg: Config, now: int, price: float, widen: float, fallback: "Leg | None" = None) -> list[Leg]:
    """The running wave, what is left of the structure, and one step of what follows it. Nothing past that (sec 0: project 1
    structure ahead)."""
    checker = Checker(cfg.rules)
    min_half = cfg.projection["box_min_atr"] * (f.atr[-1] if f.atr else 0.0)
    legs: list[Leg] = []
    cur_c, cur_st, role, p0, t0 = c, st, RUNNING, price, now
    while True:
        leg = _leg(cur_c, cur_st, role, p0, t0, f, cfg, widen, min_half, fallback if role == RUNNING else None)
        legs.append(leg)
        if cur_st.wave == AFTER:
            return legs
        nxt = _closed(cur_c, cur_st, leg.p, leg.t, checker, f.tf_ms)
        if nxt is None:  # the most likely level is not legal for it: the next one that is, or stop here
            for t in leg.targets:
                if t.reached or t.price == leg.p:
                    continue
                nxt = _closed(cur_c, cur_st, t.price, leg.t, checker, f.tf_ms)
                if nxt is not None:
                    leg.p = t.price
                    leg.src += " (the likelier one breaks a rule here)"
                    break
            if nxt is None:
                return legs
        st2 = describe(nxt, f, cfg, extreme=leg.p)
        role = AFTER_ROLE if st2.wave == AFTER else REMAINING
        cur_c, cur_st, p0, t0 = nxt, st2, leg.p, leg.t


def inner_pattern(wave: str, kinds: tuple[str, ...], child, spec: dict) -> tuple[str | None, str]:
    """Which pattern draws the running wave's inside. A child whose end lands in this wave's box has read it already."""
    if child is not None and child.proj.status == INSIDE and child.count.pattern in spec["inner"]:
        return child.count.pattern, f"the {child.tf.upper()} child reads it so"
    prefer = spec["prefer"].get(wave)
    if prefer in kinds:
        return prefer, spec["prefer_src"]
    for k in kinds:
        if k in spec["inner"]:
            return k, "the first the grammar allows"
    return None, ""


def inner_legs(c: Count, st: State, leg: Leg, pattern: str, f: Frame, cfg: Config, now: int, price: float, extreme_ts: int) -> list[Leg]:
    """The running wave's own legs, from the template's typical ratios, ending on the running wave's point."""
    spec = cfg.projection
    tpl = spec["inner"][pattern]
    sigma = f.volatility(cfg.frames[f.tf]["vol_bars"])
    if leg.reached or leg.open_end or abs(log(leg.p / price)) < spec["inner_min_sigmas"] * sigma * spec["inner_min_bars"] ** 0.5:
        return []
    if (leg.t - now) / f.tf_ms < spec["inner_min_bars"]:
        return []
    S, T0 = st.start.price, st.start.t
    u, w, a, b = [], [], 0.0, 0.0
    for x in tpl["price"]:
        a += x
        u.append(a)
    for x in tpl["time"]:
        b += x
        w.append(b)
    u = [x / a for x in u]
    w = [x / b for x in w]

    def at(E: float, Te: float, vt: tuple[float, float] | None) -> list[tuple[float, float]]:
        if vt is None:  # nothing has printed that fixes the first leg: what is left of the time is shared out from now
            v1, t1 = S * (E / S) ** u[0], now + (max(Te, now + f.tf_ms) - now) * w[0]
        else:
            v1, t1 = vt
        out = [(v1, t1)]
        for ui, wi in zip(u[1:], w[1:]):
            x = (ui - u[0]) / (1 - u[0]) if u[0] < 1 else 1.0
            y = (wi - w[0]) / (1 - w[0]) if w[0] < 1 else 1.0
            out.append((v1 * (E / v1) ** x, t1 + (Te - t1) * y))
        return out

    fixed = None
    start_i = 0
    if c.first_leg is not None:
        fixed, start_i = (c.first_leg.price, c.first_leg.t), 1
    else:
        v1 = S * (leg.p / S) ** u[0]
        if st.d * (st.extreme - v1) >= 0:  # gone further than the template's first leg: that leg is what has printed
            fixed = (st.extreme, extreme_ts)
    if fixed is not None and st.d * (leg.p - fixed[0]) <= 0:
        return []
    te = leg.t
    if fixed is not None and te <= fixed[1]:
        te = fixed[1] + int((fixed[1] - T0) * (1 - w[0]) / max(w[0], 0.01))
    mid = at(leg.p, te, fixed)
    ends = [(x, y) for x, y in ((leg.p_lo, leg.t_lo), (leg.p_hi, leg.t_hi)) if x is not None and y is not None]
    edge = [at(x, y, fixed) for x, y in ends] if len(ends) == 2 else []
    out: list[Leg] = []
    p0, t0 = price, now
    labels = tpl["legs"]
    for i in range(start_i, len(labels)):
        p, t = mid[i]
        want = st.d * (1 if tpl["price"][i] > 0 else -1)
        if i < len(labels) - 1 and want * (p - p0) <= 0:  # price is already past this leg's point: it has printed
            continue
        t = max(int(t), t0 + f.tf_ms)
        ps = [e[i][0] for e in edge] + [p]
        ts = [int(e[i][1]) for e in edge] + [t]
        d = 1 if p > p0 else -1
        out.append(Leg(labels[i], INNER, d, p0, p0, t0, p, t, min(ps), max(ps), min(ts), max(ts), [], [], tpl["src"], tpl["src"], None))
        p0, t0 = p, t
    if out and out[-1].t > leg.t:
        leg.t = out[-1].t
    return out


def _envelope(parent_legs: list[Leg], d: int) -> Leg | None:
    """The parent's leg that holds this child: its running wave, or its next one when the child has closed the running one."""
    return next((x for x in parent_legs if x.d == d and x.p_lo is not None), None)


def judge_target(p: float, t: int | None, env: Leg, terminal: bool, spec: dict, now: int) -> tuple[str, float]:
    """A level against the parent's box. Past the box's far edge or behind the parent's start is outside. Short of it is fine
    unless this level would end the child's whole structure: then the parent's wave could not end there. Late is the same, in time."""
    near, far = (env.p_hi, env.p_lo) if env.d < 0 else (env.p_lo, env.p_hi)
    start = env.start_p
    ref = abs(log(far / start)) or 1.0
    floor, slope = spec["nest_floor"], spec["nest_slope"]
    status, f = INSIDE, 1.0
    if env.d * (p - far) > 0:
        status, f = BEYOND, max(floor, 1 - slope * abs(log(p / far)) / ref)
    elif env.d * (start - p) > 0:
        status, f = BEYOND, max(floor, 1 - slope * abs(log(p / start)) / ref)
    elif env.d * (near - p) > 0:
        if terminal and env.wave != AFTER:  # the move after a structure has no rule that says how far it must go
            status, f = SHORT, max(floor, 1 - slope * abs(log(p / near)) / ref)
        else:
            status = ON_WAY
    if t is not None and env.t_hi is not None and env.t_hi > now and t > env.t_hi and env.t_lo is not None:
        base = max(env.t_hi - now, 1)
        g = max(floor, 1 - slope * (t - env.t_hi) / base)
        if g < f:
            status, f = LATE, g
    return status, f


def apply_nest(legs: list[Leg], parent_legs: list[Leg], spec: dict, now: int) -> tuple[str, float]:
    """Marks every level of the child's legs against the parent's box. The count's own mark is where its last wave ends."""
    if not legs:
        return NO_PARENT, 1.0
    env = _envelope(parent_legs, legs[0].d)
    if env is None:
        return NO_PARENT, 1.0
    own = [x for x in legs if x.role != AFTER_ROLE]
    end = own[-1] if own else legs[-1]
    for leg in legs:
        if leg.role == AFTER_ROLE:
            continue
        terminal = leg is end
        leg.status, leg.nest_f = judge_target(leg.p, leg.t, env, terminal, spec, now)
        for t in leg.targets:
            t.status, t.nest_f = judge_target(t.price, leg.t, env, terminal, spec, now)
        leg.targets.sort(key=lambda t: (t.reached, -t.nest_f, abs(t.price - leg.p0)))
    return end.status, end.nest_f


def project_tree(tree, frames: Frames, cfg: Config, widen_of) -> None:
    """Sets `proj` on every node. Parents first: a child's levels are judged against its parent's box, and a parent's inside
    then takes the child's pattern when the child lands in it."""
    spec = cfg.projection
    now, price = frames.as_of_ms, frames.price
    for lv in tree.levels:
        for n in lv.nodes:
            f = frames[n.tf]
            fallback = None
            if n.parent is not None:
                fallback = next((x for x in n.parent.proj.legs if x.d == n.state.d and x.role != AFTER_ROLE and not x.open_end), None)
            legs = own_legs(n.running_count, n.state, f, cfg, now, price, widen_of(n), fallback)
            n.proj = Projection(legs, widen=widen_of(n))
            if n.parent is not None:
                n.proj.status, n.proj.nest_f = apply_nest(legs, n.parent.proj.legs, spec, now)
    for lv in tree.levels:
        for n in lv.nodes:
            legs = n.proj.legs
            if not legs or n.state.wave == AFTER:
                continue
            child = n.children[0] if n.children else None
            pattern, why = inner_pattern(n.state.wave, n.state.kinds, child, spec)
            if pattern is None:
                continue
            got = inner_legs(n.running_count, n.state, legs[0], pattern, frames[n.tf], cfg, now, price, n.extreme_ts)
            if got:
                n.proj.inner, n.proj.inner_pattern, n.proj.inner_why = got, pattern, why
