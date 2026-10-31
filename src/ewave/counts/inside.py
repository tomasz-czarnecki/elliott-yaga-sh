"""What is inside a finished wave. Since round 4 this is a rule, not only a ranking: a wave must hold what its label says (the
`grammar` table in rules/counts.yaml; sec 0, 1, 2, 3 and research/counts-r4.md). A count dies when a wave is readable and does
not admit its form. Three answers:

  pass  a rule-legal labelling of the required form exists, on some frame at some threshold (existence, not best score)
  fail  the wave is readable and has no legal 5 where a 5 is required, or reads clearly as a 5 where only a 3 is allowed
  hold  too short to read at the finest frame, nothing visible, or a 3 and a 5 too close to tell (sec 0: hold both)

Only bars up to the wave's end are read, and a finished wave stays what it was whatever price did later: a wave passed by a
later one (the A of an expanded flat) still has its inside. So a verdict never changes and can be kept on disk. The wave still
running is provisional and can only be held. `best` is the older question, kept for ranking and drawing: the best labelling
near the wave's own frame, and how the same wave reads as the other form (`leg_form`).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from math import log
from pathlib import Path

from ..ingest.config import project_root
from .config import Config
from .enumerate import Scan
from .frames import Frame, Frames, TF_MS
from .pivots import Pivot, dated, locate, zigzag
from .rules import COMBO, ED, FLAT, IMPULSE, LD, MOTIVE, WAVES, ZIGZAG
from .score import Fit, Judge
from .state import AFTER, Count, State

FIVES = (IMPULSE, LD, ED)
THREES = (ZIGZAG, FLAT, COMBO)
FIRST_FIVE = {IMPULSE, LD, ED, ZIGZAG}  # the structures that start with a 5 (sec 0, UNSPOKEN R1)
PASS, FAIL, HOLD, RUNNING = "pass", "fail", "hold", "running"
FIVE, THREE, EITHER = "5", "3", "3 or 5"
_SOURCES = ("inside.py", "enumerate.py", "pivots.py", "rules.py", "score.py", "state.py", "frames.py")
_COMMIT_EVERY = 200  # so that an export cut short by its timeout keeps what it read


def wave_name(w: str) -> str:
    return f"W{w}" if w.isdigit() else ("the move after it" if w == AFTER else w)


def form_of(kinds) -> str:
    """What a list of allowed patterns asks for: all motive a 5, none motive a 3. A leading diagonal's waves may be either."""
    motive = [k in MOTIVE for k in kinds]
    return FIVE if all(motive) else (THREE if not any(motive) else EITHER)


@dataclass
class Inner:
    wave: str                  # the wave of the count around it
    count: Count
    fit: Fit
    legs: list["Inner"] = field(default_factory=list)


@dataclass(frozen=True)
class Verdict:
    wave: str
    required: str              # 5, 3, or 3 or 5
    found: str                 # what it reads as: 5, 3, 3 or 5, or ? when it cannot be read
    state: str                 # pass, fail, hold or running
    tf: str | None             # the frame and threshold it was read at
    k: float | None
    pattern: str | None
    why: str                   # a short reason, the key of the kill counts
    note: str
    count: Count | None = field(default=None, compare=False)  # the labelling found


@dataclass
class View:
    """What the search saw: did a frame have enough bars, and how many legs showed on the rungs it could use."""
    short: bool = True
    legs: int = 0
    over: bool = False
    tf: str | None = None
    k: float | None = None
    pivots: tuple[Pivot, ...] = ()


class Cache:
    """Verdicts of finished waves. In memory for one run, on disk across runs when given a path: only new legs are read. A
    wave's verdict depends only on its own bars, the rules and this code, so the file name holds both digests and nothing
    expires. No path: memory only."""

    def __init__(self, path: Path | str | None = None):
        self.mem: dict[tuple, object] = {}
        self.hits = self.misses = self._pending = 0
        self.db = None
        self.path = Path(path) if path else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(self.path, timeout=30)
            self.db.execute("CREATE TABLE IF NOT EXISTS leg (key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID")

    def get(self, key: str):
        if self.db is None:
            return None
        row = self.db.execute("SELECT value FROM leg WHERE key = ?", (key,)).fetchone()
        if row is None:
            self.misses += 1
            return None
        self.hits += 1
        return json.loads(row[0])

    def put(self, key: str, value) -> None:
        if self.db is None:
            return
        self.db.execute("INSERT OR REPLACE INTO leg VALUES (?, ?)", (key, json.dumps(value, separators=(",", ":"))))
        self._pending += 1
        if self._pending >= _COMMIT_EVERY:
            self.commit()

    def commit(self) -> None:
        if self.db is not None and self._pending:
            self.db.commit()
            self._pending = 0

    def close(self) -> None:
        if self.db is not None:
            self.commit()
            self.db.close()
            self.db = None


def code_digest() -> str:
    h = hashlib.sha256()
    here = Path(__file__).parent
    for name in _SOURCES:
        h.update((here / name).read_bytes())
    return h.hexdigest()[:12]


def open_cache(cfg: Config, folder: Path | str | None = None, keep: int = 3) -> Cache:
    """The cache of these rules and this code, under the gitignored .cache folder. Older files beyond `keep` are removed."""
    base = Path(folder) if folder else project_root() / ".cache" / "counts"
    path = base / f"inside-{cfg.digest}-{code_digest()}.sqlite"
    try:
        cache = Cache(path)
    except sqlite3.DatabaseError:  # a damaged file holds nothing that cannot be read again
        path.unlink(missing_ok=True)
        cache = Cache(path)
    old = sorted((p for p in base.glob("inside-*.sqlite") if p != path), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in old[keep - 1:]:
        p.unlink(missing_ok=True)
    return cache


def _pivot_row(p: Pivot) -> list:
    return [p.ts, p.kind, p.price, p.conf_ts, p.at]


def _count_row(c: Count | None) -> dict | None:
    return None if c is None else {"tf": c.tf, "pattern": c.pattern, "s": c.s, "labs": list(c.labs), "pts": [_pivot_row(p) for p in c.pts], "k": c.k}


def _count_of(d: dict | None) -> Count | None:
    return None if d is None else Count(d["tf"], d["pattern"], d["s"], tuple(d["labs"]), tuple(Pivot(*p) for p in d["pts"]), d["k"])


def _same(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-9 * abs(b)


def closed_at(f: Frame, k: float, start: Pivot, end: Pivot, j: int) -> list[Pivot] | None:
    """The pivots from start to end at this threshold, reading bars up to the end's only. None when this threshold cannot end
    on it: the inside went past the wave's end, so this wave does not end at a swing of that size."""
    pivots, running = zigzag(f, k, start, j + 1)
    last = pivots[-1]
    if len(pivots) > 1 and last.kind == end.kind and _same(last.price, end.price):
        return pivots
    if running is None or running.kind != end.kind or not _same(running.price, end.price):
        return None
    return [*pivots, dated(f, Pivot(running.ts, running.kind, running.price, end.conf_ts))]


class Insides:
    def __init__(self, frames: Frames, cfg: Config, judge: Judge, cache: Cache | None = None):
        self.frames = frames
        self.cfg = cfg
        self.judge = judge
        self.cache = cache or Cache()
        self.memo = self.cache.mem
        self.minute_frames: dict[tuple[int, int], Frame | None] = {}

    def _key(self, *parts) -> str:
        return json.dumps([self.frames.venue, self.cfg.digest, *parts], separators=(",", ":"))

    # --- the rule ---------------------------------------------------------------------------------------------------

    def _minutes(self, a: Pivot, b: Pivot, parent_ms: int) -> Frame | None:
        """1m bars for this wave, from whole days before it (ATR warm-up) up to the end of its last bar, and no later."""
        if self.frames.minutes is None:
            return None
        day = 86_400_000
        first = a.ts - a.ts % day - self.cfg.inside["minute_warmup_days"] * day
        last = min(b.ts + parent_ms, self.frames.as_of_ms)
        key = (first, last)
        if key not in self.minute_frames:
            self.minute_frames[key] = self.frames.minutes(first, last)
        return self.minute_frames[key]

    def _span(self, tf: str, parent_tf: str, a: Pivot, b: Pivot) -> tuple[Frame, Pivot, Pivot, int] | None:
        """This wave on frame tf, or None when the frame's bar counts rule it out (sec 0, drop tf)."""
        spec = self.cfg.inside
        parent_ms = TF_MS[parent_tf]
        if (b.ts + parent_ms - a.ts) / TF_MS[tf] > spec["max_bars"]:
            return None
        f = self._minutes(a, b, parent_ms) if tf == "1m" else self.frames[tf]
        if f is None or not f.ts:
            return None
        start, end = locate(f, parent_ms, a), locate(f, parent_ms, b)
        i, j = f.bar_at(start.ts), f.bar_at(end.ts)
        if j - i < spec["min_bars"]:
            return None
        return f, start, end, j

    def _search(self, parent_tf: str, a: Pivot, b: Pivot, kinds: tuple[str, ...], depth: int) -> tuple[Count | None, View]:
        """The first rule-legal labelling, by the order the book lists them (an impulse before the rarer diagonal), then
        coarsest frame first, largest threshold first."""
        view = View()
        for pattern in kinds:
            c = self._search_one(parent_tf, a, b, pattern, depth, view)
            if c is not None:
                return c, view
        return None, view

    def _search_one(self, parent_tf: str, a: Pivot, b: Pivot, pattern: str, depth: int, view: View) -> Count | None:
        spec = self.cfg.inside
        cap = spec["max_pivots"]
        labs = ("0", *WAVES[pattern])
        seen: set[tuple[float, ...]] = set()
        for tf in spec["frames"][parent_tf]:
            got = self._span(tf, parent_tf, a, b)
            if got is None:
                continue
            f, start, end, j = got
            view.short = False
            for k in spec["ks"]:
                closed = closed_at(f, k, start, end, j)
                if closed is None:
                    continue
                legs = len(closed) - 1
                if legs > cap:
                    view.over = True
                    break
                if legs > view.legs:
                    view.legs, view.tf, view.k, view.pivots = legs, tf, k, tuple(closed)
                shape = tuple(p.price for p in closed)
                if legs < 3 or shape in seen:
                    continue
                seen.add(shape)
                scan = Scan(f, k, closed, None, self.cfg, top_span=cap)
                s = scan.direction(0)
                for idx in scan.labellings(pattern, 0, legs):
                    c = Count(tf, pattern, s, labs, tuple(closed[t] for t in idx), k)
                    if depth <= 1 or self._largest_holds(c, depth - 1):
                        return c
        return None

    def _largest_holds(self, c: Count, depth: int) -> bool:
        """Sec 0, FND-8: the largest motive wave of a labelling subdivides visibly. It must hold a 5, or be unreadable."""
        fill = self.cfg.grammar[c.pattern]
        motive = [(abs(log(c.pts[n + 1].price / c.pts[n].price)), n, w) for n, w in enumerate(WAVES[c.pattern][: c.done]) if all(k in MOTIVE for k in fill[w])]
        if not motive:
            return True
        _, n, w = max(motive)
        return self.check(c.tf, c.pts[n], c.pts[n + 1], tuple(fill[w]), depth).state != FAIL

    def check(self, parent_tf: str, a: Pivot, b: Pivot, kinds: tuple[str, ...], depth: int | None = None, wave: str = "") -> Verdict:
        """Does this finished wave admit what its label requires? Same input, same answer, so it is kept."""
        depth = self.cfg.inside["depth"] if depth is None else depth
        key = ("v", parent_tf, a.ts, a.price, b.ts, b.price, kinds, depth)
        got = self.memo.get(key)
        if got is None:
            disk = self._key(*key)
            row = self.cache.get(disk)
            if row is None:
                got = self._check(parent_tf, a, b, kinds, depth)
                self.cache.put(disk, {**got.__dict__, "count": _count_row(got.count)})
            else:
                row["count"] = _count_of(row["count"])
                got = Verdict(**row)
            self.memo[key] = got
        return got if not wave else Verdict(wave, *[getattr(got, n) for n in ("required", "found", "state", "tf", "k", "pattern", "why", "note", "count")])

    def _check(self, parent_tf: str, a: Pivot, b: Pivot, kinds: tuple[str, ...], depth: int) -> Verdict:
        form = form_of(kinds)
        if form == FIVE:
            return self._check_five(parent_tf, a, b, kinds, depth)
        if form == THREE:
            return self._check_three(parent_tf, a, b, kinds, depth)
        c, view = self._search(parent_tf, a, b, kinds, 1)
        if c is not None:
            return Verdict("", form, THREE if c.pattern not in MOTIVE else FIVE, PASS, c.tf, c.k, c.pattern, "", f"reads as {c.pattern} at {c.tf}, threshold {c.k:g}", c)
        return Verdict("", form, "?", HOLD, view.tf, view.k, None, "unreadable", _unreadable(view))

    def _check_five(self, parent_tf: str, a: Pivot, b: Pivot, kinds: tuple[str, ...], depth: int) -> Verdict:
        c, view = self._search(parent_tf, a, b, kinds, depth)
        if c is not None:
            return Verdict("", FIVE, FIVE, PASS, c.tf, c.k, c.pattern, "", f"a legal {c.pattern} at {c.tf}, threshold {c.k:g}", c)
        readable = view.legs >= 5 or (view.legs == 3 and not view.over)
        if not readable:
            return Verdict("", FIVE, "?", HOLD, view.tf, view.k, None, "unreadable", _unreadable(view))
        three, _ = self._search(parent_tf, a, b, THREES, 1)
        found = THREE if three is not None else "?"
        what = "/".join(kinds)
        seen = f"{view.legs} legs at {view.tf}, threshold {view.k:g}"
        note = f"no legal {what} at any resolution, up to {seen}" + (f"; a legal {three.pattern} at {three.tf}, threshold {three.k:g}" if three is not None else "")
        return Verdict("", FIVE, found, FAIL, view.tf, view.k, three.pattern if three is not None else None, "holds no 5", note, three)

    def _check_three(self, parent_tf: str, a: Pivot, b: Pivot, kinds: tuple[str, ...], depth: int) -> Verdict:
        """A 3 is allowed. It dies only on a clear 5: an impulse legal down to its largest wave, on the frames a reader looks
        at, that beats every 3 there by more than the margin, or with no 3 at all at any resolution. A diagonal never makes
        it clear: overlap reads as corrective or diagonal (sec 0, 2). Nor does a 5 that does not end at its own extreme, a
        truncation or a wick past its end: that shape is a 3 as easily. Closer than the margin both are held (sec 0)."""
        five = self.best(parent_tf, a, b, (IMPULSE,))
        if five is not None and (self._ends_short(five[0]) or not self._largest_holds(five[0], depth - 1)):
            five = None
        three = self.best(parent_tf, a, b, kinds)
        if five is None:
            if three is not None:
                c = three[0]
                return Verdict("", THREE, THREE, PASS, c.tf, c.k, c.pattern, "", f"a legal {c.pattern} at {c.tf}, threshold {c.k:g}", c)
            c, view = self._search(parent_tf, a, b, kinds, 1)
            if c is not None:
                return Verdict("", THREE, THREE, PASS, c.tf, c.k, c.pattern, "", f"a legal {c.pattern} at {c.tf}, threshold {c.k:g}", c)
            return Verdict("", THREE, "?", HOLD, view.tf, view.k, None, "unreadable", _unreadable(view))
        c5, f5 = five
        if three is None:
            c, _ = self._search(parent_tf, a, b, kinds, 1)
            if c is None:
                return Verdict("", THREE, FIVE, FAIL, c5.tf, c5.k, c5.pattern, "reads as a 5", f"a legal impulse at {c5.tf}, threshold {c5.k:g}, and no legal 3 at any resolution", c5)
            return Verdict("", THREE, EITHER, HOLD, c5.tf, c5.k, c5.pattern, "3 or 5", f"an impulse at {c5.tf}; a 3 only finer, at {c.tf}, threshold {c.k:g}", c)
        c3, f3 = three
        gap = f5.score - f3.score
        margin = self.cfg.inside["clear_margin"]
        if gap > margin:
            return Verdict("", THREE, FIVE, FAIL, c5.tf, c5.k, c5.pattern, "reads as a 5", f"reads clearly as a 5: impulse {f5.score:.2f} at {c5.tf}, threshold {c5.k:g}, against {c3.pattern} {f3.score:.2f}", c5)
        if gap >= -margin:
            return Verdict("", THREE, EITHER, HOLD, c3.tf, c3.k, c3.pattern, "3 or 5", f"3 and 5 within {margin}: impulse {f5.score:.2f}, {c3.pattern} {f3.score:.2f}. Both held (sec 0)", c3)
        return Verdict("", THREE, THREE, PASS, c3.tf, c3.k, c3.pattern, "", f"{c3.pattern} {f3.score:.2f} at {c3.tf}, threshold {c3.k:g}, against impulse {f5.score:.2f}", c3)

    def _ends_short(self, c: Count) -> bool:
        """Did price go past this labelling's end, inside the labelling? Read on the frame it was labelled on."""
        f = self.frames[c.tf]
        i, j = f.bar_at(c.pts[0].ts), f.bar_at(c.pts[-1].ts)
        end = c.pts[-1].price
        return max(f.high[i : j + 1]) > end if c.s > 0 else min(f.low[i : j + 1]) < end

    def checks(self, c: Count, st: State | None = None) -> list[Verdict]:
        """Every finished wave against its label, and, when given a state, the running wave: provisional, never a kill."""
        fill = self.cfg.grammar[c.pattern]
        out = [self.check(c.tf, c.pts[n], c.pts[n + 1], tuple(fill[w]), wave=wave_name(w)) for n, w in enumerate(WAVES[c.pattern][: c.done])]
        if st is not None and st.wave != AFTER and st.wave in fill:
            out.append(self._running(c, st))
        return out

    def _running(self, c: Count, st: State) -> Verdict:
        kinds = tuple(self.cfg.grammar[c.pattern][st.wave])
        name = wave_name(st.wave)
        end = self._extreme(c.tf, st)
        if end is None:
            return Verdict(name, form_of(kinds), "?", RUNNING, None, None, None, "running", "running: nothing to read yet")
        got = self.check(c.tf, st.start, end, kinds)
        return Verdict(name, got.required, got.found, RUNNING, got.tf, got.k, got.pattern, "running", "running: provisional, held until it ends", None)

    # --- the older question: the best labelling near the wave's own frame ----------------------------------------------

    def best(self, parent_tf: str, a: Pivot, b: Pivot, kinds: tuple[str, ...]) -> tuple[Count, Fit] | None:
        """The best complete labelling of a to b among these patterns, or None when none can be seen."""
        key = ("b", parent_tf, a.ts, a.price, b.ts, b.price, kinds)
        if key in self.memo:
            return self.memo[key]
        disk = self._key(*key)
        row = self.cache.get(disk)
        if row is not None:
            got = None if not row["c"] else (_count_of(row["c"]), Fit(row["score"], row["axes"], [], []))
        else:
            rows = [self._best(tf, parent_tf, a, b, kinds) for tf in self.cfg.tree["inside_tf"].get(parent_tf, [])]
            got = max((r for r in rows if r), key=lambda r: r[1].score, default=None)
            self.cache.put(disk, {"c": None} if got is None else {"c": _count_row(got[0]), "score": got[1].score, "axes": got[1].axes})
        self.memo[key] = got
        return got

    def _best(self, tf: str, parent_tf: str, a: Pivot, b: Pivot, kinds: tuple[str, ...]) -> tuple[Count, Fit] | None:
        f = self.frames[tf]
        tf_ms = TF_MS[parent_tf]
        start, end = locate(f, tf_ms, a), locate(f, tf_ms, b)
        i, j = f.bar_at(start.ts), f.bar_at(end.ts)
        if j - i < self.cfg.tree["inside_min_bars"]:
            return None
        cap = self.cfg.pivots["max_pivots"]
        best: tuple[Count, Fit] | None = None
        seen: set[tuple[int, ...]] = set()
        for k in self.cfg.frames[tf]["k"]:
            closed = closed_at(f, k, start, end, j)
            if closed is None or len(closed) > cap:
                continue
            shape = tuple(p.ts for p in closed)
            if shape in seen or len(closed) < 4:
                continue
            seen.add(shape)
            scan = Scan(f, k, closed, None, self.cfg)
            s = scan.direction(0)
            for pattern in kinds:
                labs = ("0", *WAVES[pattern])
                for idx in scan.labellings(pattern, 0, len(closed) - 1):
                    c = Count(tf, pattern, s, labs, tuple(closed[t] for t in idx), k)
                    fit = self.judge.finish(self.judge.shape(c, f))
                    if best is None or fit.score > best[1].score:
                        best = (c, fit)
        return best

    def rule_five(self, parent_tf: str, a: Pivot, b: Pivot, kinds: tuple[str, ...]) -> tuple[Count, Fit] | None:
        """The labelling the rule passed this wave on, with its fit: it looks further down than `best`."""
        key = ("r", parent_tf, a.ts, a.price, b.ts, b.price, kinds)
        if key in self.memo:
            return self.memo[key]
        disk = self._key(*key)
        row = self.cache.get(disk)
        if row is not None:
            got = None if not row["c"] else (_count_of(row["c"]), Fit(row["score"], row["axes"], [], []))
        else:
            v = self.check(parent_tf, a, b, kinds)
            got = None
            if v.state == PASS and v.count is not None:
                f = self._minutes(a, b, TF_MS[parent_tf]) if v.count.tf == "1m" else self.frames[v.count.tf]
                got = (v.count, self.judge.finish(self.judge.shape(v.count, f)))
            self.cache.put(disk, {"c": None} if got is None else {"c": _count_row(got[0]), "score": got[1].score, "axes": got[1].axes})
        self.memo[key] = got
        return got

    def tree(self, c: Count, depth: int | None = None) -> list[Inner]:
        """What is inside each finished wave of this count, by the fill its grammar allows, as deep as the config says. A wave
        that must be a 5 shows the labelling the rule passed it on, unless `best` agrees on the pattern and its largest wave
        holds: `best` looks less far down, and may prefer a diagonal where the rule found the impulse the book lists first."""
        depth = self.cfg.tree["inside_depth"] if depth is None else depth
        if depth <= 0:
            return []
        out = []
        fill = self.cfg.grammar[c.pattern]
        rule_depth = self.cfg.inside["depth"]
        for n, wave in enumerate(WAVES[c.pattern][: c.done]):
            a, b = c.pts[n], c.pts[n + 1]
            kinds = tuple(fill[wave])
            got = self.best(c.tf, a, b, kinds)
            if form_of(kinds) == FIVE:
                rule = self.rule_five(c.tf, a, b, kinds)
                if rule is not None and (got is None or got[0].pattern != rule[0].pattern or not self._largest_holds(got[0], rule_depth - 1)):
                    got = rule
            if got is not None:
                out.append(Inner(wave, got[0], got[1], self.tree(got[0], depth - 1)))
        return out

    def judge_legs(self, c: Count, st: State | None = None) -> list[tuple[str, float, str]]:
        """Does each finished wave read as what its label says? A wave labelled corrective that reads clearly as a 5 is the
        count a person rejects on sight, and the book agrees: only an impulse's W1 and a zigzag's A start with a 5, and a 3 or
        5 that cannot be told apart is held as both (sec 0). The worst wave sets the item: one wrong label is enough. Plus
        what its motive waves look like inside: a fully labelled 5 is evidence for the count around it, which otherwise calls
        that whole move one bare leg. The same two questions go to what the running wave has printed so far."""
        spec = self.cfg.fit["leg_form"]
        fill = self.cfg.grammar[c.pattern]
        forms: list[float] = []
        words: list[str] = []
        fives: list[tuple[str, Fit]] = []

        def read(name: str, a: Pivot, b: Pivot, wants_five: bool | None, kinds: tuple[str, ...] = ()) -> None:
            five = self.best(c.tf, a, b, FIVES)
            three = self.best(c.tf, a, b, THREES)
            if wants_five:  # the inside rule looks further down than `best`: what it passed must not read here as "no 5"
                rule = self.rule_five(c.tf, a, b, kinds)
                if rule is not None and (five is None or rule[1].score > five[1].score):
                    five = rule
            if five is None and three is None:
                return
            f5, f3 = (five[1].score if five else 0.0), (three[1].score if three else 0.0)
            if wants_five is None:  # may be either: a 3 says nothing, a 5 is its first wave
                if five is not None and f5 >= f3 - spec["margin"]:
                    fives.append((name, five[1]))
                return
            if wants_five and five is None:  # no 5 could be labelled on these pivots: `subwaves` already says so, and a 3 is no proof
                return
            gap = (f5 - f3) if wants_five else (f3 - f5)
            forms.append(1.0 if gap >= -spec["margin"] else max(0.0, 1 + (gap + spec["margin"]) / spec["fade"]))
            if gap < -spec["margin"]:
                words.append(f"{name} reads as a {'3' if wants_five else '5'} ({max(f5, f3):.2f} against {min(f5, f3):.2f})")
            if wants_five and five is not None:
                fives.append((name, five[1]))

        for n, wave in enumerate(WAVES[c.pattern][: c.done]):
            read(f"W{wave}" if wave.isdigit() else wave, c.pts[n], c.pts[n + 1], all(k in MOTIVE for k in fill[wave]), tuple(fill[wave]))
        if st is not None:
            end = self._extreme(c.tf, st)
            if end is not None:
                name = f"W{st.wave}" if st.wave.isdigit() else ("the move after it" if st.wave == AFTER else st.wave)
                read(f"{name} so far", st.start, end, None if any(k in FIRST_FIVE for k in st.kinds) else False)
        out: list[tuple[str, float, str]] = []
        if forms:
            out.append(("leg_form", min(forms), "; ".join(words) if words else "each wave reads as its label says"))
        if fives:
            names = ", ".join(n for n, _ in fives)
            for axis in ("price", "time", "structure"):
                got = sum(ft.axes[axis] for _, ft in fives) / len(fives)
                out.append((f"inside_{axis}", got, f"inside {names}, a labelled 5: {axis} {got:.2f}"))
        return out

    def _extreme(self, tf: str, st: State) -> Pivot | None:
        """The running wave's extreme so far, as a pivot on this frame. None while it has not gone anywhere, or when the
        extreme sits in bars this frame has not closed yet."""
        f = self.frames[tf]
        if st.extreme == st.start.price:
            return None
        hi, hi_t, lo, lo_t = f.since_ts(f.bar_at(st.start.ts))
        ts = hi_t if st.d > 0 else lo_t
        if ts >= f.ts[-1] + f.tf_ms:
            return None
        return Pivot(ts, "H" if st.d > 0 else "L", st.extreme, ts + f.tf_ms)


def _unreadable(view: View) -> str:
    if view.short:
        return "too short to read at the finest frame"
    if view.legs >= 5:
        return f"up to {view.legs} legs at {view.tf}, threshold {view.k:g}: neither a 3 nor a 5 is legal there"
    if view.legs == 3:
        return f"3 legs at {view.tf}, threshold {view.k:g}, then too many to label"
    return "no structure visible at any threshold"
