"""One-time (resumable) backfill of a venue's full 1m history.

Bitstamp / Bybit: a continuous sweep of the REST API from the venue's first minute. Binance: the official daily
archives (checksum-verified, ETag recorded) first, then REST for the days that are not archived yet. Closed days are
skipped on re-runs, each day is written as soon as it is complete, and derived bars are rebuilt in chunks.
"""
from __future__ import annotations

import logging

from .audit import BINANCE, LOCK_WAIT_S, ingest_archive_day
from .config import DAY_MS, MINUTE_MS, VENUES, day_of_ms, day_start_ms, days_between, next_day, prev_day
from .http import CooldownError, GeoBlockedError, HttpError
from .schema import Row, frame_from_rows
from .sync import ClockSkewError, Collector, VenueReport

log = logging.getLogger("ewave.backfill")

BARS_CHUNK_DAYS = 180
PROGRESS_EVERY = 100


def backfill(c: Collector, vid: str, since: str | None = None) -> VenueReport:
    lock = c.venue_lock(vid)
    if not lock.acquire(LOCK_WAIT_S):
        return VenueReport(vid, "failed", f"could not get the venue lock within {LOCK_WAIT_S:.0f}s")
    run = c.catalog.start_run("backfill", c.clock.now_ms(), vid)
    try:
        c.store.cleanup_tmp(vid)
        rep = _backfill_locked(c, vid, since)
    except CooldownError as e:
        c._set_cooldown(vid, e.seconds, str(e))
        rep = VenueReport(vid, "failed", f"cooldown: {e}")
    except GeoBlockedError as e:
        c._set_cooldown(vid, 3600.0, str(e))
        rep = VenueReport(vid, "failed", f"geo-blocked: {e}")
    except (HttpError, ClockSkewError) as e:
        c.catalog.update_venue(vid, last_error=str(e)[:500])
        rep = VenueReport(vid, "failed", str(e))
    finally:
        lock.release()
    c.catalog.finish_run(run, c.clock.now_ms(), rep.status == "ok", rep.line())
    return rep


def contiguous_runs(days: list[str]) -> list[list[str]]:
    runs: list[list[str]] = []
    for d in days:
        if runs and next_day(runs[-1][-1]) == d:
            runs[-1].append(d)
        else:
            runs.append([d])
    return runs


def _backfill_locked(c: Collector, vid: str, since: str | None) -> VenueReport:
    v = VENUES[vid]
    now_eff, last_closed = c.determine_last_closed(vid)
    today = day_of_ms(now_eff)
    first_day = day_of_ms(v.first_minute_ms)
    if since:
        first_day = max(first_day, since)
    rep = VenueReport(vid, "ok")
    touched: list[str] = []

    if vid == BINANCE and c.archive is not None:
        _binance_archive_pass(c, first_day, today, last_closed, touched, rep)

    closed_days = {r["day"] for r in c.catalog.days(vid, status="closed")}
    needed = [d for d in days_between(first_day, today) if d not in closed_days]
    for run_days in contiguous_runs(needed):
        _sweep(c, vid, run_days[0], run_days[-1], today, last_closed, touched, rep)

    covered = last_closed + MINUTE_MS
    c.catalog.update_venue(vid, covered_until=covered, last_ok_run=c.clock.now_ms(), consecutive_lock_skips=0,
                           cooldown_step=0, cooldown_until=None, last_error=None)
    rep.days_touched = len(touched)
    log.info("%s: backfill finished: %d days written, covered until %s", vid, len(touched), day_of_ms(covered))
    return rep


def _sweep(c: Collector, vid: str, first: str, last: str, today: str, last_closed: int, touched: list[str],
           rep: VenueReport) -> None:
    """REST sweep over days first..last, committing each day as soon as the sweep has passed its last minute."""
    v = VENUES[vid]
    src = c.sources[vid]
    start_ms = max(v.first_minute_ms, day_start_ms(first))
    end_ms = min(day_start_ms(last) + DAY_MS - MINUTE_MS, last_closed)
    buffer: dict[str, list[Row]] = {}
    chunk: list[str] = []
    cursor = first
    done = 0

    def finish(day: str, is_today: bool) -> None:
        nonlocal done
        rows = buffer.pop(day, [])
        res = c.commit_day(vid, day, frame_from_rows(rows), source="rest", last_closed_ms=last_closed,
                           upto_ms=last_closed if is_today else None)
        touched.append(day)
        chunk.append(day)
        rep.rows_added += res.added
        if not is_today and c.try_close(vid, day, res):
            rep.days_closed += 1
        done += 1
        if done % PROGRESS_EVERY == 0:
            log.info("%s: %s done (%d days this run)", vid, day, done)

    if start_ms <= end_ms:
        for page in src.iter_pages(start_ms, end_ms):
            for r in page.rows:
                buffer.setdefault(day_of_ms(r[0]), []).append(r)
            while cursor <= last and cursor < today and day_start_ms(cursor) + DAY_MS - MINUTE_MS <= page.window_end_ms:
                finish(cursor, False)
                cursor = next_day(cursor)
            if len(chunk) >= BARS_CHUNK_DAYS:
                c.rebuild_bars(vid, chunk, page.window_end_ms + MINUTE_MS)
                chunk.clear()
    while cursor <= last:  # nothing more to fetch (e.g. today before its first closed minute)
        finish(cursor, cursor == today)
        cursor = next_day(cursor)
    if chunk:
        c.rebuild_bars(vid, chunk, last_closed + MINUTE_MS)


def _binance_archive_pass(c: Collector, first_day: str, today: str, last_closed: int, touched: list[str],
                          rep: VenueReport) -> None:
    """Ingest every published daily archive that is not already stored and verified."""
    entries = {e.day: e for e in c.archive.list_days(None)}
    log.info("binance: %d daily archives listed", len(entries))
    closed_days = {r["day"] for r in c.catalog.days(BINANCE, status="closed")}
    chunk: list[str] = []
    done = 0
    for day in days_between(first_day, prev_day(today)):
        e = entries.get(day)
        if e is None:
            continue  # not archived (yet): the REST sweep covers it if the day is not closed
        if day in closed_days and c.catalog.archive_verified(day, e.etag):
            continue
        outcome, written = ingest_archive_day(c, e, last_closed=last_closed, complement_rest=True)
        if outcome in ("pending_checksum", "not_published"):
            continue
        if outcome in ("checksum_mismatch", "format_error", "validation_failed"):
            log.error("binance %s: archive %s", day, outcome)
            rep.warnings.append(f"{day}: {outcome}")
            continue
        touched.append(day)
        chunk.append(day)
        rep.days_closed += 1
        done += 1
        if done % PROGRESS_EVERY == 0:
            log.info("binance: %s done (%d archive days this run)", day, done)
        if len(chunk) >= BARS_CHUNK_DAYS:
            c.rebuild_bars(BINANCE, chunk, last_closed + MINUTE_MS)
            chunk.clear()
    if chunk:
        c.rebuild_bars(BINANCE, chunk, last_closed + MINUTE_MS)
