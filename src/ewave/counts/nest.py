"""The tree: legal counts at the root, then for each kept parent, what the next frame must be doing inside the parent's
running wave. Pruned to a readable size, with the crossroads and the Y's of section 6 on every frame.

Degree consistency is a constraint here: a child starts exactly at the parent's last label, moves the way the parent's
running wave moves, and may only be a pattern that wave allows. When a child has finished, the parent's running wave
may be over too, but only where closing it there breaks none of the parent's own rules.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config
from .enumerate import Scan, flat_anchors, unbroken_anchors
from .frames import Frames, TF_MS
from .inside import FAIL, Cache, Inner, Insides, Verdict
from .odds import Odds, rows_for
from .pivots import Pivot, ladder_scans, locate, zigzag
from .premise import BROKEN, DEAD, Given, Premise, applies, given_on, status
from .rules import COMBO, CORRECTIVE, ED, FAMILY, FLAT, IMPULSE, LD, TRIANGLE, TRIPLE, WAVES, ZIGZAG, Checker
from .score import Fit, Judge, Subwaves, anchor_major, partner_filter, shares, tf_move
from .state import AFTER, Count, Kill, Level, State, advance, alive, describe


@dataclass
class Node:
    id: str
    tf: str
    depth: int
    count: Count
    state: State              # of the running wave: on a finished child, the parent's next wave
    own: State                # of the count itself
    fit: Fit
    share: float
    odds: list[Odds]
    closes_parent: bool       # this child finished, so the parent's wave is taken as over
    path_fit: float
    parent: "Node | None" = None
    children: list["Node"] = field(default_factory=list)
    no_child: bool = False    # the next frame found no legal parse inside the running wave
    extreme_ts: int = 0       # when the running wave's extreme printed, for the chart
    inside: list[Inner] = field(default_factory=list)  # what its finished waves look like inside
    alike: list = field(default_factory=list)          # the root's other labels for the same move, best first
    checks: list[Verdict] = field(default_factory=list)  # each wave against what it must hold inside


@dataclass
class Level_:
    tf: str
    nodes: list[Node]
    crossroads: dict


@dataclass
class Tree:
    root_tf: str
    as_of_ms: int
    price: float
    levels: list[Level_]
    stats: dict
    premise: dict | None = None  # where price stands against his premise, when one applied or was dropped


class Builder:
    def __init__(self, frames: Frames, cfg: Config, premise: Premise | None = None, cache: Cache | None = None):
        self.frames = frames
        self.cfg = cfg
        frames.wire_time(cfg.frames)
        self.judge = Judge(cfg)
        self.sub = Subwaves(frames, cfg)
        self.price = frames.price
        self.memo: dict[tuple, list] = {}
        self.stats: dict[str, dict] = {}
        self.anchor_from: dict[str, int] = {}
        self.unpaired = 0         # labellings dropped by FIB-T8: another pairing of the same legs won on time and price
        self.insides = Insides(frames, cfg, self.judge, cache)
        self.inside_rule: dict[str, dict] = {}  # per frame: readings read, killed by the inside rule, and why
        self.inside_known: dict[str, dict[tuple, bool]] = {}
        self.premise: Premise | None = None
        self.premise_status: dict | None = None
        if applies(premise, frames):
            self.premise_status = status(premise, frames, cfg)
            if self.premise_status["state"] not in (DEAD, BROKEN):
                self.premise = premise

    # --- candidates on one frame ---------------------------------------------------------------------------------

    def _read_insides(self, counts: list[tuple[Count, State]], tf: str) -> list[tuple[Count, State]]:
        """The inside rule: a reading dies when one of its finished waves is readable and does not hold what its label
        requires. Counted per frame, each reading once, however many thresholds show it and however many parents ask."""
        stat = self.inside_rule.setdefault(tf, {"read": 0, "killed": 0, "by": {}})
        known = self.inside_known.setdefault(tf, {})
        out = []
        for item in counts:
            c = item[0]
            key = (c.pattern, c.s, tuple(p.ts for p in c.pts))
            if key not in known:
                dead = [v for v in self.insides.checks(c) if v.state == FAIL]
                known[key] = not dead
                stat["read"] += 1
                stat["killed"] += bool(dead)
                for v in dead:
                    why = f"{v.wave} {v.why}"
                    stat["by"][why] = stat["by"].get(why, 0) + 1
            if known[key]:
                out.append(item)
        return out

    def _rank(self, counts: list[tuple[Count, State]], tf: str, major: bool, given: Given | None = None) -> list[tuple[Count, State, Fit]]:
        """Alive counts with their fit, best first. Variants of one reading read at several thresholds become one."""
        f = self.frames[tf]
        cfg = self.cfg
        counts = self._read_insides(counts, tf)
        seen: dict[tuple, tuple[Count, State, Fit]] = {}
        for c, st in counts:
            judged = self.judge.fit(c, st, f)
            if major:
                judged.append(anchor_major(c, f, self.anchor_from[tf]))
                whole = self.judge.whole_time(c, st, f)
                if whole:
                    judged.append(whole)
            if given is not None:
                judged += self.judge.premise_items(c, st, given.top, given.origin, f)
                judged.append(_confluence(st, given))
            mv = tf_move(tf, st, self.price, cfg)
            if mv:
                judged.append(mv)
            fit = self.judge.finish(judged)
            key = (c.pattern, c.s, tuple(p.ts for p in c.pts))
            if key not in seen or fit.score > seen[key][2].score:
                seen[key] = (c, st, fit)
        ranked = sorted(_without_open_twins(seen.values()), key=_order)
        ranked, dropped = partner_filter(ranked, self.judge, f, cfg.time["partner_margin"])
        self.unpaired += dropped
        # the costly check, for the shortlist only: sub-waves split counts (sec 6)
        short = cfg.tree["shortlist"]
        final = []
        for n, (c, st, fit) in enumerate(ranked):
            if n < short:
                judged = [(r.item, r.f, r.note) for r in fit.reasons]
                got = self.sub.judge(c, cfg.grammar)
                if got:
                    judged.append(got)
                judged += self.insides.judge_legs(c, st)
                fit = self.judge.finish(judged)
            final.append((c, st, fit))
        return sorted(final, key=_order)

    def given(self, tf: str) -> Given:
        return given_on(self.premise, self.frames, tf, self.cfg)

    def premise_candidates(self, tf: str) -> list[tuple[Count, State, Fit]]:
        """The root under his premise: every corrective reading of everything since the top, and nothing before it."""
        f = self.frames[tf]
        cfg = self.cfg
        given = self.given(tf)
        counts: list[tuple[Count, State]] = []
        for k in cfg.frames[tf]["k"]:
            pivots, running = zigzag(f, k, given.top)
            scan = Scan(f, k, pivots, running, cfg)
            counts += scan.counts_from(0, (ZIGZAG, FLAT, TRIANGLE, COMBO, TRIPLE))
        return self._rank(counts, tf, major=False, given=given)

    def root_candidates(self, tf: str) -> list[tuple[Count, State, Fit]]:
        if self.premise is not None:
            return self.premise_candidates(tf)
        f = self.frames[tf]
        cfg = self.cfg
        lookback = cfg.root["lookback_days"] * 86_400_000
        last_close = f.ts[-1] + f.tf_ms
        from_ts = last_close - lookback
        self.anchor_from[tf] = from_ts
        min_bars = cfg.root["min_span_bars"][tf]
        counts: list[tuple[Count, State]] = []
        for k in cfg.frames[tf]["k"]:
            pivots, running = zigzag(f, k)
            if not pivots:
                continue
            scan = Scan(f, k, pivots, running, cfg)
            anchors = unbroken_anchors(f, pivots, from_ts)
            flats = flat_anchors(pivots, anchors, cfg.root["flat_anchor_back"])
            for a in sorted(set(anchors) | set(flats)):
                if len(pivots) - a > cfg.pivots["max_pivots"]:
                    continue
                if (last_close - pivots[a].ts) / f.tf_ms < min_bars:
                    continue
                allowed = (IMPULSE, LD, ED, ZIGZAG, FLAT, TRIANGLE, COMBO) if a in anchors else (FLAT, COMBO)
                counts += scan.counts_from(a, allowed)
        return self._rank(counts, tf, major=True)

    def child_candidates(self, tf: str, start: Pivot, kinds: tuple[str, ...]) -> list[tuple[Count, State, Fit]]:
        key = (tf, start.ts, start.kind, kinds)
        if key in self.memo:
            return self.memo[key]
        f = self.frames[tf]
        cfg = self.cfg
        counts: list[tuple[Count, State]] = []
        for k, pivots, running in ladder_scans(f, cfg.frames[tf]["k"], cfg.pivots["max_pivots"], cfg.pivots["scales_per_window"], start):
            scan = Scan(f, k, pivots, running, cfg)
            counts += scan.counts_from(0, kinds)
        ranked = self._rank(counts, tf, major=False)
        self.memo[key] = ranked
        return ranked

    # --- the tree --------------------------------------------------------------------------------------------------

    def _node(self, nid: str, tf: str, depth: int, c: Count, st: State, fit: Fit, share: float, parent: Node | None) -> Node | None:
        """A candidate as a node of the tree. A finished child hands over to the parent's next wave, if the parent allows it."""
        f = self.frames[tf]
        cfg = self.cfg
        running = st
        closes = False
        if st.wave == AFTER and parent is not None:
            checker = Checker(cfg.rules)
            up = advance(parent.count, c.pts[-1], checker, TF_MS[parent.tf])
            if up is not None:
                up.first_leg = c.first_leg
                next_state = describe(up, f, cfg)
                if alive(up, next_state, f):
                    return None
                running = next_state
                closes = True
        fw = cfg.frames[tf]
        sigma = f.volatility(fw["vol_bars"])
        fallback = None
        if parent is not None:
            up_levels = parent.state.zone if parent.state.d == running.d else (parent.state.targets if parent.state.next_d == running.d else [])
            ahead = [lv for lv in up_levels if running.d * (lv.price - self.price) > 0]
            if ahead:
                near = min(ahead, key=lambda lv: abs(lv.price - self.price))
                fallback = Level(near.k, near.price, f"parent {near.pull}")
        odds = rows_for(running, self.price, sigma, fw["horizon_bars"], fallback, cfg.odds["min_target_sigmas"], self.frames.as_of_ms, f.tf_ms, cfg.odds["min_window_bars"])
        path = fit.score if parent is None else (parent.path_fit ** depth * fit.score) ** (1 / (depth + 1))
        hi, hi_t, lo, lo_t = f.since_ts(f.bar_at(running.start.ts))
        extreme_ts = hi_t if running.d > 0 else lo_t
        return Node(nid, tf, depth, c, running, st, fit, share, odds, closes, path, parent, extreme_ts=extreme_ts, checks=self.insides.checks(c, st))

    def _diverse(self, ranked, limit: int, needs_child, both_ways: bool = False) -> tuple[list, list]:
        """Best first, but one reading per idea before any second helping: three shades of one idea are not three counts. An
        idea below the root is a family and a running wave. At the root it is what a trader would do differently: which move
        is running, from where, and whether the structure before it is finished. Three combinations can be one idea, and two
        with the same labels on different pivots two. A count whose running wave does not parse one frame down goes last.
        both_ways: at the root, the other direction takes the last seat if it has none (sec 9). Below the root the parent has
        already set the direction."""
        picked: list = []
        seen: set[tuple] = set()
        rest: list = []
        for item in ranked:
            c, st, _ = item
            key = (st.d, st.start.ts, st.wave == AFTER) if both_ways else (FAMILY[c.pattern], c.s, st.wave)
            if key in seen:
                rest.append(item)
                continue
            seen.add(key)
            picked.append(item)
        ordered = picked + rest
        out, late = [], []
        for item in ordered:
            if needs_child(item):
                out.append(item)
            else:
                late.append(item)
            if len(out) >= limit:
                break
        out = out[:limit]
        if len(out) < limit:
            out += late[: limit - len(out)]
        # the other direction gets the last seat if it has none (sec 9)
        if both_ways and len(out) >= 2:
            ds = {_next_move(i[1], self.price)[0] for i in out}
            if len(ds) == 1:
                # a count already running that way says it plainly; one that only reaches it after a zone is second choice
                others = sorted((i for i in ordered if _next_move(i[1], self.price)[0] not in ds), key=lambda i: i[1].d in ds)
                other = next((i for i in others if needs_child(i)), None)
                if other is not None:
                    out[-1] = other
        return out, ordered

    def build(self, root_tf: str) -> Tree:
        cfg = self.cfg
        keep_root, keep_child = cfg.tree["keep_root"], cfg.tree["keep_child"]
        ladder = cfg.tree["ladder"]
        max_nodes = cfg.tree["max_nodes"]
        ranked = self.root_candidates(root_tf)
        states = _best_per_state(ranked)
        roots, _ = self._diverse(states, keep_root, lambda i: bool(self.child_candidates(ladder[0], *_child_key(ladder[0], root_tf, i[0], i[1], self.frames))), both_ways=True)
        fits = [i[2].score for i in roots] + [i[2].score for i in states if i not in roots]
        top, other = shares(fits, len(roots), cfg)
        levels: list[Level_] = []
        nodes: list[Node] = []
        for n, (item, sh) in enumerate(zip(roots, top), 1):
            c, st, fit = item
            node = self._node(f"{root_tf}.{n}", root_tf, 0, c, st, fit, sh, None)
            if node is not None:
                node.alike = _alike(c, st, states)
                nodes.append(node)
        self.stats[root_tf] = {"legal": len(ranked), "states": len(states), "other_share": other, "unpaired": self.unpaired, "inside": self.inside_rule.get(root_tf)}
        levels.append(Level_(root_tf, nodes, self._crossroads(root_tf, nodes, ranked, other)))
        parents = nodes
        for depth, tf in enumerate(ladder, 1):
            pool: list[Node] = []
            legal_all: list = []
            others = []
            for parent in parents:
                start, kinds = _child_key(tf, parent.tf, parent.count, parent.state, self.frames)
                ranked = self.child_candidates(tf, start, kinds)
                ranked = sorted(((c, st, self._with_confluence(c, st, fit, parent)) for c, st, fit in ranked if c.s == parent.state.d), key=_order)
                legal_all += ranked
                states = _best_per_state(ranked)
                if not states:
                    parent.no_child = True
                    continue
                next_tf = ladder[depth] if depth < len(ladder) else None
                needs = (lambda i: True) if next_tf is None else (lambda i: bool(self.child_candidates(next_tf, *_child_key(next_tf, tf, i[0], i[1], self.frames))))
                kept, _ = self._diverse(states, keep_child, needs)
                fits = [i[2].score for i in kept] + [i[2].score for i in states if i not in kept]
                top, other = shares(fits, len(kept), cfg)
                others.append(other)
                for n, (item, sh) in enumerate(zip(kept, top), 1):
                    c, st, fit = item
                    node = self._node(f"{parent.id}.{n}", tf, depth, c, st, fit, sh, parent)
                    if node is not None:
                        pool.append(node)
            pool = _prune(pool, max_nodes[depth])
            for node in pool:
                node.parent.children.append(node)
            other = sum(others) / len(others) if others else 1.0
            self.stats[tf] = {"legal": len(legal_all), "parents": len(parents), "other_share": other, "inside": self.inside_rule.get(tf)}
            levels.append(Level_(tf, pool, self._crossroads(tf, pool, legal_all, other)))
            parents = pool
        for lv in levels:
            for node in lv.nodes:
                node.inside = self.insides.tree(node.count)
        return Tree(root_tf, self.frames.as_of_ms, self.price, levels, self.stats, self.premise_status)

    def _with_confluence(self, c: Count, st: State, fit: Fit, parent: Node) -> Fit:
        judged = [(r.item, r.f, r.note) for r in fit.reasons]
        judged.append(_confluence(st, parent))
        judged += self._nest_time(c, st, parent)
        return self.judge.finish(judged)

    def _nest_time(self, c: Count, st: State, parent: Node) -> list[tuple[str, float, str]]:
        """The child against the parent's clock. A child that finishes the parent's wave must end inside the parent's
        window; one that does not must be able to end before that window closes. Plus the book's own nesting test, STR-C8:
        a sub-wave 2 that outlasts the primary wave 2."""
        out: list[tuple[str, float, str]] = []
        pw = parent.state.window
        fade = self.cfg.time["nest_fade"]
        if pw is not None:
            final = st.wave == AFTER and parent.count.done < len(WAVES[parent.count.pattern])
            late = early = 0
            if final:
                end = c.pts[-1].t
                late, early = max(0, end - pw.hi_ts), max(0, pw.lo_ts - end)
                what = "ends"
            elif st.window is not None:
                late = max(0, st.window.lo_ts - pw.hi_ts)
                what = "is due"
            if final or st.window is not None:
                gap = (late + early) / pw.base_ms / fade
                state = "inside" if not gap else ("after" if late else "before")
                out.append(("nest_time", max(0.0, 1 - gap), f"this count {what} {state} the parent's {pw.tool} window"))
        sub = self._sub_w2(c, st, parent)
        if sub:
            out.append(sub)
        return out

    def _sub_w2(self, c: Count, st: State, parent: Node) -> tuple[str, float, str] | None:
        pc = parent.count
        q = dict(zip(pc.labs, pc.pts))
        if pc.pattern != IMPULSE or parent.state.wave != "3" or "2" not in q or c.pattern != IMPULSE or "1" not in c.labs:
            return None
        f = self.frames[c.tf]
        mine = dict(zip(c.labs, c.pts))
        end = mine["2"].t if "2" in mine else f.ts[-1] + f.tf_ms
        primary = q["2"].t - q["1"].t
        t = (end - mine["1"].t) / max(primary, 1)
        spec = self.cfg.time["sub_w2"]
        tol = self.judge.t_tol(primary / f.tf_ms, f.resolution)
        if t < 1 - tol:
            g = 1.0
        elif t <= 1 + tol:
            g = spec["tie"]
        else:
            g = spec["tie"] * self.judge.limit(t, 1 + tol, spec["zero"])
        return ("sub_w2_time", g, f"sub-wave 2 has taken {t:.2f} x the primary W2 in time: longer kills the impulse reading")

    # --- section 6 -------------------------------------------------------------------------------------------------

    def _crossroads(self, tf: str, nodes: list[Node], legal: list, other: float) -> dict:
        price = self.price
        moves = [(n, *_next_move(n.state, price)) for n in nodes]
        ups = [m for m in moves if m[1] > 0]
        downs = [m for m in moves if m[1] < 0]
        shared = None
        if nodes and (not ups or not downs):
            d = 1 if ups else -1
            levels = [m[2] for m in moves if m[2] is not None]
            first = min(levels, key=lambda x: abs(x - price)) if levels else None
            stops = [k.price for n in nodes for k in n.state.kills if k.side == -d]
            guard = None
            if stops:
                guard = max(stops) if d > 0 else min(stops)
                guard = guard if d * (price - guard) > 0 else None
            shared = {"d": d, "first": first, "guard": guard, "n": len(nodes)}
        split = {"up": len(ups), "down": len(downs), "ups_first": _nearest([m[2] for m in ups], price), "downs_first": _nearest([m[2] for m in downs], price)}
        legal_up = sum(1 for i in legal if _next_move(i[1], price)[0] > 0)
        return {"tf": tf, "shared": shared, "split": split, "ys": _ys(nodes, price), "legal": len(legal), "legal_up": legal_up,
                "legal_down": len(legal) - legal_up, "other_share": other}


def _order(item) -> tuple:
    c, st, fit = item
    # ties: corrective first (unsure means corrective), then the rest stable by time and label
    return (-round(fit.score, 6), 0 if c.pattern in CORRECTIVE else 1, c.pattern, tuple(p.ts for p in c.pts))


def _without_open_twins(rows) -> list:
    """A last wave still called running, when the same labels finished at its first confirmed pivot are also on the board,
    is the same reading with less to judge: it would rank higher only for that. It comes back by itself if price passes
    that pivot, since the finished one dies there."""
    rows = list(rows)
    closed = {(c.pattern, c.s, tuple(p.ts for p in c.pts)) for c, _, _ in rows if c.done == len(WAVES[c.pattern])}
    return [r for r in rows if not (r[0].done == len(WAVES[r[0].pattern]) - 1 and r[0].first_leg is not None
                                    and (r[0].pattern, r[0].s, (*(p.ts for p in r[0].pts), r[0].first_leg.ts)) in closed)]


def _alike(c: Count, st: State, states: list, cap: int = 3) -> list:
    """Other patterns that read the same move at the root: the same running wave from the same pivot. They are one idea on
    the board, and their targets differ, so the reader is told."""
    idea = (st.d, st.start.ts, st.wave == AFTER)
    out, seen = [], {c.pattern}
    for item in states:
        c2, st2, _ = item
        if (st2.d, st2.start.ts, st2.wave == AFTER) == idea and c2.pattern not in seen:
            seen.add(c2.pattern)
            out.append(item)
            if len(out) >= cap:
                break
    return out


def _best_per_state(ranked: list) -> list:
    """One candidate per reading of where we are: same family, direction, running wave and start of that wave."""
    seen: set[tuple] = set()
    out = []
    for item in ranked:
        c, st, _ = item
        key = (FAMILY[c.pattern], c.s, st.wave, st.start.ts)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _child_key(tf: str, parent_tf: str, c: Count, st: State, frames: Frames) -> tuple[Pivot, tuple[str, ...]]:
    return locate(frames[tf], TF_MS[parent_tf], st.start), st.kinds


def _next_move(st: State, price: float) -> tuple[int, float | None]:
    """The move this count expects next on its own frame, and the first level on that path. A correction that has reached
    its zone hands over to the next wave; so does a motive wave past its first target."""
    ahead = [lv.price for lv in st.zone if st.d * (lv.price - price) > 0]
    if not st.zone_reached:
        return st.d, (min(ahead, key=lambda x: abs(x - price)) if ahead else None)
    d = st.next_d if st.next_d else -st.d
    later = [lv.price for lv in st.targets if d * (lv.price - price) > 0]
    return d, (min(later, key=lambda x: abs(x - price)) if later else None)


def _nearest(xs: list, price: float) -> float | None:
    xs = [x for x in xs if x is not None]
    return min(xs, key=lambda x: abs(x - price)) if xs else None


def _ys(nodes: list[Node], price: float, tol: float = 0.0025) -> list[dict]:
    """Levels where the counts part: crossing one kills some of them and leaves the rest (sec 6)."""
    rows: list[dict] = []
    for n in nodes:
        for k in n.state.kills:
            for r in rows:
                if r["side"] == k.side and abs(r["price"] / k.price - 1) <= tol:
                    if n.id not in r["kills"]:
                        r["kills"].append(n.id)
                    break
            else:
                rows.append({"price": k.price, "side": k.side, "kills": [n.id], "rule": k.rule})
    ids = [n.id for n in nodes]
    out = []
    for r in rows:
        if r["side"] * (r["price"] - price) <= 0:
            continue
        r["survive"] = [i for i in ids if i not in r["kills"]]
        out.append(r)
    above = sorted((r for r in out if r["side"] > 0), key=lambda r: r["price"])[:3]
    below = sorted((r for r in out if r["side"] < 0), key=lambda r: -r["price"])[:3]
    return above[::-1] + below


def _confluence(st: State, parent: "Node | Given") -> tuple[str, float, str]:
    """A level of this count on top of one of the parent's: the tradeable confluence of sec 1."""
    mine = [lv.price for lv in st.zone + st.targets]
    theirs = [lv.price for lv in parent.state.zone + parent.state.targets]
    best = min((abs(a / b - 1) for a in mine for b in theirs), default=None)
    if best is None:
        return ("parent_confluence", 0.0, "nothing to compare with the parent's levels")
    g = 1.0 if best <= 0.005 else max(0.0, 1 - (best - 0.005) / 0.02)
    return ("parent_confluence", g, f"a level within {best:.2%} of one of the parent's")


def _prune(pool: list[Node], limit: int) -> list[Node]:
    """Every parent keeps its best child if there is room; the seats left go to the best path fit."""
    if len(pool) <= limit:
        return pool
    by_path = sorted(pool, key=lambda n: (-n.path_fit, n.id))
    out: list[Node] = []
    seen: set[str] = set()
    for n in by_path:
        if n.parent.id not in seen and len(out) < limit:
            seen.add(n.parent.id)
            out.append(n)
    for n in by_path:
        if n not in out and len(out) < limit:
            out.append(n)
    return sorted(out, key=lambda n: n.id)
