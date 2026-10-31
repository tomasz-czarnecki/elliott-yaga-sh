"""The hindsight layer: the marks as the chart looks today, top down, on all the data. These marks repaint: the
newest ones can change when new bars arrive. The live layer (live.py) is the one that never looks ahead."""
from __future__ import annotations

from dataclasses import dataclass, field

from .chain import chain_between, node_cost_of
from .config import Rules
from .cycle import Cycle, make_cycle
from .fouryear import Bear, completed_troughs, running_bear
from .series import Bars, to_ms


@dataclass
class Hindsight:
    bears: list[Bear]
    running: Bear | None
    lows: dict[str, list[int]] = field(default_factory=dict)
    cycles: dict[str, list[Cycle]] = field(default_factory=dict)


def _signal_after(bars: Bars, i: int, sma: list[float | None]) -> bool:
    """Did price close above the moving average before trading below this low again?"""
    for j in range(i + 1, len(bars)):
        if bars.low[j] < bars.low[i]:
            return False
        if sma[j] is not None and bars.close[j] > sma[j]:
            return True
    return False


def _sma(close: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(close)
    total = 0.0
    for i, c in enumerate(close):
        total += c
        if i >= n:
            total -= close[i - n]
        if i >= n - 1:
            out[i] = total / n
    return out


def _nested(bars: Bars, level, dp: dict, anchors: list[int], first: int, last: int) -> list[int]:
    """The chain of `level` across all stretches between the parent's lows."""
    lows: list[int] = []
    cost = node_cost_of(bars, level, dp, first, last)
    edges: list[int | None] = [None, *anchors, None]
    for a, b in zip(edges, edges[1:]):
        if a is None and b is None:
            part = chain_between(bars, level, dp, None, None, first, last, cost)
        elif a is None:
            part = chain_between(bars, level, dp, None, b, first, b - 1, cost) if b > first else [b]
        elif b is None:
            part = chain_between(bars, level, dp, a, None, a + 1, last, cost)
        else:
            part = chain_between(bars, level, dp, a, b, a + 1, b - 1, cost)
        for i in part:
            if not lows or i > lows[-1]:
                lows.append(i)
    return _snap(bars, lows, set(anchors), level.snap_days, last - level.swing_k)


def _snap(bars: Bars, lows: list[int], fixed: set[int], days: int, newest: int) -> list[int]:
    """A chosen low moves to the lowest low within +-days of it, staying between its neighbours. The gap penalty can
    make the DP prefer a low a few days before the real one; on the chart that reads as a plain mistake."""
    out = list(lows)
    for n, i in enumerate(out):
        if i in fixed:
            continue
        a = max(i - days, out[n - 1] + 1 if n else 0)
        b = min(i + days, out[n + 1] - 1 if n + 1 < len(out) else newest)
        if b >= a:
            out[n] = min(range(a, b + 1), key=lambda k: (bars.low[k], k))
    return out


def build(bars: Bars, rules: Rules) -> Hindsight:
    first = max(0, bars.index_of(to_ms(rules.series["stats_start"])))
    last = len(bars) - 1
    bears = completed_troughs(bars, rules.fouryear)
    four = [b.low_i for b in bears]
    h = Hindsight(bears=bears, running=running_bear(bars))
    h.lows["fouryear"] = four
    weekly = _nested(bars, rules.levels["weekly"], rules.dp, [i for i in four if i >= first], first, last)
    h.lows["weekly"] = weekly
    h.lows["daily"] = _nested(bars, rules.levels["daily"], rules.dp, weekly, first, last)

    sma = _sma(bars.close, rules.live["sma_period"])
    for name in ("daily", "weekly"):
        level = rules.levels[name]
        cycles = []
        lows = h.lows[name]
        for s, e in zip(lows, lows[1:]):
            status = "confirmed" if _signal_after(bars, e, sma) else "provisional"
            cycles.append(make_cycle(name, bars, s, e, rules, status=status))
        if lows:
            cycles.append(make_cycle(name, bars, lows[-1], None, rules, expected=level.centre))
        h.cycles[name] = cycles
    fy = []
    for s, e in zip(four, four[1:]):
        fy.append(make_cycle("fouryear", bars, s, e, rules))
    if four:
        gaps = [b - a for a, b in zip(four, four[1:])]
        expected = sum(gaps) / len(gaps) if gaps else rules.fouryear["book_years"] * 365.25
        fy.append(make_cycle("fouryear", bars, four[-1], None, rules, expected=expected))
    h.cycles["fouryear"] = fy
    return h
