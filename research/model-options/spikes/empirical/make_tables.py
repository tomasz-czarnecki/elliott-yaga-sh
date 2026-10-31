"""Markdown tables for 02-empirical.md, generated from the CSV and JSON results in the scratch folder, so no number is typed by
hand. Writes tables.md (everything) and doc_tables.json (the compact tables the report uses) to the scratch folder.

    python3 research/model-options/spikes/empirical/make_tables.py

Plain Python only: no numpy needed.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

E = Path("/opt/data/cache/scratch/elliott_research_r1/emp")
KINDS = ("shuffle", "block", "signflip", "trendflip")
LADDER = ("15m_pct2", "1h_pct4", "4h_pct8", "1d_pct16")
OUT: list[str] = []


def emit(line: str = "") -> None:
    OUT.append(line)


def load(name: str) -> list[dict]:
    path = E / name
    return list(csv.DictReader(path.open())) if path.exists() and path.stat().st_size else []


def fl(x, default=float("nan")) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def pct(x, digits: int = 1) -> str:
    v = fl(x)
    return "n/a" if v != v else f"{v * 100:.{digits}f}%"


def num(x, digits: int = 2) -> str:
    v = fl(x)
    return "n/a" if v != v else f"{v:.{digits}f}"


def pv(x) -> str:
    v = fl(x)
    if v != v:
        return "n/a"
    return "<0.001" if v < 0.001 else f"{v:.3f}"


def table(head: list[str], rows: list[list[str]]) -> None:
    emit("| " + " | ".join(head) + " |")
    emit("|" + "---|" * len(head))
    for r in rows:
        emit("| " + " | ".join(str(c) for c in r) + " |")
    emit()


def section(title: str) -> None:
    emit(f"### {title}")
    emit()


def census() -> None:
    rows = [r for r in load("census_btc.csv") if r["venue"] == "bitstamp_btcusd"]
    if not rows:
        return
    section("A1 census, Bitstamp from 2013-03-01")
    table(["scale", "legs", "legs a year", "median leg, days", "median leg size", "six-pivot windows", "legal (up / down)", "truncated", "diagonal cand.", "independent legal"],
          [[r["scale"], f"{int(r['legs']):,}", f"{fl(r['legs_per_year']):,.0f}", num(r["median_leg_days"]), pct(r["median_leg_size"]), f"{int(r['windows']):,}",
            f"{int(r['legal']):,} ({r['legal_up']} / {r['legal_down']})", r["truncated"], r["diagonal"], f"{int(r['independent']):,}"] for r in rows])
    section("A1 which rule kills first (share of six-pivot windows, Bitstamp, per timeframe)")
    tfs = {}
    for r in rows:
        d = tfs.setdefault(r["tf"], {"windows": 0, "R1": 0, "R2": 0, "R3": 0, "R4": 0, "legal": 0, "truncated": 0, "diagonal": 0})
        d["windows"] += int(r["windows"])
        for k in ("R1", "R2", "R3", "R4"):
            d[k] += int(r[f"killed_{k}"])
        d["legal"] += int(r["legal"])
        d["truncated"] += int(r["truncated"])
        d["diagonal"] += int(r["diagonal"])
    table(["timeframe", "windows", "R1 W2 beyond start", "R2 W3 not beyond W1", "R3 W3 shortest", "R4 W4 into W1", "truncated", "legal"],
          [[tf, f"{d['windows']:,}", pct(d["R1"] / d["windows"]), pct(d["R2"] / d["windows"]), pct(d["R3"] / d["windows"]), pct(d["R4"] / d["windows"]),
            pct(d["truncated"] / d["windows"]), pct(d["legal"] / d["windows"])] for tf, d in tfs.items()])
    section("A1 three-leg corrective candidates (Bitstamp)")
    table(["scale", "three-leg windows", "legal zigzag", "legal zigzag or flat"],
          [[r["scale"], f"{int(r['threes']):,}", pct(fl(r["threes_zigzag_legal"]) / max(fl(r["threes"]), 1)), pct(fl(r["threes_any_legal"]) / max(fl(r["threes"]), 1))]
           for r in rows if r["scale"] in LADDER])


def legal_excess() -> None:
    rows = load("a2_legal.csv")
    fw = load("a2_familywise.csv")
    if not rows:
        return
    fwi = {(r["venue"], r["null"], r["trend_days"], r["scale"]): r for r in fw}
    section("A2 legal rate against nulls, Bitstamp, pools per timeframe and all scales")
    fams = (("shuffle", ""), ("signflip", ""), ("trendflip", "30"), ("trendflip", "60"), ("trendflip", "120"))
    idx = {(r["venue"], r["null"], r["trend_days"], r["scale"]): r for r in rows}
    scales = []
    for r in rows:
        if r["venue"] == "bitstamp_btcusd" and r["scale"] not in scales:
            scales.append(r["scale"])
    head = ["scale", "legal / windows", "BTC", "shuffle", "signflip", "trend +-30d", "trend +-60d", "trend +-120d"]
    out = []
    for s in scales:
        base = idx[("bitstamp_btcusd", "shuffle", "", s)]
        line = [s, f"{int(fl(base['legal'])):,} / {int(fl(base['windows'])):,}", pct(base["btc"], 2)]
        for k, d in fams:
            r = idx[("bitstamp_btcusd", k, d, s)]
            f = fwi.get(("bitstamp_btcusd", k, d, s))
            mark = ""
            if f and fl(f["familywise_p"]) < 0.05:
                mark = " **"
            line.append(f"{pct(r['null_median'], 2)} (z {num(r['z'], 1)}{mark})")
        out.append(line)
    pools = [o for o in out if o[0].startswith("pool")]
    cells = [o for o in out if not o[0].startswith("pool")]
    table(head, pools)
    table(head, cells)
    section("A2 other venues, pools")
    table(["venue", "pool", "legal / windows", "BTC", "signflip", "trend +-60d"],
          [[v, s, f"{int(fl(idx[(v, 'signflip', '', s)]['legal'])):,} / {int(fl(idx[(v, 'signflip', '', s)]['windows'])):,}", pct(idx[(v, "signflip", "", s)]["btc"], 2),
            f"{pct(idx[(v, 'signflip', '', s)]['null_median'], 2)} (z {num(idx[(v, 'signflip', '', s)]['z'], 1)})",
            f"{pct(idx[(v, 'trendflip', '60', s)]['null_median'], 2)} (z {num(idx[(v, 'trendflip', '60', s)]['z'], 1)})"]
           for v in ("binance_btcusdt", "bybit_btcusdt_perp") for s in ("pool_15m", "pool_1h", "pool_4h", "pool_1d")])
    eras = load("census_eras.csv")
    section("A2 legal rate by era, against trend +-60d, cells with p < 0.05 (24 cells, about 1.2 expected by chance)")
    counts = {}
    for r in eras:
        if r["null"] == "trendflip":
            d = counts.setdefault(r["era"], [0, 0, 0, 0.0, 0.0])
            d[0] += 1
            d[1] += fl(r["p_high"]) < 0.05
            d[2] += int(r["legal"])
    rows2 = []
    for era, d in counts.items():
        chosen = [r for r in eras if r["null"] == "trendflip" and r["era"] == era]
        w = sum(int(r["windows"]) for r in chosen)
        rows2.append([era, d[1], f"{d[2]:,} / {w:,}", pct(d[2] / w, 2)])
    table(["era", "cells p < 0.05", "legal / windows, all cells", "BTC rate"], rows2)
    section("A2 selected cells by era, against trend +-60d")
    table(["scale", "era", "legal / windows", "BTC", "null median (5-95%)", "p"],
          [[r["scale"], r["era"], f"{r['legal']} / {r['windows']}", pct(r["btc"], 2), f"{pct(r['null_median'], 2)} ({pct(r['null_p5'], 2)} to {pct(r['null_p95'], 2)})", pv(r["p_high"])]
           for r in eras if r["null"] == "trendflip" and r["scale"] in ("1h_atr2", "4h_atr2", "4h_pct8", "1d_pct16")])


def stages_table() -> None:
    rows = load("a3_stages.csv")
    fw = load("a3_familywise.csv")
    if not rows:
        return
    fwi = {(r["null"], r["trend_days"], r["scale"], r["stage"]): r for r in fw}
    idx = {(r["null"], r["trend_days"], r["scale"], r["stage"], r["slice"]): r for r in rows}
    stages = ("s1_w2_holds", "s2_w3_beyond_w1", "s3_w4_clear_of_w1", "s4_w5_completes", "s5_a_reaches_w4")
    section("A3 stages, all directions, ladder scales")
    head = ["scale", "stage", "n", "BTC (95% CI)", "signflip", "trend +-30d", "trend +-60d", "trend +-120d"]
    out = []
    for scale in LADDER + ("4h_atr2", "1h_atr2"):
        for st in stages:
            base = idx.get(("signflip", "", scale, st, "all"))
            if not base:
                continue
            line = [scale, st, f"{int(fl(base['n'])):,}", f"{pct(base['btc'])} ({pct(base['btc_lo'], 0)} to {pct(base['btc_hi'], 0)})"]
            for k, d in (("signflip", ""), ("trendflip", "30"), ("trendflip", "60"), ("trendflip", "120")):
                r = idx[(k, d, scale, st, "all")]
                f = fwi.get((k, d, scale, st))
                mark = ""
                if f and (fl(f["fw_p_high"]) < 0.05 or fl(f["fw_p_low"]) < 0.05):
                    mark = " **"
                line.append(f"{pct(r['null_median'])}{mark}")
            out.append(line)
    table(head, out)
    section("A3 family-wise hits per stage (24 scales): number of scales with family-wise p < 0.05, high / low")
    out = []
    for st in stages:
        line = [st]
        for k, d in (("signflip", ""), ("trendflip", "30"), ("trendflip", "60"), ("trendflip", "120")):
            hi = sum(1 for r in fw if r["null"] == k and r["trend_days"] == d and r["stage"] == st and fl(r["fw_p_high"]) < 0.05)
            lo = sum(1 for r in fw if r["null"] == k and r["trend_days"] == d and r["stage"] == st and fl(r["fw_p_low"]) < 0.05)
            line.append(f"{hi} / {lo}")
        out.append(line)
    table(["stage", "signflip", "trend +-30d", "trend +-60d", "trend +-120d"], out)
    section("A3 stage s3 (W4 stays out of W1) by era and direction, against trend +-60d")
    out = []
    for scale in LADDER + ("4h_atr2",):
        for sl in ("up", "down", "2014-2017", "2018-2021", "2022-2026"):
            r = idx.get(("trendflip", "60", scale, "s3_w4_clear_of_w1", sl))
            if r:
                out.append([scale, sl, f"{int(fl(r['n'])):,}", pct(r["btc"]), f"{pct(r['null_median'])} ({pct(r['null_p5'], 0)} to {pct(r['null_p95'], 0)})", pv(min(fl(r["p_high"]), fl(r["p_low"])) * 2)])
    table(["scale", "slice", "n", "BTC", "null median (5-95%)", "p two-sided"], out)
    section("A3 stage s1 and s2 by direction, against trend +-60d")
    out = []
    for scale in LADDER + ("4h_atr2",):
        for st in ("s1_w2_holds", "s2_w3_beyond_w1"):
            for sl in ("up", "down"):
                r = idx.get(("trendflip", "60", scale, st, sl))
                if r:
                    out.append([scale, st, sl, f"{int(fl(r['n'])):,}", pct(r["btc"]), pct(r["null_median"]), pv(min(fl(r["p_high"]), fl(r["p_low"])) * 2)])
    table(["scale", "stage", "direction", "n", "BTC", "null median", "p two-sided"], out)


def facts() -> None:
    path = E / "a4_facts.json"
    if not path.exists():
        return
    f = json.loads(path.read_text())
    section("A0 facts: autocorrelation")
    out = []
    for tf, d in f["f1"].items():
        for lag, a, ab, lo, hi in zip(d["lags"], d["return_acf"], d["abs_return_acf"], d["shuffle_band_5"], d["shuffle_band_95"]):
            out.append([tf, lag, f"{a:+.3f}", f"{lo:+.3f} to {hi:+.3f}", f"{ab:+.3f}"])
    table(["bars", "lag", "return ACF", "shuffle 5-95%", "abs return ACF"], out)
    table(["bars", "lag-1 return ACF, 2014-2017", "2018-2021", "2022-2026"],
          [[tf, f"{d['return_acf_lag1_2014-2017']:+.3f}", f"{d['return_acf_lag1_2018-2021']:+.3f}", f"{d['return_acf_lag1_2022-2026']:+.3f}"] for tf, d in f["f1"].items()])
    section("A0 facts: volatility forecast out of sample")
    table(["bars", "R2 2022-2026", "n"], [[tf, f"{d['r2_oos_2022_2026']:.2f}", f"{d['n_test']:,}"] for tf, d in f["f2"].items()])
    section("A0 facts: variance ratio of daily returns")
    qs = [k for k in f["f3"] if k.isdigit()]
    table(["horizon, days", "VR", "shuffle 5-95%", "p high", "2014-2017", "2018-2021", "2022-2026"],
          [[q, f"{f['f3'][q]['vr']:.2f}", f"{f['f3'][q]['shuffle_p5']:.2f} to {f['f3'][q]['shuffle_p95']:.2f}", pv(f["f3"][q]["p_high"]),
            f"{f['f3']['2014-2017'][q]:.2f}", f"{f['f3']['2018-2021'][q]:.2f}", f"{f['f3']['2022-2026'][q]:.2f}"] for q in qs])
    section("A0 facts: momentum, sign of the last N days against the next N days, non-overlapping")
    table(["N days", "same sign", "95% CI", "n", "share of up windows", "base if independent"],
          [[n, pct(d["same_sign"]), f"{pct(d['lo'], 0)} to {pct(d['hi'], 0)}", d["n"], pct(d["up_share"]), pct(d["independent_base"])] for n, d in f["f4"].items()])
    legs = load("a4_legs.csv")
    section("A0 facts: up legs and down legs")
    table(["scale", "up / down legs", "median up, size and days", "median down, size and days", "down speed / up speed", "signflip", "trendflip"],
          [[r["scale"], f"{int(r['up_legs']):,} / {int(r['down_legs']):,}", f"{pct(r['median_up_size'])}, {num(r['median_up_days'])}", f"{pct(r['median_down_size'])}, {num(r['median_down_days'])}",
            num(r["down_over_up_speed"]), f"{num(r['down_over_up_speed|signflip_median'])} ({num(r['down_over_up_speed|signflip_p5'])} to {num(r['down_over_up_speed|signflip_p95'])})",
            f"{num(r['down_over_up_speed|trendflip_median'])} ({num(r['down_over_up_speed|trendflip_p5'])} to {num(r['down_over_up_speed|trendflip_p95'])})"] for r in legs])


def ambiguity() -> None:
    rows = load("a5_ambiguity.csv")
    if not rows:
        return
    section("A4 free-degree counts per pivot")
    head = ["fine scale", "pivots", "share with a legal count", "shuffle", "trend +-60d", "mean counts per pivot", "shuffle", "trend +-60d", "share with 3 or more", "trend +-60d"]
    table(head, [[r["scale"], f"{int(r['pivots']):,}", pct(r["share_with_legal_count"]), pct(r["share_with_legal_count|shuffle_median"]), pct(r["share_with_legal_count|trendflip_median"]),
                  num(r["mean_counts"]), num(r["mean_counts|shuffle_median"]), num(r["mean_counts|trendflip_median"]), pct(r["share_with_3_or_more"]), pct(r["share_with_3_or_more|trendflip_median"])] for r in rows])


def subwaves() -> None:
    rows = load("a6_subwaves.csv")
    if not rows:
        return
    section("A5 what is inside a swing: share of coarse legs by number of fine swings, BTC against trend +-60d")
    idx = {(r["coarse"], r["fine"], r["null"], r["metric"]): r for r in rows}
    pairs = []
    for r in rows:
        if (r["coarse"], r["fine"]) not in pairs:
            pairs.append((r["coarse"], r["fine"]))
    out = []
    for a, b in pairs:
        line = [a, b]
        for m in ("share_1", "share_3", "share_5", "share_7", "share_9plus"):
            r = idx[(a, b, "trendflip", m)]
            line.append(f"{pct(r['btc'])} / {pct(r['null_median'])}")
        out.append(line)
    table(["coarse", "fine", "1 (BTC / null)", "3", "5", "7", "9+"], out)
    section("A5 legal impulses: W3 subdivides into 5, full 5-3-5-3-5 form")
    out = []
    for a, b in pairs:
        n = idx[(a, b, "trendflip", "legal_n")]
        line = [a, b, f"{fl(n['btc']):.0f}"]
        for m in ("w3_is_5", "w2_is_1_or_3", "full_form"):
            for k in ("signflip", "trendflip"):
                r = idx[(a, b, k, m)]
                line.append(f"{pct(r['btc'])} vs {pct(r['null_median'])} (p {pv(r['p_two'])})")
        out.append(line)
    table(["coarse", "fine", "legal", "W3 = 5, signflip", "W3 = 5, trend", "W2, W4 in 1 or 3, signflip", "trend", "full form, signflip", "trend"], out)
    section("A5 multiple tests")
    out = []
    for k in ("shuffle", "signflip", "trendflip"):
        chosen = [r for r in rows if r["null"] == k and r["metric"] != "legal_n"]
        out.append([k, len(chosen), sum(fl(r["p_two"]) < 0.05 for r in chosen), f"{0.05 * len(chosen):.1f}"])
    table(["null", "tests", "p < 0.05", "expected by chance"], out)


def b1() -> None:
    path = E / "b1_summary.json"
    if not path.exists():
        return
    s = json.loads(path.read_text())
    section(f"B1 omnibus, {s['tests']:,} tests")
    table(["null", "paths", "tests at z >= 1.645, BTC", "same count on null paths, median (5-95%)", "p", "largest z, BTC", "largest z on null paths, 95th pct", "BH discoveries BTC", "placebo median (95th)", "family-wise hits"],
          [[k, s["paths"][k], s["omnibus"][k]["tests_z_ge_1645_btc"], f"{s['omnibus'][k]['null_median']:.0f} ({s['omnibus'][k]['null_p5']:.0f} to {s['omnibus'][k]['null_p95']:.0f})", pv(s["omnibus"][k]["p_high"]),
            num(s["omnibus"][k]["max_z_btc"]), num(s["omnibus"][k]["max_z_null_p95"]), s["omnibus"][k]["bh_discoveries_btc"],
            f"{s['omnibus'][k]['bh_discoveries_placebo_median']:.0f} ({s['omnibus'][k]['bh_discoveries_placebo_p95']:.0f})", s["omnibus"][k]["familywise_hits_btc"]] for k in KINDS])
    levels = load("b1_levels.csv")
    for t, label in (("ret", "retracement, all pairs"), ("ext", "extension, 3-pivot pull")):
        section(f"B1 level summary, {label}, log price, wide band: mean excess across scales and mean z against each null")
        chosen = [r for r in levels if r["type"] == t and r["price"] == "log" and fl(r["width"]) == 0.04]
        table(["level", "cells", "BTC excess", "shuffle excess", "signflip excess", "z shuffle (p)", "z block (p)", "z signflip (p)", "z trend (p)"],
              [[r["level"], r["cells"], num(r["excess_btc_mean"], 3), num(r["shuffle_excess_null_mean"], 3), num(r["signflip_excess_null_mean"], 3),
                f"{num(r['shuffle_mean_z'])} ({pv(r['shuffle_p'])})", f"{num(r['block_mean_z'])} ({pv(r['block_p'])})", f"{num(r['signflip_mean_z'])} ({pv(r['signflip_p'])})",
                f"{num(r['trendflip_mean_z'])} ({pv(r['trendflip_p'])})"] for r in chosen])
    section("B1 level summary, smallest q over all level-type-price-width combinations")
    out = []
    for k in KINDS:
        best = sorted(levels, key=lambda r: fl(r[f"{k}_q"]))[:4]
        for r in best:
            out.append([k, r["type"], r["price"], r["width"], r["level"], num(r[f"{k}_mean_z"]), pv(r[f"{k}_p"]), pv(r[f"{k}_q"]), num(r["excess_btc_mean"], 3), num(r[f"{k}_excess_null_mean"], 3)])
    table(["null", "type", "price", "width", "level", "mean z", "p", "q", "BTC excess", "null excess"], out)
    tests = load("b1_tests.csv")
    section("B1 largest single z against the volatility-only null, with family-wise p")
    out = []
    for r in sorted(tests, key=lambda r: -fl(r["signflip_z"]))[:15]:
        out.append([r["scale"], r["type"], r["price"], r["width"], r["level"], num(r["excess_btc"]), num(r["signflip_mean"]), num(r["signflip_z"]), pv(r["signflip_p"]), pv(r["signflip_fw"]),
                    num(r["trendflip_z"]), pv(r["trendflip_fw"])])
    table(["scale", "type", "price", "width", "level", "BTC excess", "null excess", "z", "p", "family-wise p", "z trend", "family-wise p trend"], out)
    section("B1 power: sd of the excess statistic on null paths, signflip, retracements, log price (what size of bump could be seen)")
    out = []
    for scale in LADDER + ("15m_pct1",):
        for w in ("0.015", "0.04"):
            chosen = [r for r in tests if r["scale"] == scale and r["type"] == "ret" and r["price"] == "log" and fl(r["width"]) == fl(w) and fl(r["level"]) in (0.382, 0.5, 0.618, 0.786, 1.0, 1.618)]
            if chosen:
                sd = sum(fl(r["signflip_sd"]) for r in chosen) / len(chosen)
                out.append([scale, w, num(sd), f"+{sd * 2.5 * 100:.0f}%"])
    table(["scale", "band half-width", "sd of excess", "bump needed for z = 2.5"], out)
    density = load("b1_density.csv")
    for t in ("ret",):
        for scale in LADDER:
            section(f"B1 density, {scale}, share of leg pairs by ratio")
            chosen = [r for r in density if r["scale"] == scale and r["type"] == t]
            bands = []
            for r in chosen:
                if r["null"] == "signflip":
                    bands.append(r)
            trend = {(r["from"], r["to"]): r for r in chosen if r["null"] == "trendflip"}
            shuffle = {(r["from"], r["to"]): r for r in chosen if r["null"] == "shuffle"}
            table(["ratio", "BTC", "random-walk law", "shuffle", "signflip (5-95%)", "trend +-60d"],
                  [[f"{num(r['from'], 3)} to {num(r['to'], 3) if fl(r['to']) < 1e6 else 'up'}", pct(r["btc"]), pct(r["law"]), pct(shuffle[(r["from"], r["to"])]["null_median"]),
                    f"{pct(r['null_median'])} ({pct(r['null_p5'])} to {pct(r['null_p95'])})", pct(trend[(r["from"], r["to"])]["null_median"])] for r in bands])
    shape = load("b1_shape.csv")
    section("B1 fingerprint: does the whole shape differ from the null, and can a fit on BTC up to 2021 beat the null on 2022-2026? (48 histograms: 24 scales x retracement, extension)")
    out = []
    for k in KINDS:
        n = len(shape)
        ks05 = sum(fl(r[f"{k}_ks_p"]) < 0.05 for r in shape)
        ksq = sum(fl(r[f"{k}_ks_p_q"]) < 0.05 for r in shape)
        g05 = sum(fl(r[f"{k}_coarse_gain_p"]) < 0.05 for r in shape)
        gq = sum(fl(r[f"{k}_coarse_gain_p_q"]) < 0.05 for r in shape)
        pos = sum(fl(r[f"{k}_coarse_gain"]) > 0 for r in shape)
        out.append([k, n, ks05, ksq, g05, gq, pos])
    table(["null", "histograms", "shape p < 0.05", "shape q < 0.05", "12-band fit beats null p < 0.05", "q < 0.05", "gain above zero"], out)
    section("B1 fingerprint on ladder scales")
    out = []
    for r in shape:
        if r["scale"] in LADDER:
            out.append([r["scale"], r["type"], f"{int(r['n']):,}", f"{int(r['n_test']):,}"] + [f"{pv(r[f'{k}_ks_p'])}" for k in KINDS] + [f"{fl(r[f'{k}_coarse_gain']) * 1000:+.1f} ({pv(r[f'{k}_coarse_gain_p'])})" for k in ("signflip", "trendflip")])
    table(["scale", "type", "n", "n 2022+", "KS p shuffle", "KS p block", "KS p signflip", "KS p trend", "12-band gain signflip, millinats (p)", "gain trend (p)"], out)
    out = []
    for r in shape:
        if fl(r["trendflip_coarse_gain_p_q"]) < 0.10 or fl(r["signflip_coarse_gain_p_q"]) < 0.10:
            out.append([r["scale"], r["type"], f"{int(r['n_test']):,}", f"{fl(r['signflip_coarse_gain']) * 1000:+.1f} ({pv(r['signflip_coarse_gain_p'])}, q {pv(r['signflip_coarse_gain_p_q'])})", f"{fl(r['trendflip_coarse_gain']) * 1000:+.1f} ({pv(r['trendflip_coarse_gain_p'])}, q {pv(r['trendflip_coarse_gain_p_q'])})"])
    section("B1 fingerprint: histograms where the fit beats the null out of sample, q < 0.10")
    table(["scale", "type", "n 2022+", "gain signflip, millinats", "gain trend"], out)


def barrier() -> None:
    rows = load("b1b_barrier.csv")
    if not rows:
        return
    section("B1b barrier at 1.0, whole period and by era, ladder scales, Bitstamp and others, against trend +-60d")
    out = []
    for venue in ("bitstamp_btcusd", "binance_btcusdt", "bybit_btcusdt_perp"):
        for scale in LADDER:
            for r in rows:
                if r["venue"] == venue and r["scale"] == scale and r["null"] == "trendflip":
                    out.append([venue[:8], scale, r["period"], f"{int(fl(r['n'])):,}", f"{fl(r['asymmetry']) * 100:+.1f}", f"{fl(r['asymmetry_median']) * 100:+.1f} ({fl(r['asymmetry_p5']) * 100:+.1f} to {fl(r['asymmetry_p95']) * 100:+.1f})",
                                pv(min(1.0, 2 * min(fl(r.get("asymmetry_p_high")), fl(r.get("asymmetry_p_low"))))), num(r["spike"]), f"{num(r['spike_median'])} ({num(r['spike_p5'])} to {num(r['spike_p95'])})",
                                pv(r.get("spike_p_high"))])
    table(["venue", "scale", "period", "pairs", "asymmetry, pp", "null (5-95%)", "p", "spike at 1.0", "null (5-95%)", "p high"], out)
    section("B1b asymmetry: count of cells (24 scales) with BTC above the null's 95th percentile")
    out = []
    for venue in ("bitstamp_btcusd", "binance_btcusdt", "bybit_btcusdt_perp"):
        periods = []
        for r in rows:
            if r["venue"] == venue and r["period"] not in periods:
                periods.append(r["period"])
        for period in periods:
            for kind in ("signflip", "trendflip"):
                chosen = [r for r in rows if r["venue"] == venue and r["period"] == period and r["null"] == kind and fl(r["asymmetry"]) == fl(r["asymmetry"])]
                above = sum(fl(r["asymmetry"]) > fl(r["asymmetry_p95"]) for r in chosen)
                pos = sum(fl(r["asymmetry"]) > 0 for r in chosen)
                ov = sum(fl(r.get("run_on")) > fl(r.get("run_on_p95")) for r in chosen)
                below = sum(fl(r.get("run_on")) < fl(r.get("run_on_p5")) for r in chosen)
                out.append([venue[:8], period, kind, len(chosen), above, pos, ov, below])
    table(["venue", "period", "null", "cells", "asymmetry above null 95th", "asymmetry above 0", "run-on above null 95th", "run-on below null 5th"], out)
    section("B1b overshoot past the previous pivot, in thresholds (memoryless: mean 1, median 0.69, 22% under 0.25), against trend +-60d")
    out = []
    for venue in ("bitstamp_btcusd", "binance_btcusdt", "bybit_btcusdt_perp"):
        for scale in LADDER:
            for r in rows:
                if r["venue"] == venue and r["scale"] == scale and r["null"] == "trendflip":
                    out.append([venue[:8], scale, r["period"], f"{int(fl(r['overshoot_n'])):,}" if fl(r['overshoot_n']) == fl(r['overshoot_n']) else "", num(r["overshoot_mean"]), f"{num(r['overshoot_mean_median'])} ({num(r['overshoot_mean_p5'])} to {num(r['overshoot_mean_p95'])})",
                                pv(min(1.0, 2 * min(fl(r.get("overshoot_mean_p_high")), fl(r.get("overshoot_mean_p_low"))))), num(r["overshoot_median"]), num(r["overshoot_median_median"]), pct(r["share_overshoot_under_025"]), pct(r["share_overshoot_under_025_median"])])
    table(["venue", "scale", "period", "breaks", "mean overshoot", "null (5-95%)", "p", "median", "null", "share under 0.25", "null"], out)
    fine = load("b1b_fine.csv")
    section("B1b fine structure around r = 1, share of pairs, by ln(r), against trend +-60d")
    out = []
    for scale in LADDER:
        for r in fine:
            if r["scale"] == scale and r["null"] == "trendflip":
                out.append([scale, f"{fl(r['from']):+.3f} to {fl(r['to']):+.3f}", pct(r["btc"], 2), f"{pct(r['null_median'], 2)} ({pct(r['null_p5'], 2)} to {pct(r['null_p95'], 2)})"])
    table(["scale", "ln(r)", "BTC", "null (5-95%)"], out)
    ties_rows = [r for r in rows if r["period"] == "all" and r["null"] == "trendflip" and r["ties_btc"] != "" and r["scale"] in LADDER + ("15m_pct1",)]
    section("B1b exact price ties between a pivot and the one two pivots back")
    table(["venue", "scale", "share of pairs"], [[r["venue"][:8], r["scale"], pct(r["ties_btc"], 2)] for r in ties_rows])


def venues() -> None:
    rows = load("b1c_levels.csv")
    if not rows:
        return
    section("B1 level summary on the other venues, retracements, wide band, mean z across 24 scales (p two-sided)")
    out = []
    for level in ("0.236", "0.382", "0.5", "0.618", "0.786", "1.0", "1.272", "1.618", "2.0", "2.236", "2.618"):
        line = [level]
        for venue in ("bybit_btcusdt_perp", "binance_btcusdt"):
            for r in rows:
                if r["venue"] == venue and r["type"] == "ret" and fl(r["width"]) == 0.04 and fl(r["level"]) == fl(level):
                    line.append(f"{num(r['signflip_mean_z'])} ({pv(r['signflip_p'])})")
                    line.append(f"{num(r['trendflip_mean_z'])} ({pv(r['trendflip_p'])})")
        out.append(line)
    table(["level", "Bybit signflip", "Bybit trend", "Binance signflip", "Binance trend"], out)
    section("B1 other venues: tests with q < 0.05 (11 levels x 4 ratio types x 2 widths per venue)")
    out = []
    for r in rows:
        for k in ("signflip", "trendflip"):
            if fl(r[f"{k}_q"]) < 0.05:
                out.append([r["venue"][:8], k, r["type"], r["width"], r["level"], num(r[f"{k}_mean_z"]), pv(r[f"{k}_p"]), pv(r[f"{k}_q"]), num(r["excess_btc_mean"], 3)])
    table(["venue", "null", "type", "width", "level", "mean z", "p", "q", "BTC excess"], out)


def scan() -> None:
    top = load("b1d_top.csv")
    if not top:
        return
    section("B1 level scan: the highest levels on a dense grid, 1h, 4h, 1d scales, mean z standardised against the null's spread")
    table(["null", "type", "price", "rank", "level", "standardised z", "family-wise p for the scan", "nearest listed level", "distance"],
          [[r["null"], r["type"], r["price"], r["rank"], num(r["level"], 3), num(r["standardised"]), pv(r["scan_familywise_p"]), r["nearest_fib"], f"{num(r['distance_pct'], 1)}%"] for r in top if int(r["rank"]) <= 5])
    rows = load("b1d_scan.csv")
    section("B1 level scan: value at the listed levels (nearest grid point), standardised z, and its family-wise p")
    out = []
    grid = sorted({fl(r["level"]) for r in rows})
    for level in (0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618, 2.0, 2.236, 2.618):
        near = min(grid, key=lambda g: abs(g - level))
        line = [level]
        for rtype, price in (("ret", "log"), ("ret", "lin"), ("ext", "log"), ("ext", "lin")):
            for r in rows:
                if r["null"] == "trendflip" and r["type"] == rtype and r["price"] == price and fl(r["level"]) == near:
                    line.append(f"{num(r['standardised'])} ({pv(r['scan_familywise_p'])})")
        out.append(line)
    table(["level", "ret log", "ret lin", "ext log", "ext lin"], out)
    rep = load("b1d_replicate.csv")
    section("B1 replication of the hit: extension, linear price, 1.618, +-4 percent, counts over 1h, 4h, 1d scales")
    table(["venue", "null", "period", "in band", "shoulders", "excess", "null median (5-95%)", "p high"],
          [[r["venue"][:8], r["null"], r["period"], r["in_band"], r["shoulders"], num(r["excess"]), f"{num(r['null_median'])} ({num(r['null_p5'])} to {num(r['null_p95'])})", pv(r["p_high"])] for r in rep])


def alternation() -> None:
    rows = load("b3_alternation.csv")
    if not rows:
        return
    section("B2 alternation: Spearman of W2 depth and W4 depth, per timeframe (all scales) and era")
    table(["bars", "null", "period", "n", "BTC", "null median (5-95%)", "p low"],
          [[r["tf"], r["null"], r["period"], r["n"], num(r["spearman"]), f"{num(r['null_median'])} ({num(r['null_p5'])} to {num(r['null_p95'])})", pv(r["p_low"])] for r in rows if r["null"] == "trendflip"])


def b2() -> None:
    rows = load("b2_windows.csv")
    if not rows:
        return
    s = json.loads((E / "b2_summary.json").read_text())
    section("B2 multiple tests over all scales and windows (slice all, log)")
    table(["null", "windows", "p < 0.05", "expected by chance", "q < 0.05", "q < 0.10"],
          [[k, s["windows_primary"], s[k]["p_under_05"], f"{s[k]['expected_by_chance']:.1f}", s[k]["q_under_05"], s[k]["q_under_10"]] for k in KINDS])
    for group in ("ladder_pct", "ladder_atr", "pool_15m", "pool_1h", "pool_4h", "pool_1d"):
        chosen = [r for r in rows if r["group"] == group and r["slice"] == "all" and r["price"] == "log"]
        if not chosen:
            continue
        section(f"B2 and B3 windows, {group}, n = {chosen[0]['n']}")
        table(["ratio", "window", "BTC", "shuffle", "signflip (5-95%)", "trend +-60d (5-95%)", "p trend, two-sided"],
              [[r["key"], r["window"], pct(r["btc"]), pct(r["shuffle_median"]), f"{pct(r['signflip_median'])} ({pct(r['signflip_p5'], 0)} to {pct(r['signflip_p95'], 0)})",
                f"{pct(r['trendflip_median'])} ({pct(r['trendflip_p5'], 0)} to {pct(r['trendflip_p95'], 0)})", pv(min(1.0, 2 * min(fl(r["trendflip_p_high"]), fl(r["trendflip_p_low"]))))] for r in chosen])
    section("B2 fingerprint by era: ladder_pct, trend +-60d null")
    keys = [("w2", "0.5-0.618"), ("w2", "under 0.382"), ("w4", "0.236-0.382"), ("w3", "near 1.618"), ("w3", "near 2.618"), ("w5_012", "near 2.236"), ("w5_014", "near 1.0"), ("w5_014", "near 0.618")]
    out = []
    for key, window in keys:
        for era in ("2014-2017", "2018-2021", "2022-2026"):
            for r in rows:
                if r["group"] == "ladder_pct" and r["key"] == key and r["window"] == window and r["slice"] == era:
                    out.append([key, window, era, r["n"], pct(r["btc"]), f"{pct(r['trendflip_median'])} ({pct(r['trendflip_p5'], 0)} to {pct(r['trendflip_p95'], 0)})"])
    table(["ratio", "window", "era", "n", "BTC", "null median (5-95%)"], out)
    excess = load("b2_excess.csv")
    section("B2 local excess at the rulebook's levels, band +-5 percent, pooled")
    out = []
    for group in ("ladder_pct", "pool_1h", "pool_4h"):
        for r in excess:
            if r["group"] == group:
                out.append([group, r["key"], r["level"], r["band"], r["shoulders"], num(r["excess_btc"]), f"{num(r['signflip_median'])} ({num(r['signflip_p5'])} to {num(r['signflip_p95'])})", pv(r["signflip_p_high"]),
                            f"{num(r['trendflip_median'])} ({num(r['trendflip_p5'])} to {num(r['trendflip_p95'])})", pv(r["trendflip_p_high"])])
    table(["pool", "ratio", "level", "in band", "shoulders", "BTC excess", "signflip (5-95%)", "p", "trend (5-95%)", "p"], out)
    derived = load("b2_derived.csv")
    section("B2 derived")
    out = []
    for r in derived:
        if r["group"] in ("ladder_pct", "ladder_atr", "pool_1h", "pool_4h", "pool_1d", "pool_15m"):
            out.append([r["group"], r["n"], pct(r["share_w1_longest"]), pct(r["share_w1_longest|trendflip_median"]), pct(r["share_w3_longest"]), pct(r["share_w3_longest|trendflip_median"]),
                        pct(r["share_w5_longest"]), pct(r["share_w5_longest|trendflip_median"]), num(r["spearman_w2_w4"]), num(r["spearman_w2_w4|trendflip_median"]), pv(min(1.0, 2 * min(fl(r["spearman_w2_w4|trendflip_p_high"]), fl(r["spearman_w2_w4|trendflip_p_low"]))))])
    table(["pool", "n", "W1 longest", "trend", "W3 longest", "trend", "W5 longest", "trend", "Spearman W2,W4", "trend", "p"], out)
    out = []
    for r in derived:
        if r["group"] in ("ladder_pct", "ladder_atr", "pool_1h", "pool_4h", "pool_1d", "pool_15m"):
            out.append([r["group"], f"{pct(r['addone_1618'])} of {r['n_addone_1618']}", pct(r["addone_1618|trendflip_median"]), f"{pct(r['addone_2618'])} of {r['n_addone_2618']}", pct(r["addone_2618|trendflip_median"]),
                        f"{pct(r['shallow_w2_strong_uptrend'])} of {r['n_strong']}", pct(r["shallow_w2_strong_uptrend|trendflip_median"]), f"{pct(r['shallow_w2_other'])} of {r['n_other']}", pct(r["shallow_w2_other|trendflip_median"])])
    table(["pool", "add-one: W3 1.618 then W5 2.236", "trend", "W3 2.618 then W5 3.236", "trend", "W2 under .45 after strong uptrend", "trend", "W2 under .45 otherwise", "trend"], out)
    shape = load("b2_shape.csv")
    section("B2 shape and learnability, all scales, per ratio: histograms with shape p < 0.05, shape q < 0.05, band fit beats null q < 0.05")
    out = []
    for key in ("w2", "w3", "w4", "w5_014", "w5_012", "t2_t1", "t3_t1", "t4_t3", "t4_t2", "t5_t1", "t5_t3"):
        chosen = [r for r in shape if r["key"] == key]
        line = [key, len(chosen)]
        for k in KINDS:
            line.append(f"{sum(fl(r[f'{k}_ks_p']) < 0.05 for r in chosen)} / {sum(fl(r[f'{k}_ks_p_q']) < 0.05 for r in chosen)} / {sum(fl(r.get(f'{k}_coarse_gain_p_q')) < 0.05 for r in chosen)}")
        out.append(line)
    table(["ratio", "scales"] + [f"{k}" for k in KINDS], out)


def c() -> None:
    rows = load("c_metrics.csv")
    if not rows:
        return
    idx = {r["metric"]: r for r in rows}
    def line(metric: str, label: str, as_pct: bool = True) -> list[str]:
        r = idx.get(metric)
        if not r:
            return [label, "n/a", "", "", "", ""]
        f = pct if as_pct else num
        cells = [label, f(r["btc"])]
        for k in KINDS:
            cells.append(f"{f(r[f'{k}_median'])} ({f(r[f'{k}_p5'])} to {f(r[f'{k}_p95'])}) p {pv(r[f'{k}_p2'])}")
        return cells
    head = ["metric", "BTC", "shuffle", "block", "signflip", "trend +-60d"]
    section("C1 top position")
    out = []
    for tag in ("hind", "live"):
        out.append(line(f"c1|{tag}|n_cycles", f"{tag}: cycles", False))
        out.append(line(f"c1|{tag}|share_top_within_0.05_of_mid", f"{tag}: top within 0.05 of mid (uniform 10%)"))
        out.append(line(f"c1|{tag}|share_top_within_0.10_of_mid", f"{tag}: top within 0.10 of mid (uniform 20%)"))
        out.append(line(f"c1|{tag}|share_top_within_0.15_of_mid", f"{tag}: top within 0.15 of mid (uniform 30%)"))
        out.append(line(f"c1|{tag}|share_top_left_of_mid", f"{tag}: top left of mid"))
        out.append(line(f"c1|{tag}|mean_abs_distance_from_mid", f"{tag}: mean distance from mid", False))
        out.append(line(f"c1|{tag}|median_top_pos", f"{tag}: median top position", False))
    table(head, out)
    section("C2 pivot highs and lows by phase, primary scales")
    out = []
    for tag in ("hind", "live"):
        for scale in ("4h_pct8", "1d_pct16"):
            out.append(line(f"c2|{tag}|{scale}|share_pivot_highs_in_0.40-0.60", f"{tag} {scale}: pivot highs in 0.4-0.6"))
            out.append(line(f"c2|{tag}|{scale}|share_pivot_lows_in_0.40-0.60", f"{tag} {scale}: pivot lows in 0.4-0.6"))
            out.append(line(f"c2|{tag}|{scale}|share_cycles_with_pivot_high_in_0.40-0.60", f"{tag} {scale}: cycles with a pivot high in 0.4-0.6"))
            out.append(line(f"c2|{tag}|{scale}|biggest_pullback_starts_in_0.40-0.60", f"{tag} {scale}: biggest pullback starts in 0.4-0.6 (uniform 20%)"))
            out.append(line(f"c2|{tag}|{scale}|biggest_pullback_start_median", f"{tag} {scale}: biggest pullback start, median phase", False))
    table(head, out)
    section("C3 structure ends, primary settings")
    out = []
    for tag in ("hind", "live"):
        for scale in ("4h_pct8", "1d_pct16"):
            for struct in ("impulse", "abc", "both"):
                out.append(line(f"c3|{tag}|{scale}|{struct}|lows_with_down_end|14d", f"{tag} {scale} {struct}: weekly lows with a down-structure end within 14d"))
                out.append(line(f"c3|{tag}|{scale}|{struct}|days_with_down_end|14d", f"{tag} {scale} {struct}: any day with one within 14d"))
                out.append(line(f"c3|{tag}|{scale}|{struct}|down_ends_near_low|14d", f"{tag} {scale} {struct}: down-structure ends within 14d of a weekly low"))
                out.append(line(f"c3|{tag}|{scale}|{struct}|odds_ratio_low|14d", f"{tag} {scale} {struct}: odds ratio among pivot lows", False))
                out.append(line(f"c3|{tag}|{scale}|{struct}|cycles_with_up_end_in_mid|0.40-0.60", f"{tag} {scale} {struct}: cycles with an up-structure end in 0.4-0.6"))
                out.append(line(f"c3|{tag}|{scale}|{struct}|up_ends_in_mid|0.40-0.60", f"{tag} {scale} {struct}: up-structure ends in 0.4-0.6 (uniform 20%)"))
                out.append(line(f"c3|{tag}|{scale}|{struct}|odds_ratio_mid|0.40-0.60", f"{tag} {scale} {struct}: odds ratio among pivot highs", False))
    table(head, out)
    section("C3 any degree (a structure at any of six scales counts)")
    out = []
    for tag in ("hind", "live"):
        for struct in ("impulse", "both"):
            out.append(line(f"c3|{tag}|any_scale|{struct}|lows_with_down_end|14d", f"{tag} {struct}: weekly lows with a down-structure end within 14d"))
            out.append(line(f"c3|{tag}|any_scale|{struct}|days_with_down_end|14d", f"{tag} {struct}: any day with one within 14d"))
            out.append(line(f"c3|{tag}|any_scale|{struct}|cycles_with_up_end_in_mid|0.40-0.60", f"{tag} {struct}: cycles with an up-structure end in 0.4-0.6"))
    table(head, out)
    section("C3 sensitivity: smallest p over all scales, structures, tolerances and bands")
    c3 = [r for r in rows if r["metric"].startswith("c3|") and "days_with" not in r["metric"] and "lows_with_up_end" not in r["metric"]]
    out = []
    for k in KINDS:
        n = len(c3)
        n05 = sum(fl(r[f"{k}_p2"]) < 0.05 for r in c3)
        nq = sum(fl(r[f"{k}_q_all"]) < 0.05 for r in c3)
        hi = sum(fl(r[f"{k}_p_high"]) < 0.025 for r in c3)
        lo = sum(fl(r[f"{k}_p_low"]) < 0.025 for r in c3)
        out.append([k, n, n05, f"{0.05 * n:.0f}", nq, hi, lo])
    table(["null", "tests", "p < 0.05 two-sided", "expected by chance", "q < 0.05", "BTC above null", "BTC below null"], out)
    prim = [r for r in rows if r["primary"] == "True"]
    section("Primary rows with the smallest p per null")
    out = []
    for k in KINDS:
        for r in sorted(prim, key=lambda r: fl(r[f"{k}_p2"]))[:6]:
            out.append([k, r["metric"], num(r["btc"], 3), f"{num(r[f'{k}_median'], 3)} ({num(r[f'{k}_p5'], 3)} to {num(r[f'{k}_p95'], 3)})", pv(r[f"{k}_p2"]), pv(r.get(f"{k}_q_primary"))])
    table(["null", "metric", "BTC", "null median (5-95%)", "p two-sided", "q among primary"], out)
    section("C4 causal")
    out = []
    for scale in ("4h_pct8", "1d_pct16"):
        out.append(line(f"c4|{scale}|n_pivot_lows_at_live_low", f"{scale}: pivot lows at a live low", False))
        out.append(line(f"c4|{scale}|up_impulse_from_live_low", f"{scale}: legal up impulse starts from it"))
        out.append(line(f"c4|{scale}|up_impulse_from_other_pivot_low", f"{scale}: from any other pivot low"))
        out.append(line(f"c4|{scale}|up_impulse_difference", f"{scale}: difference"))
        out.append(line(f"c4|{scale}|next_impulse_up_after_live_low", f"{scale}: next completed legal impulse is up"))
        out.append(line(f"c4|{scale}|share_up_among_all_impulses", f"{scale}: share up among all legal impulses"))
    out.append(line("c4|barrier_2r_from_live_low|n", "2R barrier: n", False))
    out.append(line("c4|barrier_2r_from_live_low|win_rate", "2R barrier from confirmation close: win rate (driftless walk 33%)"))
    for d in (30, 60, 90):
        out.append(line(f"c4|forward_{d}d_mean_log_return", f"forward {d}d mean log return", False))
        out.append(line(f"c4|forward_{d}d_share_positive", f"forward {d}d share positive"))
    table(head, out)
    section("C5 confluence")
    out = []
    for scale in ("4h_pct8", "1d_pct16"):
        out.append(line(f"c5|{scale}|n_window_open", f"{scale}: n window open", False))
        out.append(line(f"c5|{scale}|n_window_closed", f"{scale}: n window closed", False))
        out.append(line(f"c5|{scale}|reaches_start_of_last_leg|window_open", f"{scale}: reaches start of last leg, window open"))
        out.append(line(f"c5|{scale}|reaches_start_of_last_leg|window_closed", f"{scale}: same, window closed"))
        out.append(line(f"c5|{scale}|difference_open_minus_closed", f"{scale}: difference"))
    table(head, out)
    section("C6 rhythm")
    table(head, [line("c6|power_share_168_294d", "share of return power at 168-294 d"), line("c6|power_ratio_to_neighbours", "power against neighbouring periods", False)])
    pos = {r["key"]: r for r in load("c_positions.csv")}
    section("C1 and C2 histograms, by 0.1 of the cycle")
    out = []
    for key in ("top_pos|hind", "top_pos|live", "phase_hi|hind|4h_pct8", "phase_lo|hind|4h_pct8", "phase_hi|hind|1d_pct16", "phase_lo|hind|1d_pct16", "phase_hi|live|4h_pct8", "phase_lo|live|4h_pct8"):
        r = pos.get(key)
        if not r:
            continue
        for src in ("btc", "shuffle", "trendflip"):
            out.append([key, f"{src} (n {r['n_btc'] if src == 'btc' else r[f'{src}_n']})"] + [f"{fl(r[f'{src}_{i}']) * 100:.0f}" for i in range(10)])
    table(["series", "source", "0.0", "0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9"], out)
    cyc = load("c_cycles_btc.csv")
    if cyc:
        section("BTC weekly cycles, hindsight")
        table(["start", "end", "days", "top", "top position", "translation", "failed"], [[r["start"], r["end"], r["length"], r["top"], num(r["top_pos"]), r["translation"], r["failed"]] for r in cyc])
    lows = load("c_lows_btc.csv")
    if lows:
        section("BTC weekly lows, days to the nearest legal down-structure end (negative = before the low)")
        keys = [k for k in lows[0] if k.startswith("nearest")]
        table(["low", "price"] + [k.replace("nearest_down_", "") for k in keys], [[r["low"], f"{fl(r['price']):,.0f}"] + [r.get(k, "") for k in keys] for r in lows])
    wd = load("c_weekday.csv")
    if wd:
        section("C7 pivots by weekday")
        table(["scale", "pivot", "n", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "p shuffle", "p signflip"],
              [[r["scale"], r["pivot"], r["n"]] + [pct(r[f"d{d}"]) for d in range(7)] + [pv(r["shuffle_p"]), pv(r["signflip_p"])] for r in wd])


def followups() -> None:
    rows = load("c2_midphase.csv")
    if rows:
        idx = {r["metric"]: r for r in rows}
        section("C5b up-structures by causal cycle phase: share at 0.4-0.6 of the expected length, and does the top hold there")
        out = []
        for scale in ("4h_pct8", "1d_pct16", "4h_atr4", "1d_atr2"):
            for struct in ("impulse", "abc"):
                key = f"{scale}|{struct}"
                r = idx.get(f"{key}|share_mid")
                if not r:
                    continue
                d_ = idx.get(f"{key}|difference")
                out.append([key, f"{int(fl(idx[f'{key}|n_mid']['btc']))} / {int(fl(idx[f'{key}|n_other']['btc']))}", pct(r["btc"]),
                            f"{pct(r['trendflip_median'])} ({pct(r['trendflip_p5'], 0)} to {pct(r['trendflip_p95'], 0)}) p {pv(r['trendflip_p2'])}", f"{pct(r['signflip_median'])} p {pv(r['signflip_p2'])}",
                            pct(idx.get(f"{key}|top_holds_mid", {}).get("btc")), pct(idx.get(f"{key}|top_holds_other", {}).get("btc")),
                            f"{fl(d_['btc']) * 100:+.1f} pp" if d_ else "n/a", f"{fl(d_['trendflip_median']) * 100:+.1f} pp, p {pv(d_['trendflip_p2'])}" if d_ else "n/a",
                            f"{fl(idx[f'{key}|difference_minus_law']['btc']) * 100:+.1f} pp, p {pv(idx[f'{key}|difference_minus_law']['trendflip_p2'])}" if f"{key}|difference_minus_law" in idx else "n/a"])
        table(["scale and structure", "n mid / other", "share mid", "trend (5-95%)", "signflip", "top holds, mid", "elsewhere", "difference", "trend null", "after barrier law"], out)
    rows = load("c2_spectrum.csv")
    if rows:
        section("C6 spectrum: mean return power per band against the mean over periods of 30-1000 days")
        out = []
        for span in ("all", "2013-2017", "2018-2021", "2022-2026"):
            for band in ("30-60", "60-100", "100-168", "168-294", "294-500", "500-1000"):
                for r in rows:
                    if r["metric"] == f"{span}|{band}":
                        out.append([span, band, num(r["btc"]), f"{num(r['signflip_median'])} ({num(r['signflip_p5'])} to {num(r['signflip_p95'])}) p {pv(r['signflip_p2'])}",
                                    f"{num(r['block_median'])} ({num(r['block_p5'])} to {num(r['block_p95'])}) p {pv(r['block_p2'])}", f"{num(r['shuffle_median'])} p {pv(r['shuffle_p2'])}"])
        table(["span", "period, days", "BTC", "signflip", "block", "shuffle"], out)


def d() -> None:
    rows = load("d_metrics.csv")
    if not rows:
        return
    section("D TDI shark")
    keys = ("n", "share_w3_outside", "share_w5_inside", "share_div", "share_shark", "share_shark_z6070", "shark|n", "shark|hits_p4", "no_shark|hits_p4", "shark|barrier_law", "no_shark|barrier_law",
            "shark|hits_minus_law", "no_shark|hits_minus_law", "shark_minus_no_shark|hits_p4", "div_minus_no_div|hits_p4", "shark|fwd_60", "no_shark|fwd_60", "shark_minus_no_shark|fwd_60")
    out = []
    for scale in ("4h_pct4", "4h_atr2", "4h_pct8"):
        for key in keys:
            for r in rows:
                if r["scale"] == scale and r["metric"] == key:
                    digits = 3
                    cells = [scale, key, num(r["btc"], digits)]
                    if r.get("btc_lo"):
                        cells[-1] += f" ({num(r['btc_lo'], 2)} to {num(r['btc_hi'], 2)})"
                    for k in ("shuffle", "signflip", "trendflip"):
                        cells.append(f"{num(r[f'{k}_median'], digits)} ({num(r[f'{k}_p5'], digits)} to {num(r[f'{k}_p95'], digits)}) p {pv(r[f'{k}_p2'])}")
                    out.append(cells)
    table(["scale", "metric", "BTC", "shuffle", "signflip", "trend +-60d"], out)
    section("D multiple tests")
    out = []
    for k in KINDS:
        out.append([k, len(rows), sum(fl(r[f"{k}_p2"]) < 0.05 for r in rows), f"{0.05 * len(rows):.0f}", sum(fl(r[f"{k}_q"]) < 0.05 for r in rows)])
    table(["null", "rows", "p < 0.05", "expected", "q < 0.05"], out)


# Compact tables for 02-empirical.md. Each lands in doc_tables.json under its name, and build_doc.py pastes it into the report.
DOC: dict[str, str] = {}


def _t(head: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def _rng(r: dict, k: str, f=pct) -> str:
    return f"{f(r[f'{k}_median'])} ({f(r[f'{k}_p5'])} to {f(r[f'{k}_p95'])})"


def doc_tables() -> None:
    facts_ = json.loads((E / "a4_facts.json").read_text())
    rows = []
    for tf, lag in (("1h", 1), ("1h", 24), ("4h", 1), ("4h", 42), ("1d", 1), ("1d", 30)):
        d = facts_["f1"][tf]
        i = d["lags"].index(lag)
        rows.append([tf, lag, f"{d['return_acf'][i]:+.3f}", f"{d['shuffle_band_5'][i]:+.3f} to {d['shuffle_band_95'][i]:+.3f}", f"{d['abs_return_acf'][i]:+.3f}"])
    DOC["acf"] = _t(["bars", "lag", "return autocorrelation", "shuffled bars, 5-95%", "absolute return autocorrelation"], rows)
    DOC["acf_era"] = _t(["bars", "lag-1 return autocorrelation, 2014-2017", "2018-2021", "2022-2026"],
                        [[tf, f"{d['return_acf_lag1_2014-2017']:+.3f}", f"{d['return_acf_lag1_2018-2021']:+.3f}", f"{d['return_acf_lag1_2022-2026']:+.3f}"] for tf, d in facts_["f1"].items()])
    DOC["vol"] = _t(["bars", "out-of-sample R2, 2022-2026", "test bars"], [[tf, f"{d['r2_oos_2022_2026']:.2f}", f"{d['n_test']:,}"] for tf, d in facts_["f2"].items()])
    qs = [k for k in facts_["f3"] if k.isdigit()]
    DOC["vr"] = _t(["horizon, days", "variance ratio", "shuffled days, 5-95%", "p high", "2014-2017", "2018-2021", "2022-2026"],
                   [[q, f"{facts_['f3'][q]['vr']:.2f}", f"{facts_['f3'][q]['shuffle_p5']:.2f} to {facts_['f3'][q]['shuffle_p95']:.2f}", pv(facts_["f3"][q]["p_high"]),
                     f"{facts_['f3']['2014-2017'][q]:.2f}", f"{facts_['f3']['2018-2021'][q]:.2f}", f"{facts_['f3']['2022-2026'][q]:.2f}"] for q in qs])
    DOC["momentum"] = _t(["N days", "same sign", "95% CI", "n", "share of up windows", "base if independent"],
                         [[n, pct(d["same_sign"]), f"{pct(d['lo'], 0)} to {pct(d['hi'], 0)}", d["n"], pct(d["up_share"]), pct(d["independent_base"])] for n, d in facts_["f4"].items()])
    DOC["legs"] = _t(["scale", "up / down legs", "median up: size, days", "median down: size, days", "down speed / up speed", "signflip, 5-95%", "trend +-60d, 5-95%"],
                     [[r["scale"], f"{int(r['up_legs']):,} / {int(r['down_legs']):,}", f"{pct(r['median_up_size'])}, {num(r['median_up_days'])}", f"{pct(r['median_down_size'])}, {num(r['median_down_days'])}",
                       num(r["down_over_up_speed"]), f"{num(r['down_over_up_speed|signflip_p5'])} to {num(r['down_over_up_speed|signflip_p95'])}", f"{num(r['down_over_up_speed|trendflip_p5'])} to {num(r['down_over_up_speed|trendflip_p95'])}"] for r in load("a4_legs.csv")])

    census_rows = [r for r in load("census_btc.csv") if r["venue"] == "bitstamp_btcusd"]
    DOC["census"] = _t(["scale", "legs", "legs a year", "median leg, days", "median leg size", "legal 5-waves (up / down)", "truncated", "diagonal cand.", "independent legal"],
                       [[r["scale"], f"{int(r['legs']):,}", f"{fl(r['legs_per_year']):,.0f}", num(r["median_leg_days"]), pct(r["median_leg_size"]), f"{int(r['legal']):,} ({r['legal_up']} / {r['legal_down']})", r["truncated"], r["diagonal"], f"{int(r['independent']):,}"] for r in census_rows])
    tfs: dict = {}
    for r in census_rows:
        d = tfs.setdefault(r["tf"], {"windows": 0, "R1": 0, "R2": 0, "R3": 0, "R4": 0, "legal": 0, "truncated": 0})
        d["windows"] += int(r["windows"])
        for k in ("R1", "R2", "R3", "R4"):
            d[k] += int(r[f"killed_{k}"])
        d["legal"] += int(r["legal"])
        d["truncated"] += int(r["truncated"])
    DOC["kills"] = _t(["bars", "six-pivot windows", "R1 W2 beyond start", "R2 W3 not beyond W1", "R3 W3 shortest", "R4 W4 into W1", "truncated", "legal"],
                      [[tf, f"{d['windows']:,}", pct(d["R1"] / d["windows"]), pct(d["R2"] / d["windows"]), pct(d["R3"] / d["windows"]), pct(d["R4"] / d["windows"]), pct(d["truncated"] / d["windows"]), pct(d["legal"] / d["windows"])] for tf, d in tfs.items()])

    a2 = load("a2_legal.csv")
    idx = {(r["venue"], r["null"], r["trend_days"], r["scale"]): r for r in a2}
    fams = (("shuffle", ""), ("signflip", ""), ("trendflip", "30"), ("trendflip", "60"), ("trendflip", "120"))
    DOC["a2_pools"] = _t(["pool of six scales", "legal / windows", "BTC", "shuffle", "signflip", "trend +-30d", "trend +-60d", "trend +-120d"],
                         [[s.replace("pool_", ""), f"{int(fl(idx[('bitstamp_btcusd', 'shuffle', '', s)]['legal'])):,} / {int(fl(idx[('bitstamp_btcusd', 'shuffle', '', s)]['windows'])):,}", pct(idx[("bitstamp_btcusd", "shuffle", "", s)]["btc"], 2)]
                          + [f"{pct(idx[('bitstamp_btcusd', k, d, s)]['null_median'], 2)} (z {num(idx[('bitstamp_btcusd', k, d, s)]['z'], 1)})" for k, d in fams] for s in ("pool_15m", "pool_1h", "pool_4h", "pool_1d")])
    fw = load("a2_familywise.csv")
    out = []
    for k, d in fams:
        hits = [r for r in fw if r["venue"] == "bitstamp_btcusd" and r["null"] == k and r["trend_days"] == d and fl(r["familywise_p"]) < 0.05]
        out.append([("trend +-" + d + "d") if d else k, ", ".join(f"{r['scale']} (z {num(r['z'], 1)})" for r in hits) or "none"])
    DOC["a2_fw"] = _t(["null", "scales with family-wise p < 0.05 (of 24)"], out)
    DOC["a2_venues"] = _t(["venue", "pool", "legal / windows", "BTC", "signflip", "trend +-60d"],
                          [[v.split("_")[0], s.replace("pool_", ""), f"{int(fl(idx[(v, 'signflip', '', s)]['legal'])):,} / {int(fl(idx[(v, 'signflip', '', s)]['windows'])):,}", pct(idx[(v, "signflip", "", s)]["btc"], 2),
                            f"{pct(idx[(v, 'signflip', '', s)]['null_median'], 2)} (z {num(idx[(v, 'signflip', '', s)]['z'], 1)})", f"{pct(idx[(v, 'trendflip', '60', s)]['null_median'], 2)} (z {num(idx[(v, 'trendflip', '60', s)]['z'], 1)})"]
                           for v in ("binance_btcusdt", "bybit_btcusdt_perp") for s in ("pool_15m", "pool_1h", "pool_4h", "pool_1d")])
    eras = load("census_eras.csv")
    out = []
    for era in ("2014-2017", "2018-2021", "2022-2026"):
        chosen = [r for r in eras if r["null"] == "trendflip" and r["era"] == era]
        out.append([era, sum(fl(r["p_high"]) < 0.05 for r in chosen), f"{sum(int(r['legal']) for r in chosen):,} / {sum(int(r['windows']) for r in chosen):,}"])
    DOC["a2_era_counts"] = _t(["era", "scales with BTC above trend +-60d at p < 0.05 (of 24, about 1.2 by chance)", "legal / windows, all scales"], out)
    DOC["a2_era_cells"] = _t(["scale", "era", "legal / windows", "BTC", "trend +-60d (5-95%)", "p"],
                             [[r["scale"], r["era"], f"{r['legal']} / {r['windows']}", pct(r["btc"], 2), f"{pct(r['null_median'], 2)} ({pct(r['null_p5'], 2)} to {pct(r['null_p95'], 2)})", pv(r["p_high"])]
                              for r in eras if r["null"] == "trendflip" and r["scale"] in ("1h_atr2", "4h_atr2")])

    a3 = load("a3_stages.csv")
    a3f = load("a3_familywise.csv")
    fwi = {(r["null"], r["trend_days"], r["scale"], r["stage"]): r for r in a3f}
    ai = {(r["null"], r["trend_days"], r["scale"], r["stage"], r["slice"]): r for r in a3}
    stages = (("s1_w2_holds", "W2 holds above the start of W1"), ("s2_w3_beyond_w1", "then W3 goes beyond W1"), ("s3_w4_clear_of_w1", "then W4 stays out of W1"), ("s4_w5_completes", "then W5 goes beyond W3"), ("s5_a_reaches_w4", "after a legal 5: A reaches end of W4"))
    out = []
    for st, label in stages:
        for scale in LADDER:
            b = ai[("signflip", "", scale, st, "all")]
            line = [label, scale, f"{int(fl(b['n'])):,}", f"{pct(b['btc'])} ({pct(b['btc_lo'], 0)} to {pct(b['btc_hi'], 0)})"]
            for k, d in (("signflip", ""), ("trendflip", "60")):
                r = ai[(k, d, scale, st, "all")]
                f = fwi[(k, d, scale, st)]
                line.append(pct(r["null_median"]) + (" **" if fl(f["fw_p_high"]) < 0.05 or fl(f["fw_p_low"]) < 0.05 else ""))
            out.append(line)
    DOC["stages"] = _t(["stage", "scale", "n", "BTC (95% CI)", "signflip", "trend +-60d"], out)
    out = []
    for st, label in stages:
        line = [label]
        for k, d in (("signflip", ""), ("trendflip", "30"), ("trendflip", "60"), ("trendflip", "120")):
            hi = sum(1 for r in a3f if r["null"] == k and r["trend_days"] == d and r["stage"] == st and fl(r["fw_p_high"]) < 0.05)
            lo = sum(1 for r in a3f if r["null"] == k and r["trend_days"] == d and r["stage"] == st and fl(r["fw_p_low"]) < 0.05)
            line.append(f"{hi} / {lo}")
        out.append(line)
    DOC["stage_fw"] = _t(["stage", "signflip", "trend +-30d", "trend +-60d", "trend +-120d"], out)
    out = []
    for scale in ("4h_pct8", "1d_pct16", "4h_atr2"):
        for sl in ("2014-2017", "2018-2021", "2022-2026"):
            r = ai[("trendflip", "60", scale, "s3_w4_clear_of_w1", sl)]
            out.append([scale, sl, f"{int(fl(r['n'])):,}", pct(r["btc"]), f"{pct(r['null_median'])} ({pct(r['null_p5'], 0)} to {pct(r['null_p95'], 0)})", pv(min(1.0, min(fl(r["p_high"]), fl(r["p_low"])) * 2))])
    DOC["s3_eras"] = _t(["scale", "era", "n", "BTC", "trend +-60d (5-95%)", "p two-sided"], out)

    amb = load("a5_ambiguity.csv")
    DOC["ambiguity"] = _t(["fine scale", "pivots", "share with a legal count", "shuffle", "trend +-60d", "median counts when any", "shuffle", "trend +-60d", "distinct origins when any", "trend +-60d"],
                          [[r["scale"], f"{int(r['pivots']):,}", pct(r["share_with_legal_count"]), pct(r["share_with_legal_count|shuffle_median"]), pct(r["share_with_legal_count|trendflip_median"]),
                            num(r["median_counts_when_any"], 0), num(r["median_counts_when_any|shuffle_median"], 0), num(r["median_counts_when_any|trendflip_median"], 0),
                            num(r["mean_distinct_starts_when_any"], 1), num(r["mean_distinct_starts_when_any|trendflip_median"], 1)] for r in amb])
    sub = load("a6_subwaves.csv")
    si = {(r["coarse"], r["fine"], r["null"], r["metric"]): r for r in sub}
    pairs = []
    for r in sub:
        if (r["coarse"], r["fine"]) not in pairs:
            pairs.append((r["coarse"], r["fine"]))
    half = [p_ for p_ in pairs if p_ in (("15m_pct4", "15m_pct2"), ("1h_pct8", "1h_pct4"), ("4h_pct16", "4h_pct8"), ("1d_pct16", "1d_pct8"))]
    DOC["sub_counts"] = _t(["coarse", "fine", "1 (BTC / null)", "3", "5", "7", "9 or more"],
                           [[a, b] + [f"{pct(si[(a, b, 'trendflip', m)]['btc'])} / {pct(si[(a, b, 'trendflip', m)]['null_median'])}" for m in ("share_1", "share_3", "share_5", "share_7", "share_9plus")] for a, b in half])
    DOC["sub_form"] = _t(["coarse", "fine", "legal impulses", "W3 subdivides into 5 (BTC vs null)", "W2 and W4 in 1 or 3", "full 5-3-5-3-5 form"],
                         [[a, b, f"{fl(si[(a, b, 'trendflip', 'legal_n')]['btc']):.0f}"] + [f"{pct(si[(a, b, 'trendflip', m)]['btc'])} vs {pct(si[(a, b, 'trendflip', m)]['null_median'])} (p {pv(si[(a, b, 'trendflip', m)]['p_two'])})" for m in ("w3_is_5", "w2_is_1_or_3", "full_form")] for a, b in half])

    sm = json.loads((E / "b1_summary.json").read_text())
    DOC["omnibus"] = _t(["null", "paths", "tests at z >= 1.645: BTC", "same count on null paths, median (5-95%)", "p", "family-wise hits", "of which at level 1.0 on 15m"],
                        [[k, sm["paths"][k], sm["omnibus"][k]["tests_z_ge_1645_btc"], f"{sm['omnibus'][k]['null_median']:.0f} ({sm['omnibus'][k]['null_p5']:.0f} to {sm['omnibus'][k]['null_p95']:.0f})", pv(sm["omnibus"][k]["p_high"]), sm["omnibus"][k]["familywise_hits_btc"],
                          sum(1 for r in load("b1_tests.csv") if fl(r[f"{k}_fw"]) < 0.05 and fl(r["level"]) == 1.0 and r["tf"] == "15m")] for k in KINDS])
    levels = load("b1_levels.csv")
    for t, name in (("ret", "levels_ret"), ("ext", "levels_ext")):
        chosen = [r for r in levels if r["type"] == t and r["price"] == "log" and fl(r["width"]) == 0.04]
        DOC[name] = _t(["level", "BTC mean excess", "signflip mean excess", "mean z, signflip (p)", "mean z, trend +-60d (p)"],
                       [[r["level"], num(r["excess_btc_mean"], 3), num(r["signflip_excess_null_mean"], 3), f"{num(r['signflip_mean_z'])} ({pv(r['signflip_p'])})", f"{num(r['trendflip_mean_z'])} ({pv(r['trendflip_p'])})"] for r in chosen])
    tests = load("b1_tests.csv")
    out = []
    for scale in ("15m_pct2", "1h_pct4", "4h_pct8", "1d_pct16"):
        for w in ("0.015", "0.04"):
            chosen = [r for r in tests if r["scale"] == scale and r["type"] == "ret" and r["price"] == "log" and fl(r["width"]) == fl(w) and fl(r["level"]) in (0.382, 0.5, 0.618, 0.786, 1.0, 1.618)]
            sd = sum(fl(r["signflip_sd"]) for r in chosen) / len(chosen)
            out.append([scale, w, num(sd), f"+{sd * 2.5 * 100:.0f}%"])
    DOC["power"] = _t(["scale", "band half-width", "sd of the excess on null paths", "local bump needed for z = 2.5"], out)
    density = load("b1_density.csv")
    for scale, name in (("1h_pct4", "density_1h"), ("4h_pct8", "density_4h")):
        chosen = [r for r in density if r["scale"] == scale and r["type"] == "ret"]
        sg = [r for r in chosen if r["null"] == "signflip"]
        tr = {(r["from"], r["to"]): r for r in chosen if r["null"] == "trendflip"}
        DOC[name] = _t(["ratio", "BTC", "random-walk law", "signflip (5-95%)", "trend +-60d"],
                       [[f"{num(r['from'], 3)} to {num(r['to'], 3) if fl(r['to']) < 1e6 else 'up'}", pct(r["btc"]), pct(r["law"]), f"{pct(r['null_median'])} ({pct(r['null_p5'])} to {pct(r['null_p95'])})", pct(tr[(r["from"], r["to"])]["null_median"])] for r in sg])
    shape = load("b1_shape.csv")
    DOC["fingerprint"] = _t(["null", "histograms", "shape differs, q < 0.05", "12-band fit up to 2021 beats the null on 2022-2026, q < 0.05", "gain above zero"],
                            [[k, len(shape), sum(fl(r[f"{k}_ks_p_q"]) < 0.05 for r in shape), sum(fl(r[f"{k}_coarse_gain_p_q"]) < 0.05 for r in shape), sum(fl(r[f"{k}_coarse_gain"]) > 0 for r in shape)] for k in KINDS])
    v = load("b1c_levels.csv")
    out = []
    for level in ("0.236", "0.382", "0.5", "0.618", "0.786", "1.0", "1.272", "1.618", "2.0", "2.236", "2.618"):
        line = [level]
        for venue in ("bybit_btcusdt_perp", "binance_btcusdt"):
            for r in v:
                if r["venue"] == venue and r["type"] == "ret" and fl(r["width"]) == 0.04 and fl(r["level"]) == fl(level):
                    line.append(f"{num(r['trendflip_mean_z'])} ({pv(r['trendflip_p'])})")
        out.append(line)
    DOC["venues_levels"] = _t(["level", "Bybit perp, mean z (p)", "Binance spot, mean z (p)"], out)
    top = load("b1d_top.csv")
    DOC["scan_top"] = _t(["ratio", "price", "rank", "level", "standardised z", "family-wise p for the scan"],
                         [[r["type"], r["price"], r["rank"], num(r["level"], 3), num(r["standardised"]), pv(r["scan_familywise_p"])] for r in top if r["null"] == "trendflip" and int(r["rank"]) <= 3])
    rep = load("b1d_replicate.csv")
    DOC["replicate"] = _t(["venue", "period", "in band", "shoulders", "excess", "trend +-60d (5-95%)", "p high"],
                          [[r["venue"].split("_")[0], ("2020-2021" if r["venue"].startswith("bybit") and r["period"] == "2018-2021" else "2013-2017" if r["period"] == "before_2018" else r["period"]), r["in_band"], r["shoulders"], num(r["excess"]), f"{num(r['null_median'])} ({num(r['null_p5'])} to {num(r['null_p95'])})", pv(r["p_high"])]
                           for r in rep if r["null"] == "trendflip" and r["in_band"] != "0"])

    bar = load("b1b_barrier.csv")

    def step(venue: str, period: str, tf: str) -> str:
        ch = [r for r in bar if r["venue"] == venue and r["period"] == period and r["null"] == "trendflip" and r["scale"].startswith(tf + "_") and fl(r["asymmetry"]) == fl(r["asymmetry"])]
        if not ch:
            return "n/a"
        mean = sum(fl(r["asymmetry"]) for r in ch) / len(ch) * 100
        above = sum(fl(r["asymmetry"]) > fl(r["asymmetry_p95"]) for r in ch)
        return f"{mean:+.1f} ({above}/{len(ch)})"

    cols = (("bitstamp_btcusd", "2014-2017"), ("bitstamp_btcusd", "2018-2021"), ("bitstamp_btcusd", "2022-2026"), ("binance_btcusdt", "2018-2021"), ("binance_btcusdt", "2022-2026"), ("bybit_btcusdt_perp", "2020-2021"), ("bybit_btcusdt_perp", "2022-2026"))
    null_mean = sum(fl(r["asymmetry_median"]) for r in bar if r["null"] == "trendflip" and fl(r["asymmetry_median"]) == fl(r["asymmetry_median"])) / max(1, sum(1 for r in bar if r["null"] == "trendflip" and fl(r["asymmetry_median"]) == fl(r["asymmetry_median"])))
    DOC["step"] = _t(["bars", "Bitstamp 2014-17", "2018-21", "2022-26", "Binance 2018-21", "2022-26", "Bybit 2020-21", "2022-26"], [[tf] + [step(a, b, tf) for a, b in cols] for tf in ("15m", "1h", "4h", "1d")])
    DOC["step_null"] = f"{null_mean * 100:+.1f}"
    ties_idx = {(r["venue"], r["scale"]): r for r in bar if r["period"] == "all" and r["null"] == "trendflip"}
    out = []
    for venue, period in (("bitstamp_btcusd", "2014-2017"), ("bitstamp_btcusd", "2018-2021"), ("bitstamp_btcusd", "2022-2026"), ("binance_btcusdt", "2018-2021"), ("binance_btcusdt", "2022-2026"), ("bybit_btcusdt_perp", "2020-2021"), ("bybit_btcusdt_perp", "2022-2026")):
        for r in bar:
            if r["venue"] == venue and r["period"] == period and r["scale"] == "15m_pct2" and r["null"] == "trendflip":
                out.append([venue.split("_")[0], period, f"{int(fl(r['n'])):,}", num(r["spike"]), f"{num(r['spike_median'])} ({num(r['spike_p5'])} to {num(r['spike_p95'])})", pct(ties_idx[(venue, "15m_pct2")]["ties_btc"], 2)])
    DOC["spike"] = _t(["venue", "period", "pairs", "excess at exactly 1.0, +-1.5%", "trend +-60d (5-95%)", "exact price ties, whole venue history"], out)
    out = []
    for venue, period in (("bitstamp_btcusd", "2014-2017"), ("bitstamp_btcusd", "2018-2021"), ("bitstamp_btcusd", "2022-2026"), ("bybit_btcusdt_perp", "2022-2026")):
        for scale in ("15m_pct2", "1h_pct4", "4h_pct8"):
            for r in bar:
                if r["venue"] == venue and r["period"] == period and r["scale"] == scale and r["null"] == "trendflip":
                    out.append([venue.split("_")[0], period, scale, f"{int(fl(r['overshoot_n'])):,}", num(r["overshoot_mean"]), f"{num(r['overshoot_mean_median'])} ({num(r['overshoot_mean_p5'])} to {num(r['overshoot_mean_p95'])})", pct(r["share_overshoot_under_025"]), pct(r["share_overshoot_under_025_median"])])
    DOC["overshoot"] = _t(["venue", "period", "scale", "breaks", "mean overshoot, thresholds", "trend +-60d (5-95%)", "share under 0.25", "null"], out)
    fine = load("b1b_fine.csv")
    DOC["fine"] = _t(["ln(r)", "15m_pct2: BTC / null", "1h_pct4", "4h_pct8"],
                     [[f"{fl(a['from']):+.3f} to {fl(a['to']):+.3f}"] + [f"{pct(r['btc'], 2)} / {pct(r['null_median'], 2)}" for r in [next(x for x in fine if x["scale"] == sc and x["null"] == "trendflip" and x["from"] == a["from"]) for sc in ("15m_pct2", "1h_pct4", "4h_pct8")]]
                      for a in fine if a["scale"] == "15m_pct2" and a["null"] == "trendflip"])

    b2w = load("b2_windows.csv")
    wi = {(r["group"], r["key"], r["window"], r["slice"], r["price"]): r for r in b2w}

    def claim(key: str, window: str, label: str) -> list[str]:
        a = wi[("ladder_pct", key, window, "all", "log")]
        line = [label, pct(a["btc"]), f"{pct(a['trendflip_median'])} ({pct(a['trendflip_p5'], 0)} to {pct(a['trendflip_p95'], 0)})", pv(min(1.0, 2 * min(fl(a["trendflip_p_high"]), fl(a["trendflip_p_low"]))))]
        for g in ("pool_15m", "pool_1h", "pool_4h", "pool_1d"):
            r = wi[(g, key, window, "all", "log")]
            line.append(f"{pct(r['btc'])} / {pct(r['trendflip_median'])}")
        return line

    head = ["rulebook claim", "BTC, ladder", "trend +-60d (5-95%)", "p", "15m BTC / null", "1h", "4h", "1d"]
    DOC["b2_claims"] = _t(head, [claim("w2", "0.5-0.618", "W2 ends at 0.5-0.618"), claim("w2", "near 0.382", "W2 near 0.382"), claim("w2", "near 0.786", "W2 near 0.786"), claim("w2", "under 0.382", "W2 shallower than 0.382"), claim("w2", "over 0.618", "W2 deeper than 0.618"),
                                 claim("w4", "0.236-0.382", "W4 ends at 0.236-0.382 of W3"), claim("w4", "under 0.5", "W4 under 0.5 of W3"), claim("w3", "near 1.618", "W3 near 1.618, pull 0-1-2"), claim("w3", "near 2.618", "W3 near 2.618"), claim("w3", "over 2.618", "W3 beyond 2.618"),
                                 claim("w5_012", "near 2.236", "W5 near 2.236, pull 0-1-2"), claim("w5_012", "near 3.236", "W5 near 3.236"), claim("w5_014", "near 1.0", "W5 near 1.0, pull 0-1-4"), claim("w5_014", "near 0.618", "W5 near 0.618")])
    DOC["b3_claims"] = _t(head, [claim("t2_t1", "not outlasting W1", "W2 does not outlast W1"), claim("t2_t1", "at least 0.25 of W1", "W2 takes at least 0.25 of W1"), claim("t2_t1", "at least 0.33 of W1", "W2 takes at least 0.33 of W1"),
                                 claim("t4_t3", "not outlasting W3", "W4 does not outlast W3"), claim("t4_t3", "at least 0.25 of W3", "W4 takes at least 0.25 of W3"), claim("t4_t2", "near W2 (0.8-1.25)", "W4 takes about as long as W2 (0.8-1.25)"),
                                 claim("t3_t1", "near 1.0", "W3 time near 1.0 of W1"), claim("t3_t1", "near 1.618", "W3 time near 1.618"), claim("t3_t1", "near 2.236", "W3 time near 2.236"), claim("t5_t1", "near 1.0", "W5 time near 1.0 of W1"), claim("t5_t1", "near 0.618", "W5 time near 0.618")])
    out = []
    for key, window, label in (("w2", "0.5-0.618", "W2 at 0.5-0.618"), ("w2", "under 0.382", "W2 under 0.382"), ("w4", "0.236-0.382", "W4 at 0.236-0.382"), ("w3", "near 1.618", "W3 near 1.618"), ("w3", "near 2.618", "W3 near 2.618"), ("w5_012", "near 2.236", "W5 near 2.236"), ("w5_014", "near 1.0", "W5 near 1.0")):
        line = [label]
        for era in ("2014-2017", "2018-2021", "2022-2026"):
            r = wi[("ladder_pct", key, window, era, "log")]
            line.append(f"{pct(r['btc'])} / {pct(r['trendflip_median'])} ({pct(r['trendflip_p5'], 0)} to {pct(r['trendflip_p95'], 0)})")
        out.append(line)
    n_e = [wi[("ladder_pct", "w2", "0.5-0.618", e, "log")]["n"] for e in ("2014-2017", "2018-2021", "2022-2026")]
    DOC["b2_eras"] = _t(["window", f"2014-2017 (n {n_e[0]}), BTC / null (5-95%)", f"2018-2021 (n {n_e[1]})", f"2022-2026 (n {n_e[2]})"], out)
    der = {r["group"]: r for r in load("b2_derived.csv")}
    DOC["b2_longest"] = _t(["pool", "n", "W1 longest, BTC / null", "W3 longest", "W5 longest", "W2 under .45 after a strong uptrend, BTC / null", "W2 under .45 otherwise"],
                           [[g, der[g]["n"], f"{pct(der[g]['share_w1_longest'])} / {pct(der[g]['share_w1_longest|trendflip_median'])}", f"{pct(der[g]['share_w3_longest'])} / {pct(der[g]['share_w3_longest|trendflip_median'])}", f"{pct(der[g]['share_w5_longest'])} / {pct(der[g]['share_w5_longest|trendflip_median'])}",
                             f"{pct(der[g]['shallow_w2_strong_uptrend'])} / {pct(der[g]['shallow_w2_strong_uptrend|trendflip_median'])} (n {der[g]['n_strong']})", f"{pct(der[g]['shallow_w2_other'])} / {pct(der[g]['shallow_w2_other|trendflip_median'])} (n {der[g]['n_other']})"] for g in ("ladder_pct", "pool_15m", "pool_1h", "pool_4h")])
    DOC["b2_addone"] = _t(["pool", "W3 near 1.618, then W5 near 2.236: BTC / null", "W3 near 2.618, then W5 near 3.236: BTC / null"],
                          [[g, f"{pct(der[g]['addone_1618'])} / {pct(der[g]['addone_1618|trendflip_median'])} (n {der[g]['n_addone_1618']})", f"{pct(der[g]['addone_2618'])} / {pct(der[g]['addone_2618|trendflip_median'])} (n {der[g]['n_addone_2618']})"] for g in ("ladder_pct", "pool_15m", "pool_1h", "pool_4h")])
    alt = load("b3_alternation.csv")
    DOC["alternation"] = _t(["bars", "period", "n", "Spearman W2, W4: BTC", "trend +-60d (5-95%)", "p low"],
                            [[r["tf"], r["period"], r["n"], num(r["spearman"]), f"{num(r['null_median'])} ({num(r['null_p5'])} to {num(r['null_p95'])})", pv(r["p_low"])] for r in alt if r["null"] == "trendflip" and r["tf"] in ("15m", "1h", "4h")])
    sh2 = load("b2_shape.csv")
    out = []
    for key, label in (("w2", "W2"), ("w3", "W3"), ("w4", "W4"), ("w5_014", "W5, pull 0-1-4"), ("w5_012", "W5, pull 0-1-2"), ("t2_t1", "time W2/W1"), ("t3_t1", "time W3/W1"), ("t4_t3", "time W4/W3"), ("t5_t1", "time W5/W1")):
        ch = [r for r in sh2 if r["key"] == key]
        out.append([label] + [f"{sum(fl(r[f'{k}_ks_p_q']) < 0.05 for r in ch)} / {sum(fl(r.get(f'{k}_coarse_gain_p_q')) < 0.05 for r in ch)}" for k in ("signflip", "trendflip")])
    DOC["b2_shape"] = _t(["ratio", "signflip: shape differs / fit beats null, of 24 scales, q < 0.05", "trend +-60d"], out)

    cm = {r["metric"]: r for r in load("c_metrics.csv")}

    def cline(metric: str, label: str, as_pct: bool = True) -> list[str]:
        r = cm[metric]
        f = pct if as_pct else num
        return [label, f(r["btc"])] + [f"{f(r[f'{k}_median'])} ({f(r[f'{k}_p5'], 0) if as_pct else f(r[f'{k}_p5'])} to {f(r[f'{k}_p95'], 0) if as_pct else f(r[f'{k}_p95'])}) p {pv(r[f'{k}_p2'])}" for k in ("block", "signflip", "trendflip")]

    ch = ["metric", "BTC", "block", "signflip", "trend +-60d"]
    DOC["c1"] = _t(ch, [cline("c1|hind|share_top_within_0.05_of_mid", "hindsight: top within 0.05 of the middle (uniform 10%)"), cline("c1|hind|share_top_within_0.10_of_mid", "hindsight: within 0.10 (uniform 20%)"), cline("c1|hind|share_top_within_0.15_of_mid", "hindsight: within 0.15 (uniform 30%)"), cline("c1|hind|share_top_left_of_mid", "hindsight: left of the middle"), cline("c1|hind|median_top_pos", "hindsight: median position", False),
                        cline("c1|live|share_top_within_0.05_of_mid", "live: within 0.05"), cline("c1|live|share_top_within_0.10_of_mid", "live: within 0.10"), cline("c1|live|share_top_within_0.15_of_mid", "live: within 0.15"), cline("c1|live|share_top_left_of_mid", "live: left of the middle"), cline("c1|live|median_top_pos", "live: median position", False)])
    pos = {r["key"]: r for r in load("c_positions.csv")}
    out = []
    for key, label in (("top_pos|hind", "hindsight tops"), ("top_pos|live", "live tops")):
        r = pos[key]
        out.append([f"{label}, BTC ({r['n_btc']})"] + [f"{fl(r[f'btc_{i}']) * 100:.0f}" for i in range(10)])
        out.append([f"{label}, shuffled days"] + [f"{fl(r[f'shuffle_{i}']) * 100:.0f}" for i in range(10)])
        out.append([f"{label}, trend +-60d"] + [f"{fl(r[f'trendflip_{i}']) * 100:.0f}" for i in range(10)])
    DOC["c1_hist"] = _t(["percent of cycles, by position", "0.0", "0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9"], out)
    rows = []
    for tag, tl in (("hind", "hindsight"), ("live", "live")):
        for scale in ("4h_pct8", "1d_pct16"):
            rows.append(cline(f"c2|{tag}|{scale}|share_pivot_highs_in_0.40-0.60", f"{tl} {scale}: pivot highs in 0.4-0.6"))
            rows.append(cline(f"c2|{tag}|{scale}|share_pivot_lows_in_0.40-0.60", f"{tl} {scale}: pivot lows in 0.4-0.6"))
            rows.append(cline(f"c2|{tag}|{scale}|biggest_pullback_starts_in_0.40-0.60", f"{tl} {scale}: biggest pullback starts in 0.4-0.6"))
    DOC["c2"] = _t(ch, rows)
    rows = []
    for tag, tl in (("hind", "hindsight"), ("live", "live")):
        for scale in ("4h_pct8", "1d_pct16"):
            for struct, sl in (("impulse", "5-wave"), ("abc", "zigzag")):
                rows.append(cline(f"c3|{tag}|{scale}|{struct}|lows_with_down_end|14d", f"{tl} {scale} {sl}: weekly lows with a down-structure end within 14d"))
                rows.append(cline(f"c3|{tag}|{scale}|{struct}|days_with_down_end|14d", f"{tl} {scale} {sl}: any day with one within 14d"))
                rows.append(cline(f"c3|{tag}|{scale}|{struct}|odds_ratio_low|14d", f"{tl} {scale} {sl}: odds ratio among pivot lows", False))
    DOC["c3_low"] = _t(ch, rows)
    rows = []
    for tag, tl in (("hind", "hindsight"), ("live", "live")):
        for scale in ("4h_pct8", "1d_pct16"):
            for struct, sl in (("impulse", "5-wave"), ("abc", "zigzag")):
                rows.append(cline(f"c3|{tag}|{scale}|{struct}|up_ends_in_mid|0.40-0.60", f"{tl} {scale} {sl}: up-structure ends in 0.4-0.6"))
                rows.append(cline(f"c3|{tag}|{scale}|{struct}|odds_ratio_mid|0.40-0.60", f"{tl} {scale} {sl}: odds ratio among pivot highs", False))
    DOC["c3_mid"] = _t(ch, rows)
    rows = []
    for tag, tl in (("hind", "hindsight"), ("live", "live")):
        rows.append(cline(f"c3|{tag}|any_scale|impulse|lows_with_down_end|14d", f"{tl}: weekly lows with a legal 5-wave down ending within 14d, any of six scales"))
        rows.append(cline(f"c3|{tag}|any_scale|impulse|days_with_down_end|14d", f"{tl}: any day with one"))
        rows.append(cline(f"c3|{tag}|any_scale|both|lows_with_down_end|14d", f"{tl}: weekly lows with a 5-wave or zigzag down ending within 14d"))
        rows.append(cline(f"c3|{tag}|any_scale|both|days_with_down_end|14d", f"{tl}: any day with one"))
    DOC["c3_any"] = _t(ch, rows)
    all_rows = load("c_metrics.csv")
    c3 = [r for r in all_rows if r["metric"].startswith("c3|") and "days_with" not in r["metric"] and "lows_with_up_end" not in r["metric"]]
    prim = [r for r in all_rows if r["primary"] == "True"]
    DOC["c_mult"] = _t(["null", "C3 tests, all settings", "p < 0.05 (33 by chance)", "BTC above / below null", "q < 0.05", "primary rows", "primary, smallest q"],
                       [[k, len(c3), sum(fl(r[f"{k}_p2"]) < 0.05 for r in c3), f"{sum(fl(r[f'{k}_p_high']) < 0.025 for r in c3)} / {sum(fl(r[f'{k}_p_low']) < 0.025 for r in c3)}", sum(fl(r[f"{k}_q_all"]) < 0.05 for r in c3), len(prim), pv(min(fl(r.get(f"{k}_q_primary")) for r in prim))] for k in KINDS])
    rows = []
    for scale in ("4h_pct8", "1d_pct16"):
        rows.append(cline(f"c4|{scale}|up_impulse_from_live_low", f"{scale}: a legal up 5-wave starts from a pivot low at a live weekly low"))
        rows.append(cline(f"c4|{scale}|up_impulse_from_other_pivot_low", f"{scale}: the same from any other pivot low"))
        rows.append(cline(f"c4|{scale}|next_impulse_up_after_live_low", f"{scale}: next completed legal 5-wave after confirmation is up"))
        rows.append(cline(f"c4|{scale}|share_up_among_all_impulses", f"{scale}: share up among all legal 5-waves"))
    rows.append(cline("c4|barrier_2r_from_live_low|win_rate", "2R barrier from the confirmation close (driftless walk 33%)"))
    rows.append(cline("c4|forward_60d_mean_log_return", "forward 60 days, mean log return", False))
    rows.append(cline("c4|forward_60d_share_positive", "forward 60 days, share positive"))
    DOC["c4"] = _t(ch, rows)
    rows = []
    for scale in ("4h_pct8", "1d_pct16"):
        rows.append(cline(f"c5|{scale}|reaches_start_of_last_leg|window_open", f"{scale}: reaches start of last leg, window open (n {int(fl(cm[f'c5|{scale}|n_window_open']['btc']))})"))
        rows.append(cline(f"c5|{scale}|reaches_start_of_last_leg|window_closed", f"{scale}: window closed (n {int(fl(cm[f'c5|{scale}|n_window_closed']['btc']))})"))
        rows.append(cline(f"c5|{scale}|difference_open_minus_closed", f"{scale}: difference"))
    DOC["c5"] = _t(ch, rows)
    mp = {r["metric"]: r for r in load("c2_midphase.csv")}
    rows = []
    for scale in ("4h_pct8", "1d_pct16", "4h_atr4", "1d_atr2"):
        for struct, sl in (("impulse", "5-wave"), ("abc", "zigzag")):
            key = f"{scale}|{struct}"
            r = mp[f"{key}|share_mid"]
            d_ = mp[f"{key}|difference"]
            l_ = mp[f"{key}|difference_minus_law"]
            rows.append([f"{scale} {sl}", f"{int(fl(mp[f'{key}|n_mid']['btc']))} / {int(fl(mp[f'{key}|n_other']['btc']))}", pct(r["btc"]), f"{pct(r['trendflip_median'])} (p {pv(r['trendflip_p2'])})",
                         pct(mp[f"{key}|top_holds_mid"]["btc"]), pct(mp[f"{key}|top_holds_other"]["btc"]), f"{fl(d_['btc']) * 100:+.0f}", f"{fl(d_['trendflip_median']) * 100:+.0f} (p {pv(d_['trendflip_p2'])})", f"{fl(l_['btc']) * 100:+.0f} (p {pv(l_['trendflip_p2'])})"])
    DOC["c5b"] = _t(["scale", "n mid / elsewhere", "share mid", "trend +-60d", "top holds, mid", "top holds, elsewhere", "difference, pp", "trend null, pp", "after barrier law, pp"], rows)
    sp = {r["metric"]: r for r in load("c2_spectrum.csv")}
    rows = []
    for band in ("30-60", "60-100", "100-168", "168-294", "294-500", "500-1000"):
        r = sp[f"all|{band}"]
        rows.append(["all", band, num(r["btc"]), f"{num(r['signflip_median'])} ({num(r['signflip_p5'])} to {num(r['signflip_p95'])}) p {pv(r['signflip_p2'])}", f"{num(r['block_median'])} ({num(r['block_p5'])} to {num(r['block_p95'])}) p {pv(r['block_p2'])}"])
    for span in ("2013-2017", "2018-2021", "2022-2026"):
        r = sp[f"{span}|168-294"]
        rows.append([span, "168-294", num(r["btc"]), f"{num(r['signflip_median'])} ({num(r['signflip_p5'])} to {num(r['signflip_p95'])}) p {pv(r['signflip_p2'])}", f"{num(r['block_median'])} ({num(r['block_p5'])} to {num(r['block_p95'])}) p {pv(r['block_p2'])}"])
    DOC["c6"] = _t(["span", "period, days", "BTC", "signflip", "block"], rows)
    wd = load("c_weekday.csv")
    DOC["c7"] = _t(["scale", "pivot", "n", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "p against signflip"],
                   [[r["scale"], r["pivot"], r["n"]] + [pct(r[f"d{d_}"], 0) for d_ in range(7)] + [pv(r["signflip_p"])] for r in wd])
    dm = load("d_metrics.csv")
    di = {(r["scale"], r["metric"]): r for r in dm}
    rows = []
    for scale in ("4h_pct4", "4h_atr2", "4h_pct8"):
        for key, label in (("n", "legal impulses"), ("share_div", "3-5 divergence"), ("share_shark", "shark"), ("shark|hits_p4", "shark: reaches end of W4 before a new high"), ("no_shark|hits_p4", "no shark: the same"), ("shark_minus_no_shark|hits_p4", "difference"), ("shark|hits_minus_law", "shark, minus barrier law"), ("no_shark|hits_minus_law", "no shark, minus barrier law")):
            r = di[(scale, key)]
            f = (lambda x, k=None: num(x, 0)) if key == "n" else (lambda x, k=None: pct(x))
            rows.append([scale, label, f(r["btc"])] + [f"{f(r[f'{k}_median'])} ({f(r[f'{k}_p5'])} to {f(r[f'{k}_p95'])})" for k in ("signflip", "trendflip")] + [pv(r["trendflip_p2"])])
    DOC["d"] = _t(["scale", "metric", "BTC", "signflip (5-95%)", "trend +-60d (5-95%)", "p trend"], rows)
    DOC["d_mult"] = _t(["null", "rows", "p < 0.05", "q < 0.05"], [[k, len(dm), sum(fl(r[f"{k}_p2"]) < 0.05 for r in dm), sum(fl(r[f"{k}_q"]) < 0.05 for r in dm)] for k in KINDS])
    (E / "doc_tables.json").write_text(json.dumps(DOC, indent=1))
    print(f"doc tables: {len(DOC)}")


if __name__ == "__main__":
    for f_ in (facts, census, legal_excess, stages_table, ambiguity, subwaves, b1, venues, scan, barrier, b2, alternation, c, followups, d):
        f_()
    (E / "tables.md").write_text("\n".join(OUT) + "\n")
    print(f"tables.md: {len(OUT)} lines")
    doc_tables()
