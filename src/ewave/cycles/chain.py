"""Hindsight marking at one level: the set of swing lows with the largest total depth whose gaps fit the window.

score = sum(depth of each chosen low) - penalties, all in log price (rules: dp). Dynamic programming over the
candidates, exact for this score: nodes in time order, one layer per number of cycles so far.
"""
from __future__ import annotations

from math import inf, log

from .config import Level
from .series import Bars, percentile


def swing_lows(bars: Bars, k: int, first: int, last: int) -> list[int]:
    """Bars in [first, last] that are the lowest low within +-k bars. A tie goes to the earliest bar.
    Needs k complete bars on the right, so the newest k days hold no candidate yet."""
    low = bars.low
    n = len(low)
    out = []
    for i in range(max(first, 0), min(last, n - 1 - k) + 1):
        v = low[i]
        left = low[max(0, i - k):i]
        if left and min(left) <= v:
            continue
        if min(low[i + 1:i + k + 1], default=inf) < v:
            continue
        out.append(i)
    return out


def depth(bars: Bars, i: int, window: int) -> float:
    """How far price rose on the weaker side of a low, within `window` bars: a capped log prominence. The cap keeps
    a low that is never undercut from counting for the whole bull market after it."""
    v = bars.low[i]
    left = max(bars.high[max(0, i - window):i + 1])
    right = max(bars.high[i:i + window + 1])
    return min(log(left / v), log(right / v))


def gap_penalty(gap: int, level: Level, weight: float) -> float:
    outside = max(0.0, level.lo_tol - gap, gap - level.hi_tol)
    return weight * outside / level.centre


def undercut(bars: Bars, a: int, b: int) -> float:
    """How far (log) a bar strictly between two chosen lows trades below both of them: a low the chain skipped."""
    if b - a < 2:
        return 0.0
    inner = min(bars.low[a + 1:b])
    floor = min(bars.low[a], bars.low[b])
    return log(floor / inner) if inner < floor else 0.0


def node_cost_of(bars: Bars, level: Level, dp: dict, first: int, last: int) -> float:
    """What a low must be worth to earn its place: a quantile of the depth of all candidates at this level. Without it
    every extra low adds score and the chain packs its lows at the short end of the window."""
    q = dp["node_cost_quantile"]
    depths = [depth(bars, i, level.depth_window) for i in swing_lows(bars, level.swing_k, first, last)]
    return percentile(depths, q) if q and depths else 0.0


def best_chain(bars: Bars, nodes: list[int], level: Level, dp: dict, *, fixed_start: bool, fixed_end: bool,
               span_start: int, span_end: int, node_cost: float = 0.0) -> list[int]:
    """The best chain over `nodes` (sorted bar indices). A fixed end must be in the chain and earns nothing itself: it
    is decided by the level above. A free end leaves an open stretch that pays only the gap penalty."""
    m = len(nodes)
    if m == 0:
        return []
    weight, cut_w, count_w = dp["gap_penalty"], dp["undercut_penalty"], dp["count_penalty"]
    cap = level.hi_tol * 3  # far beyond any sensible cycle; only the anchors alone may stay this far apart
    gain = [depth(bars, i, level.depth_window) - node_cost for i in nodes]
    if fixed_start:
        gain[0] = 0.0
    if fixed_end:
        gain[-1] = 0.0

    max_cycles = level.count_max + dp["count_hard_margin"]
    if not (fixed_start and fixed_end):  # an open stretch can hold more than one parent's worth of cycles
        max_cycles = max(max_cycles, int((span_end - span_start) / level.lo_tol) + 2)

    edges: list[list[tuple[int, float]]] = [[] for _ in range(m)]
    for j in range(1, m):
        for i in range(j):
            gap = nodes[j] - nodes[i]
            if gap > cap and not (i == 0 and j == m - 1):
                continue
            edges[j].append((i, gain[j] - gap_penalty(gap, level, weight) - cut_w * undercut(bars, nodes[i], nodes[j])))

    def count_cost(c: int) -> float:
        if fixed_start and fixed_end:
            return count_w * max(0, level.count_min - c, c - level.count_max)
        return count_w * max(0, c - level.count_max)

    first = [-inf] * m
    for j in range(m):
        if fixed_start and j > 0:
            break
        first[j] = gain[j] - (0.0 if fixed_start else gap_penalty_open(nodes[j] - span_start, level, weight)
                              + cut_w * _open_undercut(bars, nodes[j], span_start, nodes[j]))
    layers = [first]
    back: list[list[int]] = [[-1] * m]
    for _ in range(max_cycles):
        prev = layers[-1]
        cur = [-inf] * m
        bk = [-1] * m
        for j in range(1, m):
            for i, value in edges[j]:
                if prev[i] > -inf and prev[i] + value > cur[j]:
                    cur[j], bk[j] = prev[i] + value, i
        layers.append(cur)
        back.append(bk)
        if all(v == -inf for v in cur):
            break

    best, end_c, end_j = -inf, 0, 0
    for c, layer in enumerate(layers):
        for j in ([m - 1] if fixed_end else range(m)):
            if layer[j] == -inf:
                continue
            tail = 0.0 if fixed_end else (gap_penalty_open(span_end - nodes[j], level, weight)
                                          + cut_w * _open_undercut(bars, nodes[j], nodes[j] + 1, span_end + 1))
            total = layer[j] - tail - count_cost(c)
            if total > best:
                best, end_c, end_j = total, c, j
    if best == -inf:
        return []

    chain = []
    c, j = end_c, end_j
    while j >= 0:
        chain.append(nodes[j])
        j, c = back[c][j], c - 1
    return chain[::-1]


def gap_penalty_open(gap: int, level: Level, weight: float) -> float:
    """An unfinished stretch only pays for running too long: it may still end inside the window."""
    return weight * max(0.0, gap - level.hi_tol) / level.centre


def _open_undercut(bars: Bars, i: int, a: int, b: int) -> float:
    """The undercut on an unfinished stretch [a, b) next to low i: a lower low there is a low the chain skipped."""
    inner = min(bars.low[a:b], default=inf)
    return log(bars.low[i] / inner) if inner < bars.low[i] else 0.0


def chain_between(bars: Bars, level: Level, dp: dict, start: int | None, end: int | None, first: int, last: int,
                  node_cost: float = 0.0) -> list[int]:
    """Lows of `level` in a stretch: from anchor `start` (or free from bar `first`) to anchor `end` (or free to `last`)."""
    a = start + 1 if start is not None else first
    b = end - 1 if end is not None else last
    nodes = swing_lows(bars, level.swing_k, a, b)
    if start is not None:
        nodes.insert(0, start)
    if end is not None:
        nodes.append(end)
    return best_chain(bars, nodes, level, dp, fixed_start=start is not None, fixed_end=end is not None,
                      span_start=first if start is None else start, span_end=last if end is None else end, node_cost=node_cost)
