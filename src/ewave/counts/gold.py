"""His hand-labelled counts (gold/counts.yaml) as a regression test: the master plan's "the engine can at least reproduce
your reading". Not ground truth, and passing says nothing about a forecast.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from pathlib import Path

import yaml

from ..ingest.config import project_root
from .config import Config
from .frames import Frames, TF_MS, stamp, to_ms
from .export import verdict_word
from .inside import FAIL, Cache, Inner
from .nest import Builder, Node
from .pivots import Pivot, dated, locate
from .premise import Premise
from .rules import MOTIVE, PATTERNS, Checker
from .state import AFTER, Count


def gold_path() -> Path:
    return project_root() / "gold" / "counts.yaml"


@dataclass(frozen=True)
class GoldCount:
    id: str
    tf: str
    pattern: str
    s: int
    labels: dict[str, tuple[tuple[int, float], ...]]
    checks: tuple[str, ...]
    note: str
    as_of: str | None
    tol_bars: float
    tol_price: float

    @property
    def tf_ms(self) -> int:
        return TF_MS[self.tf]

    @property
    def first(self) -> tuple[int, float]:
        return next(iter(self.labels.values()))[0]

    @property
    def last_ms(self) -> int:
        return min(ms for ms, _ in list(self.labels.values())[-1])

    def variants(self):
        names = list(self.labels)
        for combo in product(*self.labels.values()):
            yield dict(zip(names, combo))

    def on(self, labs, pts) -> bool:
        """This count's labels sit on the entry's pivots, any acceptable one per label."""
        if tuple(labs) != tuple(self.labels):
            return False
        for lab, pt in zip(labs, pts):
            if not any(self.near(pt, ms, price) for ms, price in self.labels[lab]):
                return False
        return True

    def near(self, pt: Pivot, ms: int, price: float) -> bool:
        return abs(pt.price / price - 1) <= self.tol_price and abs(pt.t - ms) <= self.tol_bars * self.tf_ms

    def variant_of(self, labs, pts) -> str:
        out = []
        for lab, pt in zip(labs, pts):
            if len(self.labels[lab]) > 1:
                out.append(f"{lab}={pt.price:,.0f}")
        return " ".join(out) or "the only variant"


def load_gold(path: Path | str | None = None) -> list[GoldCount]:
    raw = yaml.safe_load(Path(path or gold_path()).read_bytes())
    out = []
    for e in raw["counts"]:
        labels = {str(k): tuple((to_ms(str(x["t"])), float(x["p"])) for x in v) for k, v in e["labels"].items()}
        out.append(GoldCount(e["id"], e["tf"], e["pattern"], 1 if e["direction"] == "up" else -1, labels, tuple(e["checks"]), " ".join(str(e.get("note", "")).split()),
                             e.get("as_of"), float(e.get("tol_bars", 1)), float(e.get("tol_price", 0.0005))))
    return out


@dataclass
class Check:
    name: str
    passed: bool
    lines: list[str] = field(default_factory=list)


@dataclass
class GoldResult:
    entry: GoldCount
    as_of_ms: int
    checks: list[Check]

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)


def _axes(fit) -> str:
    a = fit.axes
    return f"fit {fit.score:.3f} (price {a['price']:.2f} · time {a['time']:.2f} · structure {a['structure']:.2f})"


def _labels(c) -> str:
    return " ".join(f"{lab}={pt.price:,.0f}" for lab, pt in zip(c.labs, c.pts))


def _seed(e: GoldCount, frames: Frames) -> Pivot:
    f = frames[e.tf]
    ms, price = e.first
    i = f.bar_at(ms)
    kind = "L" if e.s > 0 else "H"
    return locate(f, f.tf_ms, Pivot(f.ts[i], kind, price, f.ts[i] + f.tf_ms))


def _candidates(e: GoldCount, b: Builder) -> list:
    """Every legal reading of that frame that starts at its 0, unconstrained: any pattern."""
    return b.child_candidates(e.tf, _seed(e, b.frames), PATTERNS)


def _rule_lines(e: GoldCount, frames: Frames, cfg: Config) -> list[str]:
    """Each variant against the hard rules, to say which ones cannot be on the board at all and why."""
    f = frames[e.tf]
    checker = Checker(cfg.rules)
    out = []
    for v in e.variants():
        c = variant_count(e, v, frames)
        broken = checker.violations(e.pattern, e.s, c.points(f.tf_ms))
        what = ", ".join(x.rule for x in broken) or "passes every rule"
        out.append(f"    {_labels(c)}: {what}")
    return out


def variant_count(e: GoldCount, v: dict, frames: Frames) -> Count:
    """One choice of his pivots as a count on his frame, with no search: what he drew, wherever the zigzag sits."""
    f = frames[e.tf]
    kinds = ["L" if (n % 2 == 0) == (e.s > 0) else "H" for n in range(len(v))]
    pts = []
    for (ms, price), k in zip(v.values(), kinds):
        i = f.bar_at(ms)
        pts.append(dated(f, Pivot(f.ts[i], k, price, f.ts[i] + f.tf_ms)))
    return Count(e.tf, e.pattern, e.s, tuple(v), tuple(pts), 0.0)


def _inner_labels(c: Count) -> str:
    return " ".join(f"{lab}={pt.price:,.0f}" for lab, pt in zip(c.labs[1:], c.pts[1:]))


def check_inside(e: GoldCount, b: Builder) -> Check:
    """His count against the inside rule, every variant, wave by wave, whatever the enumerator does. Passes when at least one
    variant has no wave that fails; the lines say which leg fails on the others and what the engine sees inside it."""
    lines = []
    clean = 0
    for v in e.variants():
        c = variant_count(e, v, b.frames)
        rows = b.insides.checks(c)
        clean += not any(x.state == FAIL for x in rows)
        lines.append(f"  {_labels(c)}: " + " · ".join(verdict_word(x) for x in rows))
        for x in rows:
            what = f"{x.pattern}: {_inner_labels(x.count)}" if x.count is not None else x.note
            lines.append(f"    {x.wave}: {x.state}. {x.note}" + (f". Inside: {what}" if x.count is not None else ""))
    lines.insert(0, f"  {clean} of {len(list(e.variants()))} variants have no failing wave")
    return Check("inside", clean > 0, lines)


def check_enumerate(e: GoldCount, b: Builder) -> Check:
    got = [(c, st, fit) for c, st, fit in _candidates(e, b) if c.pattern == e.pattern and e.on(c.labs, c.pts)]
    lines = []
    for c, st, fit in got:
        lines.append(f"  found {_labels(c)}, at threshold {c.k:g}: {_axes(fit)}")
    return Check("enumerate", bool(got), lines or ["  not found among the legal readings"])


def check_rank(e: GoldCount, b: Builder) -> Check:
    rows = [r for r in _candidates(e, b) if r[0].pts[-1].t >= e.last_ms - e.tol_bars * e.tf_ms]
    hits = [n for n, (c, _, _) in enumerate(rows, 1) if c.pattern == e.pattern and e.on(c.labs, c.pts)]
    lines = [f"  rank {hits[0]} of {len(rows)} readings that start at its 0 and reach its last label" if hits else f"  not among the {len(rows)} readings that reach its last label"]
    for n, (c, st, fit) in enumerate(rows[:3], 1):
        lines.append(f"  {n}. {c.pattern} {_labels(c)}: {_axes(fit)}")
    return Check("rank_first", bool(hits) and hits[0] == 1, lines)


def _find_inner(e: GoldCount, rows: list[Inner], path: tuple[str, ...]) -> tuple[str, ...] | None:
    for r in rows:
        here = (*path, f"inside {r.wave}")
        if r.count.pattern == e.pattern and e.on(r.count.labs, r.count.pts):
            return here
        deeper = _find_inner(e, r.legs, here)
        if deeper:
            return deeper
    return None


def _shown(e: GoldCount, node: Node) -> str | None:
    """Where the tree under this node shows the count: its own labels, or inside a finished wave."""
    if node.count.pattern == e.pattern and e.on(node.count.labs, node.count.pts):
        return f"{node.id}, as its own labels"
    at = _find_inner(e, node.inside, ())
    if at:
        return f"{node.id}, {', '.join(at)}"
    for k in node.children:
        got = _shown(e, k)
        if got:
            return got
    return None


def _room(e: GoldCount, node: Node) -> str | None:
    """Why this root reading has no room for the count, or None when it has: a label that calls that very move one
    corrective wave, since only an impulse's W1 and a zigzag's A start with a 5 (sec 0, UNSPOKEN R1)."""
    c = node.count
    ms, price = e.first
    last_ms, last_price = list(e.labels.values())[-1][0]
    if e.pattern not in MOTIVE:
        return None
    for lab, a, z in zip(c.labs[1:], c.pts, c.pts[1:]):
        if abs(a.price / price - 1) <= e.tol_price and abs(z.price / last_price - 1) <= e.tol_price:
            return f"it calls that whole move {lab}, a wave that must be a 3"
    return None


def check_tree(e: GoldCount, frames: Frames, cfg: Config, premise: Premise | None, cache: Cache | None = None) -> Check:
    b = Builder(frames, cfg, premise, cache)
    tree = b.build("1d")
    lines = []
    shown = 0
    ok = True
    for node in tree.levels[0].nodes:
        where = _shown(e, node)
        why = _room(e, node)
        head = f"  {node.id} {node.count.pattern} in {node.own.wave} ({_labels(node.count)})"
        if where:
            shown += 1
            lines.append(f"{head}: shown at {where}")
        elif why:
            lines.append(f"{head}: no room, {why}")
        else:
            ok = False
            lines.append(f"{head}: has room and does not show it")
    return Check("in_tree", ok and shown > 0, lines)


def check_kept(e: GoldCount, frames: Frames, cfg: Config, cache: Cache | None = None) -> Check:
    """Without the premise: the root keeps a reading of this pattern between its first and last pivot. Which of his exact
    variants can be on the board is printed too, with the rule that stops the others."""
    b = Builder(frames, cfg, None, cache)
    ranked = b.root_candidates(e.tf)
    first, last = list(e.labels)[0], list(e.labels)[-1]
    ends = []
    exact = []
    for n, (c, st, fit) in enumerate(ranked, 1):
        if c.pattern != e.pattern or c.labs[-1] != last:
            continue
        if not (any(e.near(c.pts[0], ms, p) for ms, p in e.labels[first]) and any(e.near(c.pts[-1], ms, p) for ms, p in e.labels[last])):
            continue
        ends.append((n, c, fit))
        if e.on(c.labs, c.pts):
            exact.append((n, c, fit))
    lines = []
    if ends:
        n, c, fit = ends[0]
        lines.append(f"  kept among {len(ranked)} legal root readings: {len(ends)} with the same 0 and {last}. Best at rank {n}: {_labels(c)}: {_axes(fit)}")
    else:
        lines.append(f"  no reading of this pattern between its 0 and {last} among {len(ranked)} legal root readings")
    if exact:
        n, c, fit = exact[0]
        lines.append(f"  his exact pivots too, rank {n}: {_labels(c)}: {_axes(fit)}")
    else:
        lines.append("  his exact pivots are not on the board. Each variant against the hard rules:")
        lines += _rule_lines(e, frames, cfg)
    return Check("kept", bool(ends), lines)


def run_entry(e: GoldCount, frames: Frames, cfg: Config, premise: Premise | None, cache: Cache | None = None) -> GoldResult:
    b = Builder(frames, cfg, None, cache)
    checks = []
    for name in e.checks:
        if name == "enumerate":
            checks.append(check_enumerate(e, b))
        elif name == "rank_first":
            checks.append(check_rank(e, b))
        elif name == "in_tree":
            checks.append(check_tree(e, frames, cfg, premise, cache))
        elif name == "kept":
            checks.append(check_kept(e, frames, cfg, cache))
        elif name == "inside":
            checks.append(check_inside(e, b))
        else:
            raise ValueError(f"unknown gold check {name!r}")
    return GoldResult(e, frames.as_of_ms, checks)


def render(results: list[GoldResult]) -> str:
    out = []
    for r in results:
        e = r.entry
        out.append(f"{'PASS' if r.passed else 'FAIL'} {e.id}: {e.tf} {e.pattern} {'up' if e.s > 0 else 'down'}, as of {stamp(r.as_of_ms)} UTC")
        out.append(f"  his note: {e.note}")
        for c in r.checks:
            out.append(f" {'pass' if c.passed else 'FAIL'} {c.name}")
            out.extend(c.lines)
        out.append("")
    return "\n".join(out)
