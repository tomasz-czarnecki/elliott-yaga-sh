"""The forward log and its scoring. Each export appends what the board says now, one line per distinct prediction, with the null
odds at that moment. `ewave-counts score` resolves them on what happened after, causally: only bars opening at or after the
as-of time are read, and when one bar holds both levels the invalidation goes first.

A prediction is "price reaches the target before the invalidation, inside the horizon". The null is the volatility barrier
(odds.py): a random walk at that moment's volatility, knowing nothing of waves. The engine has no probability of its own to
offer, so its forecast is the null's log odds moved by how far hit rates of that group have beaten the null so far, on rows that
had already resolved at that as-of time. With no edge that shift stays near 0 and both score the same. A JSON line per
prediction: Parquet cannot be appended to (CLAUDE.md).
"""
from __future__ import annotations

import hashlib
import json
import random
from bisect import bisect_left
from dataclasses import dataclass
from math import ceil, log, sqrt
from pathlib import Path

from ..ingest.config import data_root
from .confluence import cluster_of
from .frames import Frame, TF_MS, stamp
from .odds import barrier_prob

TARGET, STOP, NEITHER, OPEN = "target", "invalidation", "neither", "open"


def log_path() -> Path:
    return data_root() / "counts" / "forward.jsonl"


def row_hash(row: dict) -> str:
    """What the prediction says, not when: the same target from the same reading is one prediction, however long it stands."""
    keys = ("rules", "tf", "reading", "wave", "kind", "d", "target", "stop", "win_lo", "win_hi")
    return hashlib.sha256(json.dumps([row[k] for k in keys], separators=(",", ":")).encode()).hexdigest()[:16]


def _reading(n: dict) -> str:
    return "|".join([n["tf"], n["pattern"], n["dir"] or "", *(str(x["t"]) for x in n["labels"])])


def null_odds(price: float, target: float, stop: float, sigma: float, h_bars: int) -> tuple[float, float]:
    """P(target before stop within h_bars), and with no limit."""
    x = abs(log(price / stop))
    a = x + abs(log(target / price))
    return barrier_prob(x, a, sigma * sigma * h_bars), x / a


def _row(n: dict, obj_meta: dict, kind: str, d: str, target: float, pull: str, stop: dict, h_bars: int, wave: dict, role: str, clusters: dict | None = None) -> dict | None:
    price, now = obj_meta["price"], obj_meta["as_of_ms"]
    sign = 1 if d == "up" else -1
    if sign * (target - price) <= 0 or sign * (stop["p"] - price) >= 0 or h_bars < 1:
        return None
    sigma = n["sigma"]
    p_h, p_geo = null_odds(price, target, stop["p"], sigma, h_bars)
    win = n["window"] if role == "running" else None
    win_lo = None if not win else win["lo"] * 1000
    win_hi = None if not win else win["hi"] * 1000
    p_win = None
    if win_lo is not None and win_hi is not None and win_hi > now:
        bars_tf = TF_MS[n["tf"]]
        by_hi = null_odds(price, target, stop["p"], sigma, max(1, ceil((win_hi - now) / bars_tf)))[0]
        by_lo = null_odds(price, target, stop["p"], sigma, max(0, ceil((win_lo - now) / bars_tf)))[0] if win_lo > now else 0.0
        p_win = max(0.0, by_hi - by_lo)
    legs = n["projection"]["legs"]
    nest = next((t["nest_f"] for leg in legs for t in leg["targets"] if abs(t["p"] - target) < 0.01), 1.0)
    row = {"as_of_ms": now, "as_of": stamp(now), "rules": obj_meta["rules"], "root": obj_meta["root"], "node": n["id"], "tf": n["tf"], "reading": _reading(n), "title": n["short"],
           "pattern": n["pattern"], "wave": wave["label"], "kind": kind, "d": d, "price": price, "target": round(target, 2), "pull": pull, "stop": round(stop["p"], 2), "stop_rule": stop["rule"],
           "win_lo": win_lo, "win_hi": win_hi, "h_bars": h_bars, "sigma": round(sigma, 6), "p_null": round(p_h, 5), "p_geo": round(p_geo, 5), "p_win": None if p_win is None else round(p_win, 5),
           "rr": round(abs(target - price) / abs(price - stop["p"]), 3), "fit": n["fit"]["score"], "clarity": n["clarity_min"], "nest_f": nest, "magnet": _magnet(target, clusters)}
    row["hash"] = row_hash(row)
    return row


def _magnet(target: float, clusters: dict | None) -> int:
    """How many counts share this level's cluster: 1 is the count alone."""
    got = None if not clusters else cluster_of(target, clusters["rows"], clusters["tol"])
    return 0 if got is None else got["readings"]


def rows_from(tree: dict, meta: dict) -> list[dict]:
    """What the board predicts now. `leg`: the running wave to its nearest level ahead. `likely`: to the path's point, when that
    is another level. `next`: the wave after it, secondary. Each row has the invalidation it was given."""
    out = []
    clusters = tree.get("clusters")
    for lv in tree["levels"]:
        for n in lv["nodes"]:
            wave = n["wave"]
            for o in n["odds"]:
                kind = {"leg": "leg", "parent": "leg", "next": "next"}[o["name"]]
                stop = {"p": o["stop"], "rule": o["stop_rule"]}
                row = _row(n, meta, kind, o["dir"], o["target"], o["pull"], stop, o["h_bars"], wave, "running" if kind == "leg" else "next", clusters)
                if row:
                    out.append(row)
            leg = next((o for o in n["odds"] if o["name"] in ("leg", "parent")), None)
            legs = n["projection"]["legs"]
            if leg and legs and legs[0]["role"] == "running" and not legs[0]["reached"] and not legs[0]["open_end"] and abs(legs[0]["p"] - leg["target"]) > 0.01:
                row = _row(n, meta, "likely", leg["dir"], legs[0]["p"], legs[0]["src"], {"p": leg["stop"], "rule": leg["stop_rule"]}, leg["h_bars"], wave, "running", clusters)
                if row:
                    out.append(row)
    return out


def rows_of(obj: dict, spec: dict) -> list[dict]:
    """What an export's payload predicts."""
    out = []
    for root in spec["roots"]:
        tree = obj["trees"].get(root)
        if tree is not None:
            out += rows_from(tree, {"price": obj["price"], "as_of_ms": obj["as_of"] * 1000, "rules": obj["rules_version"], "root": root})
    return out


def dedupe(rows: list[dict], seen: set[str]) -> list[dict]:
    out = []
    for r in rows:
        if r["hash"] not in seen:
            seen.add(r["hash"])
            out.append(r)
    return out


def read_log(path: Path | str | None = None) -> list[dict]:
    p = Path(path) if path else log_path()
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:  # a line cut short by a killed run: the rows before and after it still count
            continue
    return out


def append_log(rows: list[dict], path: Path | str | None = None) -> int:
    """Only what is new. Returns how many lines were written."""
    p = Path(path) if path else log_path()
    seen = {r["hash"] for r in read_log(p)}
    new = dedupe(rows, seen)
    if new:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a") as fh:
            for r in new:
                fh.write(json.dumps(r, separators=(",", ":")) + "\n")
    return len(new)


@dataclass(frozen=True)
class Outcome:
    outcome: str
    ts: int | None
    in_window: bool | None


def resolve(row: dict, fine: Frame) -> Outcome:
    """Target or invalidation first, read on 15m bars from the as-of time on. The invalidation goes first inside one bar, since a
    bar cannot say which came first. `open` until the horizon has passed."""
    d = 1 if row["d"] == "up" else -1
    target, stop = row["target"], row["stop"]
    as_of = row["as_of_ms"]
    end_ms = as_of + row["h_bars"] * TF_MS[row["tf"]]
    i = bisect_left(fine.ts, as_of)
    while i < len(fine.ts) and fine.ts[i] < end_ms:
        hi, lo = fine.high[i], fine.low[i]
        if (lo <= stop) if d > 0 else (hi >= stop):
            return Outcome(STOP, fine.ts[i], None)
        if (hi >= target) if d > 0 else (lo <= target):
            lo_w, hi_w = row.get("win_lo"), row.get("win_hi")
            inside = None if lo_w is None or hi_w is None else lo_w <= fine.ts[i] <= hi_w
            return Outcome(TARGET, fine.ts[i], inside)
        i += 1
    last = fine.ts[-1] + fine.tf_ms if fine.ts else 0
    return Outcome(NEITHER if end_ms <= last else OPEN, None, None)


def _clip(p: float) -> float:
    return min(max(p, 0.01), 0.99)


def _logit(p: float) -> float:
    return log(p / (1 - p))


def _expit(x: float) -> float:
    from math import exp
    return 1 / (1 + exp(-x))


def brier(ps: list[float], ys: list[int]) -> float:
    return sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(ys) if ys else float("nan")


def log_loss(ps: list[float], ys: list[int]) -> float:
    if not ys:
        return float("nan")
    return -sum(y * log(_clip(p)) + (1 - y) * log(1 - _clip(p)) for p, y in zip(ps, ys)) / len(ys)


def walk_forward(rows: list[dict], prior: float) -> list[float]:
    """The engine's forecast for each row: the null's log odds, moved by the excess of hits over the null on rows of its group that
    had resolved before this row was made. One Newton step of a logistic shift, shrunk by `prior`. Rows carry `y` and `resolved_ms`."""
    order = sorted(rows, key=lambda r: r["as_of_ms"])
    done = sorted((r for r in rows if r.get("resolved_ms") is not None), key=lambda r: r["resolved_ms"])
    excess = info = 0.0
    j = 0
    out: dict[int, float] = {}
    for r in order:
        while j < len(done) and done[j]["resolved_ms"] <= r["as_of_ms"]:
            q = _clip(done[j]["p_null"])
            excess += done[j]["y"] - q
            info += q * (1 - q)
            j += 1
        shift = excess / (info + prior)
        out[id(r)] = _expit(_logit(_clip(r["p_null"])) + shift)
    return [out[id(r)] for r in rows]


def _bootstrap(rows: list[dict], n: int, seed: int = 11) -> tuple[float, float] | None:
    """An interval for hit rate minus null, resampling whole as-of dates: rows of one date share one path."""
    by: dict[int, list[dict]] = {}
    for r in rows:
        by.setdefault(r["as_of_ms"], []).append(r)
    keys = list(by)
    if len(keys) < 3:
        return None
    rng = random.Random(seed)
    got = []
    for _ in range(n):
        ys = ps = c = 0.0
        for _k in range(len(keys)):
            for r in by[keys[rng.randrange(len(keys))]]:
                ys += r["y"]
                ps += r["p_null"]
                c += 1
        got.append((ys - ps) / c if c else 0.0)
    got.sort()
    return got[int(0.025 * n)], got[int(0.975 * n)]


def summary(rows: list[dict], prior: float, boot: int) -> dict:
    """One group of resolved rows against the null."""
    if not rows:
        return {"n": 0}
    ys = [r["y"] for r in rows]
    null = [r["p_null"] for r in rows]
    eng = walk_forward(rows, prior)
    rate, mean = sum(ys) / len(ys), sum(null) / len(null)
    base = {"n": len(rows), "dates": len({r["as_of_ms"] for r in rows}), "hits": sum(ys), "stops": sum(1 for r in rows if r["outcome"] == STOP), "neither": sum(1 for r in rows if r["outcome"] == NEITHER),
            "rate": rate, "null": mean, "lift": rate - mean, "brier_null": brier(null, ys), "brier_eng": brier(eng, ys), "ll_null": log_loss(null, ys), "ll_eng": log_loss(eng, ys),
            "se": sqrt(max(sum(p * (1 - p) for p in null), 1e-9)) / len(rows)}
    if boot:
        ci = _bootstrap(rows, boot)
        base["ci"] = ci
    win = [r for r in rows if r.get("p_win") is not None]
    if win:
        base["window_n"] = len(win)
        base["window_rate"] = sum(1 for r in win if r["in_window"]) / len(win)
        base["window_null"] = sum(r["p_win"] for r in win) / len(win)
    return base


def reliability(rows: list[dict], edges=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0)) -> list[dict]:
    out = []
    for lo, hi in zip(edges, edges[1:]):
        got = [r for r in rows if lo <= r["p_null"] < hi or (hi == 1.0 and r["p_null"] == 1.0)]
        if got:
            out.append({"lo": lo, "hi": hi, "n": len(got), "null": sum(r["p_null"] for r in got) / len(got), "rate": sum(r["y"] for r in got) / len(got)})
    return out


def resolved_rows(rows: list[dict], fine: Frame) -> tuple[list[dict], int]:
    """Each row with what came of it, and how many are still open. An open row is left out, not counted as a miss."""
    out, still = [], 0
    for r in rows:
        o = resolve(r, fine)
        if o.outcome == OPEN:
            still += 1
            continue
        end = o.ts if o.ts is not None else r["as_of_ms"] + r["h_bars"] * TF_MS[r["tf"]]
        out.append({**r, "outcome": o.outcome, "y": int(o.outcome == TARGET), "in_window": o.in_window, "resolved_ms": end})
    return out, still


def groups(rows: list[dict]) -> dict[tuple[str, str], list[dict]]:
    by: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        by.setdefault((r["tf"], r["kind"]), []).append(r)
        by.setdefault(("all", r["kind"]), []).append(r)
    return by


def render(rows: list[dict], fine: Frame, spec: dict) -> str:
    done, still = resolved_rows(rows, fine)
    lines = [f"Forward log: {len(rows)} predictions, {len(done)} resolved, {still} still open. Open rows are left out, so short horizons resolve first."]
    if not done:
        lines.append("Nothing has resolved yet. No hit rate can be stated.")
        return "\n".join(lines)
    lines.append("frame kind   n dates hit% null% lift   95% (dates)    Brier null/engine  logloss null/engine  in window / null")
    order = ["1d", "4h", "1h", "15m", "all"]
    for (tf, kind), got in sorted(groups(done).items(), key=lambda kv: (order.index(kv[0][0]) if kv[0][0] in order else 9, kv[0][1])):
        s = summary(got, spec["shift_prior"], spec["bootstrap"])
        ci = s.get("ci")
        band = "" if not ci else f"{ci[0] * 100:+5.1f} to {ci[1] * 100:+5.1f}"
        win = "" if "window_n" not in s else f"{s['window_rate'] * 100:.0f}% / {s['window_null'] * 100:.0f}% (n {s['window_n']})"
        lines.append(f"{tf:>5} {kind:<6} {s['n']:>3} {s['dates']:>4} {s['rate'] * 100:>4.0f} {s['null'] * 100:>4.0f} {s['lift'] * 100:>+5.1f}  {band:<14} {s['brier_null']:.4f}/{s['brier_eng']:.4f}  {s['ll_null']:.4f}/{s['ll_eng']:.4f}  {win}")
    lines.append("Forecasts: the null is the volatility barrier; the engine is that null moved walk-forward by what its group has hit so far. Lift under 0, or an interval across 0, is no edge.")
    return "\n".join(lines)
