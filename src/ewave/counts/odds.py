"""The only probability on the board: how often a driftless random walk at today's volatility hits the target before the
invalidation, within a stated number of bars. It knows nothing of waves. It is the floor a count must beat, not an edge
(research/model-options/RECOMMENDATION.md). Geometry is the same with no time limit: stop / (stop + target).
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, exp, log, pi, sin, sqrt

from .state import Kill, Level, State


def barrier_prob(x: float, a: float, sig2_h: float) -> float:
    """P(Brownian motion from x in (0, a) hits a before 0 and before the horizon). Two-barrier series:

        u(x, T) = x/a + sum_n 2(-1)^n/(n pi) sin(n pi x/a) exp(-n^2 pi^2 sig2_h / (2 a^2))
    """
    if x <= 0:
        return 0.0
    if x >= a:
        return 1.0
    frac = x / a
    rate = pi * pi * sig2_h / (2 * a * a)
    # terms fall as exp(-n^2 rate); go on until they are below 1e-12, within reason
    terms = 5000 if rate <= 0 else min(5000, int(sqrt(28 / rate)) + 2)
    total = frac
    for n in range(1, terms + 1):
        total += 2 * (-1) ** n / (n * pi) * sin(n * pi * frac) * exp(-n * n * rate)
    return min(max(total, 0.0), 1.0)


@dataclass(frozen=True)
class Odds:
    name: str           # "leg" (the running wave to its zone) or "next" (the wave after it)
    d: int
    target: float
    pull: str
    stop: float
    stop_rule: str
    p_h: float          # within the horizon
    p_geo: float        # no time limit
    rr: float           # reward : risk
    h_bars: int
    sigma: float        # per bar
    h_src: str = "fixed"  # where the horizon came from: the time window, or the frame's fixed number


def first_target(levels: list[Level], price: float, d: int, min_log: float = 0.0) -> Level | None:
    """The nearest level still ahead of price and further than min_log: the conservative target goes first (sec 4)."""
    ahead = [lv for lv in levels if d * (lv.price - price) > 0 and abs(log(lv.price / price)) > min_log]
    return min(ahead, key=lambda lv: abs(lv.price - price)) if ahead else None


def odds_row(name: str, target: Level, stop: Kill, price: float, d: int, sigma: float, h_bars: int, h_src: str = "fixed") -> Odds | None:
    if d * (target.price - price) <= 0 or d * (stop.price - price) >= 0:
        return None
    x = abs(log(price / stop.price))
    a = x + abs(log(target.price / price))
    p_h = barrier_prob(x, a, sigma * sigma * h_bars)
    risk = abs(price - stop.price)
    return Odds(name, d, target.price, target.pull, stop.price, stop.rule, p_h, x / a, abs(target.price - price) / risk if risk else 0.0,
                h_bars, sigma, h_src)


def horizons(st: State, h_bars: int, now_ms: int | None, tf_ms: int, min_bars: int) -> tuple[int, str, int, str]:
    """Bars and source of the leg's and the next wave's horizon. Taken from the time window where there is one still ahead
    (FIB-T9): the leg has until the window closes, the next wave until then plus its own largest template. Otherwise, and
    when that would be too short to mean anything, the frame's fixed horizon."""
    leg, leg_src, nxt, nxt_src = h_bars, "fixed", h_bars, "fixed"
    if now_ms is None or st.window is None:
        return leg, leg_src, nxt, nxt_src
    left = st.window.hi_ts - now_ms
    if left / tf_ms >= min_bars:
        leg, leg_src = ceil(left / tf_ms), "window"
    if st.next_span_ms:
        total = (max(left, 0) + st.next_span_ms) / tf_ms
        if total >= min_bars:
            nxt, nxt_src = ceil(total), "window"
    return leg, leg_src, nxt, nxt_src


def rows_for(st: State, price: float, sigma: float, h_bars: int, fallback: Level | None = None, min_sigmas: float = 0.0,
             now_ms: int | None = None, tf_ms: int = 1, min_window_bars: int = 0) -> list[Odds]:
    """Two plans. "leg": the running wave to its zone, against what would end it. "next": the wave after it to its first
    target, against the running wave's limit (a running motive wave has none on that side: a new extreme says it is not
    over). The one State.next_first names goes first. `fallback`: a parent's level, for a first wave with no pull yet.
    A level within min_sigmas bars of volatility of price is skipped: it is already there."""
    leg_row = next_row = None
    leg_h, leg_src, next_h, next_src = horizons(st, h_bars, now_ms, tf_ms, min_window_bars)
    min_log = min_sigmas * sigma
    # a level the running wave has already reached is behind it, even if price has come back since
    furthest = st.extreme if st.d * (st.extreme - price) > 0 else price
    leg = first_target(st.zone, furthest, st.d, min_log)
    leg_stop = next((k for k in st.kills if k.side == -st.d), None)
    if leg and leg_stop:
        leg_row = odds_row("leg", leg, leg_stop, price, st.d, sigma, leg_h, leg_src)
    if st.next_d:
        nxt = first_target(st.targets, price, st.next_d, min_log)
        stop = next((k for k in st.kills if k.side == -st.next_d), None)
        if stop is None:
            stop = Kill(st.extreme, st.d, "new_extreme", "a new extreme: the running wave is not over")
        if nxt:
            next_row = odds_row("next", nxt, stop, price, st.next_d, sigma, next_h, next_src)
    rows = [r for r in ((next_row, leg_row) if st.next_first else (leg_row, next_row)) if r]
    if not rows and fallback is not None and leg_stop and st.d * (fallback.price - furthest) > 0:
        row = odds_row("parent", fallback, leg_stop, price, st.d, sigma, leg_h, leg_src)
        if row:
            rows.append(row)
    return rows
