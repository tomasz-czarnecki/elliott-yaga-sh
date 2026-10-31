"""Every rule-legal reading of a pivot window, to measure how ambiguous it is.

The grammar follows section 0-3 of the rulebook. A wave between two pivots is either one leg of this zigzag (its inside
is not visible at this scale, so it may be a 3 or a 5) or a nested structure over an odd number of legs:

    motive     = leaf | impulse(motive corrective motive corrective motive) | diagonal(5 waves)
    corrective = leaf | zigzag(motive corrective motive) | flat(corrective corrective motive)
               | triangle(5 correctives) | combination(corrective corrective corrective)

Each nested node must pass rules.violations. `readings` lists the top-level structures that end at the last pivot,
because those are the ones a reader must choose between now, with the count of nested ways to fill each one in.

hidden_sub=True is the generous version: a motive wave may also show as three legs here, a five whose second correction
stayed under the zigzag threshold. The book says the smaller waves of a five need not subdivide visibly (sec 0).
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from rules import COMBO, ED, FLAT_EXP, FLAT_REG, FLAT_RUN, IMPULSE, LD, TRIANGLE, ZIGZAG, Point, hard, rule_levels, violations

FAMILY = {IMPULSE: "impulse", LD: "diagonal", ED: "diagonal", ZIGZAG: "zigzag", FLAT_REG: "flat", FLAT_RUN: "flat",
          FLAT_EXP: "flat", TRIANGLE: "triangle", COMBO: "combination"}


@dataclass(frozen=True)
class Reading:
    pattern: str
    direction: str        # of the first wave
    labels: tuple         # ((label, pivot index), ...)
    next_label: str | None
    next_move: str | None # up/down, what the structure expects next
    ways: int             # nested fillings of this skeleton
    invalidation: tuple   # prices the rulebook would name


def _splits(i: int, j: int, parts: int):
    """Strictly increasing cut points i < c1 < ... < c(parts-1) < j with every part spanning an odd number of legs."""
    if parts == 1:
        if (j - i) % 2 == 1:
            yield ()
        return
    for c in range(i + 1, j - (parts - 2), 2):
        for rest in _splits(c, j, parts - 1):
            yield (c, *rest)


class Grammar:
    def __init__(self, prices: list[float], bars: list[int], max_span: int = 19, hidden_sub: bool = False):
        self.p = prices
        self.b = bars
        self.n = len(prices)
        self.max_span = max_span
        self.hidden_sub = hidden_sub
        self._motive = lru_cache(maxsize=None)(self._motive_raw)
        self._corrective = lru_cache(maxsize=None)(self._corrective_raw)

    def _pts(self, labs: list[str], idx: tuple[int, ...]) -> dict[str, Point]:
        return {lab: Point(self.b[i], self.p[i]) for lab, i in zip(labs, idx)}

    def _dir(self, i: int, j: int) -> str:
        return "up" if self.p[j] > self.p[i] else "down"

    def legal(self, pattern: str, direction: str, labs: list[str], idx: tuple[int, ...]) -> bool:
        return not hard(violations(pattern, direction, self._pts(labs, idx)))

    def motive(self, i: int, j: int) -> int:
        return self._motive(i, j)

    def corrective(self, i: int, j: int) -> int:
        return self._corrective(i, j)

    def _motive_raw(self, i: int, j: int) -> int:
        span = j - i
        if span % 2 == 0 or span <= 0:
            return 0
        if span == 1:
            return 1
        if span == 3 and self.hidden_sub:
            sgn = 1 if self.p[j] > self.p[i] else -1
            return int(sgn * (self.p[i + 2] - self.p[i]) > 0 and sgn * (self.p[j] - self.p[i + 1]) > 0)
        if span < 5 or span > self.max_span:
            return 0
        d = self._dir(i, j)
        labs = ["0", "1", "2", "3", "4", "5"]
        ways = 0
        for cut in _splits(i, j, 5):
            a, b, c, e = cut
            idx = (i, a, b, c, e, j)
            impulse_ok = self.legal(IMPULSE, d, labs, idx)
            ending_ok = self.legal(ED, d, labs, idx)
            leading_ok = self.legal(LD, d, labs, idx)
            if not (impulse_ok or ending_ok or leading_ok):
                continue
            w2, w4 = self._corrective(a, b), self._corrective(c, e)
            if not w2 or not w4:
                continue
            m135 = self._motive(i, a) * self._motive(b, c) * self._motive(e, j)
            if impulse_ok:
                ways += m135 * w2 * w4
            if leading_ok:
                ways += m135 * w2 * w4  # 5-3-5-3-5
            if ending_ok or leading_ok:
                ways += self._corrective(i, a) * w2 * self._corrective(b, c) * w4 * self._corrective(e, j)  # 3-3-3-3-3
        return ways

    def _corrective_raw(self, i: int, j: int) -> int:
        span = j - i
        if span % 2 == 0 or span <= 0:
            return 0
        if span == 1:
            return 1
        if span > self.max_span:
            return 0
        d = self._dir(i, j)
        ways = 0
        for cut in _splits(i, j, 3):
            a, b = cut
            idx = (i, a, b, j)
            labs = ["0", "A", "B", "C"]
            if self.legal(ZIGZAG, d, labs, idx):
                ways += self._motive(i, a) * self._corrective(a, b) * self._motive(b, j)
            if any(self.legal(f, d, labs, idx) for f in (FLAT_REG, FLAT_RUN, FLAT_EXP)):
                ways += self._corrective(i, a) * self._corrective(a, b) * self._motive(b, j)
            if self.legal(COMBO, d, ["0", "W", "X", "Y"], idx):
                ways += self._corrective(i, a) * self._corrective(a, b) * self._corrective(b, j)
        if span >= 5:
            for cut in _splits(i, j, 5):
                a, b, c, e = cut
                if self.legal(TRIANGLE, d, ["0", "A", "B", "C", "D", "E"], (i, a, b, c, e, j)):
                    t = (self._corrective(i, a) * self._corrective(a, b) * self._corrective(b, c)
                         * self._corrective(c, e) * self._corrective(e, j))
                    ways += t
        return ways


def _reading(g: Grammar, pattern: str, labs: list[str], idx: tuple[int, ...], ways: int, open_last: bool = False) -> Reading | None:
    d = g._dir(idx[0], idx[1])
    pts = g._pts(labs, idx)
    if hard(violations(pattern, d, pts, open_last=open_last)):
        return None
    lv = rule_levels(pattern, d, pts)
    return Reading(pattern, d, tuple(zip(labs, idx)), lv["next"], lv["next_move"], ways, tuple(sorted({round(x, 6) for x, _ in lv["invalidation"]})))


def readings(prices: list[float], bars: list[int], first: int = 0, simple: bool = False, open_last: bool = False, hidden_sub: bool = False) -> list[Reading]:
    """Top-level structures whose last label sits on the last pivot. simple=True: one leg per wave, no nesting.
    open_last: the last pivot is the running extreme of an unfinished wave."""
    g = Grammar(prices, bars, hidden_sub=hidden_sub)
    last = len(prices) - 1
    out: list[Reading] = []

    def wave_ways(kinds: str, idx: tuple[int, ...]) -> int:
        w = 1
        for k, a, b in zip(kinds, idx, idx[1:]):
            w *= g.motive(a, b) if k == "m" else g.corrective(a, b)
            if not w:
                return 0
        return w

    def chains(parts: int):
        for start in range(first, last):
            if simple:
                if start + parts == last:
                    yield (start, *range(start + 1, last + 1))
            elif (last - start) % 2 == parts % 2:
                for cut in _splits(start, last, parts):
                    yield (start, *cut, last)

    impulse_labs = ["0", "1", "2", "3", "4", "5"]
    plan = [
        (IMPULSE, impulse_labs, "mcmcm"), (ED, impulse_labs, "ccccc"), (LD, impulse_labs, "mcmcm"),
        (ZIGZAG, ["0", "A", "B", "C"], "mcm"),
        (FLAT_REG, ["0", "A", "B", "C"], "ccm"), (FLAT_RUN, ["0", "A", "B", "C"], "ccm"), (FLAT_EXP, ["0", "A", "B", "C"], "ccm"),
        (TRIANGLE, ["0", "A", "B", "C", "D", "E"], "ccccc"), (COMBO, ["0", "W", "X", "Y", "X2", "Z"], "ccccc"),
    ]
    for pattern, labs, kinds in plan:
        for parts in range(1, len(kinds) + 1):
            if parts == 1 and pattern != IMPULSE and pattern != ZIGZAG:
                continue  # a single finished first wave reads the same for every pattern
            for idx in chains(parts):
                if open_last:
                    # the running wave has no finished inside to parse: a motive one must only still respect its own start
                    a = idx[-2]
                    if kinds[parts - 1] == "m":
                        sgn = 1 if prices[last] > prices[a] else -1
                        if any(sgn * (prices[k] - prices[a]) <= 0 for k in range(a + 1, last + 1)):
                            continue
                    ways = wave_ways(kinds[:parts - 1], idx[:-1])
                else:
                    ways = wave_ways(kinds[:parts], idx)
                if not ways:
                    continue
                r = _reading(g, pattern, labs[:parts + 1], idx, ways, open_last)
                if r:
                    out.append(r)
    return out


def summary(rs: list[Reading]) -> dict:
    """How far apart the legal readings of one window are. Every reading ending on the last pivot expects the next leg
    to turn, so what really differs is the trend of the structure, the wave reached and the invalidation level."""
    fam = {}
    for r in rs:
        key = f"{FAMILY[r.pattern]}:{r.labels[-1][0]}"
        fam[key] = fam.get(key, 0) + 1
    up = sum(r.direction == "up" for r in rs)
    down = sum(r.direction == "down" for r in rs)
    inv = {x for r in rs for x in r.invalidation}
    return {
        "readings": len(rs),
        "nested_ways": sum(r.ways for r in rs),
        "structures_up": up,
        "structures_down": down,
        "share_up": up / (up + down) if up + down else None,
        "distinct_states": len(fam),
        "distinct_invalidation_levels": len(inv),
        "inv_low": min(inv) if inv else None,
        "inv_high": max(inv) if inv else None,
        "by_state": dict(sorted(fam.items(), key=lambda kv: -kv[1])[:12]),
    }


WAVE_KINDS = {IMPULSE: "mcmcm", LD: "mcmcm", ED: "ccccc", ZIGZAG: "mcm", FLAT_REG: "ccm", FLAT_RUN: "ccm", FLAT_EXP: "ccm", TRIANGLE: "ccccc", COMBO: "ccccc"}

__all__ = ["Grammar", "Reading", "readings", "summary", "FAMILY", "WAVE_KINDS"]
