"""Scores the Opus answers: JSON validity, rule breaks, agreement, rulebook math, confidence on noise, outcomes, cost.

    uv run --with numpy python research/model-options/spikes/bakeoff/llm_eval.py

Reads $BAKE_OUT/windows and $BAKE_OUT/llm. Writes llm_counts.csv, llm_eval.json and llm_tables.md to $BAKE_OUT.
"""
from __future__ import annotations

import csv
import datetime as dt
import itertools
import json
import math
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from enumerator import FAMILY, WAVE_KINDS, Grammar, readings, summary
from ml_features import barrier_prob
from rules import LD, ORDER, PATTERNS, Point, hard, rule_levels, violations

OUT = Path(os.environ.get("BAKE_OUT", "/opt/data/cache/scratch/elliott_research_r1/bake"))
LLM = OUT / "llm"
BTC = ["D1", "D2", "D3", "H1", "H2", "H3", "L1"]
NULLS = ["N1", "N2", "N3"]
FAMOUS_SOURCE = {"N1": "D1", "N2": "H2", "N3": "D3"}
NOISE_WORDS = re.compile(r"synthetic|random|shuffl|artificial|fabricat|fake|simulat|generated|scrambl|not real", re.I)
VOL_BARS = {"1d": 30, "4h": 84}


def strict_parse(text: str):
    try:
        return json.loads(text), "strict"
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0)), "recovered"
        except json.JSONDecodeError:
            pass
    return None, "invalid"


def to_points(seg: dict, w: dict, condition: str) -> tuple[dict[str, Point], list[str]]:
    """Labels to prices. Returns the points and any problems: a pivot that does not exist, a price no bar printed."""
    pts: dict[str, Point] = {}
    issues: list[str] = []
    rows = {r["pivot"]: r for r in w["pivots"]}
    for lab in seg.get("labels", []):
        name = str(lab.get("label"))
        if condition == "pivot":
            r = rows.get(lab.get("pivot"))
            if r is None:
                issues.append("pivot_not_in_table")
                continue
            pts[name] = Point(r["bar"], r["price"])
        elif condition == "raw":
            b = lab.get("bar")
            if not isinstance(b, int) or not 0 <= b < len(w["bars"]):
                issues.append("bar_not_in_table")
                continue
            price = float(lab.get("price", 0))
            bar = w["bars"][b]
            off = min(abs(price - bar["high"]), abs(price - bar["low"])) / max(bar["high"], 1e-9)
            if off > 0.01:
                issues.append("price_off_1pct")
            elif off > 0.001:
                issues.append("price_off_0.1pct")
            pts[name] = Point(b, price)
        else:
            b = bar_from_time(str(lab.get("time")), w)
            price = float(lab.get("price", 0))
            if b is None:
                issues.append("time_not_on_chart")
                continue
            near = w["bars"][max(0, b - 3):b + 4]
            off = min(min(abs(price - x["high"]), abs(price - x["low"])) for x in near) / max(price, 1e-9)
            if off > 0.05:
                issues.append("price_off_5pct")
            elif off > 0.01:
                issues.append("price_off_1pct")
            pts[name] = Point(b, price)
    return pts, issues


def _parse_time(text: str) -> dt.datetime | None:
    m = re.search(r"(\d{2,4})-(\d{1,2})-(\d{1,2})(?:[T ](\d{1,2}))?", text)
    if not m:
        return None
    y = int(m.group(1))
    y = y + 2000 if y < 100 else y
    try:
        return dt.datetime(y, int(m.group(2)), int(m.group(3)), int(m.group(4) or 0))
    except ValueError:
        return None


def bar_from_time(text: str, w: dict) -> int | None:
    t = _parse_time(text)
    if t is None:
        return None
    best, gap = None, None
    for x in w["bars"]:
        g = abs((_parse_time(x["time"]) - t).total_seconds())
        if gap is None or g < gap:
            best, gap = x["bar"], g
    return best


def is_open(seg: dict, pts: dict[str, Point], count: dict, w: dict, last_seg: bool, condition: str) -> bool:
    """Is the structure's last label the running extreme of the wave now unfolding?"""
    if not last_seg or not pts:
        return False
    seq = [lab for lab in ORDER.get(seg.get("pattern"), []) if lab in pts]
    if not seq:
        return False
    last = seq[-1]
    if str(count.get("current_wave")) == last:
        return True
    prov = next((r for r in w["pivots"] if r["provisional"]), None)
    if prov is None:
        return False
    if condition == "pivot":
        return pts[last].bar == prov["bar"]
    return abs(pts[last].bar - prov["bar"]) <= 2


def levels_for(seg: dict, pts: dict[str, Point], open_last: bool) -> tuple[list, list]:
    pat, d = seg.get("pattern"), seg.get("direction")
    seq = [lab for lab in ORDER.get(pat, []) if lab in pts]
    done = rule_levels(pat, d, pts)
    inv, tgt = list(done["invalidation"]), list(done["targets"])
    if open_last and len(seq) >= 2:
        running = rule_levels(pat, d, {k: pts[k] for k in seq[:-1]})
        inv += running["invalidation"]
        tgt += running["targets"]
    return inv, tgt


def nested_breaks(seg: dict, w: dict, open_last: bool, hidden_sub: bool) -> list[str]:
    """Pivot table only: does each wave spanning several legs parse, one degree down, as what the count says it is?
    Section 0 calls labelling a 1-5 without checking that 1, 3, 5 each hold five waves the first beginner error."""
    pat = seg.get("pattern")
    kinds = WAVE_KINDS.get(pat)
    if not kinds:
        return []
    labs = [lab for lab in seg.get("labels", []) if isinstance(lab.get("pivot"), int)]
    order = {name: k for k, name in enumerate(ORDER[pat])}
    labs = sorted((x for x in labs if str(x["label"]) in order), key=lambda x: order[str(x["label"])])
    prices, bars = [r["price"] for r in w["pivots"]], [r["bar"] for r in w["pivots"]]
    g = Grammar(prices, bars, hidden_sub=hidden_sub)
    out = []
    for k, (a, b) in enumerate(zip(labs, labs[1:])):
        if open_last and k == len(labs) - 2:
            continue  # the wave still running
        i, j = a["pivot"], b["pivot"]
        if not (0 <= i < j < len(prices)) or (j - i) % 2 == 0:
            continue
        kind = kinds[k] if k < len(kinds) else "c"
        ok = g.motive(i, j) if kind == "m" else g.corrective(i, j)
        if pat == LD and kind == "m" and not ok:  # a leading diagonal may also be 3-3-3-3-3
            ok = g.corrective(i, j)
        if not ok:
            out.append(f"{str(b['label'])}_{'not_a_5' if kind == 'm' else 'not_a_3'}")
    return out


def random_break_rate(seg: dict, w: dict, draws: int = 300, seed: int = 3) -> float | None:
    """How often a random labelling of the same pattern and length, on the same pivot table, breaks a hard rule: what
    a count of zero breaks should be compared with."""
    pat = seg.get("pattern")
    n_labels = len(seg.get("labels", []))
    if pat not in PATTERNS or n_labels < 3:
        return None
    labs = ORDER[pat][:n_labels]
    rows = w["pivots"]
    rng = np.random.default_rng(seed)
    breaks, tries = 0, 0
    for _ in range(draws):
        start = int(rng.integers(0, max(1, len(rows) - n_labels + 1)))
        idx = [start]
        for _k in range(n_labels - 1):
            idx.append(idx[-1] + 2 * int(rng.integers(0, 3)) + 1)
        if idx[-1] >= len(rows):
            continue
        pts = {lab: Point(rows[i]["bar"], rows[i]["price"]) for lab, i in zip(labs, idx)}
        d = "up" if pts[labs[1]].price > pts[labs[0]].price else "down"
        tries += 1
        breaks += bool(hard(violations(pat, d, pts)))
    return breaks / tries if tries else None


def chance_near(levels: list[float], tol: float, draws: int = 400) -> float:
    """How often a random price between the lowest and highest candidate lands within tol of a candidate: the score a
    level picked at random would get on the same list."""
    rng = np.random.default_rng(1)
    lv = np.array([x for x in levels if x > 0])
    if len(lv) < 2:
        return float("nan")
    pts = np.exp(rng.uniform(np.log(lv.min()), np.log(lv.max()), draws))
    return float(np.mean(np.min(np.abs(pts[:, None] - lv[None, :]) / lv[None, :], axis=1) <= tol))


def judge_count(count: dict, w: dict, condition: str) -> dict:
    segs = count.get("segments") or []
    hard_breaks, soft_flags, issues = [], [], []
    nested_strict, nested_loose, random_rates = [], [], []
    skeleton: list[tuple[str, int]] = []
    last_info = None
    for k, seg in enumerate(segs):
        pat = seg.get("pattern")
        pts, bad = to_points(seg, w, condition)
        issues += bad
        last_seg = k == len(segs) - 1
        op = is_open(seg, pts, count, w, last_seg, condition)
        if pat not in PATTERNS:
            hard_breaks.append("S3_unknown_pattern")
            continue
        vs = violations(pat, seg.get("direction"), pts, open_last=op)
        hard_breaks += [v.rule for v in hard(vs)]
        if condition == "pivot":
            nested_strict += nested_breaks(seg, w, op, False)
            nested_loose += nested_breaks(seg, w, op, True)
            rb = random_break_rate(seg, w)
            if rb is not None:
                random_rates.append(rb)
        soft_flags += [v.rule for v in vs if v.severity != "R"]
        skeleton += [(lab, p.bar) for lab, p in pts.items()]
        if last_seg:
            last_info = (seg, pts, op)
    out = {"n_segments": len(segs), "hard": hard_breaks, "soft": soft_flags, "issues": issues, "skeleton": skeleton, "nested_strict": nested_strict, "nested_loose": nested_loose, "random_break": float(np.mean(random_rates)) if random_rates else None,
           "n_labels": sum(len(sg.get("labels", [])) for sg in segs)}
    inv_price = (count.get("invalidation") or {}).get("price")
    tz = count.get("target_zone") or {}
    lo, hi = tz.get("low"), tz.get("high")
    out.update(inv=inv_price, side=(count.get("invalidation") or {}).get("side"), t_lo=lo, t_hi=hi, next_move=count.get("next_move"),
               current_wave=str(count.get("current_wave")), p_target=count.get("p_target_before_invalidation"), confidence=count.get("confidence"))
    out["inv_is_rule"], out["target_is_rule"], out["inv_rule_name"], out["target_rule_name"] = None, None, None, None
    if last_info:
        seg, pts, op = last_info
        # the wave reached, from the last printed label: current_wave is free text and the same state gets worded differently
        seq = [lab for lab in ORDER.get(seg.get("pattern"), []) if lab in pts]
        out["state"] = f"{FAMILY.get(seg.get('pattern'), seg.get('pattern'))}:{seg.get('direction')}:{seq[-1] if seq else '?'}"
        out["last_pattern"] = seg.get("pattern")
        inv, tgt = levels_for(seg, pts, op)
        # earlier segments can legitimately supply the levels too, e.g. W4's invalidation while a flat runs inside it
        for s2 in segs[:-1]:
            p2, _ = to_points(s2, w, condition)
            if p2 and s2.get("pattern") in PATTERNS:
                i2, t2 = levels_for(s2, p2, True)
                inv += i2
                tgt += t2
        if isinstance(inv_price, (int, float)) and inv:
            d = [(abs(inv_price - x) / max(abs(x), 1e-9), name) for x, name in inv]
            best = min(d, key=lambda t: t[0])
            out["inv_is_rule"], out["inv_rule_name"] = bool(best[0] <= 0.005), best[1]
            out["inv_chance"] = chance_near([x for x, _ in inv], 0.005)
        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and tgt:
            a, b = min(lo, hi), max(lo, hi)
            inside = [name for x, name in tgt if a * 0.995 <= x <= b * 1.005]
            out["target_is_rule"] = bool(inside)
            out["target_rule_name"] = inside[0] if inside else None
            levels = [x for x, _ in tgt]
            near = lambda v: min(abs(v - x) / max(abs(x), 1e-9) for x in levels)
            out["target_edge_is_rule"] = bool(near(a) <= 0.003 or near(b) <= 0.003)
            out["target_both_edges_rule"] = bool(near(a) <= 0.003 and near(b) <= 0.003)
            out["edge_chance"] = chance_near(levels, 0.003)
    return out


def first_move(w: dict) -> str | None:
    """Which way price first moved by the window's own zigzag threshold after the last bar."""
    bars = w["bars"][-15:]
    trs = [max(math.log(b["high"] / b["low"]), abs(math.log(b["high"] / a["close"])), abs(math.log(b["low"] / a["close"]))) for a, b in zip(bars, bars[1:])]
    thr = w["k"] * float(np.mean(trs))
    close = w["last_close"]
    for bar in w["future"][:w["horizon"]]:
        up, down = math.log(bar["high"] / close) >= thr, math.log(close / bar["low"]) >= thr
        if up and down:
            return "up" if bar["order"] == 1 else "down" if bar["order"] == -1 else None
        if up:
            return "up"
        if down:
            return "down"
    return None


def resolve(count: dict, w: dict) -> dict:
    """Did price reach the zone before the invalidation, in the window's own future? Same tie rule as the ML test."""
    out = {"outcome": None, "baseline_p": None, "dir_hit": None}
    fut = w["future"]
    if not fut:
        return out
    moved = first_move(w)
    if moved and count.get("next_move") in ("up", "down"):
        out["dir_hit"] = count["next_move"] == moved
    close = w["last_close"]
    tz, inv = count.get("target_zone") or {}, count.get("invalidation") or {}
    if not all(isinstance(x, (int, float)) for x in (tz.get("low"), tz.get("high"), inv.get("price"))):
        return out
    lo, hi, ip = min(tz["low"], tz["high"]), max(tz["low"], tz["high"]), float(inv["price"])
    if lo <= close <= hi:
        out["outcome"] = "already_in_zone"
        return out
    up = lo > close
    target = lo if up else hi
    if (up and ip >= close) or (not up and ip <= close):
        out["outcome"] = "levels_on_wrong_side"
        return out
    res = None
    for bar in fut[:w["horizon"]]:
        fav, adv = (bar["high"], bar["low"]) if up else (bar["low"], bar["high"])
        hit_t = fav >= target if up else fav <= target
        hit_i = adv <= ip if up else adv >= ip
        if hit_t and hit_i:
            first = (bar["order"] == 1) if up else (bar["order"] == -1)
            res = "target" if first else "invalidation"
            break
        if hit_t:
            res = "target"
            break
        if hit_i:
            res = "invalidation"
            break
    if res is None:
        res = "timeout" if len(fut) >= w["horizon"] else "unresolved"
    out["outcome"] = res
    closes = [b["close"] for b in w["bars"]]
    r = np.diff(np.log(closes))[-VOL_BARS[w["tf"]]:]
    sigma = float(np.sqrt(np.mean(r * r)))
    x = abs(math.log(close / ip))
    a = abs(math.log(target / ip))
    out["baseline_p"] = float(barrier_prob(np.array([x]), np.array([a]), np.array([sigma ** 2 * w["horizon"]]))[0])
    return out


def jaccard(a: list, b: list, tol: int) -> float:
    if not a and not b:
        return 1.0
    used, hit = set(), 0
    for lab, bar in a:
        for k, (lab2, bar2) in enumerate(b):
            if k not in used and lab == lab2 and abs(bar - bar2) <= tol:
                used.add(k)
                hit += 1
                break
    return hit / (len(a) + len(b) - hit)


def overlap(a, b) -> bool:
    return a[0] is not None and b[0] is not None and min(a[0], a[1]) <= max(b[0], b[1]) and min(b[0], b[1]) <= max(a[0], a[1])


def pairs_agree(xs: list[dict], ys: list[dict] | None, tol: int) -> dict:
    prs = list(itertools.combinations(xs, 2)) if ys is None else list(itertools.product(xs, ys))
    if not prs:
        return {"n": 0}
    f = lambda fn: float(np.mean([fn(a, b) for a, b in prs]))
    return {"n": len(prs),
            "same_state": f(lambda a, b: a.get("state") == b.get("state")),
            "same_next": f(lambda a, b: a.get("next_move") == b.get("next_move")),
            "skeleton_jaccard": f(lambda a, b: jaccard(a["skeleton"], b["skeleton"], tol)),
            "inv_within_1pct": f(lambda a, b: a.get("inv") is not None and b.get("inv") is not None and abs(a["inv"] - b["inv"]) / abs(b["inv"]) <= .01),
            "targets_overlap": f(lambda a, b: overlap((a.get("t_lo"), a.get("t_hi")), (b.get("t_lo"), b.get("t_hi"))))}


def day_real(w: dict) -> str:
    t = dt.datetime.fromisoformat(w["last_time"]) - dt.timedelta(days=w["shift_days"])
    return t.strftime("%Y-%m-%d %H:%M")


def main() -> None:
    windows = {p.stem: json.loads(p.read_text()) for p in (OUT / "windows").glob("*.json")}
    ledger = [json.loads(x) for x in (LLM / "ledger.jsonl").read_text().splitlines()]
    rows, by_cell = [], defaultdict(list)
    calls = {}
    for rec in ledger:
        job = rec["id"]
        if job == "smoke" or rec.get("placeholder"):
            continue
        calls[job] = rec
        wid, condition = rec["window"], rec["condition"]
        w = windows[wid]
        raw = json.loads((LLM / f"{job}.out.json").read_text())
        parsed, how = strict_parse(raw.get("result", ""))
        base = {"id": job, "window": wid, "kind": w["kind"], "condition": condition, "run": rec["run"], "json": how}
        if parsed is None:
            rows.append({**base, "schema_ok": False})
            continue
        pri, alt = parsed.get("primary"), parsed.get("alternate")
        other = parsed.get("other_unclear_share")
        rec_text = str(parsed.get("recognised_period"))
        note = str(parsed.get("data_note"))
        pc = (pri or {}).get("confidence") or 0
        ac = (alt or {}).get("confidence") or 0
        base.update(schema_ok=isinstance(other, (int, float)) and (pri is None or "segments" in pri), other=other, sum_ok=abs(pc + ac + (other or 0) - 1) <= .011,
                    recognised=rec_text, recognised_yes=not rec_text.strip().lower().startswith("none"), data_note=note, noise_word=bool(NOISE_WORDS.search(note + " " + rec_text + " " + str(parsed.get("reasoning")))),
                    reasoning=parsed.get("reasoning"))
        for role, c in (("primary", pri), ("alternate", alt)):
            row = {**base, "role": role, "null_count": c is None}
            if c is not None:
                row.update(judge_count(c, w, condition))
                row.update(resolve(c, w))
                by_cell[(wid, condition, role)].append(row)
            rows.append(row)

    # enumerator: how many legal readings each window has, and whether Opus used them
    enum = {}
    for wid, w in windows.items():
        pr, br = [x["price"] for x in w["pivots"]], [x["bar"] for x in w["pivots"]]
        conf = [x for x in w["pivots"] if not x["provisional"]]
        pc, bc = [x["price"] for x in conf], [x["bar"] for x in conf]
        strict = readings(pr, br, open_last=True) + readings(pc, bc)
        loose = readings(pr, br, open_last=True, hidden_sub=True) + readings(pc, bc, hidden_sub=True)
        simple = readings(pr, br, simple=True, open_last=True) + readings(pc, bc, simple=True)
        keyset = lambda rs: {(r.pattern, tuple((lab, br[i]) for lab, i in r.labels)) for r in rs}
        enum[wid] = {"pivots": len(w["pivots"]), "bars": w["bars_in_window"], "simple": summary(simple), "nested": summary(strict), "loose": summary(loose),
                     "keys": keyset(strict), "keys_loose": keyset(loose), "keys_simple": keyset(simple)}

    def in_enum(row: dict, which: str) -> bool | None:
        if row.get("skeleton") is None or not row.get("last_pattern"):
            return None
        # compare the last segment only: earlier segments are context
        job = row["id"]
        parsed, _ = strict_parse(json.loads((LLM / f"{job}.out.json").read_text()).get("result", ""))
        c = parsed[row["role"]]
        seg = c["segments"][-1]
        pts, _ = to_points(seg, windows[row["window"]], row["condition"])
        seq = [lab for lab in ORDER.get(seg.get("pattern"), []) if lab in pts]
        key = (seg.get("pattern"), tuple((lab, pts[lab].bar) for lab in seq))
        return key in enum[row["window"]][which]

    for row in rows:
        if row.get("condition") == "pivot" and row.get("skeleton") is not None:
            row["in_enumerator"] = in_enum(row, "keys")
            row["in_enumerator_loose"] = in_enum(row, "keys_loose")
            if row["in_enumerator_loose"] is False:
                piv = windows[row["window"]]["pivots"]
                last_bar = max(b for _, b in row["skeleton"]) if row["skeleton"] else None
                ends_early = last_bar is not None and last_bar < piv[-2]["bar"]
                row["why_not_listed"] = "ends before the last pivots" if ends_early else ("hard break" if row["hard"] else ("legs do not parse" if row["nested_loose"] else "other"))

    # outputs
    keys = ["id", "window", "kind", "condition", "run", "role", "json", "null_count", "state", "next_move", "confidence", "other", "p_target", "inv", "t_lo", "t_hi", "inv_is_rule", "inv_rule_name",
            "target_is_rule", "target_rule_name", "hard", "soft", "issues", "nested_strict", "nested_loose", "in_enumerator", "in_enumerator_loose", "outcome", "baseline_p", "recognised_yes", "recognised", "noise_word", "data_note", "reasoning"]
    with (OUT / "llm_counts.csv").open("w", newline="") as f:
        wr = csv.DictWriter(f, keys, extrasaction="ignore")
        wr.writeheader()
        for r in rows:
            wr.writerow(r)

    md: list[str] = []
    def table(title: str, head: list[str], body: list[list]) -> None:
        md.append(f"\n### {title}\n")
        md.append("| " + " | ".join(head) + " |")
        md.append("|" + "---|" * len(head))
        for b in body:
            md.append("| " + " | ".join("" if x is None else (f"{x:.2f}" if isinstance(x, float) else str(x)) for x in b) + " |")

    answered = [r for r in rows if r.get("role") == "primary"]
    # 1 validity
    n_calls = len({r["id"] for r in rows})
    strict = len({r["id"] for r in rows if r.get("json") == "strict"})
    rec = len({r["id"] for r in rows if r.get("json") == "recovered"})
    table("JSON validity", ["calls", "strict JSON", "recovered", "invalid", "probabilities sum to 1", "primary null"],
          [[n_calls, strict, rec, n_calls - strict - rec, sum(1 for r in answered if r.get("sum_ok")), sum(1 for r in answered if r.get("null_count"))]])

    def group(r: dict) -> str:
        return "null" if r["kind"] == "null" else ("unmasked" if r["kind"] == "unmasked" else "BTC")
    counts = [r for r in rows if r.get("skeleton") is not None and r.get("condition") != "image"]
    # 2 rule breaks
    body = []
    for name, sel in (("BTC, pivot table", lambda r: group(r) == "BTC" and r["condition"] == "pivot"), ("BTC, raw bars", lambda r: group(r) == "BTC" and r["condition"] == "raw"),
                      ("null, pivot table", lambda r: group(r) == "null" and r["condition"] == "pivot"), ("null, raw bars", lambda r: group(r) == "null" and r["condition"] == "raw"),
                      ("BTC unmasked, pivot", lambda r: group(r) == "unmasked")):
        cs = [r for r in counts if sel(r)]
        if not cs:
            continue
        pri = [r for r in cs if r["role"] == "primary"]
        alt = [r for r in cs if r["role"] == "alternate"]
        tmin = lambda r: any(x in r["soft"] for x in ("C_w2_under_min_time", "C_w4_under_min_time"))
        body.append([name, len(cs), f"{np.mean([bool(r['hard']) for r in cs]):.0%}", f"{np.mean([bool(r['hard']) for r in pri]):.0%}", f"{np.mean([bool(r['hard']) for r in alt]):.0%}" if alt else None,
                     f"{np.mean([tmin(r) for r in cs]):.0%}", f"{np.mean([tmin(r) for r in pri]):.0%}", f"{np.mean([bool(r['soft']) for r in cs]):.0%}", f"{np.mean([bool(r['issues']) for r in cs]):.0%}"])
    table("Hard-rule breaks per count (primary and alternate)", ["group", "counts", "any hard break, sec 0-3", "primary", "alternate", "W2 or W4 under the 25% time minimum (sec 4)", "same, primary only", "any guideline flag", "price or pivot not on the chart"], body)
    rb = [r["random_break"] for r in counts if r.get("random_break") is not None]
    md.append(f"\nLabels checked: {sum(r.get('n_labels', 0) for r in counts)}. A random labelling of the same pattern and length on the same pivot table breaks a hard rule {np.mean(rb):.0%} of the time.")
    tally = Counter(x for r in counts for x in set(r["hard"]))
    table("Which hard rules broke", ["rule", "counts"], [[k, v] for k, v in tally.most_common()])
    piv = [r for r in counts if r["condition"] == "pivot" and group(r) != "unmasked"]
    body = []
    for name, sel in (("BTC", lambda r: group(r) == "BTC"), ("null", lambda r: group(r) == "null")):
        cs = [r for r in piv if sel(r)]
        if cs:
            body.append([name, len(cs), f"{np.mean([bool(r['nested_strict']) for r in cs]):.0%}", f"{np.mean([bool(r['nested_loose']) for r in cs]):.0%}"])
    table("One degree down: legs the count lumps into one wave that do not parse as that wave (pivot table)", ["group", "counts", "strict: a 5 must show 1, 5, 9 legs", "loose: a 5 may also show 3 legs"], body)
    table("Which guidelines were flagged", ["flag", "counts"], [[k, v] for k, v in Counter(x for r in counts for x in set(r["soft"])).most_common(12)])
    table("Price issues in raw-bar answers", ["issue", "counts"], [[k, v] for k, v in Counter(x for r in counts for x in r["issues"]).most_common()])

    img = [r for r in rows if r.get("condition") == "image" and r.get("skeleton") is not None]
    if img:
        table("Chart-image condition", ["call", "role", "state", "next", "confidence", "other", "hard breaks", "label issues", "invalidation is a rule level", "target holds a rule level", "recognised"],
              [[r["id"], r["role"], r.get("state"), r.get("next_move"), r.get("confidence"), r.get("other"), ",".join(r["hard"]) or "none", ",".join(r["issues"]) or "none", r.get("inv_is_rule"), r.get("target_is_rule"), r.get("recognised")[:60]] for r in img])

    # 3 per window
    body = []
    for wid in BTC + NULLS + ["D1u"]:
        for cond in ("pivot", "raw"):
            p = [r for r in counts if r["window"] == wid and r["condition"] == cond and r["role"] == "primary"]
            if not p:
                continue
            a = pairs_agree(p, None, max(2, windows[wid]["bars_in_window"] // 100))
            body.append([wid, cond, len(p), f"{np.mean([bool(r['hard']) for r in p]):.0%}", Counter(r.get("state") for r in p).most_common(1)[0][0], f"{a.get('same_state', 0):.0%}", f"{a.get('same_next', 0):.0%}", f"{a.get('skeleton_jaccard', 0):.2f}",
                         f"{a.get('inv_within_1pct', 0):.0%}", f"{a.get('targets_overlap', 0):.0%}", f"{np.mean([r['confidence'] for r in p]):.2f}", f"{np.mean([r['other'] for r in p]):.2f}"])
    table("Run-to-run agreement of the primary count (pairs of runs)", ["window", "condition", "runs", "hard break", "commonest state", "same state", "same next move", "label overlap", "invalidation within 1%", "target zones overlap", "mean confidence", "mean other"], body)

    allag = defaultdict(list)
    for wid in BTC + NULLS:
        for cond in ("pivot", "raw"):
            p = [r for r in counts if r["window"] == wid and r["condition"] == cond and r["role"] == "primary"]
            if len(p) >= 2:
                a = pairs_agree(p, None, max(2, windows[wid]["bars_in_window"] // 100))
                allag[("null" if wid in NULLS else "BTC", cond)].append(a)
    table("Run-to-run agreement, mean over windows", ["group", "condition", "windows", "same state", "same next move", "label overlap", "invalidation within 1%", "target zones overlap"],
          [[g, c, len(v), *[f"{np.mean([x[m] for x in v]):.2f}" for m in ("same_state", "same_next", "skeleton_jaccard", "inv_within_1pct", "targets_overlap")]] for (g, c), v in sorted(allag.items())])

    # 4 pivot vs raw
    body = []
    cross = defaultdict(list)
    for wid in BTC + NULLS:
        p = [r for r in counts if r["window"] == wid and r["condition"] == "pivot" and r["role"] == "primary"]
        q = [r for r in counts if r["window"] == wid and r["condition"] == "raw" and r["role"] == "primary"]
        if p and q:
            a = pairs_agree(p, q, max(3, windows[wid]["bars_in_window"] // 50))
            cross["null" if wid in NULLS else "BTC"].append(a)
            body.append([wid, a["n"], f"{a['same_state']:.0%}", f"{a['same_next']:.0%}", f"{a['skeleton_jaccard']:.2f}", f"{a['inv_within_1pct']:.0%}", f"{a['targets_overlap']:.0%}"])
    table("Pivot table against raw bars, same window", ["window", "pairs", "same state", "same next move", "label overlap", "invalidation within 1%", "target zones overlap"], body)
    table("Pivot against raw, mean", ["group", "windows", "same state", "same next move", "label overlap", "invalidation within 1%", "target zones overlap"],
          [[g, len(v), *[f"{np.mean([x[m] for x in v]):.2f}" for m in ("same_state", "same_next", "skeleton_jaccard", "inv_within_1pct", "targets_overlap")]] for g, v in sorted(cross.items())])

    # 5 math
    body = []
    for name, sel in (("BTC, pivot table", lambda r: group(r) == "BTC" and r["condition"] == "pivot"), ("BTC, raw bars", lambda r: group(r) == "BTC" and r["condition"] == "raw"), ("null", lambda r: group(r) == "null")):
        cs = [r for r in counts if sel(r)]
        inv = [r["inv_is_rule"] for r in cs if r["inv_is_rule"] is not None]
        tgt = [r["target_is_rule"] for r in cs if r["target_is_rule"] is not None]
        edge = [r["target_edge_is_rule"] for r in cs if r.get("target_edge_is_rule") is not None]
        both = [r["target_both_edges_rule"] for r in cs if r.get("target_both_edges_rule") is not None]
        ic = [r["inv_chance"] for r in cs if r.get("inv_chance") == r.get("inv_chance") and r.get("inv_chance") is not None]
        ec = [r["edge_chance"] for r in cs if r.get("edge_chance") == r.get("edge_chance") and r.get("edge_chance") is not None]
        body.append([name, len(cs), f"{np.mean(inv):.0%}" if inv else None, f"{np.mean(ic):.0%}" if ic else None, f"{np.mean(tgt):.0%}" if tgt else None, f"{np.mean(edge):.0%}" if edge else None, f"{np.mean(both):.0%}" if both else None, f"{np.mean(ec):.0%}" if ec else None])
    table("Do the levels follow the rulebook's math?", ["group", "counts", "invalidation within 0.5% of a rule level", "a random price would", "target zone holds a rule level", "a zone edge within 0.3% of one", "both edges", "a random edge would"], body)
    misses = [(r["id"], r["role"], r.get("state"), r.get("inv"), r.get("inv_rule_name")) for r in counts if r["inv_is_rule"] is False][:12]
    table("Examples of invalidations matching no rule level", ["call", "role", "state", "invalidation", "nearest rule"], [list(m) for m in misses])

    # 6 enumerator
    body = []
    for wid in BTC + NULLS:
        e = enum[wid]
        ps = [r for r in counts if r["window"] == wid and r["condition"] == "pivot"]
        used = [r.get("in_enumerator") for r in ps if r.get("in_enumerator") is not None]
        states = {r.get("state") for r in ps if r["role"] == "primary"}
        n = e["nested"]
        used_l = [r.get("in_enumerator_loose") for r in ps if r.get("in_enumerator_loose") is not None]
        l_ = e["loose"]
        body.append([wid, windows[wid]["kind"], e["bars"], e["pivots"], e["simple"]["readings"], n["readings"], l_["readings"], l_["nested_ways"], l_["distinct_states"], f"{l_['structures_up']}/{l_['structures_down']}", l_["distinct_invalidation_levels"],
                     f"{sum(bool(u) for u in used)}/{len(used)}" if used else None, f"{sum(bool(u) for u in used_l)}/{len(used_l)}" if used_l else None, len(states)])
    table("How ambiguous is each window?", ["window", "kind", "bars", "pivots", "simple readings", "strict readings", "loose readings", "loose fillings", "states", "up/down structures", "invalidation levels", "Opus in strict list (last segment)", "Opus in loose list", "distinct primary states from Opus"], body)

    why = Counter(r.get("why_not_listed") for r in counts if r.get("in_enumerator_loose") is False)
    table("Why a pivot-table count is not in the loose list", ["reason", "counts"], [[k, v] for k, v in why.most_common()])

    # 7 null vs BTC
    pri = [r for r in counts if r["role"] == "primary"]
    body = []
    cats = [("BTC, recognised", lambda r: group(r) == "BTC" and r["recognised_yes"]), ("BTC, not recognised", lambda r: group(r) == "BTC" and not r["recognised_yes"]), ("BTC, all", lambda r: group(r) == "BTC"), ("null", lambda r: group(r) == "null")]
    for name, sel in cats:
        cs = [r for r in pri if sel(r)]
        if not cs:
            continue
        body.append([name, len(cs), f"{np.mean([r['confidence'] for r in cs]):.2f}", f"{np.mean([r['other'] for r in cs]):.2f}", f"{np.mean([r['p_target'] for r in cs if isinstance(r['p_target'], (int, float))]):.2f}",
                     f"{np.mean([bool(r['hard']) for r in cs]):.0%}", f"{np.mean([r['noise_word'] for r in cs]):.0%}"])
    table("Confidence on BTC against random paths (primary count)", ["group", "calls", "mean confidence", "mean other/unclear", "mean P(target first)", "hard break", "mentions noise or fake data"], body)
    body = []
    for wid in BTC + NULLS:
        cs = [r for r in pri if r["window"] == wid]
        if cs:
            body.append([wid, windows[wid]["kind"], len(cs), f"{np.mean([r['confidence'] for r in cs]):.2f}", f"{np.mean([r['other'] for r in cs]):.2f}", f"{sum(r['recognised_yes'] for r in cs)}/{len(cs)}", f"{min(r['confidence'] for r in cs):.2f}-{max(r['confidence'] for r in cs):.2f}"])
    table("Per window", ["window", "kind", "calls", "mean confidence", "mean other", "recognised the period", "confidence range"], body)
    def auc(pos: list[float], neg: list[float]) -> float | None:
        if not pos or not neg:
            return None
        return float(np.mean([(a > b) + .5 * (a == b) for a in pos for b in neg]))
    b_c, n_c = [r for r in pri if group(r) == "BTC" and r["condition"] != "image"], [r for r in pri if group(r) == "null" and r["condition"] != "image"]
    b_c2 = [r for r in b_c if not r["recognised_yes"]]
    table("Can Opus's own numbers tell BTC from noise? (AUC, 0.50 = not at all)", ["number", "BTC calls vs null calls", "BTC calls not recognised vs null calls"],
          [[name, auc([r[k] for r in b_c], [r[k] for r in n_c]), auc([r[k] for r in b_c2], [r[k] for r in n_c])] for name, k in (("primary confidence", "confidence"), ("other/unclear share (higher on noise would be right)", "other"), ("P(target first)", "p_target"))])
    pairs = [("D1", "N1"), ("H2", "N2"), ("D3", "N3")]
    table("Matched pairs: a BTC window against its own bars shuffled", ["BTC", "null", "confidence BTC", "confidence null", "other BTC", "other null", "BTC pivots", "null pivots", "BTC loose readings", "null loose readings"],
          [[a, b, f"{np.mean([r['confidence'] for r in pri if r['window'] == a]):.2f}", f"{np.mean([r['confidence'] for r in pri if r['window'] == b]):.2f}", f"{np.mean([r['other'] for r in pri if r['window'] == a]):.2f}", f"{np.mean([r['other'] for r in pri if r['window'] == b]):.2f}",
            enum[a]["pivots"], enum[b]["pivots"], enum[a]["loose"]["readings"], enum[b]["loose"]["readings"]] for a, b in pairs if any(r["window"] == a for r in pri) and any(r["window"] == b for r in pri)])
    table("Recognised periods (one per call)", ["call", "recognised"], [[r["id"], r["recognised"][:110]] for r in pri if r["recognised_yes"]])
    table("Data notes on null windows", ["call", "note"], [[r["id"], r["data_note"][:130]] for r in pri if group(r) == "null"])

    # 8 outcomes
    res = [r for r in pri if r.get("outcome") in ("target", "invalidation", "timeout") and isinstance(r.get("p_target"), (int, float)) and r.get("baseline_p") is not None]
    body = []
    for name, sel in (("BTC, recognised", lambda r: group(r) == "BTC" and r["recognised_yes"]), ("BTC, not recognised", lambda r: group(r) == "BTC" and not r["recognised_yes"]), ("BTC, all", lambda r: group(r) == "BTC"), ("null", lambda r: group(r) == "null"), ("BTC unmasked", lambda r: group(r) == "unmasked")):
        cs = [r for r in res if sel(r)]
        if not cs:
            continue
        y = np.array([r["outcome"] == "target" for r in cs], float)
        p = np.array([r["p_target"] for r in cs])
        q = np.array([r["baseline_p"] for r in cs])
        dh = [r["dir_hit"] for r in cs if r.get("dir_hit") is not None]
        body.append([name, len(cs), len({r["window"] for r in cs}), f"{y.mean():.0%}", f"{p.mean():.2f}", f"{q.mean():.2f}", f"{np.mean((p-y)**2):.3f}", f"{np.mean((q-y)**2):.3f}", f"{np.mean(dh):.0%} of {len(dh)}" if dh else None])
    table("Forecast check: primary target before invalidation, in the window's own future", ["group", "calls", "windows", "target first", "Opus P", "volatility-only P", "Brier Opus", "Brier volatility-only", "next move called right"], body)
    table("Outcomes", ["window", *["target", "invalidation", "timeout", "already_in_zone", "levels_on_wrong_side"]],
          [[wid, *[sum(1 for r in pri if r["window"] == wid and r.get("outcome") == o) for o in ("target", "invalidation", "timeout", "already_in_zone", "levels_on_wrong_side")]] for wid in BTC + NULLS])

    # today's chart, in real prices, for the forward log
    w = windows.get("L1")
    if w:
        f = w["factor"]
        real = lambda x: f"{x / f:,.0f}" if isinstance(x, (int, float)) else ""
        body = []
        for r in rows:
            if r.get("window") == "L1" and r.get("skeleton") is not None:
                body.append([r["id"], r["role"], r.get("state"), r.get("next_move"), r.get("confidence"), r.get("other"), real(r.get("inv")), f"{real(r.get('t_lo'))} to {real(r.get('t_hi'))}", r.get("p_target")])
        table(f"Opus on today's chart, 4H, real USD (last close {w['last_close'] / f:,.0f}, bar {day_real(w)})", ["call", "role", "state", "next move", "confidence", "other", "invalidation", "target zone", "P(target first)"], body)

    # 9 cost
    recs = [r for r in ledger if r["id"] != "smoke" and not r.get("placeholder")]
    secs = np.array([r["secs"] for r in recs])
    cost = np.array([r.get("cost_usd") or 0 for r in recs])
    out_tok = np.array([r.get("output") or 0 for r in recs])
    think = np.array([r.get("thinking") or 0 for r in recs])
    table("Cost per call", ["calls", "median s", "max s", "mean output tokens", "of which thinking", "mean USD at list price", "total USD at list price"],
          [[len(recs), f"{np.median(secs):.0f}", f"{secs.max():.0f}", f"{out_tok.mean():.0f}", f"{think.mean():.0f}", f"{cost.mean():.2f}", f"{cost.sum():.2f}"]])
    by_c = defaultdict(list)
    for r in recs:
        by_c[r["condition"]].append(r)
    table("Cost by condition", ["condition", "calls", "median s", "mean USD", "mean prompt chars"], [[c, len(v), f"{np.median([x['secs'] for x in v]):.0f}", f"{np.mean([x.get('cost_usd') or 0 for x in v]):.2f}", f"{np.mean([x['prompt_chars'] for x in v]):.0f}"] for c, v in sorted(by_c.items())])

    (OUT / "llm_tables.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
