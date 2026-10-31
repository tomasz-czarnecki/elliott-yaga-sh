"""`site/data/local/counts.json`: what the chart panel shows. It stays out of git (site/data/local/ is ignored), so it
never reaches the public site. Times are in s, as the chart library wants them. Same input, same output, apart from
`generated_at_ms`.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..ingest.config import project_root
from ..ingest.store import atomic_write
from .config import Config
from .frames import Frames, stamp
from .inside import FAIL, HOLD, PASS, RUNNING, Cache, Inner, Verdict
from .nest import Builder, Node, Tree, _next_move
from .premise import DEAD, BROKEN, Premise, applies, given_on, ratios_text, rule_notes, status, time_notes
from .rules import ED, FLAT, IMPULSE, LD, TRIPLE, flat_kind
from .state import AFTER, _ret, crosshairs, sits_on_crosshair

FORMAT = "ewave-counts-4"
NOTE = ("Ranking is rulebook fit, not a win chance: no probability that a count is true can be measured. The only "
        "probability shown is how often a random walk at today's volatility reaches the target before the invalidation. "
        "Fib time here is the rulebook's plausibility filter, not a proven edge: its templates hit at random-path rates.")
NAMES = {IMPULSE: "Impulse", LD: "Leading diagonal", ED: "Ending diagonal", "zigzag": "Zigzag", FLAT: "Flat",
         "triangle": "Triangle", "combination": "Combination", TRIPLE: "Triple combination"}


def default_path() -> Path:
    return project_root() / "site" / "data" / "local" / "counts.json"


def _s(ms: int | None) -> int | None:
    return None if ms is None else ms // 1000


def _dir(d: int | None) -> str | None:
    return None if not d else ("up" if d > 0 else "down")


def _price(p: float) -> str:
    return f"{p:,.0f}"


def _wave_name(w: str) -> str:
    return f"W{w}" if w.isdigit() else ("the move after it" if w == AFTER else ("the second X" if w == "X2" else w))


def pattern_name(node: Node) -> str:
    c = node.count
    if c.pattern == FLAT and "B" in c.labs:
        kind = flat_kind(c.s, {lab: pt.price for lab, pt in zip(c.labs, c.pts)})
        return f"Flat ({kind})"
    return NAMES[c.pattern]


def title(node: Node) -> str:
    """One line a trader can read: the structure, its direction, where it stands."""
    c, st = node.count, node.state
    name = pattern_name(node)
    way = _dir(c.s)
    if c.done == 0:
        return f"First leg {way} running"
    if node.closes_parent:
        return f"{name} {way} finished at {_price(c.pts[-1].price)}, so {node.parent.tf.upper()} {_wave_name(node.parent.state.wave)} is over: {_wave_name(st.wave)} {_dir(st.d)} running"
    if st.wave == AFTER:
        return f"{name} {way} finished at {_price(c.pts[-1].price)}, next move {_dir(st.d)} running"
    return f"{name} {way}, in {_wave_name(st.wave)}"


def short_title(node: Node) -> str:
    """The same reading in a few words, for one line of the panel's list. `title` keeps the whole sentence."""
    c, st = node.count, node.state
    name = f"{pattern_name(node)} {_dir(c.s)}"
    if c.done == 0:
        return f"First leg {_dir(c.s)} running"
    if node.closes_parent or st.wave == AFTER:
        return f"{name} · done {_price(c.pts[-1].price)}"
    return f"{name} · in {_wave_name(st.wave)}"


def next_text(node: Node) -> str:
    """One structure ahead, no further (sec 0, posture)."""
    st = node.state
    if st.next_wave is None:
        return f"after this, the book draws no further pull from this count alone: read the {_dir(st.d)} move one frame down"
    tgt = sorted(lv.price for lv in st.targets)
    where = f", levels {_price(tgt[0])} to {_price(tgt[-1])}" if tgt else ""
    return f"then {_wave_name(st.next_wave)} {_dir(st.next_d)}{where}"


# The time ratio shown on each leg: against which wave it is judged (IMP-T1..T4, FIB-T5, CPX-G3).
_LEG_BASE = {IMPULSE: {"2": "1", "3": "1", "4": "3", "5": "1"}, LD: {"2": "1", "3": "1", "4": "2", "5": "1"}, ED: {"2": "1", "3": "1", "4": "2", "5": "1"},
             "zigzag": {"B": "A", "C": "A"}, FLAT: {"B": "A", "C": "A"}, "combination": {"X": "W", "Y": "W"}, TRIPLE: {"X": "W", "Y": "W", "X2": "Y", "Z": "W"}}
_LEG_ITEM = {"1": None, "2": "w2_time", "3": "w3_time", "4": "w4_time", "5": "w5_time", "B": ("b_time", "tri_legs"), "C": "ac_time", "X": "x_time", "Y": "wy_time", "X2": "x_time", "Z": "wy_time"}


def _span(ms: float) -> str:
    days = ms / 86_400_000
    if days >= 2:
        return f"{days:.0f}d"
    hours = ms / 3_600_000
    return f"{hours:.0f}h" if hours >= 2 else f"{ms / 60_000:.0f}m"


def _legs(node: Node) -> list[dict]:
    """Each finished leg with its duration and its ratio against the wave it is judged by, for the tags on the chart."""
    c = node.count
    bases = _LEG_BASE.get(c.pattern, {})
    durations: dict[str, int] = {}
    out = []
    failed = {r.item for r in node.fit.reasons if r.axis == "time" and r.f < 0.3}
    for (a, pa), (b, pb) in zip(zip(c.labs, c.pts), list(zip(c.labs, c.pts))[1:]):
        ms = pb.t - pa.t
        durations[b] = ms
        base = bases.get(b)
        x = round(ms / durations[base], 2) if base and durations.get(base) else None
        item = _LEG_ITEM.get(b)
        names = item if isinstance(item, tuple) else (item,)
        out.append({"from": a, "to": b, "ms": ms, "text": _span(ms), "x": x, "of": base, "bad": any(n in failed for n in names),
                    "t0": _s(pa.t), "t1": _s(pb.t), "p0": pa.price, "p1": pb.price})
    return out


def _window(node: Node, now_ms: int) -> dict | None:
    w = node.state.window
    if w is None:
        return None
    x = w.x(now_ms)
    return {"tool": w.tool, "pull": w.pull, "base": w.base, "base_text": _span(w.base_ms),
            "lo": _s(w.lo_ts), "hi": _s(w.hi_ts), "lo_str": stamp(w.lo_ts)[:10], "hi_str": stamp(w.hi_ts)[:10],
            "levels": [{"k": t.k, "t": _s(t.ts), "pull": t.pull} for t in w.levels],
            "x": round(x, 2), "status": w.status(now_ms)}


def window_text(win: dict | None, wave: str) -> str:
    if not win:
        return f"no time window: the book gives {wave} no base to measure from"
    head = f"due {win['lo_str']} to {win['hi_str']}"
    so_far = f"{win['x']:.2f} x {win['base']} so far"
    if win["status"] == "past":
        return f"past its window ({head}), {so_far}"
    return f"{head}, {so_far}"


def _levels(levels) -> list[dict]:
    return [{"k": lv.k, "p": round(lv.price, 2), "pull": lv.pull} for lv in levels]


def _kill(k, price: float) -> dict:
    return {"p": round(k.price, 2), "side": "above" if k.side > 0 else "below", "rule": k.rule, "note": k.note,
            "dist": round(abs(k.price / price - 1), 4)}


def kill_next(node: Node, price: float):
    return min(node.state.kills, key=lambda k: abs(k.price - price))


def _inside(rows: list[Inner]) -> list[dict]:
    """What a finished wave looks like inside, for the chart's faint labels and the panel's line."""
    out = []
    for r in rows:
        c = r.count
        name = NAMES[c.pattern]
        if c.pattern == FLAT:
            name = f"Flat ({flat_kind(c.s, {lab: pt.price for lab, pt in zip(c.labs, c.pts)})})"
        out.append({"wave": r.wave, "pattern": c.pattern, "name": name, "tf": c.tf, "k": c.k, "score": round(r.fit.score, 3),
                    "axes": {k: round(v, 3) for k, v in r.fit.axes.items()},
                    "labels": [{"l": lab, "t": _s(pt.ts), "at": _s(pt.t), "p": pt.price, "kind": pt.kind} for lab, pt in zip(c.labs, c.pts)],
                    "inside": _inside(r.legs)})
    return out


TF_NAME = {"1d": "1D", "12h": "12H", "4h": "4H", "1h": "1H", "15m": "15m", "1m": "1m"}


def verdict_word(v: Verdict) -> str:
    """One wave against what it must hold: "W3 5 ok (15m)", "W5 5 unreadable", "W4 3 or 5 held", "W5 running"."""
    if v.state == PASS:
        return f"{v.wave} {v.required} ok ({TF_NAME.get(v.tf, v.tf)})"
    if v.state == FAIL:
        return f"{v.wave} {v.required} FAIL, reads as {v.found}"
    if v.state == RUNNING:
        return f"{v.wave} running" + ("" if v.found == "?" else f", {v.found} so far")
    return f"{v.wave} {v.required} unreadable" if v.found == "?" else f"{v.wave} {v.found} held"


def verdict_row(v: Verdict) -> dict:
    return {"wave": v.wave, "required": v.required, "found": v.found, "state": v.state, "tf": v.tf, "k": v.k, "pattern": v.pattern, "note": v.note, "text": verdict_word(v)}


def _node(node: Node, price: float, now_ms: int, cfg: Config) -> dict:
    c, st = node.count, node.state
    move_d, move_level = _next_move(st, price)
    win = _window(node, now_ms)
    hit = sits_on_crosshair(st, node.extreme_ts, cfg.time["hit_tol"])
    return {
        "id": node.id,
        "parent": node.parent.id if node.parent else None,
        "tf": node.tf,
        "depth": node.depth,
        "title": title(node),
        "short": short_title(node),
        "pattern": c.pattern,
        "pattern_name": pattern_name(node),
        "dir": _dir(c.s),
        "k": c.k,
        "labels": [{"l": lab, "t": _s(pt.ts), "at": _s(pt.t), "p": pt.price, "kind": pt.kind, "conf": _s(pt.conf_ts)} for lab, pt in zip(c.labs, c.pts)],
        "wave": {"label": st.wave, "name": _wave_name(st.wave), "dir": _dir(st.d), "kinds": list(st.kinds),
                 "start": {"t": _s(st.start.ts), "at": _s(st.start.t), "p": st.start.price}, "so_far": round(st.extreme, 2), "so_far_t": _s(node.extreme_ts), "motive": st.motive_running},
        "zone": _levels(st.zone),
        "next": {"label": st.next_wave, "dir": _dir(st.next_d), "targets": _levels(st.targets), "text": next_text(node)},
        "closes_parent": node.closes_parent,
        "invalidation": _kill(st.invalidation, price),
        "kills": [_kill(k, price) for k in st.kills],
        "kill_next": _kill(kill_next(node, price), price),
        "window": win,
        "window_text": window_text(win, _wave_name(st.wave)),
        "crosshairs": [{"t": _s(x.ts), "p": round(x.price, 2), "time_k": x.time_k, "price_k": x.price_k, "pull": x.pull} for x in crosshairs(st, now_ms, cfg.time["max_crosshairs"])],
        "crosshair_hit": None if hit is None else {"t": _s(hit.ts), "p": round(hit.price, 2), "time_k": hit.time_k, "price_k": hit.price_k, "pull": hit.pull},
        "legs": _legs(node),
        "fit": {"score": round(node.fit.score, 3), "axes": {k: round(v, 3) for k, v in node.fit.axes.items()}, "fails": node.fit.fails, "share": round(node.share, 4),
                "reasons": [{"item": r.item, "f": r.f, "w": r.w, "note": r.note, "sec": r.sec, "axis": r.axis, "counted": r.counted} for r in node.fit.reasons]},
        "odds": [{"name": o.name, "dir": _dir(o.d), "target": round(o.target, 2), "pull": o.pull, "stop": round(o.stop, 2), "stop_rule": o.stop_rule,
                  "p": round(o.p_h, 4), "p_nolimit": round(o.p_geo, 4), "rr": round(o.rr, 2), "h_bars": o.h_bars, "h_src": o.h_src, "sigma": round(o.sigma, 5)} for o in node.odds],
        "next_move": {"dir": _dir(move_d), "level": None if move_level is None else round(move_level, 2)},
        "inside": _inside(node.inside),
        "inside_rule": [verdict_row(v) for v in node.checks],
        "inside_line": " · ".join(verdict_word(v) for v in node.checks),
        "alike": [{"name": NAMES[c2.pattern], "wave": _wave_name(st2.wave), "score": round(f2.score, 3), "axes": {k: round(v, 3) for k, v in f2.axes.items()},
                   "labels": [{"l": lab, "p": pt.price} for lab, pt in zip(c2.labs, c2.pts)]} for c2, st2, f2 in node.alike],
        "children": [n.id for n in node.children],
        "no_child": node.no_child,
    }


def _crossroads(cr: dict) -> dict:
    out = dict(cr)
    if cr["shared"]:
        out["shared"] = {**cr["shared"], "dir": _dir(cr["shared"]["d"])}
    out["ys"] = [{**y, "side": "above" if y["side"] > 0 else "below"} for y in cr["ys"]]
    return out


def premise_payload(premise: Premise | None, frames: Frames, cfg: Config) -> dict | None:
    """His premise with its own levels: what would invalidate it, what only puts it under review, the correction's price
    pulls and time window against the five, and what his labels do against the hard rules."""
    if not applies(premise, frames):
        return None
    tf = "1d"
    given = given_on(premise, frames, tf, cfg)
    st = status(premise, frames, cfg)
    w = given.state.window
    use_log = cfg.frames[tf].get("log_fib", False)
    origin, top = premise.origin.price, premise.top.price
    pulls = []
    for k in cfg.levels["next_degree_ret"]:
        pulls.append({"k": k, "linear": round(top - k * (top - origin), 2), "log": round(top * (origin / top) ** k, 2)})
    now = frames.as_of_ms
    kinds = {"0": "L", "1": "H", "2": "L", "3": "H", "4": "L", "5": "H"}
    return {
        "statement": premise.statement, "owner": premise.owner, "version": premise.version, "digest": premise.digest, "degree": premise.degree,
        "applied": st["state"] not in (DEAD, BROKEN),
        "status": st["state"], "status_note": st["note"],
        "origin": origin, "top": top, "top_t": _s(frames[tf].ts[frames[tf].bar_at(premise.top.ms)]), "top_str": stamp(premise.top.ms)[:10],
        "labels": [{"l": m.label, "t": _s(frames[tf].ts[frames[tf].bar_at(m.ms)]), "at": _s(m.ms), "p": m.price, "kind": kinds[m.label],
                    "alt": [{"t": _s(frames[tf].ts[frames[tf].bar_at(a[0])]), "p": a[1], "note": a[2]} for a in m.alts]} for m in premise.marks],
        "invalid_below": {"p": origin, "note": f"the origin of the 5: below it the premise is invalid (sec 0, UNSPOKEN R1)"},
        "review_above": {"p": top, "note": "a new high is not automatically a kill: the B of an expanded flat, or an extended fifth (sec 3, E5-2)"},
        "broken_above": {"p": round(st["ceiling"], 2), "note": "the flat ceiling of the fall so far: past it no corrective reading is left from this top (sec 3)"},
        "pulls": pulls,
        "window": {"tool": w.tool, "base": w.base, "base_text": _span(w.base_ms), "lo": _s(w.lo_ts), "hi": _s(w.hi_ts), "lo_str": stamp(w.lo_ts)[:10], "hi_str": stamp(w.hi_ts)[:10],
                   "levels": [{"k": t.k, "t": _s(t.ts), "str": stamp(t.ts)[:10]} for t in w.levels], "x": round(w.x(now), 3), "status": w.status(now)},
        "ratios": ratios_text(premise),
        "rule_notes": rule_notes(premise, frames, tf, cfg),
        "time_notes": time_notes(premise, cfg),
    }


def tree_payload(tree: Tree, cfg: Config) -> dict:
    return {
        "root": tree.root_tf,
        "levels": [{"tf": lv.tf, "crossroads": _crossroads(lv.crossroads), "stats": tree.stats.get(lv.tf),
                    "nodes": [_node(n, tree.price, tree.as_of_ms, cfg) for n in lv.nodes]} for lv in tree.levels],
    }


def recent_bars(frames: Frames, tail_days: int) -> dict:
    """The last bars of each chart frame. The public bar files refresh once a day, the counts more often: without these
    the newest labels would float past the end of the candles. Private, like the rest of this file."""
    out = {}
    for tf in ("1d", "4h", "1h", "15m"):
        f = frames[tf]
        start = frames.as_of_ms - tail_days * 86_400_000
        rows = [[t // 1000, o, h, l, c, v] for t, o, h, l, c, v in zip(f.ts, f.open, f.high, f.low, f.close, f.volume) if t >= start]
        out[tf] = rows
    return out


def payload(frames: Frames, cfg: Config, now_ms: int, premise: Premise | None = None, cache: Cache | None = None) -> dict:
    trees = {}
    cache = cache or Cache()  # the roots share one set of verdicts
    for root in cfg.tree["roots"]:
        trees[root] = tree_payload(Builder(frames, cfg, premise, cache).build(root), cfg)
    return {
        "format": FORMAT,
        "rules_version": cfg.version,
        "rules_digest": cfg.digest,
        "venue": frames.venue,
        "generated_at_ms": now_ms,
        "as_of": _s(frames.as_of_ms),
        "as_of_str": stamp(frames.as_of_ms),
        "price": frames.price,
        "note": NOTE,
        "premise": premise_payload(premise, frames, cfg),
        "default_root": cfg.tree["roots"][0],
        "recent_bars": recent_bars(frames, cfg.tree["recent_bars_days"]),
        "trees": trees,
    }


def write(obj: dict, out: Path | str | None = None) -> tuple[Path, int]:
    path = Path(out) if out else default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, separators=(",", ":")).encode()
    atomic_write(path, lambda f: f.write(data))
    return path, len(data)
