"""Markdown tables of an `evaluate` result, one row per metric: BTC against each null."""
from __future__ import annotations

from .config import LEVELS

SECTIONS = [
    ("Cycle length and timing window", [
        ("hind.n", "cycles, hindsight", "n"),
        ("hind.len_median", "median length, hindsight (d)", "d"),
        ("hind.in_strict", "in window, hindsight (constrained by the DP)", "%"),
        ("hind.in_tol", "in window +-10%, hindsight (constrained)", "%"),
        ("free.n", "gaps between plain swing lows", "n"),
        ("free.in_strict", "in window, plain swing lows (unconstrained)", "%"),
        ("free.in_tol", "in window +-10%, plain swing lows", "%"),
        ("live.n", "cycles, live", "n"),
        ("live.len_median", "median length, live (d)", "d"),
        ("live.in_strict", "in window, live (only a minimum gap)", "%"),
        ("live.in_tol", "in window +-10%, live", "%"),
    ]),
    ("Translation and failure", [
        ("hind.share_lt", "share LT, hindsight", "%"),
        ("hind.share_rt", "share RT, hindsight", "%"),
        ("hind.share_failed", "share failed, hindsight", "%"),
        ("hind.lower_end|LT", "P(end below start | LT), hindsight", "%"),
        ("hind.lower_end|RT", "P(end below start | RT), hindsight", "%"),
        ("hind.lower_next|LT", "P(next low lower | LT), hindsight", "%"),
        ("hind.lower_next|RT", "P(next low lower | RT), hindsight", "%"),
        ("live.lower_end|LT", "P(end below start | LT), live", "%"),
        ("live.lower_end|RT", "P(end below start | RT), live", "%"),
        ("live.lower_next|LT", "P(next low lower | LT), live", "%"),
        ("live.lower_next|RT", "P(next low lower | RT), live", "%"),
        ("mid.lower_end|LT", "P(end below start | top left of the midpoint when the cycle can first end), causal", "%"),
        ("mid.lower_end|notLT", "P(end below start | top not left of it), causal", "%"),
        ("mid.n_LT", "n, top left of the midpoint", "n"),
        ("mid.n_notLT", "n, top not left of it", "n"),
        ("hind.lower_end|failed", "P(end below start | failed), hindsight", "%"),
        ("live.lower_end|failed", "P(end below start | failed), live", "%"),
    ]),
    ("Half-cycle low", [
        ("hind.higher_end|HCL_above", "P(end above start | HCL above start), hindsight", "%"),
        ("hind.higher_end|HCL_below", "P(end above start | HCL below start), hindsight", "%"),
        ("live.higher_end|HCL_above", "P(end above start | HCL above start), live", "%"),
        ("live.higher_end|HCL_below", "P(end above start | HCL below start), live", "%"),
    ]),
    ("Alternation", [
        ("hind.lag1_corr", "lag-1 correlation of lengths, hindsight", "r"),
        ("hind.long_after_short", "P(long | previous short), hindsight", "%"),
        ("hind.long_after_long", "P(long | previous long), hindsight", "%"),
        ("live.lag1_corr", "lag-1 correlation of lengths, live", "r"),
        ("live.long_after_short", "P(long | previous short), live", "%"),
        ("live.long_after_long", "P(long | previous long), live", "%"),
    ]),
    ("Live against hindsight", [
        ("agree.n_log", "lows ever confirmed live", "n"),
        ("agree.revised", "of those, later revised", "%"),
        ("agree.lag_median", "median confirmation lag (d)", "d"),
        ("agree.hind_found_live", "hindsight lows also found live", "%"),
        ("agree.live_in_hind", "standing live lows also in hindsight", "%"),
        ("hold.all_confirmed", "confirmed lows never traded below before the next", "%"),
        ("hold.no_trade_below", "standing lows not traded below before the next", "%"),
        ("hold.no_close_below", "standing lows not closed below before the next", "%"),
    ]),
    ("Prediction box, taken on the first day the cycle can end, scored on the next low", [
        ("zone.n", "boxes scored", "n"),
        ("zone.time_hit", "next low inside the time range", "%"),
        ("zone.price_hit", "next low inside the price range", "%"),
        ("zone.both_hit", "next low inside the box", "%"),
    ]),
]


def _fmt(v, kind: str) -> str:
    if v is None:
        return "n/a"
    if kind == "%":
        return f"{v * 100:.0f}%"
    if kind == "r":
        return f"{v:+.2f}"
    if kind == "n":
        return f"{v:.0f}"
    return f"{v:.0f}"


def _null_cell(s: dict | None, kind: str) -> str:
    if not s:
        return "n/a"
    return f"{_fmt(s['median'], kind)} ({_fmt(s['p5'], kind)} to {_fmt(s['p95'], kind)})"


def _flag(row: dict, kind: str) -> str:
    """Where BTC falls: outside a null's 5-95 percent range is worth a look, nothing more (many rows are compared)."""
    btc = row["btc"]
    if btc is None:
        return ""
    out = []
    for key, tag in (("shuffled", "S"), ("block", "B")):
        s = row.get(key)
        if s and (btc < s["p5"] or btc > s["p95"]):
            out.append(tag + ("+" if btc > s["p95"] else "-"))
    return " ".join(out)


def count_outside(comp: dict) -> dict:
    """How many rate rows of the tables fall outside each null's 5-95 percent range. By chance alone: about 10 percent."""
    out = {"cells": 0, "outside": 0}
    for name in LEVELS:
        for _, rows in SECTIONS:
            for key, _, kind in rows:
                row = comp.get(f"{name}.{key}")
                if row is None or row["btc"] is None or kind == "n":
                    continue
                for tag in ("shuffled", "block"):
                    s = row.get(tag)
                    if s:
                        out["cells"] += 1
                        out["outside"] += row["btc"] < s["p5"] or row["btc"] > s["p95"]
    return out


def render_tables(result: dict) -> str:
    comp = result["comparison"]
    lines = [f"rules {result['rules_version']} ({result['rules_digest']}), as of {result['as_of_day']}, "
             f"null paths: {result['paths']}", ""]
    lines.append(f"4-year: {result['fouryear_null']}")
    lines.append(f"repaint: {result['repaint']}")
    lines.append(f"rows outside the 5-95 range: {count_outside(comp)}")
    for name in LEVELS:
        for title, rows in SECTIONS:
            lines += ["", f"### {name.capitalize()} level: {title}", "",
                      "| metric | BTC | shuffled, median (5-95%) | block, median (5-95%) | outside |", "|---|---|---|---|---|"]
            for key, label, kind in rows:
                row = comp.get(f"{name}.{key}")
                if row is None:
                    continue
                lines.append(f"| {label} | {_fmt(row['btc'], kind)} | {_null_cell(row.get('shuffled'), kind)} | "
                             f"{_null_cell(row.get('block'), kind)} | {_flag(row, kind)} |")
    return "\n".join(lines)
