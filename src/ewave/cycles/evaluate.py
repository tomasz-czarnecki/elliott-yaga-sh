"""The honest test: the identical pipeline on BTC and on random paths built from BTC's own days.

Both null models keep each day's candle shape, BTC's total return and the bars before stats_start. `shuffled` destroys
all time order; `block` keeps runs of block_days, so volatility clustering survives but anything longer does not.
"""
from __future__ import annotations

import random
from concurrent.futures import ProcessPoolExecutor

from .chain import swing_lows
from .config import LEVELS, Rules
from .cycle import LT, RT
from .fouryear import completed_troughs
from .hindsight import build
from .live import replay
from .series import Bars, median, percentile, to_ms


def _rate(hits: list[bool]) -> float | None:
    return sum(hits) / len(hits) if hits else None


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    return sxy / (sxx * syy) ** 0.5 if sxx and syy else None


def _lengths(cycles) -> list[int]:
    return [c.length for c in cycles]


def _cycle_block(prefix: str, cycles: list, level, m: dict) -> None:
    """What both layers report for finished cycles."""
    ls = _lengths(cycles)
    m[f"{prefix}.n"] = len(ls)
    if not ls:
        return
    m[f"{prefix}.len_median"] = median(ls)
    m[f"{prefix}.len_p25"] = percentile(ls, 25)
    m[f"{prefix}.len_p75"] = percentile(ls, 75)
    m[f"{prefix}.in_strict"] = _rate([level.lo <= x <= level.hi for x in ls])
    m[f"{prefix}.in_tol"] = _rate([level.lo_tol <= x <= level.hi_tol for x in ls])
    m[f"{prefix}.share_lt"] = _rate([c.translation == LT for c in cycles])
    m[f"{prefix}.share_rt"] = _rate([c.translation == RT for c in cycles])
    m[f"{prefix}.share_failed"] = _rate([c.failed for c in cycles])

    # Same cycle: does the end low come in below the start low? Translation here uses the finished cycle.
    m[f"{prefix}.lower_end|LT"] = _rate([c.lower_end for c in cycles if c.translation == LT])
    m[f"{prefix}.lower_end|RT"] = _rate([c.lower_end for c in cycles if c.translation == RT])
    # Next cycle: does the low after this one come in below this cycle's end low?
    nexts = list(zip(cycles, cycles[1:]))
    m[f"{prefix}.lower_next|LT"] = _rate([b.end_price < a.end_price for a, b in nexts if a.translation == LT])
    m[f"{prefix}.lower_next|RT"] = _rate([b.end_price < a.end_price for a, b in nexts if a.translation == RT])
    m[f"{prefix}.higher_end|HCL_above"] = _rate([not c.lower_end for c in cycles if c.hcl_above_start is True])
    m[f"{prefix}.higher_end|HCL_below"] = _rate([not c.lower_end for c in cycles if c.hcl_above_start is False])
    m[f"{prefix}.lower_end|failed"] = _rate([c.lower_end for c in cycles if c.failed])  # 1 minus this: the "fake out"
    m[f"{prefix}.lag1_corr"] = _pearson(ls, ls[1:]) if len(ls) > 3 else None
    mid = (level.lo + level.hi) / 2
    pairs = list(zip(ls, ls[1:]))
    m[f"{prefix}.long_after_short"] = _rate([b >= mid for a, b in pairs if a < mid])
    m[f"{prefix}.long_after_long"] = _rate([b >= mid for a, b in pairs if a >= mid])


def path_metrics(bars: Bars, rules: Rules) -> dict:
    """Every number in the comparison tables, for one path."""
    first = max(0, bars.index_of(to_ms(rules.series["stats_start"])))
    h = build(bars, rules)
    e = replay(bars, rules)
    m: dict = {}
    troughs = completed_troughs(bars, rules.fouryear)
    m["fouryear.n_bears"] = len(troughs)
    lows = [b.low_i for b in troughs]
    gaps = [b - a for a, b in zip(lows, lows[1:])]
    m["fouryear.max_gap_spread"] = (max(gaps) - min(gaps)) if len(gaps) >= 2 else None
    for name in LEVELS:
        level = rules.levels[name]
        machine = e.daily if name == "daily" else e.weekly
        done = [c for c in h.cycles[name] if c.length is not None]
        _cycle_block(f"{name}.hind", done, level, m)
        _cycle_block(f"{name}.live", machine.cycles, level, m)

        k = rules.null["unconstrained_swing_k"][name]
        swings = swing_lows(bars, k, first, len(bars) - 1)
        gs = [b - a for a, b in zip(swings, swings[1:])]
        m[f"{name}.free.n"] = len(gs)
        m[f"{name}.free.in_strict"] = _rate([level.lo <= g <= level.hi for g in gs])
        m[f"{name}.free.in_tol"] = _rate([level.lo_tol <= g <= level.hi_tol for g in gs])

        # Live: what was knowable on the first day the cycle could end, scored on the next confirmed low.
        hits = machine.zone_hits
        m[f"{name}.mid.lower_end|LT"] = _rate([z["below_start"] for z in hits if z["translation"] == LT])
        m[f"{name}.mid.lower_end|notLT"] = _rate([z["below_start"] for z in hits if z["translation"] != LT])
        m[f"{name}.mid.n_LT"] = sum(z["translation"] == LT for z in hits)
        m[f"{name}.mid.n_notLT"] = sum(z["translation"] != LT for z in hits)
        m[f"{name}.zone.n"] = len(hits)
        m[f"{name}.zone.time_hit"] = _rate([z["time_hit"] for z in hits])
        m[f"{name}.zone.price_hit"] = _rate([z["price_hit"] for z in hits])
        m[f"{name}.zone.both_hit"] = _rate([z["time_hit"] and z["price_hit"] for z in hits])

        m[f"{name}.swing.relaxed"] = machine.swing_seen
        m[f"{name}.swing.strict"] = machine.swing_strict

        hind = h.lows[name]
        live = [x.i for x in machine.chain]
        tol = level.match_tol
        m[f"{name}.agree.hind_found_live"] = _rate([any(abs(i - j) <= tol for j in live) for i in hind])
        m[f"{name}.agree.live_in_hind"] = _rate([any(abs(i - j) <= tol for j in hind) for i in live])
        m[f"{name}.agree.lag_median"] = median([(x.ts_confirmed - x.ts_low) / 86_400_000 for x in machine.chain]) if machine.chain else None
        m[f"{name}.agree.n_log"] = len(machine.log)
        m[f"{name}.agree.revised"] = _rate([x.status == "revised" for x in machine.log])
        standing = [x for x in machine.chain if x.ts_next is not None]
        m[f"{name}.hold.no_trade_below"] = _rate([x.ts_undercut is None for x in standing])
        m[f"{name}.hold.no_close_below"] = _rate([x.ts_failed is None for x in standing])
        # Of every low the machine ever confirmed: still not traded below when the next one confirmed.
        m[f"{name}.hold.all_confirmed"] = _rate([x.status != "revised" and x.ts_undercut is None for x in machine.log])
    return m


def null_path(bars: Bars, first: int, kind: str, block_days: int, rng: random.Random) -> Bars:
    """Bars up to `first` as they were, then BTC's own days from there in a new order, each day's OHLC taken relative
    to the previous close."""
    rows = [(bars.open[i] / bars.close[i - 1], bars.high[i] / bars.close[i - 1], bars.low[i] / bars.close[i - 1],
             bars.close[i] / bars.close[i - 1]) for i in range(first, len(bars))]
    m = len(rows)
    if kind == "shuffled":
        order = list(range(m))
        rng.shuffle(order)
    elif kind == "block":
        order = []
        while len(order) < m:
            start = rng.randrange(m)
            order.extend((start + j) % m for j in range(block_days))
        order = order[:m]
    else:
        raise ValueError(kind)
    o, h, l, c = bars.open[:first], bars.high[:first], bars.low[:first], bars.close[:first]
    prev = bars.close[first - 1]
    for k in order:
        ro, rh, rl, rc = rows[k]
        o.append(prev * ro)
        h.append(prev * rh)
        l.append(prev * rl)
        c.append(prev * rc)
        prev = c[-1]
    return Bars(bars.ts, o, h, l, c)


def _run_null(job: tuple) -> dict:
    bars, first, kind, block, seed, rules_raw, digest = job
    rules = Rules(rules_raw, digest)
    return path_metrics(null_path(bars, first, kind, block, random.Random(seed)), rules)


def run_nulls(bars: Bars, rules: Rules, paths_shuffled: int | None = None, paths_block: int | None = None,
              workers: int | None = None) -> dict[str, list[dict]]:
    cfg = rules.null
    first = bars.index_of(to_ms(rules.series["stats_start"]))
    counts = {"shuffled": cfg["paths_shuffled"] if paths_shuffled is None else paths_shuffled,
              "block": cfg["paths_block"] if paths_block is None else paths_block}
    jobs = []
    for offset, (kind, n) in enumerate(counts.items()):
        for i in range(n):
            jobs.append((bars, first, kind, cfg["block_days"], cfg["seed"] + 1_000_000 * offset + i, rules.raw, rules.digest))
    out: dict[str, list[dict]] = {k: [] for k in counts}
    with ProcessPoolExecutor(max_workers=workers or cfg["workers"]) as pool:
        for job, result in zip(jobs, pool.map(_run_null, jobs, chunksize=4)):
            out[job[2]].append(result)
    return out


def summarize(values: list[float]) -> dict | None:
    v = [x for x in values if x is not None]
    if not v:
        return None
    return {"median": median(v), "p5": percentile(v, 5), "p95": percentile(v, 95), "n": len(v)}


def compare(btc: dict, nulls: dict[str, list[dict]]) -> dict:
    """For each metric: BTC, each null's median and 5-95 percent range, and BTC's rank inside that null."""
    out = {}
    for key, value in btc.items():
        row: dict = {"btc": value}
        for kind, runs in nulls.items():
            s = summarize([r.get(key) for r in runs])
            row[kind] = s
            if s and value is not None:
                vals = [r[key] for r in runs if r.get(key) is not None]
                row[f"{kind}_rank"] = (sum(x < value for x in vals) + 0.5 * sum(x == value for x in vals)) / len(vals)
        out[key] = row
    return out


def repaint_check(bars: Bars, rules: Rules, step_days: int = 90, recent_days: int = 180) -> dict:
    """How far today's hindsight marks can be trusted at the right edge: rebuild them on data cut at many past dates,
    and see how many of the lows then marked in the last `recent_days` are still marked on all the data."""
    first = bars.index_of(to_ms("2016-01-01"))
    final = build(bars, rules)
    out = {}
    for name in LEVELS:
        tol = rules.levels[name].match_tol
        kept, total = 0, 0
        for t in range(first, len(bars) - 365, step_days):
            h = build(bars.upto(t + 1), rules)
            recent = [i for i in h.lows[name] if i > t - recent_days]
            total += len(recent)
            kept += sum(any(abs(i - j) <= tol for j in final.lows[name]) for i in recent)
        out[name] = {"kept": kept, "total": total, "rate": kept / total if total else None}
    return out


__all__ = ["path_metrics", "null_path", "run_nulls", "compare", "repaint_check"]
