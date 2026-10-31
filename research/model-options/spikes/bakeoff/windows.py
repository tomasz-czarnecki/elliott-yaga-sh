"""The chart windows shown to the LLM: BTC windows, and shuffled-return paths built from the same bars.

Every window is masked: prices multiplied by a constant and dates moved, so a model cannot recall what happened next.
Null windows are the source window's own bars in a new order (each bar's OHLC relative to the previous close), so they
keep the same bars, net move and volatility, but no time structure. One draw per seed, never redrawn.

Run from the repo root:
    uv run --with numpy python research/model-options/spikes/bakeoff/windows.py
Writes to $BAKE_OUT/windows/ (default /opt/data/cache/scratch/elliott_research_r1/bake/windows/).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import random
from pathlib import Path

import numpy as np

from enumerator import readings, summary
from zigzag import Series, day_str, load_series, rsi, threshold, zigzag

OUT = Path(os.environ.get("BAKE_OUT", "/opt/data/cache/scratch/elliott_research_r1/bake"))
VENUE = "bitstamp_btcusd"
PRE_ROLL = 300
HORIZON = {"1d": 120, "4h": 150}
K = {"1d": 3, "4h": 4}  # 1D: median leg 22-28 percent; 4H: median leg 10-12 percent. See 03-bakeoff.md.

# id, timeframe, start, end (exclusive), kind, why. Starts and ends are deliberately not on the exact extreme of the move:
# a window that ends on the famous top hands the model the answer.
WINDOWS = [
    {"id": "D1", "tf": "1d", "start": "2020-03-01", "end": "2021-04-25", "kind": "bull", "why": "2020 crash low to the April 2021 top and the first drop; widely counted as a clean five"},
    {"id": "D2", "tf": "1d", "start": "2021-10-25", "end": "2022-12-15", "kind": "bear", "why": "November 2021 top to the November 2022 low"},
    {"id": "D3", "tf": "1d", "start": "2015-01-01", "end": "2015-11-20", "kind": "messy", "why": "base after the 2015 low, wild two-way legs; honest answer is unclear"},
    {"id": "H1", "tf": "4h", "start": "2017-10-20", "end": "2017-12-22", "kind": "bull", "why": "the 2017 blow-off and the first drop"},
    {"id": "H2", "tf": "4h", "start": "2025-10-02", "end": "2025-12-01", "kind": "bear", "why": "the October 2025 top and the fall to November 2025"},
    {"id": "H3", "tf": "4h", "start": "2023-06-20", "end": "2023-08-20", "kind": "messy", "why": "tight two-month range with a sudden drop at the end; honest answer is unclear"},
    {"id": "L1", "tf": "4h", "start": "2026-08-10", "end": "2026-10-30", "kind": "live", "why": "today's chart, after the model's training data, no future to score; honest answer is probably unclear"},
    {"id": "N1", "tf": "1d", "start": "2020-03-01", "end": "2021-04-25", "kind": "null", "source": "D1", "seed": 20261031, "why": "D1's bars shuffled"},
    {"id": "N2", "tf": "4h", "start": "2025-10-02", "end": "2025-12-01", "kind": "null", "source": "H2", "seed": 20261032, "why": "H2's bars shuffled"},
    {"id": "N3", "tf": "1d", "start": "2015-01-01", "end": "2015-11-20", "kind": "null", "source": "D3", "seed": 20261033, "why": "D3's bars shuffled"},
    {"id": "D1u", "tf": "1d", "start": "2020-03-01", "end": "2021-04-25", "kind": "unmasked", "source": "D1", "why": "D1 with its real dates and prices, to see what memory does"},
]


def ms(day: str) -> int:
    return int(dt.datetime.fromisoformat(day).replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


def shuffled(s: Series, a: int, b: int, post: int, seed: int) -> Series:
    """Bars before a as they were; bars a..b, then a..post, each reshuffled within its own stretch."""
    rng = random.Random(seed)
    rel = np.column_stack([s.open[1:] / s.close[:-1], s.high[1:] / s.close[:-1], s.low[1:] / s.close[:-1], s.close[1:] / s.close[:-1]])
    idx_win = list(range(a - 1, b - 1))
    idx_post = list(range(b - 1, post - 1))
    rng.shuffle(idx_win)
    rng.shuffle(idx_post)
    order = idx_win + idx_post
    o, h, l, c = s.open.copy(), s.high.copy(), s.low.copy(), s.close.copy()
    hl = s.order.copy()
    prev = s.close[a - 1]
    for pos, k in enumerate(order):
        t = a + pos
        o[t], h[t], l[t], c[t] = prev * rel[k]
        hl[t] = s.order[k + 1]
        prev = c[t]
    return Series(s.ts, o, h, l, c, hl, s.tf_ms)


def mask_for(wid: str) -> tuple[float, int]:
    """Price factor (log-uniform 0.05 to 20, never within a factor of 2 of the real level) and whole-day date shift."""
    rng = random.Random("mask-" + wid)
    while True:
        factor = float(np.exp(rng.uniform(np.log(0.05), np.log(20))))
        if not 0.5 < factor < 2:
            return factor, rng.randrange(3000, 7000)


def fmt(x: float) -> str:
    return f"{x:.2f}"


def build(spec: dict, cache: dict) -> dict:
    tf = spec["tf"]
    s0 = cache.setdefault(tf, load_series(VENUE, tf))
    a, b = int(np.searchsorted(s0.ts, ms(spec["start"]))), int(np.searchsorted(s0.ts, ms(spec["end"])))
    post = min(len(s0), b + HORIZON[tf])
    s = shuffled(s0, a, b, post, spec["seed"]) if spec["kind"] == "null" else s0
    upto = s.slice(0, b)
    pivots, prov = zigzag(upto, threshold(upto, K[tf]), start=max(0, a - PRE_ROLL))
    pivots = [p for p in pivots if p.i >= a]
    r = rsi(upto.close)
    masked = spec["kind"] != "unmasked"
    factor, shift = mask_for(spec.get("source", spec["id"]) if spec["kind"] == "unmasked" else spec["id"]) if masked else (1.0, 0)
    t_of = lambda i: day_str(int(s.ts[i]) + shift * 86_400_000, with_time=tf != "1d")

    rows = [{"pivot": n, "bar": p.i - a, "time": t_of(p.i), "kind": p.kind, "price": round(p.price * factor, 2),
             "rsi11": round(float(r[p.i]), 1), "conf_bar": p.conf_i - a, "provisional": False} for n, p in enumerate(pivots)]
    if prov and prov["i"] >= a:
        rows.append({"pivot": len(rows), "bar": prov["i"] - a, "time": t_of(prov["i"]), "kind": prov["kind"],
                     "price": round(prov["price"] * factor, 2), "rsi11": round(float(r[prov["i"]]), 1), "conf_bar": None, "provisional": True})
    bars = [{"bar": t - a, "time": t_of(t), "open": round(s.open[t] * factor, 2), "high": round(s.high[t] * factor, 2),
             "low": round(s.low[t] * factor, 2), "close": round(s.close[t] * factor, 2), "rsi11": round(float(r[t]), 1)} for t in range(a, b)]
    future = [{"high": round(s.high[t] * factor, 2), "low": round(s.low[t] * factor, 2), "order": int(s.order[t])} for t in range(b, post)]

    lines = ["pivot,time,kind,price,bars_since_prev,rsi11"]
    for n, row in enumerate(rows):
        gap = "" if n == 0 else row["bar"] - rows[n - 1]["bar"]
        tag = ",provisional" if row["provisional"] else ""
        lines.append(f"{row['pivot']},{row['time']},{row['kind']},{fmt(row['price'])},{gap},{row['rsi11']}{tag}")
    pivot_table = "\n".join(lines)
    raw_table = "\n".join(["bar,time,open,high,low,close,rsi11"] + [
        f"{x['bar']},{x['time']},{fmt(x['open'])},{fmt(x['high'])},{fmt(x['low'])},{fmt(x['close'])},{x['rsi11']}" for x in bars])

    prices = [x["price"] for x in rows]
    bar_ids = [x["bar"] for x in rows]
    nested = readings(prices, bar_ids)
    simple = readings(prices, bar_ids, simple=True)
    confirmed = [x for x in rows if not x["provisional"]]
    nested_conf = readings([x["price"] for x in confirmed], [x["bar"] for x in confirmed])
    legal = [{"pattern": x.pattern, "direction": x.direction, "labels": list(x.labels), "next": x.next_label,
              "next_move": x.next_move, "ways": x.ways, "invalidation": list(x.invalidation)} for x in nested]
    return {
        **spec, "k": K[tf], "bars_in_window": b - a, "horizon": HORIZON[tf], "masked": masked, "factor": factor, "shift_days": shift,
        "pivots": rows, "bars": bars, "future": future, "last_close": bars[-1]["close"], "last_time": bars[-1]["time"],
        "last_rsi": bars[-1]["rsi11"], "pivot_table": pivot_table, "raw_table": raw_table,
        "ambiguity": {"nested": summary(nested), "simple": summary(simple), "nested_confirmed_only": summary(nested_conf)},
        "legal_readings": legal,
    }


def main() -> None:
    out = OUT / "windows"
    out.mkdir(parents=True, exist_ok=True)
    cache: dict = {}
    for spec in WINDOWS:
        w = build(spec, cache)
        (out / f"{w['id']}.json").write_text(json.dumps(w))
        a = w["ambiguity"]["nested"]
        print(f"{w['id']:4} {w['tf']} {w['kind']:8} bars {w['bars_in_window']:4} pivots {len(w['pivots']):3} first {w['bars'][0]['open']:>10} last {w['last_close']:>10} "
              f"factor {w['factor']:.3f} readings simple {w['ambiguity']['simple']['readings']:3} nested {a['readings']:4} ways {a['nested_ways']:>9} "
              f"invalidation levels {a['distinct_invalidation_levels']:3} raw chars {len(w['raw_table'])}")


if __name__ == "__main__":
    main()
