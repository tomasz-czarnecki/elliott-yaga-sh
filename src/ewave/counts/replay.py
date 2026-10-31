"""The tree at past dates, on data cut at each date, against what price did next. A sanity check, not a backtest: a few
dates say nothing about a win rate, and none is claimed."""
from __future__ import annotations

from bisect import bisect_left

from .config import Config
from .frames import Frames, stamp, to_ms
from .nest import Builder, Node, _next_move


def resolve(full: Frames, tf: str, as_of_ms: int, target: float, stop: float, d: int, h_bars: int) -> dict:
    """What happened first after the date: target, invalidation or neither, within the horizon. Read on 15m bars; when
    one bar holds both, the invalidation goes first."""
    fine = full["15m"]
    i = bisect_left(fine.ts, as_of_ms)
    end_ms = as_of_ms + h_bars * full[tf].tf_ms
    while i < len(fine.ts) and fine.ts[i] < end_ms:
        hi, lo = fine.high[i], fine.low[i]
        hit_stop = lo <= stop if d > 0 else hi >= stop
        hit_target = hi >= target if d > 0 else lo <= target
        if hit_stop:
            return {"outcome": "invalidation", "ts": fine.ts[i]}
        if hit_target:
            return {"outcome": "target", "ts": fine.ts[i]}
        i += 1
    last = fine.ts[-1] + fine.tf_ms
    return {"outcome": "neither" if end_ms <= last else "open", "ts": min(end_ms, last)}


def excursions(full: Frames, as_of_ms: int, days: int) -> dict:
    fine = full["15m"]
    i = bisect_left(fine.ts, as_of_ms)
    j = bisect_left(fine.ts, as_of_ms + days * 86_400_000)
    if i >= len(fine.ts) or j <= i:
        return {}
    return {"close": fine.close[j - 1], "high": max(fine.high[i:j]), "low": min(fine.low[i:j])}


def run_date(full: Frames, cfg: Config, when: str, root: str, days: int, premise=None) -> dict:
    as_of = to_ms(when)
    cut = full.upto(as_of)
    tree = Builder(cut, cfg, premise).build(root)
    price = cut.price
    rows = []
    for node in tree.levels[0].nodes:
        rows.append(_row(full, node, price, cut.as_of_ms))
    ladder = []
    for lv in tree.levels[1:]:
        for node in lv.nodes[:2]:
            ladder.append(_row(full, node, price, cut.as_of_ms))
    return {"when": stamp(cut.as_of_ms), "price": price, "roots": rows, "children": ladder, "after": excursions(full, cut.as_of_ms, days), "days": days,
            "stats": tree.stats.get(root)}


def _row(full: Frames, node: Node, price: float, as_of_ms: int) -> dict:
    st = node.state
    primary = node.odds[0] if node.odds else None
    move_d, move_level = _next_move(st, price)
    out = {"id": node.id, "tf": node.tf, "fit": node.fit.score, "pattern": node.count.pattern, "s": node.count.s, "wave": st.wave, "axes": dict(node.fit.axes), "window_hi": None if st.window is None else st.window.hi_ts, "window_lo": None if st.window is None else st.window.lo_ts,
           "labels": [(lab, pt.ts, pt.price) for lab, pt in zip(node.count.labs, node.count.pts)],
           "invalidation": st.invalidation.price, "move_d": move_d, "move_level": move_level, "primary": None}
    if primary:
        r = resolve(full, node.tf, as_of_ms, primary.target, primary.stop, primary.d, primary.h_bars)
        out["primary"] = {"name": primary.name, "d": primary.d, "target": primary.target, "stop": primary.stop, "p": primary.p_h, "rr": primary.rr, **r}
    return out


def render(rows: list[dict]) -> str:
    out = ["| as of | close | root count | price / time / structure | running | due | target before invalidation | vol odds | R:R | what came first | high / low / close after |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        a = r["after"]
        tail = f"{a.get('high', 0):,.0f} / {a.get('low', 0):,.0f} / {a.get('close', 0):,.0f} ({r['days']} d)" if a else "n/a"
        for x in r["roots"]:
            p = x["primary"]
            levels = "none" if not p else f"{'up' if p['d'] > 0 else 'down'} {p['target']:,.0f} before {p['stop']:,.0f}"
            odds = "" if not p else f"{p['p']:.0%}"
            rr = "" if not p else f"{p['rr']:.2f}"
            first = "" if not p else f"{p['outcome']}" + ("" if p["outcome"] in ("open",) else f" {stamp(p['ts'])[:10]}")
            lab = " ".join(f"{a_}={b_:,.0f}" for a_, _, b_ in x["labels"])
            way = "up" if x["s"] > 0 else "down"
            ax = x["axes"]
            due = "none" if x["window_hi"] is None else f"{stamp(x['window_lo'])[:10]} to {stamp(x['window_hi'])[:10]}"
            out.append(f"| {r['when'][:10]} | {r['price']:,.0f} | {x['pattern']} {way}, fit {x['fit']:.2f}: {lab} | {ax['price']:.2f} / {ax['time']:.2f} / {ax['structure']:.2f} | {x['wave']} | {due} | {levels} | {odds} | {rr} | {first} | {tail} |")
    return "\n".join(out)
