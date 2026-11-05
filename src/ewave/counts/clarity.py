"""How clearly a finished wave holds what its label says. Round 4 asked whether a legal labelling exists anywhere; a barely
there B passed the same as a clear one. This walks the same ladder (rules: inside) and grades what it sees:

  rungs     thresholds and frames where the wave itself is a swing, down to where it gets too fine to label
  found     rungs with a legal labelling of the required form
  opposite  rungs with a legal labelling of the other form

A 3 has to show its break: a rung that reads the wave as one straight leg counts against it (sec 0, velocity test). A 5 may
hide its small corrections under the threshold (sec 0), so a straight leg says nothing about it, and only rungs with visible
legs count. On a rung a 3 and a 5 read alike the rung is no evidence for the 3, so the 3's grade also takes its margin in rungs. A legal 3
exists on nearly every rung that holds a 5, so a 5's grade does not; both take the gap in fit (`best`). A finished wave's
clarity is the weakest of its own grade and the grades of what is inside its labelling, one level down (sec 0, FND-8: for a 5,
its largest motive wave; for a 3, each of its legs), on the clearest labelling its grammar allows.

Clarity never kills: rules kill, guidelines rank (sec 0, FND-4). It lowers the count's rank and widens its projection boxes.
Only bars up to the wave's end are read, so a grade never changes and is kept with the verdicts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isnan, log

from .config import Config
from .enumerate import Scan
from .inside import EITHER, FIVE, FIVES, THREE, THREES, Insides, closed_at, form_of, wave_name
from .pivots import Pivot
from .rules import MOTIVE, WAVES
from .state import Count

TF_NAME = {"1d": "1D", "12h": "12H", "4h": "4H", "1h": "1H", "15m": "15m", "1m": "1m"}


@dataclass(frozen=True)
class Grade:
    required: str
    rungs: int
    found: int
    opposite: int
    share: float
    margin: float              # (found - opposite) / rungs
    gap: float | None          # fit of the required form minus fit of the other, where both can be labelled
    value: float               # 0 to 1
    word: str
    first: str | None          # the coarsest rung that holds it: "4H k5, 7 legs"
    where: str                 # "12 of 20 swing sizes", "only at the finest swing sizes", "at no swing size"


@dataclass(frozen=True)
class SubGrade:
    wave: str
    grade: Grade


@dataclass(frozen=True)
class Reading:
    """One labelling of a finished wave, with its legs graded."""
    count: Count
    subs: tuple[SubGrade, ...]
    value: float               # the weakest leg


@dataclass(frozen=True)
class WaveClarity:
    wave: str                  # the wave of the count, named for the reader
    label: str                 # its label, as the chart has it
    own: Grade
    shown: Reading | None      # the labelling inside it that the chart draws
    best: Reading | None       # the clearest labelling its grammar allows; the same one, or the one that rescues it
    value: float
    word: str
    text: str                  # "X 3, weak: B at 12 of 20 swing sizes"


def _name(pattern: str) -> str:
    return pattern.replace("_", " ")


def word_of(x: float, words: dict) -> str:
    return "clear" if x >= words["clear"] else ("fair" if x >= words["fair"] else ("weak" if x >= words["weak"] else "very weak"))


def _exists(scan: Scan, patterns, legs: int) -> bool:
    return legs >= 3 and any(next(iter(scan.labellings(p, 0, legs)), None) is not None for p in patterns)


class Clarities:
    def __init__(self, insides: Insides, cfg: Config):
        self.ins = insides
        self.cfg = cfg
        self.spec = cfg.raw["clarity"]
        self.memo: dict[tuple, Grade] = {}

    def _walk(self, ptf: str, a: Pivot, b: Pivot, kinds: tuple[str, ...]) -> dict:
        """The ladder of one wave: how many rungs see it, how many hold each form. Largest threshold first, own frame first."""
        spec = self.cfg.inside
        cap = spec["max_pivots"]
        form = form_of(kinds)
        other = () if form == EITHER else (THREES if form == FIVE else FIVES)
        size = abs(log(b.price / a.price))
        rows: list[tuple[str, float, int, bool, bool]] = []
        seen: dict[tuple[float, ...], tuple[bool, bool]] = {}
        for tf in spec["frames"][ptf]:
            got = self.ins._span(tf, ptf, a, b)
            if got is None:
                continue
            f, start, end, j = got
            atr = f.atr[max(f.bar_at(start.ts) - 1, 0)]
            for k in spec["ks"]:
                if not isnan(atr) and k * atr >= size:  # the wave itself is no swing at this size: this rung says nothing
                    continue
                closed = closed_at(f, k, start, end, j)
                if closed is None:
                    continue
                legs = len(closed) - 1
                if legs > cap:
                    break
                shape = tuple(p.price for p in closed)
                if shape not in seen:
                    scan = Scan(f, k, closed, None, self.cfg, top_span=cap)
                    seen[shape] = (_exists(scan, kinds, legs), _exists(scan, other, legs))
                rows.append((tf, k, legs, *seen[shape]))
        if form == FIVE:  # a 5 may hide its corrections under the threshold: a straight leg says nothing about it (sec 0)
            rows = [r for r in rows if r[2] > 1]
        found = [r for r in rows if r[3]]
        return {"form": form, "rungs": len(rows), "found": len(found), "opposite": sum(1 for r in rows if r[4]),
                "first": None if not found else [found[0][0], found[0][1], found[0][2]],
                "first_at": None if not found else rows.index(found[0])}

    def grade(self, ptf: str, a: Pivot, b: Pivot, kinds: tuple[str, ...]) -> Grade:
        key = ("cl", ptf, a.ts, a.price, b.ts, b.price, kinds)
        got = self.memo.get(key)
        if got is not None:
            return got
        disk = self.ins._key(*key)
        row = self.ins.cache.get(disk)
        if row is None:
            row = self._walk(ptf, a, b, kinds)
            form = row["form"]
            mine = self.ins.best(ptf, a, b, kinds)
            if form == FIVE:  # the rule looks further down than `best`, as `leg_form` does
                rule = self.ins.rule_five(ptf, a, b, kinds)
                if rule is not None and (mine is None or rule[1].score > mine[1].score):
                    mine = rule
            theirs = None if form == EITHER else self.ins.best(ptf, a, b, THREES if form == FIVE else FIVES)
            row["gap"] = None if mine is None or theirs is None else mine[1].score - theirs[1].score
            self.ins.cache.put(disk, row)
        got = self._graded(row)
        self.memo[key] = got
        return got

    def _graded(self, row: dict) -> Grade:
        form, rungs, found, opposite = row["form"], row["rungs"], row["found"], row["opposite"]
        spec = self.spec
        share = found / rungs if rungs else 0.0
        margin = (found - opposite) / rungs if rungs else 0.0
        gap = row["gap"]
        # a tie in fit costs nothing (sec 0: hold both); the other form better by `fade` halves it
        by_fit = 1.0 if gap is None or gap >= 0 else max(0.5, 1 + gap / (2 * spec["fade"]))
        by_rungs = 0.5 + 0.5 * max(margin, 0.0) if form == THREE else 1.0
        value = share * by_rungs * by_fit
        first = None if row["first"] is None else f"{TF_NAME.get(row['first'][0], row['first'][0])} k{row['first'][1]:g}, {row['first'][2]} legs"
        where = self._where(row)
        if gap is not None and gap <= -spec["fade"] / 2:
            where += f", and reads better as a {'3' if form == FIVE else '5'} by {-gap:.2f}"
        return Grade(form, rungs, found, opposite, share, margin, gap, value, word_of(value, spec["words"]), first, where)

    def _where(self, row: dict) -> str:
        rungs, found = row["rungs"], row["found"]
        if rungs == 0:
            return "too short to read"
        if not found:
            return "at no swing size"
        if found <= max(1, self.spec["finest_share"] * rungs) and row["first_at"] >= (1 - self.spec["finest_share"]) * rungs - 1:
            return "only at the finest swing sizes"
        return f"at {found} of {rungs} swing sizes"

    def _reading(self, c: Count, required: str) -> Reading:
        fill = self.cfg.grammar[c.pattern]
        waves = list(enumerate(WAVES[c.pattern][: c.done]))
        if required == FIVE:  # sec 0, FND-8: the largest motive wave subdivides visibly; the others need not
            motive = [(abs(log(c.pts[n + 1].price / c.pts[n].price)), n, w) for n, w in waves if all(k in MOTIVE for k in fill[w])]
            waves = [(n, w) for _, n, w in sorted(motive, reverse=True)[:1]]
        subs = tuple(SubGrade(w, self.grade(c.tf, c.pts[n], c.pts[n + 1], tuple(fill[w]))) for n, w in waves)
        return Reading(c, subs, min((s.grade.value for s in subs), default=1.0))

    def count(self, c: Count) -> list[WaveClarity]:
        """Every finished wave of a count. Its clarity is the weakest of its own grade and the legs of its clearest labelling:
        a wave gets the benefit of the doubt, and the panel says when that is not the labelling on the chart."""
        fill = self.cfg.grammar[c.pattern]
        inner = {r.wave: r for r in self.ins.tree(c, 1)}
        out = []
        for n, w in enumerate(WAVES[c.pattern][: c.done]):
            kinds = tuple(fill[w])
            a, b = c.pts[n], c.pts[n + 1]
            own = self.grade(c.tf, a, b, kinds)
            got = inner.get(w)
            shown = self._reading(got.count, own.required) if got is not None else None
            best = shown
            for kind in kinds:
                rival = self.ins.best(c.tf, a, b, (kind,))
                if rival is not None and (shown is None or rival[0].pattern != shown.count.pattern):
                    reading = self._reading(rival[0], own.required)
                    if best is None or reading.value > best.value:
                        best = reading
            value = own.value if best is None else min(own.value, best.value)
            word = word_of(value, self.spec["words"])
            name = wave_name(w)
            out.append(WaveClarity(name, w, own, shown, best, value, word, self._text(name, own, shown, best, value, word)))
        return out

    def _text(self, name: str, own: Grade, shown: Reading | None, best: Reading | None, value: float, word: str) -> str:
        """"X 3, weak: B at 12 of 20 swing sizes". A clearer labelling than the chart's is named, and the chart's own weakness stays."""
        head = f"{name} {own.required}, {word}"
        if best is not None and shown is not None and best is not shown and best.count.pattern != shown.count.pattern and shown.value < best.value:
            bad = min(shown.subs, key=lambda x: x.grade.value, default=None)
            why = "" if bad is None else f": {wave_name(bad.wave)} {bad.grade.where}"
            return f"{head} as a {_name(best.count.pattern)}; the {_name(shown.count.pattern)} on the chart is {word_of(shown.value, self.spec['words'])}{why}"
        weak = min(best.subs, key=lambda x: x.grade.value, default=None) if best is not None else None
        if weak is not None and weak.grade.value <= own.value and value < self.spec["words"]["clear"]:
            return f"{head}: {wave_name(weak.wave)} {weak.grade.where}"
        return f"{head}: {own.where}"

    def judge(self, c: Count) -> tuple[str, float, str] | None:
        """The item in the fit. Only a wave below `ok` costs anything: a clear wave says nothing more than a fair one."""
        rows = self.count(c)
        if not rows:
            return None
        worst = min(rows, key=lambda r: r.value)
        return ("clarity", min(1.0, worst.value / self.spec["ok"]), worst.text)

    def widen(self, rows: list[WaveClarity]) -> float:
        """How much wider this count's boxes are drawn: 1 down to `ok`, up to 1 + widen at no clarity at all."""
        if not rows:
            return 1.0
        worst = min(r.value for r in rows)
        return 1.0 + self.spec["widen"] * max(0.0, 1 - worst / self.spec["ok"])
