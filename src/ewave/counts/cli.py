"""`ewave-counts report | rank | export | replay | gold`. Reads the bars; never writes anything the collector owns."""
from __future__ import annotations

import argparse
import sys
import time

from . import export as export_mod
from . import gold as gold_mod
from . import replay as replay_mod
from .config import load_config
from .frames import load_frames, stamp, to_ms
from .inside import open_cache
from .nest import Builder, _best_per_state
from .premise import load_premise
from .report import render


def _frames(args, cfg):
    frames = load_frames(args.venue or cfg.raw["venue"], cfg.pivots["atr_bars"], cfg.pivots["rsi_bars"])
    if getattr(args, "as_of", None):
        frames = frames.upto(to_ms(args.as_of))
    return frames


def _premise(args):
    return None if args.no_premise else load_premise(args.premise)


def cmd_report(args) -> int:
    cfg = load_config(args.rules)
    frames = _frames(args, cfg)
    cache = open_cache(cfg)
    try:
        obj = export_mod.payload(frames, cfg, int(time.time() * 1000), _premise(args), cache)
    finally:
        cache.close()
    roots = None if args.root == "both" else [args.root]
    print(render(obj, roots, args.brief))
    return 0


def cmd_export(args) -> int:
    cfg = load_config(args.rules)
    frames = _frames(args, cfg)
    cache = open_cache(cfg)
    try:
        path, size = export_mod.write(export_mod.payload(frames, cfg, int(time.time() * 1000), _premise(args), cache), args.out)
        print(f"{path}: {size / 1000:.0f} KB, as of {stamp(frames.as_of_ms)} UTC; inside verdicts: {cache.hits} from the cache, {cache.misses} read")
    finally:
        cache.close()
    return 0


def cmd_rank(args) -> int:
    """The root's states below the kept ones too: where a count went when the tree no longer shows it."""
    cfg = load_config(args.rules)
    frames = _frames(args, cfg)
    cache = open_cache(cfg)
    try:
        b = Builder(frames, cfg, _premise(args), cache)
        print(f"As of {stamp(frames.as_of_ms)} UTC, rules {cfg.version}. Best {args.top} states of the {args.root} root, by fit.")
        for n, (c, st, fit) in enumerate(_best_per_state(b.root_candidates(args.root))[: args.top], 1):
            a = fit.axes
            labels = " ".join(f"{lab}={pt.price:,.0f}" for lab, pt in zip(c.labs, c.pts))
            veto = f" failed: {','.join(fit.fails)}" if fit.fails else ""
            print(f"{n:>3} {fit.score:.3f} price {a['price']:.2f} time {a['time']:.2f} structure {a['structure']:.2f}  {c.pattern} {'up' if c.s > 0 else 'down'} in {st.wave}: {labels}{veto}")
    finally:
        cache.close()
    return 0


def cmd_replay(args) -> int:
    cfg = load_config(args.rules)
    full = _frames(args, cfg)
    rows = [replay_mod.run_date(full, cfg, d.strip(), args.root, args.days, _premise(args)) for d in args.dates.split(",")]
    print(replay_mod.render(rows))
    return 0


def cmd_gold(args) -> int:
    """His counts against the engine: pass or fail per entry, with rank and axis scores. Exits 1 when one fails."""
    cfg = load_config(args.rules)
    premise = _premise(args)
    full = _frames(args, cfg)
    results = []
    cache = open_cache(cfg)
    try:
        for e in gold_mod.load_gold(args.gold):
            frames = full.upto(to_ms(e.as_of)) if e.as_of and not args.latest else full
            results.append(gold_mod.run_entry(e, frames, cfg, premise, cache))
    finally:
        cache.close()
    print(gold_mod.render(results))
    return 0 if all(r.passed for r in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ewave-counts", description=__doc__)
    parser.add_argument("--rules", help="rules file (default: rules/counts.yaml)")
    parser.add_argument("--venue", help="venue id (default: the rules file's, Bybit perp)")
    parser.add_argument("--premise", help="premise file (default: rules/premise.yaml)")
    parser.add_argument("--no-premise", action="store_true", help="ignore his premise: search every root, as r2 did")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("report", help="the whole tree as text, as of the last complete 15m bar")
    p.add_argument("--root", default="1d", choices=["1d", "12h", "both"])
    p.add_argument("--as-of", help="cut the data here, e.g. 2026-05-01T00:00")
    p.add_argument("--brief", action="store_true", help="each node with its legs and time window only")
    p.set_defaults(func=cmd_report)
    p = sub.add_parser("rank", help="the root's states, kept or not, with their three axes")
    p.add_argument("--root", default="1d", choices=["1d", "12h"])
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--as-of")
    p.set_defaults(func=cmd_rank)
    p = sub.add_parser("export", help="write site/data/local/counts.json for the chart panel")
    p.add_argument("--out")
    p.add_argument("--as-of")
    p.set_defaults(func=cmd_export)
    p = sub.add_parser("replay", help="the root counts at past dates, on cut data, against what came next")
    p.add_argument("--dates", required=True, help="comma separated, e.g. 2024-08-06,2025-04-08")
    p.add_argument("--root", default="1d", choices=["1d", "12h"])
    p.add_argument("--days", type=int, default=30)
    p.set_defaults(func=cmd_replay)
    p = sub.add_parser("gold", help="his hand-labelled counts against the engine (gold/counts.yaml)")
    p.add_argument("--gold", help="gold file (default: gold/counts.yaml)")
    p.add_argument("--latest", action="store_true", help="on today's bars, not on the bars each entry was labelled on")
    p.set_defaults(func=cmd_gold)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
