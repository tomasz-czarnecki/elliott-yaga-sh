"""`ewave-cycles report | export | evaluate`. Reads the bars; never writes anything the collector owns."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from ..ingest.config import data_root
from ..ingest.store import atomic_write
from . import export as export_mod
from .config import load_rules
from .evaluate import compare, path_metrics, repaint_check, run_nulls
from .hindsight import build
from .live import replay
from .series import day_str, load_daily, to_ms
from .tables import render_tables
from .zones import overlaps


def _money(p: float | None) -> str:
    return "n/a" if p is None else f"${p:,.2f}"


def _zone_line(z: dict) -> str:
    box = "no price box" if z["p_lo"] is None else f"{_money(z['p_lo'])} to {_money(z['p_hi'])}"
    head = f"{day_str(z['t_from'])} to {day_str(z['t_to'])}, {box}"
    if z["level"] == "fouryear":
        so_far = z["lowest_so_far"]
        return (f"{head}. From {z['n_bears']} bears and {z['n_gaps']} gaps (a pattern, not a statistic). ATH {day_str(z['ath_ts'])} "
                f"{_money(z['ath_price'])}; lowest so far {day_str(so_far['ts'])} {_money(so_far['price'])} "
                f"(-{so_far['drawdown']:.1%}, {so_far['ath_to_low_days']} days after the ATH)")
    tail = f"; {z['n']} past cycles ({z['source']}), p{z['percentiles'][0]}-p{z['percentiles'][1]}"
    cand = f"; unconfirmed candidate {day_str(z['candidate']['ts'])} {_money(z['candidate']['price'])}" if z["candidate"] else ""
    return (f"{head}. Day {z['elapsed']} since {day_str(z['anchor_ts'])} {_money(z['anchor_price'])}, translation so far "
            f"{z['translation']}, {'failed' if z['failed'] else 'not failed'}, top {day_str(z['top_ts'])} {_money(z['top_price'])}"
            f"{', OVERDUE' if z['overdue'] else ''}{tail}{cand}")


def cmd_report(args) -> int:
    rules = load_rules(args.rules)
    bars = load_daily(rules.series["venue"])
    h = build(bars, rules)
    e = replay(bars, rules)
    print(f"rules {rules.version} ({rules.digest}), {rules.series['venue']}, last complete bar {day_str(bars.ts[-1])}")
    print("\n4-year lows (hindsight):")
    for b in h.bears:
        print(f"  {day_str(bars.ts[b.low_i])} {_money(b.low)}  ATH {day_str(bars.ts[b.ath_i])} {_money(b.ath)}, "
              f"-{b.drawdown:.1%}, ATH to low {b.ath_to_low_days} d")
    since = to_ms(args.since)
    for name in ("weekly", "daily"):
        print(f"\n{name} cycles from {args.since} (hindsight): start, end, days, top pos, translation, failed, status")
        for c in h.cycles[name]:
            if c.start_ts >= since:
                end = "open" if c.end_ts is None else f"{day_str(c.end_ts)} {_money(c.end_price)}"
                days = c.elapsed if c.length is None else c.length
                print(f"  {day_str(c.start_ts)} {_money(c.start_price)} -> {end}, {days} d, {c.top_pos:.2f}, {c.translation}, "
                      f"{'FAILED' if c.failed else '-'}, {c.status}")
    machines = {"daily": e.daily, "weekly": e.weekly, "fouryear": e.fouryear}
    for name, m in machines.items():
        print(f"\n{name} lows confirmed live from {args.since}: low, price, confirmed, signal, status")
        for x in m.log:
            if x.ts_low >= since or name == "fouryear":
                print(f"  {day_str(x.ts_low)} {_money(x.price)}, {day_str(x.ts_confirmed)}, {x.signal}, {x.status}")
    print("\nZones as of the last complete bar:")
    zones = e.zones()
    for z in zones:
        print(f"  {z['level']}: {_zone_line(z)}")
    for o in overlaps(zones):
        print(f"  overlap {' + '.join(o['levels'])}: {day_str(o['t_from'])} to {day_str(o['t_to'])}")
    return 0


def cmd_export(args) -> int:
    rules = load_rules(args.rules)
    bars = load_daily(rules.series["venue"])
    path, size = export_mod.write(export_mod.payload(bars, rules, int(time.time() * 1000)), args.out)
    print(f"{path}: {size / 1000:.0f} KB, as of {day_str(bars.ts[-1])}")
    return 0


def cmd_evaluate(args) -> int:
    rules = load_rules(args.rules)
    bars = load_daily(rules.series["venue"])
    started = time.time()
    btc = path_metrics(bars, rules)
    nulls = run_nulls(bars, rules, args.paths_shuffled, args.paths_block, args.workers)
    result = {
        "rules_version": rules.version, "rules_digest": rules.digest, "as_of_day": day_str(bars.ts[-1]),
        "paths": {k: len(v) for k, v in nulls.items()},
        "fouryear_null": {
            k: {"at_least_3_bears": sum(r["fouryear.n_bears"] >= 3 for r in v) / len(v),
                "gap_spread_within_btc": sum(r["fouryear.max_gap_spread"] is not None
                                             and r["fouryear.max_gap_spread"] <= btc["fouryear.max_gap_spread"] for r in v) / len(v)}
            for k, v in nulls.items() if v},
        "comparison": compare(btc, nulls),
        "repaint": repaint_check(bars, rules),
    }
    out = Path(args.out) if args.out else data_root() / "derived" / "cycles" / f"evaluate-{rules.version}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(result, indent=1).encode()
    atomic_write(out, lambda f: f.write(data))
    print(render_tables(result))
    print(f"\n{out} ({time.time() - started:.0f} s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ewave-cycles", description=__doc__)
    parser.add_argument("--rules", help="rules file (default: rules/cycles.yaml)")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("report", help="the marks and the zones, as text")
    p.add_argument("--since", default="2023-01-01", help="list weekly and daily cycles from this date")
    p.set_defaults(func=cmd_report)
    p = sub.add_parser("export", help="write site/data/local/cycles.json for the chart overlay")
    p.add_argument("--out")
    p.set_defaults(func=cmd_export)
    p = sub.add_parser("evaluate", help="BTC against the null paths; prints the tables")
    p.add_argument("--paths-shuffled", type=int)
    p.add_argument("--paths-block", type=int)
    p.add_argument("--workers", type=int)
    p.add_argument("--out")
    p.set_defaults(func=cmd_evaluate)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
