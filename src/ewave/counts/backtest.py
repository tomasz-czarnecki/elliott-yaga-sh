"""The board at past dates, on data cut at each date, projected and scored against what came next, the volatility null and
sign-flipped random paths. The same code as the forward log: an as-of time, the rows it would have written, and what happened after.

Dates: weekly since the premise's top, on its root, plus the replay dates of rounds 2 and 3 (before the top the premise does not
apply, and the root is searched). Each prediction counts once, on the first date it appeared, as in the forward log.

Control: BTC to the 2026-02-06 low, then every 15m bar's direction flipped at random, with the premise on: round 3's check B. It
keeps the volatility and removes direction. Only dates after the flip point are compared, and BTC is shown on those same dates.
1m bars are off on the paths, so BTC runs without them too for that comparison. A rough check: few paths, and it also removes
BTC's slow trend. Overlapping dates share one price path, so the intervals resample whole dates.
"""
from __future__ import annotations

import json
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from math import exp, log
from multiprocessing import get_context
from pathlib import Path

from ..ingest.config import project_root
from .config import Config
from .export import tree_payload
from .forward import dedupe, groups, reliability, resolved_rows, rows_from, summary
from .frames import Frame, Frames, HIGH_FIRST, LOW_FIRST, TF_MS, prepared, resample_12h, stamp, to_ms
from .inside import Cache, open_cache
from .nest import Builder
from .premise import BROKEN, DEAD, status

REPLAY_DATES = ("2023-01-01", "2023-07-01", "2024-01-01", "2024-07-01", "2025-01-01", "2025-07-01", "2025-12-01", "2026-01-01", "2026-03-01", "2026-05-01", "2026-07-01", "2026-09-22", "2026-10-15")
WEEKLY_FROM = "2025-10-13"
FLIP_FROM = "2026-02-09"   # the first Monday after the low the control keeps
FLIP_AT = "2026-02-06T12:00"


def weekly_dates(start: str, end_ms: int) -> list[str]:
    d = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    out = []
    while d.timestamp() * 1000 < end_ms:
        out.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=7)
    return out


def resample_bars(fine: Frame, tf: str) -> Frame:
    """Coarser bars from 15m ones, on the bar's own UTC grid."""
    size = TF_MS[tf]
    out = Frame(tf, [], [], [], [], [], [], [])
    i, n = 0, len(fine.ts)
    while i < n:
        bucket = fine.ts[i] - fine.ts[i] % size
        j, hi, lo = i, i, i
        while j < n and fine.ts[j] < bucket + size:
            if fine.high[j] > fine.high[hi]:
                hi = j
            if fine.low[j] < fine.low[lo]:
                lo = j
            j += 1
        out.ts.append(bucket)
        out.open.append(fine.open[i])
        out.high.append(fine.high[hi])
        out.low.append(fine.low[lo])
        out.close.append(fine.close[j - 1])
        out.order.append((HIGH_FIRST if hi < lo else LOW_FIRST) if hi != lo else fine.order[hi])
        out.volume.append(sum(fine.volume[i:j]))
        i = j
    return out


def flip_after(full: Frames, at_ms: int, seed: int) -> Frames:
    """Real bars up to at_ms, then each 15m bar's direction flipped with a coin: its gap, body and wicks mirrored in log. Bars up to
    at_ms stay exactly as printed, on every frame."""
    rng = random.Random(seed)
    f = full["15m"]
    n = len(f.ts)
    op, hi, lo, cl, order = list(f.open), list(f.high), list(f.low), list(f.close), list(f.order)
    prev_real = None
    prev_new = None
    for i in range(n):
        if f.ts[i] < at_ms:
            prev_real, prev_new = f.close[i], f.close[i]
            continue
        s = 1 if rng.random() < 0.5 else -1
        o, h, l, c = f.open[i], f.high[i], f.low[i], f.close[i]
        gap = log(o / prev_real) if prev_real else 0.0
        o2 = prev_new * exp(s * gap)
        if s > 0:
            h2, l2, c2 = o2 * h / o, o2 * l / o, o2 * c / o
            order[i] = f.order[i]
        else:
            h2, l2, c2 = o2 * o / l, o2 * o / h, o2 * o / c
            order[i] = {HIGH_FIRST: LOW_FIRST, LOW_FIRST: HIGH_FIRST}.get(f.order[i], f.order[i])
        op[i], hi[i], lo[i], cl[i] = o2, h2, l2, c2
        prev_real, prev_new = c, c2
    fine = Frame("15m", list(f.ts), op, hi, lo, cl, order, list(f.volume))
    by = {"15m": fine}
    for tf in ("1h", "4h", "1d"):
        by[tf] = resample_bars(fine, tf)
    by["12h"] = resample_12h(by["1h"])
    return prepared(Frames(f"flip{seed}", by, fine.ts[-1] + fine.tf_ms, None))


def rows_at(full: Frames, cfg: Config, when: str, premise, cache: Cache, root: str = "1d") -> list[dict]:
    """What the board would have written on that date, with nothing later in view."""
    cut = full.upto(to_ms(when))
    tree = Builder(cut, cfg, premise, cache).build(root)
    obj = tree_payload(tree, cfg, cut["1d"].atr[-1] if cut["1d"].atr else 0.0)
    return rows_from(obj, {"price": cut.price, "as_of_ms": cut.as_of_ms, "rules": cfg.version, "root": root})


def run_dates(full: Frames, cfg: Config, dates: list[str], premise, cache: Cache, on_date=None) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for when in dates:
        t = time.time()
        got = dedupe(rows_at(full, cfg, when, premise, cache), seen)
        out += got
        if on_date:
            on_date(when, len(got), time.time() - t)
    return out


def scored(rows: list[dict], fine: Frame, spec: dict) -> dict:
    done, still = resolved_rows(rows, fine)
    table = {}
    for (tf, kind), got in groups(done).items():
        table[f"{tf}/{kind}"] = summary(got, spec["shift_prior"], spec["bootstrap"])
    return {"rows": len(rows), "resolved": len(done), "open": still, "table": table, "reliability": {k: reliability(v) for k, v in {f"{tf}/{kind}": g for (tf, kind), g in groups(done).items() if tf in ("4h", "1h", "all")}.items()}}


def _crosstabs(rows: list[dict], fine: Frame, spec: dict) -> dict:
    """Do the board's own marks separate outcomes? Fit, clarity, the parent's box, R:R: each split in the leg rows of 4H and 1H. Thin: read none of it as a finding."""
    done, _ = resolved_rows([r for r in rows if r["kind"] == "leg" and r["tf"] in ("4h", "1h")], fine)
    out = {}
    if not done:
        return out
    def split(name, key):
        a = [r for r in done if key(r)]
        b = [r for r in done if not key(r)]
        out[name] = {"yes": summary(a, spec["shift_prior"], 0), "no": summary(b, spec["shift_prior"], 0)}
    med = sorted(r["fit"] for r in done)[len(done) // 2]
    split(f"fit >= {med:.2f}", lambda r: r["fit"] >= med)
    split("clarity >= 0.3", lambda r: (r["clarity"] or 0) >= 0.3)
    split("target inside or on the way to the parent's box", lambda r: r["nest_f"] >= 0.999)
    split("target on a magnet of 3 or more counts", lambda r: r["magnet"] >= 3)
    return out


_SHARED: dict = {}  # set before the pool forks: the frames are too large to send to each job


def _control_job(seed: int) -> dict:
    full, cfg, premise, dates, at_ms, spec = _SHARED["job"]
    os.nice(5)
    path = flip_after(full, at_ms, seed)
    t = time.time()
    rows = run_dates(path, cfg, dates, premise, Cache())
    done = scored(rows, path["15m"], spec)
    done["crosstabs"] = _crosstabs(rows, path["15m"], spec)
    done["seed"] = seed
    done["seconds"] = round(time.time() - t, 1)
    done["left_premise"] = premise is not None and status(premise, path, cfg)["state"] in (BROKEN, DEAD)
    return done


def _line(name: str, s: dict) -> str:
    if not s.get("n"):
        return f"{name}: n 0"
    ci = s.get("ci")
    band = "" if not ci else f" [{ci[0] * 100:+.1f}, {ci[1] * 100:+.1f}]"
    win = "" if "window_n" not in s else f" window {s['window_rate'] * 100:.0f}%/{s['window_null'] * 100:.0f}% n{s['window_n']}"
    return f"{name}: n {s['n']} dates {s['dates']} hit {s['rate'] * 100:.1f}% null {s['null'] * 100:.1f}% lift {s['lift'] * 100:+.1f}{band} Brier {s['brier_null']:.4f}/{s['brier_eng']:.4f} logloss {s['ll_null']:.4f}/{s['ll_eng']:.4f}{win}"


def run(full: Frames, cfg: Config, premise, args) -> str:
    spec = cfg.raw["forward"]
    out_dir = Path(args.out) if args.out else project_root() / ".cache" / "counts" / "backtest"
    out_dir.mkdir(parents=True, exist_ok=True)
    weekly = weekly_dates(WEEKLY_FROM, full.as_of_ms)
    dates = sorted(set(weekly) | set(REPLAY_DATES))
    lines = []

    def note(when, n, secs):
        print(f"{when}: +{n} rows, {secs:.1f} s", flush=True)

    if args.no_minutes:
        full = replace(full, minutes=None)
    t = time.time()
    cache = open_cache(cfg) if not args.no_minutes else Cache()
    try:
        rows = run_dates(full, cfg, dates, premise, cache, note)
    finally:
        cache.close()
    (out_dir / f"btc{'_nomin' if args.no_minutes else ''}.jsonl").write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows))
    fine = full["15m"]
    all_rows = scored(rows, fine, spec)
    post = [r for r in rows if r["as_of"][:10] in set(weekly)]
    since = scored(post, fine, spec)
    flip_dates = [d for d in weekly if d >= FLIP_FROM]
    same = [r for r in rows if r["as_of"][:10] in set(flip_dates)]
    btc_same = scored(same, fine, spec)
    result = {"as_of": stamp(full.as_of_ms), "rules": cfg.version, "dates": dates, "seconds": round(time.time() - t, 1), "all": all_rows, "since_top": since, "flip_dates": btc_same,
              "crosstabs": _crosstabs(rows, fine, spec), "crosstabs_since_top": _crosstabs(post, fine, spec)}
    for label, block in (("All dates", all_rows), ("Weekly since the top", since), ("Flip dates, BTC", btc_same)):
        lines.append(f"{label}: {block['rows']} predictions, {block['resolved']} resolved, {block['open']} open")
        for key in sorted(block["table"]):
            lines.append("  " + _line(key, block["table"][key]))
    if args.paths:
        _SHARED["job"] = (replace(full, minutes=None), cfg, premise, flip_dates, to_ms(FLIP_AT), spec)
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=get_context("fork")) as ex:
            paths = []
            for done in ex.map(_control_job, range(args.paths)):
                print(f"path {done['seed']}: {done['rows']} rows in {done['seconds']} s", flush=True)
                paths.append(done)
        result["paths"] = paths
        lines.append(f"Control: {args.paths} sign-flipped paths, dates {flip_dates[0]} to {flip_dates[-1]}; {sum(1 for p in paths if p['left_premise'])} left the premise")
        for key in sorted(btc_same["table"]):
            vals = [p["table"][key] for p in paths if key in p["table"] and p["table"][key].get("n")]
            if not vals:
                continue
            lifts = sorted(v["lift"] for v in vals)
            mean = sum(lifts) / len(lifts)
            mine = btc_same["table"][key]["lift"]
            lower = sum(1 for x in lifts if x < mine)
            lines.append(f"  {key}: BTC lift {mine * 100:+.1f}, paths mean {mean * 100:+.1f}, range {lifts[0] * 100:+.1f} to {lifts[-1] * 100:+.1f}, paths below BTC {lower} of {len(lifts)}")
    (out_dir / f"summary{'_nomin' if args.no_minutes else ''}.json").write_text(json.dumps(result, indent=1, default=str))
    return "\n".join(lines)
