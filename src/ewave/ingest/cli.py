"""ewave-data: sync / backfill / audit / rebuild / reindex / status / gaps / show / export-site."""
from __future__ import annotations

import argparse
import logging
import signal
import sys

import polars as pl

from . import health
from .audit import audit_native, pick_native_days, run_audit
from .backfill import backfill
from .config import MINUTE_MS, VENUES, UTC, data_root, iso_ms, raise_nofile_limit, resolve_venue
from .export import export_site, site_data_dir
from .maintenance import rebuild, reindex
from .sources.binance import BinanceArchive, BinanceSource
from .sources.bitstamp import BitstampSource
from .sources.bybit import BybitSource
from .sync import Collector


def build_collector(root=None) -> Collector:
    sources = {
        "bitstamp_btcusd": BitstampSource(),
        "binance_btcusdt": BinanceSource(),
        "bybit_btcusdt_perp": BybitSource(),
    }
    return Collector(root or data_root(), sources=sources, archive=BinanceArchive())


def _venues(names: list[str] | None) -> list[str] | None:
    return [resolve_venue(n).id for n in names] if names else None


def cmd_sync(c: Collector, a) -> int:
    reports = c.sync(_venues(a.venue))
    for r in reports:
        print(r.line())
    problems = health.problems(c)
    for p in problems:
        print(f"PROBLEM: {p}")
    return 0 if all(r.ok for r in reports) and not problems else 1


def cmd_backfill(c: Collector, a) -> int:
    if not a.venue:
        print("backfill needs --venue (bitstamp, binance, bybit)", file=sys.stderr)
        return 2
    rc = 0
    for vid in _venues(a.venue):
        rep = backfill(c, vid, a.since)
        print(rep.line())
        for w in rep.warnings:
            print(f"  warning: {w}")
        rc = rc or (0 if rep.status == "ok" else 1)
    return rc


def cmd_audit(c: Collector, a) -> int:
    vids = _venues(a.venue)
    if a.native:
        rc = 0
        for vid in vids or list(VENUES):
            days = pick_native_days(c, vid, a.days, a.sample)
            if not days:
                print(f"{vid}: no closed days to compare")
                continue
            for line in audit_native(c, vid, days):
                print(line)
                rc = rc or int("mismatches" in line and not line.endswith("mismatches 0"))
        return rc
    rep = run_audit(c, vids)
    for line in rep.lines:
        print(line)
    return 0 if rep.ok else 1


def cmd_rebuild(c: Collector, a) -> int:
    for vid in _venues(a.venue) or list(VENUES):
        print(rebuild(c, vid, a.year))
    return 0


def cmd_reindex(c: Collector, a) -> int:
    for vid in _venues(a.venue) or list(VENUES):
        print(reindex(c, vid))
    return 0


def cmd_status(c: Collector, a) -> int:
    if a.check:
        probs = health.problems(c)
        for p in probs:
            print(f"ewave-data: {p}")
        return 1 if probs else 0
    print(health.format_status(c))
    return 0


def cmd_gaps(c: Collector, a) -> int:
    vids = _venues(a.venue) or list(VENUES)
    if a.no_trades:
        for vid in vids:
            runs = _no_trade_runs(c, vid, a.no_trades)
            print(f"{vid}: {len(runs)} runs of >= {a.no_trades} zero-volume minutes")
            for s, e, n in runs:
                print(f"  {iso_ms(s)} -> {iso_ms(e)} UTC  {n} min")
        return 0
    total = 0
    for g in c.catalog.gaps():
        if g["venue"] in vids:
            print(f"{g['venue']:20s} {iso_ms(g['start_ts'])} -> {iso_ms(g['end_ts'])} UTC  {g['minutes']} min")
            total += 1
    print(f"{total} gaps of missing minutes")
    return 0


def _no_trade_runs(c: Collector, vid: str, min_len: int) -> list[tuple[int, int, int]]:
    runs: list[tuple[int, int, int]] = []
    start = last = None
    for day in c.store.list_days(vid):
        df = c.store.read_day(vid, day)
        for t, v in zip(df["ts"].to_list(), df["volume"].to_list()):
            if v == 0 and start is not None and t == last + MINUTE_MS:
                last = t
            elif v == 0:
                if start is not None and (last - start) // MINUTE_MS + 1 >= min_len:
                    runs.append((start, last, (last - start) // MINUTE_MS + 1))
                start = last = t
            else:
                if start is not None and (last - start) // MINUTE_MS + 1 >= min_len:
                    runs.append((start, last, (last - start) // MINUTE_MS + 1))
                start = last = None
    if start is not None and (last - start) // MINUTE_MS + 1 >= min_len:
        runs.append((start, last, (last - start) // MINUTE_MS + 1))
    return runs


def cmd_show(c: Collector, a) -> int:
    v = resolve_venue(a.venue)
    if a.tf == "1m":
        df = c.store.read_day(v.id, a.day)
        if df is None:
            print(f"no 1m file for {v.id} {a.day}", file=sys.stderr)
            return 1
        from .schema import to_disk

        df = to_disk(df)
    else:
        from datetime import datetime, timedelta

        year = a.day[:4]
        full = c.store.read_bars_year(v.id, a.tf, year)
        if full is None:
            print(f"no {a.tf} bars for {v.id} {year}", file=sys.stderr)
            return 1
        d0 = datetime.fromisoformat(a.day).replace(tzinfo=UTC)
        df = full.filter((pl.col("ts") >= d0) & (pl.col("ts") < d0 + timedelta(days=1)))
    if a.csv:
        sys.stdout.write(df.write_csv())
    else:
        with pl.Config(tbl_rows=2000, tbl_cols=30, tbl_width_chars=250):
            print(df)
    return 0


def cmd_export_site(c: Collector, a) -> int:
    for line in export_site(c, a.out or site_data_dir()):
        print(line)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ewave-data", description="BTC 1m data collector for the Elliott Wave analyzer")
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_venue(sp, plural=True):
        sp.add_argument("--venue", action="append", help="bitstamp | binance | bybit (repeatable)")

    s = sub.add_parser("sync", help="fetch new closed minutes, close finished days, update bars (timer: every 15 min)")
    add_venue(s)
    s.set_defaults(fn=cmd_sync)

    s = sub.add_parser("backfill", help="one-time, resumable download of a venue's full history")
    add_venue(s)
    s.add_argument("--since", help="first day to fetch, YYYY-MM-DD (default: the venue's first day)")
    s.set_defaults(fn=cmd_backfill)

    s = sub.add_parser("audit", help="daily: Binance archive check + late-correction re-fetch; --native compares candles")
    add_venue(s)
    s.add_argument("--native", action="store_true", help="compare derived bars with each exchange's own candles")
    s.add_argument("--days", type=int, default=30, help="with --native: the last N closed days (default 30)")
    s.add_argument("--sample", type=int, default=50, help="with --native: plus N random older days (default 50)")
    s.set_defaults(fn=cmd_audit)

    s = sub.add_parser("rebuild", help="rebuild derived bars from the raw day files")
    add_venue(s)
    s.add_argument("--year")
    s.set_defaults(fn=cmd_rebuild)

    s = sub.add_parser("reindex", help="rebuild the catalog's days/gaps from the files")
    add_venue(s)
    s.set_defaults(fn=cmd_reindex)

    s = sub.add_parser("status", help="freshness and problems; --check prints only problems (exit 1 if any)")
    s.add_argument("--check", action="store_true")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("gaps", help="missing minutes recorded in the catalog, or zero-volume runs with --no-trades")
    add_venue(s)
    s.add_argument("--no-trades", type=int, metavar="MIN", help="list zero-volume runs of at least MIN minutes")
    s.set_defaults(fn=cmd_gaps)

    s = sub.add_parser("show", help="print one day of data (1m or derived bars)")
    s.add_argument("venue")
    s.add_argument("day", help="YYYY-MM-DD")
    s.add_argument("--tf", default="1m", choices=["1m", "15m", "1h", "4h", "1d"])
    s.add_argument("--csv", action="store_true")
    s.set_defaults(fn=cmd_show)

    s = sub.add_parser("export-site", help="write complete bars and stats.json for the static site")
    s.add_argument("--out", help="output directory (default: site/data in the project)")
    s.set_defaults(fn=cmd_export_site)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, stream=sys.stderr,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    # turn SIGTERM into SystemExit so finally-blocks run: temp files are removed and locks released
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    raise_nofile_limit()
    c = build_collector()
    try:
        return args.fn(c, args)
    finally:
        c.close()


if __name__ == "__main__":
    raise SystemExit(main())
