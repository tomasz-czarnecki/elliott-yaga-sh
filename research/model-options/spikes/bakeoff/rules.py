"""Deterministic NewWave rule checker for one labelled wave structure.

Rules come from the compact NewWave rulebook, sections 0 to 3. Only the numbers and the logic are encoded here; the
course text stays out of the repo. A check needs prices and pivots of one degree only, so anything that depends on the
inside of a leg (is it a 3 or a 5, order blocks, TDI) cannot be tested and is not claimed.

    violations(pattern, direction, labels) -> list[Violation]

`labels` maps a wave label to a Point(bar, price). Partial structures are allowed; rules needing a missing point are
skipped. severity "R" = a rule in the book (a break kills the count), "soft" = a guideline, a course convention or a
point where the book conflicts with itself. Length rules are lenient on log vs linear: a count breaks them only when it
breaks them on both scales, because the book allows either on wide ranges.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log

IMPULSE = "impulse"
LD = "leading_diagonal"
ED = "ending_diagonal"
ZIGZAG = "zigzag"
FLAT_REG = "flat_regular"
FLAT_RUN = "flat_running"
FLAT_EXP = "flat_expanded"
TRIANGLE = "triangle"
COMBO = "combination"
PATTERNS = {IMPULSE, LD, ED, ZIGZAG, FLAT_REG, FLAT_RUN, FLAT_EXP, TRIANGLE, COMBO}
FLATS = {FLAT_REG, FLAT_RUN, FLAT_EXP}

ORDER = {
    IMPULSE: ["0", "1", "2", "3", "4", "5"], LD: ["0", "1", "2", "3", "4", "5"], ED: ["0", "1", "2", "3", "4", "5"],
    ZIGZAG: ["0", "A", "B", "C"], FLAT_REG: ["0", "A", "B", "C"], FLAT_RUN: ["0", "A", "B", "C"], FLAT_EXP: ["0", "A", "B", "C"],
    TRIANGLE: ["0", "A", "B", "C", "D", "E"], COMBO: ["0", "W", "X", "Y", "X2", "Z"],
}


@dataclass(frozen=True)
class Point:
    bar: int
    price: float


@dataclass(frozen=True)
class Violation:
    rule: str
    severity: str  # R or soft
    note: str


def _lin(a: float, b: float) -> float:
    return abs(b - a)


def _log(a: float, b: float) -> float:
    return abs(log(b / a)) if a > 0 and b > 0 else _lin(a, b)


def ratio(a0: float, a1: float, b0: float, b1: float) -> tuple[float, float]:
    """len(b0-b1) / len(a0-a1), linear and log. Zero-length legs give infinity."""
    la, lb = _lin(a0, a1), _lin(b0, b1)
    ga, gb = _log(a0, a1), _log(b0, b1)
    return (lb / la if la else float("inf"), gb / ga if ga else float("inf"))


def _below(x: float, y: float, s: int) -> bool:
    """x is on the origin side of y for a structure heading in direction s (strictly)."""
    return s * (x - y) < 0


def _breaks_min(r: tuple[float, float], floor: float) -> bool:
    return r[0] < floor and r[1] < floor


def _breaks_max(r: tuple[float, float], ceiling: float) -> bool:
    return r[0] >= ceiling and r[1] >= ceiling


def _order_issues(pattern: str, s: int, pts: dict[str, Point]) -> list[Violation]:
    """Labels ascend in time and every wave moves the way it should."""
    out: list[Violation] = []
    seq = [lab for lab in ORDER[pattern] if lab in pts]
    want = ORDER[pattern][:len(seq)]
    if seq != want:
        out.append(Violation("S0_labels_skipped", "R", f"labels {seq} do not run in order from {want}"))
    for a, b in zip(seq, seq[1:]):
        if pts[b].bar < pts[a].bar:
            out.append(Violation("S1_time_order", "R", f"{b} is before {a}"))
    if pattern in (FLAT_REG, FLAT_RUN, FLAT_EXP, ZIGZAG, IMPULSE, LD, ED):
        # odd steps move with the structure, even steps against it
        for k, (a, b) in enumerate(zip(seq, seq[1:])):
            step = s if k % 2 == 0 else -s
            if step * (pts[b].price - pts[a].price) <= 0:
                out.append(Violation("S2_wave_direction", "R", f"{a} to {b} moves the wrong way"))
    if pattern in (TRIANGLE, COMBO):
        for k, (a, b) in enumerate(zip(seq, seq[1:])):
            step = s if k % 2 == 0 else -s
            if step * (pts[b].price - pts[a].price) <= 0:
                out.append(Violation("S2_wave_direction", "R", f"{a} to {b} moves the wrong way"))
    return out


def _impulse(s: int, p: dict[str, Point]) -> list[Violation]:
    v: list[Violation] = []
    if "2" in p and not s * (p["2"].price - p["0"].price) > 0:
        v.append(Violation("I1_w2_beyond_start_w1", "R", "W2 at or beyond the start of W1 (sec 1)"))
    if "3" in p and not s * (p["3"].price - p["1"].price) > 0:
        v.append(Violation("I2_w3_not_beyond_w1", "R", "W3 does not pass the end of W1 (sec 1)"))
    if "5" in p:
        w1 = (p["0"].price, p["1"].price)
        w3 = (p["2"].price, p["3"].price)
        w5 = (p["4"].price, p["5"].price)
        short_lin = _lin(*w3) < _lin(*w1) and _lin(*w3) < _lin(*w5)
        short_log = _log(*w3) < _log(*w1) and _log(*w3) < _log(*w5)
        if short_lin and short_log:
            v.append(Violation("I3_w3_shortest", "R", "W3 is the shortest of 1, 3, 5 (sec 1)"))
    if "4" in p and not s * (p["4"].price - p["1"].price) >= 0:
        v.append(Violation("I4_w4_into_w1", "R", "W4 enters W1 territory, not a diagonal (sec 1)"))
    return v + _impulse_soft(s, p)


def _impulse_soft(s: int, p: dict[str, Point]) -> list[Violation]:
    v: list[Violation] = []
    if "2" in p:
        r = ratio(p["0"].price, p["1"].price, p["1"].price, p["2"].price)
        if not (0.33 <= min(r) and max(r) <= 0.70) and not (0.33 <= r[0] <= 0.70 or 0.33 <= r[1] <= 0.70):
            v.append(Violation("G_w2_outside_fib", "soft", f"W2 retraces {r[0]:.2f} of W1, template 0.382-0.618 (sec 1)"))
        t = (p["2"].bar - p["1"].bar) / max(1, p["1"].bar - p["0"].bar)
        if t > 1:
            v.append(Violation("C_w2_outlasts_w1", "soft", f"W2 takes {t:.2f} x W1 in time, must not outlast it (sec 1)"))
        if t < 0.25:
            v.append(Violation("C_w2_under_min_time", "soft", f"W2 takes {t:.2f} x W1 in time, minimum 0.25 (sec 1, 4)"))
    if "4" in p:
        r = ratio(p["2"].price, p["3"].price, p["3"].price, p["4"].price)
        if not (0.2 <= r[0] <= 0.55 or 0.2 <= r[1] <= 0.55):
            v.append(Violation("G_w4_outside_fib", "soft", f"W4 retraces {r[0]:.2f} of W3, template 0.236-0.5 (sec 1)"))
        t = (p["4"].bar - p["3"].bar) / max(1, p["3"].bar - p["2"].bar)
        if t > 1:
            v.append(Violation("C_w4_outlasts_w3", "soft", f"W4 takes {t:.2f} x W3 in time (sec 1)"))
        if t < 0.25:
            v.append(Violation("C_w4_under_min_time", "soft", f"W4 takes {t:.2f} x W3 in time, minimum 0.25 (sec 1, 4)"))
    if "5" in p and s * (p["5"].price - p["3"].price) < 0:
        v.append(Violation("G_truncated_w5", "soft", "W5 does not pass W3: a truncation (sec 1)"))
    return v


def _diagonal(pattern: str, s: int, p: dict[str, Point]) -> list[Violation]:
    v: list[Violation] = []
    if "2" in p and not s * (p["2"].price - p["0"].price) > 0:
        v.append(Violation("D1_w2_beyond_start_w1", "R", "W2 at or beyond the start of W1 (sec 2)"))
    if "3" in p and not s * (p["3"].price - p["1"].price) > 0:
        v.append(Violation("D2_w3_not_beyond_w1", "R", "W3 does not pass the end of W1 (sec 2)"))
    if "4" in p and not s * (p["4"].price - p["2"].price) > 0:
        v.append(Violation("D4_w4_beyond_end_w2", "R", "W4 at or beyond the end of W2 (sec 2)"))
    if "4" in p and s * (p["4"].price - p["1"].price) >= 0:
        v.append(Violation("D5_no_overlap", "soft", "W4 stays out of W1: the defining overlap is missing, the book allows it in crypto (sec 2 G)"))
    if "5" in p:
        w1, w3, w5 = _lin(p["0"].price, p["1"].price), _lin(p["2"].price, p["3"].price), _lin(p["4"].price, p["5"].price)
        g1, g3, g5 = _log(p["0"].price, p["1"].price), _log(p["2"].price, p["3"].price), _log(p["4"].price, p["5"].price)
        if (w3 < w1 and w3 < w5) and (g3 < g1 and g3 < g5):
            v.append(Violation("D3_w3_shortest", "R", "W3 is the shortest of 1, 3, 5 (sec 2)"))
        w2, w4 = _lin(p["1"].price, p["2"].price), _lin(p["3"].price, p["4"].price)
        contracting = w3 < w1 and w4 < w2 and w5 < w3
        expanding = w3 > w1 and w4 > w2 and w5 > w3 and s * (p["5"].price - p["3"].price) > 0
        if not (contracting or expanding):
            v.append(Violation("D6_not_contracting_or_expanding", "R", "neither 3<1,4<2,5<3 nor 3>1,4>2,5>3 with W5 past W3 (sec 2)"))
        if _breaks_min(ratio(p["3"].price, p["4"].price, p["4"].price, p["5"].price), 0.618):
            v.append(Violation("D7_w5_under_618_of_w4", "R", "W5 under 0.618 of W4 (sec 2)"))
        if pattern == LD and not s * (p["5"].price - p["3"].price) > 0:
            v.append(Violation("D8_ld_w5_not_beyond_w3", "R", "a leading diagonal's W5 must end beyond W3 (sec 2)"))
    return v


def _zigzag(s: int, p: dict[str, Point]) -> list[Violation]:
    v: list[Violation] = []
    if "B" in p and not s * (p["B"].price - p["0"].price) > 0:
        v.append(Violation("Z1_b_beyond_start_a", "R", "B at or beyond the start of A (sec 3)"))
    if "C" in p:
        if _breaks_min(ratio(p["0"].price, p["A"].price, p["B"].price, p["C"].price), 0.618):
            v.append(Violation("Z2_c_under_618", "R", "C under 0.618 of A from B (sec 3)"))
        if s * (p["C"].price - p["A"].price) <= 0:
            v.append(Violation("G_c_not_beyond_a", "soft", "C does not pass the end of A, usually it does (sec 3)"))
    if "B" in p:
        r = ratio(p["0"].price, p["A"].price, p["A"].price, p["B"].price)
        if not (0.33 <= r[0] <= 0.82 or 0.33 <= r[1] <= 0.82):
            v.append(Violation("G_b_outside_range", "soft", f"B retraces {r[0]:.2f} of A, range 0.38-0.79 (sec 3)"))
    return v


def _flat(pattern: str, s: int, p: dict[str, Point]) -> list[Violation]:
    v: list[Violation] = []
    if "B" in p:
        r = ratio(p["0"].price, p["A"].price, p["A"].price, p["B"].price)
        if _breaks_max(r, 1.618):
            v.append(Violation("F1_b_at_1618", "R", f"B is {r[0]:.2f} of A, at 1.618 it is not a B (sec 3)"))
        beyond = s * (p["B"].price - p["0"].price) <= 0  # past the start of A
        if pattern == FLAT_REG and r[0] > 1.05 and r[1] > 1.05:
            v.append(Violation("F2_regular_b_too_long", "R", f"regular flat B is {r[0]:.2f} of A, ceiling about 1.05 (sec 3, K1)"))
        if pattern in (FLAT_RUN, FLAT_EXP) and not beyond:
            v.append(Violation("F3_b_not_beyond_start", "R", "running or expanded flat needs B past the start of A (sec 3)"))
        if r[0] < 0.38 and r[1] < 0.38:
            v.append(Violation("G_flat_b_shallow", "soft", f"flat B only {r[0]:.2f} of A (sec 3 G)"))
    if "C" in p:
        if _breaks_min(ratio(p["0"].price, p["A"].price, p["B"].price, p["C"].price), 0.618):
            v.append(Violation("F4_c_under_618", "R", "C under 0.618 of A from B (sec 3)"))
        passes = s * (p["C"].price - p["A"].price) > 0
        if pattern == FLAT_RUN and passes:
            v.append(Violation("F5_running_c_passes_a", "R", "running flat C must not pass the end of A (sec 3)"))
        if pattern == FLAT_EXP and not passes:
            v.append(Violation("F6_expanded_c_short_of_a", "R", "expanded flat C must pass the end of A (sec 3)"))
    return v


def _triangle(s: int, p: dict[str, Point], expanding: bool = False) -> list[Violation]:
    v: list[Violation] = []
    if expanding:
        return v
    if "C" in p and s * (p["C"].price - p["A"].price) > 0:
        v.append(Violation("T1_c_beyond_a", "R", "C beyond A (sec 3)"))
    if "D" in p and s * (p["D"].price - p["B"].price) < 0:
        v.append(Violation("T2_d_beyond_b", "R", "D beyond B (sec 3)"))
    if "E" in p:
        if s * (p["E"].price - p["C"].price) > 0:
            v.append(Violation("T3_e_beyond_c", "R", "E beyond C (sec 3)"))
        if _breaks_min(ratio(p["C"].price, p["D"].price, p["D"].price, p["E"].price), 0.382):
            v.append(Violation("T4_e_under_382", "R", "E under 0.382 of C to D (sec 3)"))
    return v


def _combo(s: int, p: dict[str, Point]) -> list[Violation]:
    v: list[Violation] = []
    if "X" in p and _breaks_min(ratio(p["0"].price, p["W"].price, p["W"].price, p["X"].price), 0.01):
        v.append(Violation("W1_x_under_1pct", "R", "X under 1 percent of W (sec 3)"))
    if "Y" in p and _breaks_min(ratio(p["0"].price, p["W"].price, p["X"].price, p["Y"].price), 0.618):
        v.append(Violation("W2_y_under_618", "R", "Y under 0.618 of W from X (sec 3)"))
    if "X2" in p and "X" in p and s * (p["X2"].price - p["X"].price) < 0:
        v.append(Violation("W3_second_x_beyond_first", "R", "second X beyond first X (sec 3)"))
    if "Z" in p and _breaks_max(ratio(p["0"].price, p["W"].price, p["X2"].price, p["Z"].price), 1.618 + 1e-9):
        v.append(Violation("G_z_over_1618", "soft", "Z over 1.618 of W (sec 3)"))
    if "Y" in p and _breaks_max(ratio(p["0"].price, p["W"].price, p["X"].price, p["Y"].price), 1.618 + 1e-9):
        v.append(Violation("G_y_over_1618", "soft", "Y over 1.618 of W, more likely a W3, a C or a flat (sec 3)"))
    return v


# When the last label is the running extreme of an unfinished wave, a rule that sets a minimum for that wave cannot be
# judged yet. Rules that set a limit it has already broken still can.
_ONLY_WHEN_DONE = {
    "2": {"C_w2_under_min_time", "G_w2_outside_fib"},
    "3": {"I2_w3_not_beyond_w1", "D2_w3_not_beyond_w1"},
    "4": {"C_w4_under_min_time", "G_w4_outside_fib"},
    "5": {"D6_not_contracting_or_expanding", "D7_w5_under_618_of_w4", "D8_ld_w5_not_beyond_w3", "G_truncated_w5"},
    "C": {"Z2_c_under_618", "F4_c_under_618", "F6_expanded_c_short_of_a", "G_c_not_beyond_a"},
    "E": {"T4_e_under_382"},
    "Y": {"W2_y_under_618"},
    "B": {"F3_b_not_beyond_start"},
}


def violations(pattern: str, direction: str, labels: dict[str, Point], open_last: bool = False) -> list[Violation]:
    """All rule breaks of one structure. `direction` is the direction of its first wave. open_last: the last label is
    still running."""
    if pattern not in PATTERNS:
        return [Violation("S3_unknown_pattern", "R", f"pattern {pattern!r}")]
    s = 1 if direction == "up" else -1
    if "0" not in labels:
        return [Violation("S4_no_origin", "R", "no label 0: rules cannot be checked")]
    out = _violations(pattern, s, labels)
    if open_last:
        seq = [lab for lab in ORDER[pattern] if lab in labels]
        skip = _ONLY_WHEN_DONE.get(seq[-1], set())
        out = [v for v in out if v.rule not in skip]
    return out


def _violations(pattern: str, s: int, labels: dict[str, Point]) -> list[Violation]:
    out = _order_issues(pattern, s, labels)
    if pattern == IMPULSE:
        out += _impulse(s, labels)
    elif pattern in (LD, ED):
        out += _diagonal(pattern, s, labels)
    elif pattern == ZIGZAG:
        out += _zigzag(s, labels)
    elif pattern in FLATS:
        out += _flat(pattern, s, labels)
    elif pattern == TRIANGLE:
        out += _triangle(s, labels)
    elif pattern == COMBO:
        out += _combo(s, labels)
    return out


def hard(vs: list[Violation]) -> list[Violation]:
    return [x for x in vs if x.severity == "R"]


def _ext(a: float, b: float, c: float, k: float, s: int) -> list[float]:
    """The k extension of a-b projected from c, linear and log: the book uses log on a log chart."""
    lin = c + s * k * abs(b - a)
    out = [lin]
    if a > 0 and b > 0 and c > 0:
        out.append(c * (max(a, b) / min(a, b)) ** (s * k))
    return out


def _ret(a: float, b: float, k: float) -> list[float]:
    """The k retracement of a-b, measured back from b, linear and log."""
    out = [b - k * (b - a)]
    if a > 0 and b > 0:
        out.append(b * (a / b) ** k)
    return out


def rule_levels(pattern: str, direction: str, labels: dict[str, Point]) -> dict:
    """Where the rulebook puts the invalidation and the next targets, given the last printed label.

    `direction` is the direction of the structure's first wave. Returns {"next": label, "invalidation": [(price, rule)],
    "targets": [(price, rule)], "next_move": "up"/"down"}. The candidates are generous on purpose: an answer fails only
    when it matches none of them.
    """
    s = 1 if direction == "up" else -1
    seq = [lab for lab in ORDER.get(pattern, []) if lab in labels]
    if not seq or "0" not in labels:
        return {"next": None, "invalidation": [], "targets": [], "next_move": None}
    last = seq[-1]
    p = {k: labels[k].price for k in seq}
    inv: list[tuple[float, str]] = []
    tgt: list[tuple[float, str]] = []
    nxt = None
    move = None
    if pattern in (IMPULSE, LD, ED):
        if last == "1":
            nxt, move = "2", -s
            inv.append((p["0"], "W2 not beyond start of W1"))
            for k in (0.382, 0.5, 0.618, 0.786):
                tgt += [(x, f"W2 ret pull 0-1 {k}") for x in _ret(p["0"], p["1"], k)]
        elif last == "2":
            nxt, move = "3", s
            inv.append((p["0"], "W2 not beyond start of W1"))
            inv.append((p["2"], "end of W2 must hold"))
            for k in (1.0, 1.618, 2.618, 3.236):
                tgt += [(x, f"W3 ext pull 0-1-2 {k}") for x in _ext(p["0"], p["1"], p["2"], k, s)]
            for k in (2.236, 3.236, 4.236):
                tgt += [(x, f"W5 ext pull 0-1-2 {k}") for x in _ext(p["0"], p["1"], p["2"], k, s)]
            if pattern != IMPULSE:
                for k in (0.618, 0.786, 1.0, 1.236, 1.382, 1.618):
                    tgt += [(x, f"diag W3 ext {k}") for x in _ext(p["0"], p["1"], p["2"], k, s)]
        elif last == "3":
            nxt, move = "4", -s
            inv.append((p["1"], "W4 not into W1"))
            inv.append((p["2"], "W4 not beyond end of W2 (diagonal)"))
            for k in (0.236, 0.382, 0.5, 0.618):
                tgt += [(x, f"W4 ret pull 2-3 {k}") for x in _ret(p["2"], p["3"], k)]
        elif last == "4":
            nxt, move = "5", s
            inv.append((p["1"], "W4 not into W1"))
            inv.append((p["2"], "W4 not beyond end of W2 (diagonal)"))
            inv.append((p["4"], "end of W4 must hold"))
            for k in (0.618, 1.0, 1.236, 1.618):
                tgt += [(x, f"W5 ext pull 0-1-4 {k}") for x in _ext(p["0"], p["1"], p["4"], k, s)]
            for k in (1.618, 2.236, 2.618, 3.236, 4.236):
                tgt += [(x, f"W5 ext pull 0-1-2 {k}") for x in _ext(p["0"], p["1"], p["2"], k, s)]
            if "3" in p:
                for k in (0.618, 1.0, 1.618):
                    tgt += [(x, f"W5 ext net 0-3 from 4 {k}") for x in _ext(p["0"], p["3"], p["4"], k, s)]
        elif last == "5":
            nxt, move = "A or next-degree 2", -s
            inv.append((p["0"], "completed 5: origin"))
            inv.append((p["5"], "a new extreme means the 5 is not done"))
            inv.append((p["4"], "end of W4"))
            for k in (0.236, 0.382, 0.5, 0.618, 0.786, 1.0):
                tgt += [(x, f"ret pull 0-5 {k}") for x in _ret(p["0"], p["5"], k)]
                tgt += [(x, f"ret pull 4-5 {k}") for x in _ret(p["4"], p["5"], k)]
                tgt += [(x, f"ret pull 2-5 {k}") for x in _ret(p["2"], p["5"], k)]
                tgt += [(x, f"ret pull 3-5 region {k}") for x in _ret(p["3"], p["4"], k)]
    elif pattern in (ZIGZAG, FLAT_REG, FLAT_RUN, FLAT_EXP):
        flat = pattern != ZIGZAG
        if last == "A":
            nxt, move = "B", -s
            inv.append((p["0"], "B not beyond start of A"))
            if flat:
                inv += [(x, "B at 1.618 of A") for x in _ret(p["A"], p["0"], -0.618)]
            for k in (0.382, 0.5, 0.618, 0.786, 1.0, 1.236, 1.382):
                tgt += [(x, f"B ret pull 0-A {k}") for x in _ret(p["0"], p["A"], k)]
        elif last == "B":
            nxt, move = "C", s
            inv.append((p["0"], "B not beyond start of A"))
            inv.append((p["B"], "end of B must hold"))
            if flat:
                inv += [(x, "B at 1.618 of A") for x in _ret(p["0"], p["A"], 1.618)]
            for k in (0.618, 1.0, 1.236, 1.382, 1.618, 2.236):
                tgt += [(x, f"C ext pull 0-A-B {k}") for x in _ext(p["0"], p["A"], p["B"], k, s)]
        elif last == "C":
            nxt, move = "next structure", -s
            inv.append((p["C"], "a new extreme means C is not done"))
            inv.append((p["B"], "completed 5: origin of C"))
            inv.append((p["0"], "start of the correction"))
            for k in (0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.236, 1.618):
                tgt += [(x, f"ret pull 0-C {k}") for x in _ret(p["0"], p["C"], k)]
                tgt += [(x, f"ret pull B-C {k}") for x in _ret(p["B"], p["C"], k)]
                tgt += [(x, f"ext pull A-B-C {k}") for x in _ext(p["A"], p["B"], p["C"], k, -s)]
    elif pattern == TRIANGLE:
        nxt = {"A": "B", "B": "C", "C": "D", "D": "E", "E": "thrust"}[last] if last in "ABCDE" else None
        for lab in seq:
            inv.append((p[lab], f"triangle boundary {lab}"))
        for a, b in zip(seq, seq[1:]):
            for k in (0.382, 0.5, 0.618, 0.786, 1.0):
                tgt += [(x, f"triangle leg ret {a}-{b} {k}") for x in _ret(p[a], p[b], k)]
        if last == "E" and "A" in p:
            move = s if len(seq) % 2 == 1 else -s
            tgt += [(x, "height A to 0 from E") for x in _ext(p["0"], p["A"], p["E"], 1.0, s)]
    elif pattern == COMBO:
        if last == "W":
            nxt, move = "X", -s
            inv.append((p["0"], "start of W"))
            for k in (0.382, 0.5, 0.618, 0.786, 1.0, 1.236, 1.382):
                tgt += [(x, f"X ret pull 0-W {k}") for x in _ret(p["0"], p["W"], k)]
        elif last == "X":
            nxt, move = "Y", s
            inv.append((p["0"], "start of W"))
            inv.append((p["X"], "end of X must hold"))
            for k in (0.618, 1.0, 1.236, 1.618):
                tgt += [(x, f"Y ext pull 0-W-X {k}") for x in _ext(p["0"], p["W"], p["X"], k, s)]
        elif last == "Y":
            nxt, move = "next structure", -s
            inv.append((p["Y"], "a new extreme means Y is not done"))
            inv.append((p["X"], "origin of Y"))
            inv.append((p["0"], "start of the combination"))
            for k in (0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.236):
                tgt += [(x, f"ret pull 0-Y {k}") for x in _ret(p["0"], p["Y"], k)]
                tgt += [(x, f"ret pull X-Y {k}") for x in _ret(p["X"], p["Y"], k)]
        elif last == "X2":
            nxt, move = "Z", s
            inv.append((p["X2"], "end of second X"))
            inv.append((p["X"], "second X not beyond first X"))
            for k in (0.618, 1.0, 1.236, 1.382, 1.618):
                tgt += [(x, f"Z ext pull 0-W-X2 {k}") for x in _ext(p["0"], p["W"], p["X2"], k, s)]
        elif last == "Z":
            nxt, move = "next structure", -s
            inv.append((p["Z"], "a new extreme means Z is not done"))
            inv.append((p["0"], "start of the combination"))
            for k in (0.382, 0.5, 0.618, 0.786, 1.0):
                tgt += [(x, f"ret pull 0-Z {k}") for x in _ret(p["0"], p["Z"], k)]
    if nxt is None:
        return {"next": None, "invalidation": inv, "targets": tgt, "next_move": None}
    return {"next": nxt, "invalidation": inv, "targets": tgt, "next_move": ("up" if move == 1 else "down" if move == -1 else None)}


__all__ = ["Point", "Violation", "violations", "hard", "rule_levels", "ratio", "ORDER", "PATTERNS", "FLATS", "IMPULSE", "LD",
           "ED", "ZIGZAG", "FLAT_REG", "FLAT_RUN", "FLAT_EXP", "TRIANGLE", "COMBO"]
