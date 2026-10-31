"""NewWave hard-rule checker for 5-wave impulse candidates, and the corrective (three-leg) candidates of section C.

Rules from the compact rulebook section 1, in the order lesson 14 checks them, with wave 3 beyond wave 1 added:
  R1  W2 never beyond the start of W1
  R2  W3 always beyond the end of W1
  R3  W3 never the shortest of 1, 3, 5
  R4  W4 never into W1 price territory (a non-diagonal)
A candidate is six consecutive pivots of one zigzag: degree comes from the threshold, each wave is a single leg at that
threshold, and sub-waves are not inspected. Direction is set by the first pivot.

Truncation (W5 ends short of W3) is a guideline in the rulebook, so it does not kill a candidate; it is flagged. Section
statistics use the non-truncated ones, the census reports both. A candidate failing only R4 is flagged as a diagonal
candidate if it also passes the diagonal rules of section 2 that a single-leg view can check.

Fib pull conventions (rulebook sections 1 and 4):
  w2      retracement pull 0-1      (p1-p2)/(p1-p0)
  w3      extension pull 0-1-2      (p3-p2)/(p1-p0)
  w4      retracement pull 2-3 only (p3-p4)/(p3-p2)
  w5_014  extension pull 0-1-4      (p5-p4)/(p1-p0)
  w5_012  extension pull 0-1-2      (p5-p2)/(p1-p0)
Times use the same pulls on the bar index of each pivot. Ratios exist in log and in linear price.

Not a script.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from zigzag import Pivots

R1, R2, R3, R4, TRUNCATED, DIAGONAL = 1, 2, 4, 8, 16, 32
RULE_NAMES = {R1: "R1 W2 beyond start of W1", R2: "R2 W3 not beyond W1", R3: "R3 W3 shortest", R4: "R4 W4 into W1"}
RATIOS = ("w2", "w3", "w4", "w5_014", "w5_012")
TIMES = ("t2_t1", "t3_t1", "t4_t3", "t4_t2", "t5_t1", "t5_t3")


def _windows(x: np.ndarray, size: int) -> np.ndarray:
    return np.lib.stride_tricks.sliding_window_view(x, size)


@dataclass(frozen=True)
class Candidates:
    """One row per six-pivot window of a zigzag."""
    start: np.ndarray      # position of p0 in the pivot list
    direction: np.ndarray  # +1 up impulse (p0 is a low), -1 down impulse
    flags: np.ndarray      # bit mask of broken rules plus TRUNCATED and DIAGONAL, on log price
    r3_linear: np.ndarray  # R3 broken on linear price: the only rule where the price scale can matter
    log: dict[str, np.ndarray]
    lin: dict[str, np.ndarray]
    time: dict[str, np.ndarray]
    i: np.ndarray          # bars of p0..p5, shape (n, 6)
    confirmed_p5: np.ndarray

    def __len__(self) -> int:
        return self.start.size

    @property
    def rules_ok(self) -> np.ndarray:
        return (self.flags & (R1 | R2 | R3 | R4)) == 0

    @property
    def legal(self) -> np.ndarray:
        """Passes every hard rule and W5 ends beyond W3."""
        return self.rules_ok & ((self.flags & TRUNCATED) == 0)

    @property
    def truncated(self) -> np.ndarray:
        return self.rules_ok & ((self.flags & TRUNCATED) != 0)

    @property
    def diagonal(self) -> np.ndarray:
        return (self.flags & DIAGONAL) != 0

    def subset(self, mask: np.ndarray) -> "Candidates":
        return Candidates(self.start[mask], self.direction[mask], self.flags[mask], self.r3_linear[mask],
                          {k: v[mask] for k, v in self.log.items()}, {k: v[mask] for k, v in self.lin.items()},
                          {k: v[mask] for k, v in self.time.items()}, self.i[mask], self.confirmed_p5[mask])


def _ratios(q: np.ndarray) -> dict[str, np.ndarray]:
    """q: signed so that the impulse rises, shape (n, 6)."""
    w1 = q[:, 1] - q[:, 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        return {
            "w2": (q[:, 1] - q[:, 2]) / w1,
            "w3": (q[:, 3] - q[:, 2]) / w1,
            "w4": (q[:, 3] - q[:, 4]) / (q[:, 3] - q[:, 2]),
            "w5_014": (q[:, 5] - q[:, 4]) / w1,
            "w5_012": (q[:, 5] - q[:, 2]) / w1,
        }


def check(piv: Pivots) -> Candidates:
    """Every six-pivot window of the zigzag, with the rules it breaks."""
    if len(piv) < 6:
        empty = np.empty(0)
        e_i = np.empty(0, np.int64)
        return Candidates(e_i, e_i, e_i, np.empty(0, bool), {k: empty for k in RATIOS}, {k: empty for k in RATIOS},
                          {k: empty for k in TIMES}, np.empty((0, 6), np.int64), e_i)
    x = _windows(piv.x, 6)
    n = x.shape[0]
    direction = np.where(piv.kind[:n] == -1, 1, -1)
    q = (x - x[:, :1]) * direction[:, None]
    w1, w3, w5 = q[:, 1], q[:, 3] - q[:, 2], q[:, 5] - q[:, 4]
    w2, w4 = q[:, 1] - q[:, 2], q[:, 3] - q[:, 4]
    flags = np.zeros(n, np.int64)
    flags |= np.where(q[:, 2] <= 0, R1, 0)
    flags |= np.where(q[:, 3] <= q[:, 1], R2, 0)
    flags |= np.where((w3 <= w1) & (w3 <= w5), R3, 0)
    flags |= np.where(q[:, 4] <= q[:, 1], R4, 0)
    flags |= np.where(q[:, 5] <= q[:, 3], TRUNCATED, 0)
    # Diagonal: only R4 broken, W4 stays above the end of W2, W5 reaches .618 of W4, and the shape contracts or expands.
    only_r4 = (flags & (R1 | R2 | R3 | R4)) == R4
    contracting = (w3 < w1) & (w4 < w2) & (w5 < w3)
    expanding = (w3 > w1) & (w4 > w2) & (w5 > w3) & (q[:, 5] > q[:, 3])
    flags |= np.where(only_r4 & (q[:, 4] > q[:, 2]) & (w5 >= 0.618 * w4) & (contracting | expanding), DIAGONAL, 0)

    p = np.exp(x)
    lin = (p - p[:, :1]) * direction[:, None]
    w1l, w3l, w5l = lin[:, 1], lin[:, 3] - lin[:, 2], lin[:, 5] - lin[:, 4]
    r3_linear = (w3l <= w1l) & (w3l <= w5l)

    i = _windows(piv.i, 6)
    d = np.diff(i, axis=1).astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        time = {
            "t2_t1": d[:, 1] / d[:, 0],
            "t3_t1": d[:, 2] / d[:, 0],
            "t4_t3": d[:, 3] / d[:, 2],
            "t4_t2": d[:, 3] / d[:, 1],
            "t5_t1": d[:, 4] / d[:, 0],
            "t5_t3": d[:, 4] / d[:, 2],
        }
    return Candidates(np.arange(n), direction, flags, r3_linear, _ratios(q), _ratios(lin), time, i.copy(),
                      piv.confirmed[5:].copy())


STAGES = ("s1_w2_holds", "s2_w3_beyond_w1", "s3_w4_clear_of_w1", "s4_w5_completes", "s5_a_reaches_w4")


def stages(piv: Pivots) -> dict[str, np.ndarray]:
    """What the count predicts as it grows, one leg at a time, all knowable when the conditioning pivot confirms. Each
    entry: a 3 x n array, row 0 direction (+1 impulse up), row 1 whether the stage passed, row 2 the position of p0 in the
    pivot list, on the windows that reached the stage.
      s1  after W1:           W2 stops above the start of W1
      s2  after a legal W2:   W3 goes beyond the end of W1
      s3  after a legal W3:   W4 stays out of W1 territory
      s4  after a legal W4:   W5 goes beyond W3 and W3 is not the shortest
      s5  after a legal 5:    the next leg (A) reaches the end of W4
    """
    x = piv.x
    n = x.size
    out: dict[str, np.ndarray] = {}
    if n < 7:
        return {k: np.empty((3, 0)) for k in STAGES}
    direction = np.where(piv.kind == -1, 1.0, -1.0)
    pos = np.arange(n, dtype=float)
    # q[j, s]: pivot j+s relative to pivot j, signed so the impulse rises. NaN where it does not exist yet.
    q = np.full((n, 7), np.nan)
    for s in range(7):
        q[: n - s, s] = (x[s:] - x[: n - s]) * direction[: n - s]
    alive = np.isfinite(q[:, 2])
    pass1 = q[:, 2] > 0
    out["s1_w2_holds"] = np.vstack([direction[alive], pass1[alive], pos[alive]])
    alive = pass1 & np.isfinite(q[:, 3])
    pass2 = q[:, 3] > q[:, 1]
    out["s2_w3_beyond_w1"] = np.vstack([direction[alive], pass2[alive], pos[alive]])
    alive = alive & pass2 & np.isfinite(q[:, 4])
    pass3 = q[:, 4] > q[:, 1]
    out["s3_w4_clear_of_w1"] = np.vstack([direction[alive], pass3[alive], pos[alive]])
    alive = alive & pass3 & np.isfinite(q[:, 5])
    w1, w3, w5 = q[:, 1], q[:, 3] - q[:, 2], q[:, 5] - q[:, 4]
    pass4 = (q[:, 5] > q[:, 3]) & ~((w3 <= w1) & (w3 <= w5))
    out["s4_w5_completes"] = np.vstack([direction[alive], pass4[alive], pos[alive]])
    alive = alive & pass4 & np.isfinite(q[:, 6])
    pass5 = q[:, 6] <= q[:, 4]
    out["s5_a_reaches_w4"] = np.vstack([direction[alive], pass5[alive], pos[alive]])
    return out


def first_broken(flags: np.ndarray) -> dict[str, int]:
    """Which rule kills a candidate first, in checking order."""
    out = {}
    alive = np.ones(flags.size, bool)
    for bit, name in RULE_NAMES.items():
        hit = alive & ((flags & bit) != 0)
        out[name] = int(hit.sum())
        alive &= ~hit
    return out


def non_overlapping(c: Candidates) -> int:
    """Greedy count of candidates that share no bar: a rough count of independent structures at this scale."""
    count, last_end = 0, -1
    for a, b in zip(c.i[:, 0], c.i[:, 5]):
        if a >= last_end:
            count += 1
            last_end = b
    return count


@dataclass(frozen=True)
class Threes:
    """Three-leg corrective candidates: A, B, C on four consecutive pivots. legal: B never beyond the start of A, C goes
    beyond the end of A (zigzag), and C is at least .618 of A (pull 0-A-B, rulebook section 3). legal_any also admits the
    flats: B up to but not including 1.618 of A, C at least .618 of A."""
    start: np.ndarray
    direction: np.ndarray  # direction of A and C: -1 a correction that falls
    legal: np.ndarray
    legal_any: np.ndarray
    i: np.ndarray          # bars of the 4 pivots
    confirmed_end: np.ndarray


def threes(piv: Pivots) -> Threes:
    if len(piv) < 4:
        e_i = np.empty(0, np.int64)
        return Threes(e_i, e_i, np.empty(0, bool), np.empty(0, bool), np.empty((0, 4), np.int64), e_i)
    x = _windows(piv.x, 4)
    n = x.shape[0]
    direction = np.where(piv.kind[:n] == -1, 1, -1)
    q = (x - x[:, :1]) * direction[:, None]
    a, b, c = q[:, 1], q[:, 1] - q[:, 2], q[:, 3] - q[:, 2]
    zigzag = (q[:, 2] > 0) & (q[:, 3] > q[:, 1]) & (c >= 0.618 * a)
    any_three = (b < 1.618 * a) & (c >= 0.618 * a)
    return Threes(np.arange(n), direction, zigzag, any_three, _windows(piv.i, 4).copy(), piv.confirmed[3:].copy())
