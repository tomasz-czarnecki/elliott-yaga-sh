"""Magnets: levels from every frame and every root that land near each other. A cluster weighs what its counts weigh, each
reading once however many roots show it: the same 15m count under three roots is one count. It says where the board's levels
pile up, not that price respects them: Fib levels are hit at random-path rates (research/model-options/02-empirical.md B2).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, log


@dataclass(frozen=True)
class Source:
    price: float
    weight: float        # the count's fit, times what its parent says about this level
    reading: str         # identifies the count across roots
    node: str
    tf: str
    name: str            # "Combination, Y"
    pull: str
    role: str            # running, remaining, next or after
    status: str = ""


@dataclass
class Cluster:
    lo: float
    hi: float
    center: float
    weight: float
    sources: list[Source] = field(default_factory=list)

    @property
    def readings(self) -> int:
        return len({s.reading for s in self.sources})


def merge(sources: list[Source], tol: float) -> list[Cluster]:
    """Levels within `tol` of a cluster's first level, in log, make one cluster. A fixed width: chaining would let a run of near
    levels walk across a wide range and call it one. Each reading counts once in a cluster, at its best weight."""
    rows = sorted((s for s in sources if s.price > 0), key=lambda s: s.price)
    out: list[Cluster] = []
    group: list[Source] = []
    for s in rows:
        if group and log(s.price / group[0].price) > 2 * tol:
            out.append(_cluster(group))
            group = []
        group.append(s)
    if group:
        out.append(_cluster(group))
    return sorted(out, key=lambda c: (-c.weight, c.center))


def _cluster(group: list[Source]) -> Cluster:
    best: dict[str, float] = {}
    for s in group:
        best[s.reading] = max(best.get(s.reading, 0.0), s.weight)
    total = sum(best.values())
    w = sum(s.weight for s in group) or 1.0
    center = exp(sum(s.weight * log(s.price) for s in group) / w)
    return Cluster(group[0].price, group[-1].price, center, total, group)


def _reading(n: dict) -> str:
    return "|".join([n["tf"], n["pattern"], n["dir"] or "", *(str(x["t"]) for x in n["labels"])])


def sources_of(nodes: list[dict], after_weight: float) -> list[Source]:
    """Every level ahead on the board, except what a wave has already reached. The move after a structure counts for less: it
    is one step further from what has printed."""
    out = []
    for n in nodes:
        fit = n["fit"]["score"]
        reading = _reading(n)
        for leg in n["projection"]["legs"]:
            role = leg["role"]
            scale = after_weight if role == "after" else 1.0
            for t in leg["targets"]:
                if t["reached"]:
                    continue
                out.append(Source(t["p"], fit * t["nest_f"] * scale, reading, n["id"], n["tf"], f"{n['pattern_name']}, {leg['name']}", t["pull"], role, t["status"]))
    return out


def clusters_payload(nodes: list[dict], price: float, atr_1d: float, spec: dict) -> dict:
    tol = spec["tol_atr"] * atr_1d
    got = merge(sources_of(nodes, spec["after_weight"]), tol)
    total = sum(c.weight for c in got) or 1.0
    rows = []
    for n, c in enumerate(got):
        rows.append({"id": f"m{n + 1}", "p": round(c.center, 2), "lo": round(c.lo, 2), "hi": round(c.hi, 2), "weight": round(c.weight, 3), "share": round(c.weight / total, 4),
                     "readings": c.readings, "frames": sorted({s.tf for s in c.sources}, key=["1d", "12h", "4h", "1h", "15m"].index), "dist": round(c.center / price - 1, 4),
                     "side": "above" if c.center > price else "below",
                     "feeds": [{"node": s.node, "tf": s.tf, "name": s.name, "pull": s.pull, "role": s.role, "p": round(s.price, 2), "status": s.status, "weight": round(s.weight, 3)} for s in sorted(c.sources, key=lambda s: -s.weight)]})
    return {"tol": round(tol, 5), "rows": rows}


def cluster_of(price: float, rows: list[dict], tol: float) -> dict | None:
    """The cluster a level belongs to: it holds the level, or the nearest within tol."""
    best, dist = None, None
    for c in rows:
        d = 0.0 if c["lo"] <= price <= c["hi"] else min(abs(log(price / c["lo"])), abs(log(price / c["hi"])))
        if d <= tol and (dist is None or d < dist):
            best, dist = c, d
    return best
