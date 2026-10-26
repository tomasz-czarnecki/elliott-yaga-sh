"""rebuild (derived bars from raw days) and reindex (catalog days/gaps from the raw files)."""
from __future__ import annotations

import hashlib
import logging
import re

from .audit import BINANCE, LOCK_WAIT_S
from .config import DAY_MS, MINUTE_MS, VENUES, day_of_ms, day_start_ms
from .resample import last_traded_close
from .schema import content_hash, expected_minutes, find_gaps, grid_bounds
from .sync import Collector

log = logging.getLogger("ewave.maintenance")

_ZIP_RE = re.compile(r"^BTCUSDT-1m-(\d{4}-\d{2}-\d{2})\.([A-Za-z0-9_-]+)\.zip$")


def rebuild(c: Collector, vid: str, year: str | None = None) -> str:
    lock = c.venue_lock(vid)
    if not lock.acquire(LOCK_WAIT_S):
        return f"{vid}: could not get the venue lock"
    try:
        days = c.store.list_days(vid)
        if year:
            days = [d for d in days if d.startswith(year)]
        covered = c.catalog.venue_state(vid)["covered_until"]
        c.rebuild_bars(vid, days, covered)
        return f"{vid}: rebuilt bars for {len(days)} days"
    finally:
        lock.release()


def reindex(c: Collector, vid: str) -> str:
    """Rebuild ``days`` and ``gaps`` from the files. Runs of closed days are inferred conservatively."""
    lock = c.venue_lock(vid)
    if not lock.acquire(LOCK_WAIT_S):
        return f"{vid}: could not get the venue lock"
    try:
        v = VENUES[vid]
        now = c.clock.now_ms()
        today = day_of_ms(now)
        zips: dict[str, tuple[str, bytes]] = {}
        if vid == BINANCE and c.store.binance_sources_dir().exists():
            for p in c.store.binance_sources_dir().glob("BTCUSDT-1m-*.zip"):
                m = _ZIP_RE.match(p.name)
                if m:
                    zips[m.group(1)] = (m.group(2), p.read_bytes())
        c.catalog.delete_days(vid)
        carry = None
        n = 0
        for day in c.store.list_days(vid):
            frame = c.store.read_day(vid, day)
            ts = frame["ts"].to_list()
            exp = expected_minutes(v, day)
            past = day_start_ms(day) + DAY_MS <= now - 2 * DAY_MS
            bounds = grid_bounds(v, day, None if day < today else ts[-1])
            gaps = find_gaps(ts, *bounds) if bounds else []
            carry = last_traded_close(frame, carry)
            revision = 0
            sup = c.store.root / "raw" / "_superseded" / vid
            if sup.exists():
                revs = [int(p.suffixes[-2][2:]) for p in sup.glob(f"{day}.r*.parquet") if p.suffixes[-2][2:].isdigit()]
                revision = max(revs) + 1 if revs else 0
            source = "rest"
            if day in zips:
                etag, data = zips[day]
                source = "archive"
                c.catalog.upsert_archive(day, etag, zip_sha256=hashlib.sha256(data).hexdigest(), checksum_ok=1,
                                         size=len(data), checked_at=now, first_seen_at=now, outcome="reindexed")
            c.catalog.upsert_day(
                vid, day, status="closed" if (past and frame.height == exp) else "open", n_rows=frame.height,
                expected_minutes=exp, missing_minutes=sum(g[2] for g in gaps), first_ts=ts[0], last_ts=ts[-1],
                last_traded_close=carry, content_hash=content_hash(frame),
                file_sha256=hashlib.sha256(c.store.raw_path(vid, day).read_bytes()).hexdigest(),
                source=source, revision=revision, fetched_at=now)
            if bounds:
                c.catalog.replace_gaps(vid, bounds[0], bounds[1], gaps)
            n += 1
        return f"{vid}: reindexed {n} day files"
    finally:
        lock.release()
