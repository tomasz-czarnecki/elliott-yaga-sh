"""His premise (rules/premise.yaml): the macro count, given and not searched. The root of the tree is then the correction
since its end, and nothing before the red line is ever re-counted.

The book's consequences of a finished 5 stay honest here. The hard invalidation of the premise is the origin of the 5
(sec 0, UNSPOKEN R1). A new high above its end is not automatically a kill: it can be the B of an expanded flat, up to the
flat ceiling of the first leg down (sec 3), or an extended fifth (sec 3 and E5-2), so it only puts the premise under review.
Past that ceiling no corrective reading is left from this top, so the premise is called broken, and the tree goes back to
searching every root until he edits the file. His own labels are never killed by a rule: where one breaks one, it says so.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import yaml

from ..ingest.config import project_root
from .config import Config
from .frames import Frame, Frames, stamp, to_ms
from .pivots import Pivot, dated
from .rules import IMPULSE, Checker
from .state import Count, State, _flat_ceiling, describe

BROKEN, REVIEW, HOLDS, DEAD = "broken", "review", "holds", "dead"


def premise_path() -> Path:
    return project_root() / "rules" / "premise.yaml"


@dataclass(frozen=True)
class Mark:
    label: str
    ms: int
    price: float
    alts: tuple[tuple[int, float, str], ...]


@dataclass(frozen=True)
class Premise:
    version: str
    owner: str
    statement: str
    degree: str
    venue: str
    marks: tuple[Mark, ...]
    digest: str

    @property
    def origin(self) -> Mark:
        return self.marks[0]

    @property
    def top(self) -> Mark:
        return self.marks[-1]


def load_premise(path: Path | str | None = None) -> Premise | None:
    """None when there is no file, or when he has switched it off."""
    p = Path(path) if path else premise_path()
    if not p.exists():
        return None
    data = p.read_bytes()
    raw = yaml.safe_load(data)
    if not raw.get("active", True):
        return None
    marks = []
    for label, m in raw["labels"].items():
        alts = tuple((to_ms(str(a["t"])), float(a["p"]), a.get("note", "")) for a in m.get("alt", []))
        marks.append(Mark(str(label), to_ms(str(m["t"])), float(m["p"]), alts))
    return Premise(raw["version"], raw["owner"], raw["statement"], raw["degree"], raw["venue"], tuple(marks), hashlib.sha256(data).hexdigest()[:12])


def applies(premise: Premise | None, frames: Frames) -> bool:
    """Its venue, and only once its top is in the past: a run cut before the red line knows nothing of it."""
    return premise is not None and frames.venue == premise.venue and frames.as_of_ms > premise.top.ms + 86_400_000


def _pivot(f: Frame, ms: int, price: float, kind: str) -> Pivot:
    i = f.bar_at(ms)
    return dated(f, Pivot(f.ts[i], kind, price, f.ts[i] + f.tf_ms))


@dataclass
class Given:
    """The premise on one frame: his five as a count, which the engine reads and never searches."""
    premise: Premise
    tf: str
    count: Count
    state: State

    @property
    def top(self) -> Pivot:
        return self.count.pts[-1]

    @property
    def origin(self) -> Pivot:
        return self.count.pts[0]


def given_on(premise: Premise, frames: Frames, tf: str, cfg: Config) -> Given:
    f = frames[tf]
    kinds = ["L", "H", "L", "H", "L", "H"]
    pts = tuple(_pivot(f, m.ms, m.price, k) for m, k in zip(premise.marks, kinds))
    c = Count(tf, IMPULSE, 1, tuple(m.label for m in premise.marks), pts, 0.0)
    return Given(premise, tf, c, describe(c, f, cfg))


def status(premise: Premise, frames: Frames, cfg: Config) -> dict:
    """Where price stands against the premise's own levels."""
    f = frames["1h"]
    i = f.bar_at(premise.top.ms) + 1
    hi, lo = f.hi_since(i), f.lo_since(i)
    top, origin = premise.top.price, premise.origin.price
    ceiling = _flat_ceiling(top, lo, cfg) if lo < top else top
    if lo <= origin:
        return {"state": DEAD, "high": hi, "low": lo, "ceiling": ceiling,
                "note": f"price went below {origin:,.0f}, the origin of the 5: the premise is invalid (sec 0, UNSPOKEN R1). Every root is searched again until it is edited."}
    if hi >= ceiling:
        return {"state": BROKEN, "high": hi, "low": lo, "ceiling": ceiling,
                "note": f"price went above {ceiling:,.0f}, the flat ceiling of the fall from {top:,.0f}: no corrective reading is left from this top, the 5 had not ended (sec 3). Every root is searched again until it is edited."}
    if hi > top:
        return {"state": REVIEW, "high": hi, "low": lo, "ceiling": ceiling,
                "note": f"a new high, {hi:,.0f}, above {top:,.0f}. Not a kill: only a flat or a combination whose B or X went past the origin stays on the board, up to {ceiling:,.0f}; the other reading, an extended fifth, is his to make by editing the premise."}
    return {"state": HOLDS, "high": hi, "low": lo, "ceiling": ceiling,
            "note": f"under {top:,.0f} and over {origin:,.0f}: it holds."}


def _flag(rule: str, note: str, marks: dict) -> dict:
    return {"rule": rule, "note": note, "labels": {k: v for k, v in marks.items() if k in ("1", "2", "3")}}


def rule_notes(premise: Premise, frames: Frames, tf: str, cfg: Config) -> list[dict]:
    """His labels against the hard rules, every choice of pivots. Told plainly, and they kill nothing: the count is his."""
    f = frames[tf]
    checker = Checker(cfg.rules)
    rows = []
    options = [[(m.ms, m.price)] + [(a[0], a[1]) for a in m.alts] for m in premise.marks]
    kinds = ["L", "H", "L", "H", "L", "H"]
    labels = [m.label for m in premise.marks]
    for combo in product(*options):
        pts = tuple(_pivot(f, ms, price, k) for (ms, price), k in zip(combo, kinds))
        c = Count(tf, IMPULSE, 1, tuple(labels), pts, 0.0)
        broken = checker.violations(IMPULSE, 1, c.points(f.tf_ms))
        rows.append({"labels": {lab: stamp(ms)[:10] for lab, (ms, _) in zip(labels, combo)}, "broken": [{"rule": v.rule, "note": v.note} for v in broken]})
    return rows


def time_notes(premise: Premise, cfg: Config) -> list[str]:
    """His waves under the minimum time, on his own pivots: a strong guideline, told plainly, and nothing dies of it (FIB-T3)."""
    r = ratios_text(premise)
    share = cfg.time["minimum"]["share"]
    return [f"{w} took {r[w]['days']}d, {r[w]['time']} x {r[w]['of']}, under the {share} minimum" for w in ("W2", "W4") if r[w]["time"] < share]


def ratios_text(premise: Premise) -> dict:
    """The five's proportions on his own pivots, in log price and in time."""
    from math import log

    p = {m.label: m.price for m in premise.marks}
    t = {m.label: m.ms / 86_400_000 for m in premise.marks}
    g = lambda a, b: abs(log(p[b] / p[a]))
    d = lambda a, b: t[b] - t[a]
    return {"W2": {"price": round(g("1", "2") / g("0", "1"), 3), "days": round(d("1", "2")), "time": round(d("1", "2") / d("0", "1"), 2), "of": "W1"},
            "W3": {"price": round(g("2", "3") / g("0", "1"), 2), "days": round(d("2", "3")), "time": round(d("2", "3") / d("0", "1"), 2), "of": "W1"},
            "W4": {"price": round(g("3", "4") / g("2", "3"), 3), "days": round(d("3", "4")), "time": round(d("3", "4") / d("2", "3"), 2), "of": "W3"},
            "W5": {"price": round(g("4", "5") / g("0", "1"), 2), "days": round(d("4", "5")), "time": round(d("4", "5") / d("0", "1"), 2), "of": "W1"},
            "whole_days": round(d("0", "5"))}
