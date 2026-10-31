"""Prediction zones: a box, time x price, for the next low that has not confirmed yet.

Time:  last confirmed low + the level's window; the 4-year level uses its measured gaps, with their n.
Price: the top so far minus the measured top-to-next-low drops of past live cycles of the same level and translation
       (percentiles from the rules file). A failed cycle puts the box below the prior low, a right-translated one above
       it (Camel section 5). Everything comes from cycles already finished at that moment, so a zone is causal.
"""
from __future__ import annotations

from itertools import combinations
from math import exp, log

from .config import DAY_MS
from .cycle import RT, UNDETERMINED
from .series import percentile


def _range(values: list[float], qlo: float, qhi: float) -> tuple[float, float]:
    return percentile(values, qlo), percentile(values, qhi)


def level_zone(machine, last: int) -> dict | None:
    """The box of one level as of day index `last`, from the machine's own past. None before its first low."""
    if not machine.chain:
        return None
    level = machine.level
    rules = machine.rules
    bars = machine.engine.bars()
    anchor = machine.chain[-1]
    cycle = machine.open_cycle(last)
    translation = cycle.translation
    failed = cycle.failed
    top = cycle.top_price
    start = anchor.price

    t_from, t_to = anchor.ts_low + level.lo * DAY_MS, anchor.ts_low + level.hi * DAY_MS
    now_close = bars.ts[last] + DAY_MS
    overdue = now_close > t_to
    if overdue:  # the window has passed without a low: keep the box in front of the price, at the window's own width
        t_from, t_to = now_close, now_close + (level.hi - level.lo) * DAY_MS

    done = [c for c in machine.cycles if c.drop_log is not None]
    qlo, qhi = rules.zones["percentiles"]
    same = [c for c in done if c.translation == translation] if translation != UNDETERMINED else []
    source = translation
    pool = same
    if len(pool) < rules.zones["min_samples"]:
        pool, source = done, "all"
    p_lo = p_hi = None
    side = None
    if pool:
        drop_lo, drop_hi = _range([c.drop_log for c in pool], qlo, qhi)
        p_lo, p_hi = top * exp(-drop_hi), top * exp(-drop_lo)
        if failed:
            side = "below_prior_low"
            if p_lo >= start:  # the measured drops stop above it: use how far past failed cycles went below their start
                under = [log(c.start_price / c.end_price) for c in done if c.failed and c.end_price < c.start_price]
                if under:
                    u_lo, u_hi = _range(under, qlo, qhi)
                    p_lo, p_hi = start * exp(-u_hi), start * exp(-u_lo)
                    source += "+failed_undercut"
                else:
                    p_lo = None
            elif p_hi > start:
                p_hi = start
        elif translation == RT:
            side = "above_prior_low"
            if p_hi <= start:  # the measured drops go below it: use how far past right-translated cycles ended above it
                over = [log(c.end_price / c.start_price) for c in done if c.translation == RT and c.end_price > c.start_price]
                if over:
                    o_lo, o_hi = _range(over, qlo, qhi)
                    p_lo, p_hi = start * exp(o_lo), start * exp(o_hi)
                    source += "+rt_rise"
                else:
                    p_lo = None
            elif p_lo < start:
                p_lo = start
    if p_lo is None:
        p_hi = None
    return {
        "level": level.name,
        "anchor_ts": anchor.ts_low, "anchor_price": start, "anchor_confirmed": anchor.ts_confirmed,
        "t_from": t_from, "t_to": t_to, "elapsed": last - anchor.i, "overdue": overdue,
        "window_days": [level.lo, level.hi],
        "p_lo": p_lo, "p_hi": p_hi,
        "translation": translation, "failed": failed, "side": side,
        "top_ts": cycle.top_ts, "top_price": top, "n": len(pool), "source": source, "percentiles": [qlo, qhi],
        "candidate": None if machine.candidate is None else {
            "ts": bars.ts[machine.candidate.i], "price": machine.candidate.price},
    }


def fouryear_zone(machine, engine, last: int) -> dict | None:
    """The next 4-year low, from the bears that have completed by now. Few samples: min to max, and n is printed.

    With a low standing in the current bear only the gap from it is known, and no price: the next top is not in yet."""
    done = machine.completed
    bars = engine.bars()
    if not done or machine.ath is None:
        return None
    lows = [b.low_i for b in done]
    gaps = [b - a for a, b in zip(lows, lows[1:])]
    ath_to_low = [b.ath_to_low_days for b in done]
    drops = [b.log_drop for b in done]
    standing = machine.confirmed
    base = standing.i if standing else lows[-1]
    spans = {}
    if gaps:
        spans["gap_from_last_low"] = [bars.ts[base] + d * DAY_MS for d in (min(gaps), max(gaps))]
    if not standing:
        spans["ath_to_low"] = [bars.ts[machine.ath_i] + d * DAY_MS for d in (min(ath_to_low), max(ath_to_low))]
    if not spans:
        return None
    t_from = min(s[0] for s in spans.values())
    t_to = max(s[1] for s in spans.values())
    now_close = bars.ts[last] + DAY_MS
    p_lo = p_hi = None
    if not standing:
        p_lo, p_hi = machine.ath * exp(-max(drops)), machine.ath * exp(-min(drops))
    so_far = None
    if machine.low_i is not None:
        so_far = {"ts": bars.ts[machine.low_i], "price": machine.low, "drawdown": 1 - machine.low / machine.ath,
                  "ath_to_low_days": machine.low_i - machine.ath_i}
    return {
        "level": "fouryear",
        "anchor_ts": bars.ts[base], "anchor_price": bars.low[base],
        "ath_ts": bars.ts[machine.ath_i], "ath_price": machine.ath,
        "t_from": t_from, "t_to": t_to, "elapsed": last - base, "overdue": now_close > t_to,
        "spans": spans, "n_gaps": len(gaps), "n_bears": len(done),
        "drawdowns": [b.drawdown for b in done], "ath_to_low_days": ath_to_low, "gaps_days": gaps,
        "p_lo": p_lo, "p_hi": p_hi,
        "translation": None, "failed": False, "side": None,
        "lowest_so_far": so_far,
    }


def overlaps(zones: list[dict]) -> list[dict]:
    """Where the time windows of different levels overlap: the stronger part of a zone."""
    out = []
    for n in (3, 2):
        for group in combinations(zones, n):
            a = max(z["t_from"] for z in group)
            b = min(z["t_to"] for z in group)
            if a <= b:
                out.append({"levels": [z["level"] for z in group], "t_from": a, "t_to": b})
    return out
