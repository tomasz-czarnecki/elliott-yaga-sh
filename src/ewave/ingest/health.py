"""`status` and `status --check`: is the data fresh, and did anything go wrong that nobody has looked at yet?"""
from __future__ import annotations

from .audit import BINANCE
from .config import DAY_MS, MINUTE_MS, VENUES, day_of_ms, iso_ms
from .locks import is_held, read_holder
from .sync import Collector

STALE_LAST_MINUTE_MS = 45 * MINUTE_MS
NO_SYNC_MS = 30 * MINUTE_MS
NO_AUDIT_MS = 26 * 3600 * 1000
BINANCE_PENDING_DAYS = 7
LOCK_SKIPS_LIMIT = 4


def _dur(ms: int) -> str:
    m = ms // MINUTE_MS
    return f"{m} min" if m < 180 else f"{m / 60:.1f} h"


def _ago(now: int, then: int | None) -> str:
    return "never" if then is None else f"{_dur(now - then)} ago"


def problems(c: Collector, venue_ids: list[str] | None = None) -> list[str]:
    now = c.clock.now_ms()
    out: list[str] = []
    for vid in venue_ids or list(VENUES):
        vs = c.catalog.venue_state(vid)
        last = c.catalog.last_ts(vid)
        if last is None:
            out.append(f"{vid}: no data yet - run `ewave-data backfill --venue {vid}`")
            continue
        if now - last > STALE_LAST_MINUTE_MS:
            why = vs["last_error"] or ("cooling down" if (vs["cooldown_until"] or 0) > now else "no error recorded")
            out.append(f"{vid}: last minute is {(now - last) // MINUTE_MS} min old ({iso_ms(last)} UTC); {why}")
        if vs["last_ok_run"] is None:
            out.append(f"{vid}: no successful sync yet")
        elif now - vs["last_ok_run"] > NO_SYNC_MS:
            out.append(f"{vid}: no successful sync for {_dur(now - vs['last_ok_run'])} (last ok {iso_ms(vs['last_ok_run'])} UTC)")
        if vs["consecutive_lock_skips"] >= LOCK_SKIPS_LIMIT:
            holder = read_holder(c.store.state_dir, vid) if is_held(c.store.state_dir, vid) else "nobody now"
            out.append(f"{vid}: skipped {vs['consecutive_lock_skips']} syncs in a row because the lock was busy "
                       f"(holder: {holder})")
    if BINANCE in (venue_ids or VENUES) and c.catalog.last_ts(BINANCE) is not None:
        cutoff = day_of_ms(now - BINANCE_PENDING_DAYS * DAY_MS)
        verified = c.catalog.verified_archive_days()
        pending = [r["day"] for r in c.catalog.days(BINANCE, status="closed", before=cutoff) if r["day"] not in verified]
        if pending:
            out.append(f"{BINANCE}: {len(pending)} closed days older than {BINANCE_PENDING_DAYS} days have no verified "
                       f"archive (oldest {pending[0]})")
    first = c.catalog.first_run_at()
    last_audit = c.catalog.last_run("audit", ok_only=True)
    if (last_audit is None and first is not None and now - first > NO_AUDIT_MS) or \
            (last_audit is not None and now - last_audit["finished_at"] > NO_AUDIT_MS):
        out.append(f"no successful audit for {_dur(now - (last_audit['finished_at'] if last_audit else first))}")
    fails = c.catalog.checks(kind="validation", result="fail", unresolved_only=True, limit=5)
    for f in fails:
        out.append(f"{f['venue']} {f['day']}: validation failure not yet resolved: {f['detail'][:140]}")
    return out


def format_status(c: Collector) -> str:
    now = c.clock.now_ms()
    lines = [f"ewave-data status @ {iso_ms(now)} UTC   data: {c.store.root}"]
    for vid, v in VENUES.items():
        vs = c.catalog.venue_state(vid)
        last = c.catalog.last_ts(vid)
        days = c.catalog.days(vid)
        n_open = sum(1 for d in days if d["status"] != "closed")
        gaps7 = sum(g["minutes"] for g in c.catalog.gaps(vid, since_ms=now - 7 * DAY_MS))
        holder = read_holder(c.store.state_dir, vid) if is_held(c.store.state_dir, vid) else None
        lines.append("")
        lines.append(f"{vid}  ({v.title})")
        lines.append(f"  last minute   {iso_ms(last)} UTC" + (f"  ({(now - last) // MINUTE_MS} min behind)" if last else ""))
        lines.append(f"  days          {len(days)} ({len(days) - n_open} closed, {n_open} open)   "
                     f"missing minutes in last 7 days: {gaps7}")
        lines.append(f"  covered until {iso_ms(vs['covered_until'])} UTC   last ok sync: {_ago(now, vs['last_ok_run'])}")
        if (vs["cooldown_until"] or 0) > now:
            lines.append(f"  COOLDOWN until {iso_ms(vs['cooldown_until'])} UTC ({vs['last_error']})")
        elif vs["last_error"]:
            lines.append(f"  last error    {vs['last_error'][:160]}")
        if holder:
            lines.append(f"  lock held by  {holder}")
    sync = c.catalog.last_run("sync")
    audit = c.catalog.last_run("audit")
    lines.append("")
    lines.append(f"last sync run   {_ago(now, sync['finished_at']) if sync else 'never'}" + (f" - {'ok' if sync['ok'] else 'FAILED'}" if sync else ""))
    lines.append(f"last audit run  {_ago(now, audit['finished_at']) if audit else 'never'}" + (f" - {'ok' if audit['ok'] else 'FAILED'}" if audit else ""))
    probs = problems(c)
    lines.append("")
    lines.append("PROBLEMS:" if probs else "no problems found")
    lines.extend(f"  - {p}" for p in probs)
    return "\n".join(lines)
