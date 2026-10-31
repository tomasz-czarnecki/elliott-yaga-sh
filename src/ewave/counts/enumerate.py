"""Every rule-legal count of a pivot window.

The grammar follows sections 0 to 3 and is data (grammar in rules/counts.yaml): a wave between two pivots is one leg,
whose inside is not visible at this threshold, or a nested structure over an odd number of legs, each wave of which must
parse in turn. `Scan` holds one pivot list at one threshold. `structures` walks every labelling from an anchor whose
last label sits on a confirmed pivot; whatever has printed since then is inside the running wave.
"""
from __future__ import annotations

from .config import Config
from .frames import Frame
from .pivots import Pivot, Running
from .rules import ED, FLAT, IMPULSE, LD, MOTIVE, TRIANGLE, TRIPLE, WAVES, ZIGZAG, Checker, Point
from .state import Count, State, _since, alive, describe


def _splits(i: int, j: int, parts: int, max_span: int):
    """Strictly increasing cut points i < c1 < ... < c(parts-1) < j, every part spanning an odd number of legs."""
    if parts == 1:
        if (j - i) % 2 == 1 and j - i <= max_span:
            yield ()
        return
    for c in range(i + 1, min(j - (parts - 2), i + max_span + 1), 2):
        for rest in _splits(c, j, parts - 1, max_span):
            yield (c, *rest)


class Scan:
    """One list of pivots at one threshold, with the memo of what parses between any two of them."""

    def __init__(self, f: Frame, k: float, pivots: list[Pivot], running: Running | None, cfg: Config, top_span: int | None = None):
        self.f = f
        self.k = k
        self.pivots = pivots
        self.running = running
        self.cfg = cfg
        self.grammar = cfg.grammar
        self.max_span = cfg.pivots["max_span"]
        self.top_span = top_span or self.max_span  # legs a whole labelling may cover; each of its waves stays under max_span
        self.hidden_sub = cfg.pivots["hidden_sub"]
        self.checker = Checker(cfg.rules)
        self.prices = [p.price for p in pivots]
        tf_ms = f.tf_ms
        self.points = [Point(p.t / tf_ms, p.price) for p in pivots]
        self._memo: dict[tuple[str, int, int], bool] = {}
        self._open: dict[tuple[int, tuple[str, ...]], bool] = {}

    def direction(self, i: int) -> int:
        return 1 if self.prices[i + 1] > self.prices[i] else -1

    def accepts(self, kinds, i: int, j: int) -> bool:
        """Can this wave be what it claims? One leg always can: its inside is not visible here."""
        if j - i == 1:
            return True
        return any(self.parse(kind, i, j) for kind in kinds)

    def parse(self, pattern: str, i: int, j: int) -> bool:
        key = (pattern, i, j)
        got = self._memo.get(key)
        if got is None:
            got = self._memo[key] = self._parse(pattern, i, j)
        return got

    def _parse(self, pattern: str, i: int, j: int) -> bool:
        span = j - i
        if span % 2 == 0 or span <= 1 or span > self.max_span:
            return False
        s = self.direction(i)
        p = self.prices
        if pattern in MOTIVE and not self._motive_bounds(s, i, j):
            return False
        if span == 3 and pattern == IMPULSE and self.hidden_sub:
            return s * (p[i + 2] - p[i]) > 0 and s * (p[j] - p[i + 1]) > 0
        return any(True for _ in self.labellings(pattern, i, j))

    def labellings(self, pattern: str, i: int, j: int):
        """Every complete labelling of this pattern over pivots i to j, each as the pivot indexes of its labels."""
        waves = WAVES[pattern]
        span = j - i
        if span % 2 == 0 or span < len(waves) or span > self.top_span:
            return
        s = self.direction(i)
        if pattern in MOTIVE and not self._motive_bounds(s, i, j):
            return
        labs = ("0", *waves)
        fill = self.grammar[pattern]
        for cut in _splits(i, j, len(waves), self.max_span):
            idx = (i, *cut, j)
            pts = {lab: self.points[t] for lab, t in zip(labs, idx)}
            if not self.checker.legal(pattern, s, pts) or not self.inner_ok(pattern, s, idx):
                continue
            if all(self.accepts(fill[w], a, b) for w, a, b in zip(waves, idx, idx[1:])):
                yield idx

    def _motive_bounds(self, s: int, i: int, j: int) -> bool:
        """A motive wave never goes back past its own start (sec 0), and ends at its extreme. A truncation may stop short
        of it, but must win back most of the fall from there: the same number as the truncated W5 of the rules."""
        p = self.prices
        top = i
        for t in range(i + 1, j + 1):
            if s * (p[t] - p[i]) <= 0:
                return False
            if s * (p[t] - p[top]) > 0:
                top = t
        if top == j:
            return True
        low = min(range(top + 1, j + 1), key=lambda t: s * p[t])
        back = abs(p[j] - p[low]) / abs(p[top] - p[low])
        return back >= self.cfg.rules["truncated_w5_min"]

    def inner_ok(self, pattern: str, s: int, idx: tuple[int, ...]) -> bool:
        """A rule limit holds for every pivot inside a wave, not only for the wave's end."""
        p = self.prices
        if pattern == IMPULSE:
            if len(idx) > 2 and any(s * (p[t] - p[idx[0]]) <= 0 for t in range(idx[1], idx[2])):
                return False  # W2
            if len(idx) > 4 and any(s * (p[t] - p[idx[1]]) < 0 for t in range(idx[3], idx[4])):
                return False  # W4
        elif pattern in (LD, ED):
            if len(idx) > 2 and any(s * (p[t] - p[idx[0]]) <= 0 for t in range(idx[1], idx[2])):
                return False
            if len(idx) > 4 and any(s * (p[t] - p[idx[2]]) <= 0 for t in range(idx[3], idx[4])):
                return False
        elif pattern == ZIGZAG:
            if len(idx) > 2 and any(s * (p[t] - p[idx[0]]) <= 0 for t in range(idx[1], idx[2])):
                return False
        return True

    def open_ok(self, i: int, kinds: tuple[str, ...]) -> bool:
        """Do the legs printed since pivot i form the legal start of a structure of these kinds? One leg, or none, always
        does. Two or more must be labelled up to some pivot, and what is left must be the legal start of the next wave."""
        n = len(self.pivots) - 1
        if n - i <= 1:
            return True
        key = (i, kinds)
        got = self._open.get(key)
        if got is None:
            got = self._open[key] = self._open_search(i, kinds)
        return got

    def _open_search(self, i: int, kinds: tuple[str, ...]) -> bool:
        s = self.direction(i)
        for pattern in kinds:
            for idx in self._walk(pattern, s, (i,)):
                if len(idx) == 1:
                    continue
                c = self._count(pattern, s, idx)
                if c is None:
                    continue
                st = describe(c, self.f, self.cfg)
                if alive(c, st, self.f) is None and self.open_ok(idx[-1], st.kinds):
                    return True
        return False

    def _walk(self, pattern: str, s: int, idx: tuple[int, ...]):
        """Depth first over labellings that extend idx. Yields every prefix: the last wave after it is the running one."""
        yield idx
        waves = WAVES[pattern]
        done = len(idx) - 1
        if done == len(waves):
            return
        n = len(self.pivots) - 1
        i = idx[-1]
        labs = ("0", *waves[:done + 1])
        wave = waves[done]
        fill = self.grammar[pattern][wave]
        for c in range(i + 1, min(n, i + self.max_span) + 1, 2):
            if not self.accepts(fill, i, c):
                continue
            nxt = (*idx, c)
            pts = {lab: self.points[t] for lab, t in zip(labs, nxt)}
            if not self.checker.legal(pattern, s, pts):
                continue
            yield from self._walk(pattern, s, nxt)

    def counts_from(self, a: int, patterns: tuple[str, ...]) -> list[tuple[Count, State]]:
        """Every legal labelling from anchor a, of these patterns, whose running wave has not been killed and whose
        printed legs can start what that wave claims to be. A first wave still running reads the same for every pattern:
        it appears once, and may be filled by anything any of them allows."""
        n = len(self.pivots) - 1
        s = self.direction(a) if a < n else (1 if self.pivots[a].kind == "L" else -1)
        out: list[tuple[Count, State]] = []
        first: list[tuple[Count, State]] = []
        for pattern in patterns:
            for idx in self._walk(pattern, s, (a,)):
                c = self._count(pattern, s, idx)
                if c is None:
                    continue
                st = describe(c, self.f, self.cfg)
                if alive(c, st, self.f) is not None or not self.open_ok(idx[-1], st.kinds):
                    continue
                (first if c.done == 0 else out).append((c, st))
        if first:
            kinds = tuple(dict.fromkeys(k for _, st in first for k in st.kinds))
            c, st = first[0]
            st.kinds = kinds
            out.append((c, st))
        return out

    def _count(self, pattern: str, s: int, idx: tuple[int, ...]) -> Count | None:
        waves = WAVES[pattern]
        done = len(idx) - 1
        n = len(self.pivots) - 1
        if pattern in (LD, ED):
            # While waves 1 to 3 are the same as an impulse's, the impulse says it. A diagonal shows only from its overlap.
            if done < 3:
                return None
            if done == 3:
                last = self.pivots[idx[-1]]
                hi, lo = _since(self.f, last)
                e = hi if last.kind == "L" else lo
                if s * (e - self.prices[idx[1]]) >= 0:
                    return None
        # While it has no Y it is the same as a double three, and the double three says it.
        if pattern == TRIPLE and done < 3:
            return None
        labs = ("0", *waves[:done])
        first_leg = self.pivots[idx[-1] + 1] if idx[-1] < n else None
        return Count(self.f.tf, pattern, s, labs, tuple(self.pivots[i] for i in idx), self.k, first_leg)


def unbroken_anchors(f: Frame, pivots: list[Pivot], from_ts: int) -> list[int]:
    """Pivots no price has passed since: an up-move can only start at a low that still stands (sec 1). These are the
    possible higher-degree starts."""
    out = []
    for i, p in enumerate(pivots):
        if p.ts < from_ts:
            continue
        hi, lo = _since(f, p)
        if (p.kind == "L" and lo >= p.price) or (p.kind == "H" and hi <= p.price):
            out.append(i)
    return out


def flat_anchors(pivots: list[Pivot], extremes: list[int], back: int) -> list[int]:
    """A flat's B may pass its origin (sec 3), so its origin is a broken pivot just before a standing extreme."""
    out = []
    for j in extremes:
        for step in range(1, back + 1):
            i = j - 2 * step
            if i >= 0:
                out.append(i)
    return sorted(set(out) - set(extremes))
