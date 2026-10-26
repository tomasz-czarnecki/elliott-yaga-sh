"""Daily audit: Binance archive reconciliation, late-correction re-fetches, and the on-demand native-candle check."""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field

import polars as pl

from .config import DAY_MS, MINUTE_MS, TIMEFRAMES, UTC, VENUES, day_of_ms, day_start_ms, floor_minute, iso_ms
from .http import CooldownError, GeoBlockedError, HttpError
from .schema import expected_minutes, frame_from_rows, grid_bounds
from .sources.binance import (
    ArchiveEntry, ArchiveError, ChecksumMismatch, ChecksumPending,
)
from .sync import ClockSkewError, Collector

log = logging.getLogger("ewave.audit")

BINANCE = "binance_btcusdt"
LOCK_WAIT_S = 600.0
FULL_LISTING_EVERY_MS = 7 * DAY_MS
REFETCH_DAYS = 3


@dataclass
class AuditReport:
    lines: list[str] = field(default_factory=list)
    ok: bool = True

    def add(self, msg: str, ok: bool = True) -> None:
        self.lines.append(msg)
        log.info(msg) if ok else log.error(msg)
        self.ok = self.ok and ok


def ingest_archive_day(c: Collector, entry: ArchiveEntry, *, last_closed: int, complement_rest: bool) -> tuple[str, bool]:
    """Download, verify and reconcile one Binance daily archive. Returns (outcome, day_rows_were_written)."""
    vid = BINANCE
    v = VENUES[vid]
    day = entry.day
    now = c.clock.now_ms()
    try:
        ad = c.archive.fetch_day(day)
    except ChecksumPending:
        return "pending_checksum", False
    except ChecksumMismatch as e:
        c.catalog.upsert_archive(day, entry.etag, checksum_ok=0, checked_at=now, outcome="checksum_mismatch")
        c.catalog.add_check(vid, day, "archive", "fail", str(e), now)
        return "checksum_mismatch", False
    except ArchiveError as e:
        c.catalog.upsert_archive(day, entry.etag, checksum_ok=0, checked_at=now, outcome="format_error")
        c.catalog.add_check(vid, day, "archive", "fail", str(e), now)
        return "format_error", False
    if ad is None:
        return "not_published", False

    etag = entry.etag or ad.etag
    c.store.save_source(f"BTCUSDT-1m-{day}.{etag}.zip", ad.zip_bytes)
    c.store.save_source(f"BTCUSDT-1m-{day}.{etag}.zip.CHECKSUM", ad.checksum_text.encode())
    frame = frame_from_rows(ad.rows)
    missing = expected_minutes(v, day) - frame.height
    fields = dict(last_modified=ad.last_modified, size=ad.size, zip_sha256=ad.zip_sha256, checksum_ok=1,
                  n_rows=frame.height, missing_minutes=missing, checked_at=now)
    if not c.catalog.archive_rows(day) or not any(r["etag"] == etag for r in c.catalog.archive_rows(day)):
        fields["first_seen_at"] = now

    stored = c.store.read_day(vid, day)
    if stored is not None and stored.height and not set(stored["ts"].to_list()) <= set(frame["ts"].to_list()):
        c.catalog.upsert_archive(day, etag, outcome="kept_stored_archive_fewer_minutes", **fields)
        c.catalog.add_check(vid, day, "archive", "flag",
                            f"archive has {frame.height} rows but we hold minutes it lacks ({stored.height} rows); "
                            "kept ours", now)
        return "kept_stored_archive_fewer_minutes", False

    res = c.commit_day(vid, day, frame, source="archive", last_closed_ms=last_closed, upto_ms=None)
    if res.failed:
        c.catalog.upsert_archive(day, etag, outcome="validation_failed", **fields)
        return "validation_failed", False

    source = "archive"
    frame_final = res.frame
    written = res.written
    if complement_rest and res.missing > 0 and day_of_ms(c.clock.now_ms()) > day:
        bounds = grid_bounds(v, day, last_closed)
        rest_rows = c.sources[vid].fetch_minutes(*bounds) if bounds else []
        have = set(frame["ts"].to_list())
        extra = [r for r in rest_rows if r[0] not in have]
        if extra:
            res2 = c.commit_day(vid, day, frame_from_rows(extra), source="rest", last_closed_ms=last_closed,
                                upto_ms=None)
            if not res2.failed:
                source, frame_final, written = "rest", res2.frame, written or res2.written
                c.catalog.add_check(vid, day, "archive", "info",
                                    f"archive lacked {len(extra)} minutes that REST has; kept the more complete copy", now)
    c.mark_closed(vid, day, frame_final, source=source)
    c.catalog.upsert_archive(day, etag, outcome=f"stored_{source}" if written else f"verified_{source}", **fields)
    return ("replaced_stored" if written and stored is not None else "stored" if written else "verified"), written


def audit_binance(c: Collector, rep: AuditReport) -> None:
    now = c.clock.now_ms()
    today = day_of_ms(now)
    last_full = c.catalog.get_meta("binance_full_listing_at")
    full = last_full is None or now - int(last_full) >= FULL_LISTING_EVERY_MS
    start_day = None if full else day_of_ms(now - 30 * DAY_MS)
    entries = c.archive.list_days(start_day)
    _, last_closed = c.determine_last_closed(BINANCE)
    touched: list[str] = []
    stats: dict[str, int] = {}
    for e in entries:
        if e.day >= today:
            continue
        row = c.catalog.get_day(BINANCE, e.day)
        if row is None or row["status"] != "closed":
            continue
        if c.catalog.archive_verified(e.day, e.etag):
            continue
        outcome, written = ingest_archive_day(c, e, last_closed=last_closed, complement_rest=False)
        stats[outcome] = stats.get(outcome, 0) + 1
        if written:
            touched.append(e.day)
    if full:
        c.catalog.set_meta("binance_full_listing_at", str(now))
    covered = c.catalog.venue_state(BINANCE)["covered_until"]
    c.refresh_bars(BINANCE, touched, covered)
    for d in touched:
        c.propagate_carry(BINANCE, d, covered)
    summary = ", ".join(f"{k}={n}" for k, n in sorted(stats.items())) or "nothing new"
    bad = sum(n for k, n in stats.items() if k in ("checksum_mismatch", "format_error", "validation_failed"))
    rep.add(f"{BINANCE}: archive {'full' if full else 'recent'} listing ({len(entries)} files): {summary}", ok=not bad)


def audit_refetch(c: Collector, vid: str, rep: AuditReport) -> None:
    """Re-fetch the last closed days and merge them: late exchange corrections show up as revisions."""
    days = [r["day"] for r in c.catalog.days(vid, status="closed")][-REFETCH_DAYS:]
    if not days:
        rep.add(f"{vid}: no closed days to re-check yet")
        return
    _, last_closed = c.determine_last_closed(vid)
    touched = []
    for day in days:
        res = c.refetch_day(vid, c.sources[vid], day, last_closed)
        if res.written:
            touched.append(day)
    covered = c.catalog.venue_state(vid)["covered_until"]
    c.refresh_bars(vid, touched, covered)
    for d in touched:
        c.propagate_carry(vid, d, covered)
    rep.add(f"{vid}: re-checked {len(days)} days ({days[0]}..{days[-1]}), {len(touched)} changed")


def run_audit(c: Collector, venue_ids: list[str] | None = None) -> AuditReport:
    rep = AuditReport()
    run = c.catalog.start_run("audit", c.clock.now_ms())
    for vid in venue_ids or list(c.sources):
        lock = c.venue_lock(vid)
        if not lock.acquire(LOCK_WAIT_S):
            rep.add(f"{vid}: could not get the venue lock within {LOCK_WAIT_S:.0f}s", ok=False)
            continue
        try:
            c.store.cleanup_tmp(vid)
            if vid == BINANCE and c.archive is not None:
                audit_binance(c, rep)
            else:
                audit_refetch(c, vid, rep)
        except (CooldownError, GeoBlockedError, HttpError, ClockSkewError) as e:
            rep.add(f"{vid}: audit failed: {e}", ok=False)
        finally:
            lock.release()
    c.catalog.finish_run(run, c.clock.now_ms(), rep.ok, " | ".join(rep.lines))
    return rep


# ---- native candle comparison (on demand) ---------------------------------------------------------------


def _close_enough(a: float | None, b: float | None, rel: float = 1e-9) -> bool:
    if a is None or b is None:
        return a is b
    return abs(a - b) <= rel * max(1.0, abs(a), abs(b))


def audit_native(c: Collector, vid: str, days: list[str]) -> list[str]:
    """Compare our derived bars with the exchange's own candles. Returns a list of printable mismatch lines."""
    v = VENUES[vid]
    src = c.sources[vid]
    out: list[str] = []
    compared = skipped = bad = 0
    for day in days:
        d0 = day_start_ms(day)
        for tf, minutes in TIMEFRAMES.items():
            ours = c.store.read_bars_year(vid, tf, day[:4])
            if ours is None:
                out.append(f"{vid} {day} {tf}: no derived bars file")
                bad += 1
                continue
            lo = pl.lit(d0).cast(pl.Datetime("ms")).dt.replace_time_zone("UTC")
            ours = ours.filter((pl.col("ts") >= lo) & (pl.col("ts") < lo + pl.duration(days=1))).with_columns(
                pl.col("ts").dt.epoch("ms").alias("t_ms"))
            native = {n[0]: n for n in src.native_candles(tf, d0, d0 + DAY_MS - 1)}
            for b in ours.iter_rows(named=True):
                n = native.get(b["t_ms"])
                full = b["n_minutes"] == minutes
                if n is None:
                    # exchanges may omit bars that never traded; only complain about traded bars
                    if b["n_traded"] > 0 and b["complete"]:
                        out.append(f"{vid} {day} {tf} {iso_ms(b['t_ms'])}: not in the exchange's own candles")
                        bad += 1
                    else:
                        skipped += 1
                    continue
                if not b["complete"] or not full:
                    skipped += 1
                    continue
                if vid == BINANCE and b["n_traded"] != b["n_minutes"]:
                    skipped += 1  # Binance's own bars are plain aggregates and differ where zero-volume rows exist
                    continue
                compared += 1
                _, no, nh, nl, nc, nv = n
                same = (b["open"], b["high"], b["low"], b["close"]) == (no, nh, nl, nc) and _close_enough(b["volume"], nv)
                if not same:
                    bad += 1
                    out.append(f"{vid} {day} {tf} {iso_ms(b['t_ms'])}: ours o={b['open']} h={b['high']} l={b['low']} "
                               f"c={b['close']} v={b['volume']:.8f} | exchange o={no} h={nh} l={nl} c={nc} v={nv:.8f}")
    c.catalog.add_check(vid, None, "native", "ok" if not bad else "fail",
                        f"{len(days)} days: compared {compared} bars, skipped {skipped}, mismatches {bad}",
                        c.clock.now_ms())
    out.append(f"{vid}: {len(days)} days, compared {compared} bars, skipped {skipped}, mismatches {bad}")
    return out


def pick_native_days(c: Collector, vid: str, last_n: int, sample_n: int, seed: int | None = None) -> list[str]:
    closed = [r["day"] for r in c.catalog.days(vid, status="closed")]
    rng = random.Random(seed if seed is not None else day_of_ms(c.clock.now_ms()))
    recent = closed[-last_n:] if last_n else []
    pool = closed[: len(closed) - len(recent)]
    sample = rng.sample(pool, min(sample_n, len(pool))) if sample_n else []
    return sorted(set(recent) | set(sample))
