"""NewWave hard rules for one labelled structure, sections 0 to 4 of the compact rulebook. Numbers and logic only.

    Checker(cfg.rules).violations(pattern, s, labels) -> list[Violation]

`labels` maps a wave label to a Point(bar, price). `s` is +1 when the structure's first wave goes up. Partial structures
are allowed: a rule that needs a missing point is skipped. Only rules live here: a break kills the count. Guidelines
rank, and live in score.py; the minimum correction time is one of those since round 4 (FIB-T3 is filed under CONVENTION, and
its stated consequence is "the pivots are wrong or the correction is unfinished"). What a wave holds inside is a rule too,
and lives in inside.py, because it needs the bars. A length rule breaks only when it breaks on both log and linear, because the book allows
either on wide ranges (sec 4).
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log

IMPULSE = "impulse"
LD = "leading_diagonal"
ED = "ending_diagonal"
ZIGZAG = "zigzag"
FLAT = "flat"
TRIANGLE = "triangle"
COMBO = "combination"
TRIPLE = "triple_combination"
PATTERNS = (IMPULSE, LD, ED, ZIGZAG, FLAT, TRIANGLE, COMBO, TRIPLE)
MOTIVE = {IMPULSE, LD, ED}
CORRECTIVE = {ZIGZAG, FLAT, TRIANGLE, COMBO, TRIPLE}
WAVES = {
    IMPULSE: ["1", "2", "3", "4", "5"], LD: ["1", "2", "3", "4", "5"], ED: ["1", "2", "3", "4", "5"],
    ZIGZAG: ["A", "B", "C"], FLAT: ["A", "B", "C"], TRIANGLE: ["A", "B", "C", "D", "E"], COMBO: ["W", "X", "Y"],
    TRIPLE: ["W", "X", "Y", "X2", "Z"],
}
FAMILY = {IMPULSE: "impulse", LD: "diagonal", ED: "diagonal", ZIGZAG: "zigzag", FLAT: "flat", TRIANGLE: "triangle", COMBO: "combination", TRIPLE: "combination"}


@dataclass(frozen=True)
class Point:
    bar: float
    price: float


@dataclass(frozen=True)
class Violation:
    rule: str
    note: str


def lengths(a0: float, a1: float, b0: float, b1: float) -> tuple[float, float]:
    """len(b) / len(a), linear and log. A zero-length a gives infinity."""
    la, lb = abs(a1 - a0), abs(b1 - b0)
    ga, gb = abs(log(a1 / a0)), abs(log(b1 / b0))
    return (lb / la if la else float("inf"), gb / ga if ga else float("inf"))


class Checker:
    def __init__(self, numbers: dict):
        self.n = numbers

    def _impulse(self, s: int, p: dict) -> list[Violation]:
        v = []
        if "2" in p:
            if s * (p["2"].price - p["0"].price) <= 0:
                v.append(Violation("I1_w2_beyond_start", "W2 at or beyond the start of W1 (sec 1)"))
        if "3" in p and s * (p["3"].price - p["1"].price) <= 0:
            v.append(Violation("I2_w3_not_beyond_w1", "W3 does not pass the end of W1 (sec 1)"))
        if "4" in p:
            if s * (p["4"].price - p["1"].price) < 0:
                v.append(Violation("I4_w4_into_w1", "W4 enters W1 territory (sec 1)"))
        if "5" in p:
            w1 = lengths(p["2"].price, p["3"].price, p["0"].price, p["1"].price)  # W1 / W3
            w5 = lengths(p["2"].price, p["3"].price, p["4"].price, p["5"].price)  # W5 / W3
            if (w1[0] > 1 and w5[0] > 1) and (w1[1] > 1 and w5[1] > 1):
                v.append(Violation("I3_w3_shortest", "W3 is the shortest of 1, 3, 5 (sec 1)"))
            if s * (p["5"].price - p["3"].price) < 0:
                r = lengths(p["3"].price, p["4"].price, p["4"].price, p["5"].price)
                if r[0] < self.n["truncated_w5_min"] and r[1] < self.n["truncated_w5_min"]:
                    v.append(Violation("I7_truncation_too_deep", "W5 far short of W3: not a truncation (ours, sec 1)"))
        return v

    def _diagonal(self, pattern: str, s: int, p: dict) -> list[Violation]:
        v = []
        if "2" in p:
            if s * (p["2"].price - p["0"].price) <= 0:
                v.append(Violation("D1_w2_beyond_start", "W2 at or beyond the start of W1 (sec 2)"))
        if "3" in p and s * (p["3"].price - p["1"].price) <= 0:
            v.append(Violation("D2_w3_not_beyond_w1", "W3 does not pass the end of W1 (sec 2)"))
        if "4" in p:
            if s * (p["4"].price - p["2"].price) <= 0:
                v.append(Violation("D4_w4_beyond_w2", "W4 at or beyond the end of W2 (sec 2)"))
            if s * (p["4"].price - p["1"].price) >= 0:
                v.append(Violation("D5_no_overlap", "W4 stays out of W1: not this diagonal (sec 2)"))
        if "5" in p:
            w1 = abs(p["1"].price - p["0"].price)
            w2 = abs(p["2"].price - p["1"].price)
            w3 = abs(p["3"].price - p["2"].price)
            w4 = abs(p["4"].price - p["3"].price)
            w5 = abs(p["5"].price - p["4"].price)
            if w3 < w1 and w3 < w5:
                v.append(Violation("D3_w3_shortest", "W3 is the shortest of 1, 3, 5 (sec 2)"))
            past = s * (p["5"].price - p["3"].price) > 0
            if not ((w3 < w1 and w4 < w2 and w5 < w3) or (w3 > w1 and w4 > w2 and w5 > w3 and past)):
                v.append(Violation("D6_shape", "neither contracting nor expanding (sec 2)"))
            r = lengths(p["3"].price, p["4"].price, p["4"].price, p["5"].price)
            if r[0] < self.n["diagonal_w5_min"] and r[1] < self.n["diagonal_w5_min"]:
                v.append(Violation("D7_w5_short", "W5 under the minimum against W4 (sec 2)"))
            if pattern == LD and not past:
                v.append(Violation("D8_ld_w5_not_past_w3", "a leading diagonal's W5 must end beyond W3 (sec 2)"))
        return v

    def _correction_common(self, s: int, p: dict) -> list[Violation]:
        v = []
        if "C" in p:
            r = lengths(p["0"].price, p["A"].price, p["B"].price, p["C"].price)
            if r[0] < self.n["c_min_ext"] and r[1] < self.n["c_min_ext"]:
                v.append(Violation("C2_c_short", "C under the minimum extension of A from B (sec 3)"))
        return v

    def _zigzag(self, s: int, p: dict) -> list[Violation]:
        v = self._correction_common(s, p)
        if "B" in p and s * (p["B"].price - p["0"].price) <= 0:
            v.append(Violation("Z1_b_beyond_start", "B at or beyond the start of A (sec 3)"))
        return v

    def _flat(self, s: int, p: dict) -> list[Violation]:
        v = self._correction_common(s, p)
        if "B" in p:
            r = lengths(p["0"].price, p["A"].price, p["A"].price, p["B"].price)
            if r[0] >= self.n["flat_b_max"] and r[1] >= self.n["flat_b_max"]:
                v.append(Violation("F1_b_too_long", f"B is {r[0]:.2f} of A: at the ceiling it is not a B (sec 3)"))
        return v

    def _triangle(self, s: int, p: dict) -> list[Violation]:
        v = []
        if "C" in p and s * (p["C"].price - p["A"].price) > 0:
            v.append(Violation("T1_c_beyond_a", "C beyond A (sec 3)"))
        if "D" in p and s * (p["D"].price - p["B"].price) < 0:
            v.append(Violation("T2_d_beyond_b", "D beyond B (sec 3)"))
        if "E" in p:
            if s * (p["E"].price - p["C"].price) > 0:
                v.append(Violation("T3_e_beyond_c", "E beyond C (sec 3)"))
            r = lengths(p["C"].price, p["D"].price, p["D"].price, p["E"].price)
            if r[0] < self.n["triangle_e_min"] and r[1] < self.n["triangle_e_min"]:
                v.append(Violation("T4_e_short", "E under the minimum of C to D (sec 3)"))
        return v

    def _combo(self, s: int, p: dict) -> list[Violation]:
        v = []
        if "X" in p:
            r = lengths(p["0"].price, p["W"].price, p["W"].price, p["X"].price)
            if r[0] < self.n["x_min_ret"] and r[1] < self.n["x_min_ret"]:
                v.append(Violation("W1_x_too_small", "X under the minimum of W (sec 3)"))
            if r[0] >= self.n["flat_b_max"] and r[1] >= self.n["flat_b_max"]:
                v.append(Violation("W5_x_too_long", "X at the flat ceiling of W: a WXY is a flat ending in a 3 (ours, sec 3)"))
        if "Y" in p:
            r = lengths(p["0"].price, p["W"].price, p["X"].price, p["Y"].price)
            if r[0] < self.n["y_min_ext"] and r[1] < self.n["y_min_ext"]:
                v.append(Violation("W2_y_short", "Y under the minimum extension of W (sec 3)"))
        return v

    def _triple(self, s: int, p: dict) -> list[Violation]:
        """W-X-Y-X-Z (sec 3): a double three with a second connector and a last leg."""
        v = self._combo(s, p)
        if "X2" in p:
            if s * (p["X2"].price - p["X"].price) < 0:
                v.append(Violation("W6_x2_beyond_x", "the second X beyond the first (sec 3)"))
        return v

    def violations(self, pattern: str, s: int, p: dict) -> list[Violation]:
        if pattern not in WAVES:
            return [Violation("S3_unknown_pattern", f"pattern {pattern!r}")]
        if "0" not in p:
            return [Violation("S4_no_origin", "no origin")]
        seq = ["0", *[w for w in WAVES[pattern] if w in p]]
        want = ["0", *WAVES[pattern]][:len(seq)]
        out = []
        if seq != want or len(seq) != len(p):
            out.append(Violation("S0_labels_skipped", f"labels {list(p)} do not run in order"))
            return out
        for k, (a, b) in enumerate(zip(seq, seq[1:])):
            if p[b].bar < p[a].bar:
                out.append(Violation("S1_time_order", f"{b} is before {a}"))
            step = s if k % 2 == 0 else -s
            if step * (p[b].price - p[a].price) <= 0:
                out.append(Violation("S2_wave_direction", f"{a} to {b} moves the wrong way"))
        if out:
            return out
        if pattern == IMPULSE:
            return self._impulse(s, p)
        if pattern in (LD, ED):
            return self._diagonal(pattern, s, p)
        if pattern == ZIGZAG:
            return self._zigzag(s, p)
        if pattern == FLAT:
            return self._flat(s, p)
        if pattern == TRIANGLE:
            return self._triangle(s, p)
        if pattern == TRIPLE:
            return self._triple(s, p)
        return self._combo(s, p)

    def legal(self, pattern: str, s: int, p: dict) -> bool:
        return not self.violations(pattern, s, p)


def flat_kind(s: int, p: dict[str, float]) -> str:
    """Regular, running or expanded (sec 3), from label prices. Before C prints, a B past the start can still be either of the last two."""
    if "B" not in p:
        return "flat"
    if s * (p["B"] - p["0"]) > 0:
        return "regular"
    if "C" not in p:
        return "running or expanded"
    return "expanded" if s * (p["C"] - p["A"]) > 0 else "running"
