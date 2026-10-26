"""The collector core: committing days, derived bars, the 15-minute sync and the day-closing rules.

Invariants:
  * The forming minute is never stored (``last_closed`` = floor(now) - 1 min, from the earlier of local/server time).
  * Rows from an exchange are merged into a day by ``ts``: fetched values win, stored rows are never deleted.
  * A day is rewritten only if its logical content changed; a closed day that changes keeps its old file under
    ``raw/_superseded`` and bumps ``revision``.
  * Every write is temp file -> fsync -> rename -> fsync(dir), then the catalog row; every writer holds the venue lock.
  * One venue failing never blocks the others.
"""
from __future__ import annotations

import logging
import re
import traceback
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from .catalog import Catalog
from .clock import SystemClock
from .config import (
    DAY_MS, MINUTE_MS, TIMEFRAMES, VENUES, Venue, day_of_ms, day_start_ms, days_between, floor_minute, iso_ms,
    next_day, prev_day,
)
from .http import CooldownError, GeoBlockedError, HttpError
from .locks import VenueLock, command_label, read_holder
from .resample import has_traded_minute, last_traded_close, resample_day
from .schema import (
    Row, content_hash, diff_frames, expected_minutes, find_gaps, first_missing_minute, frame_from_rows, grid_bounds,
    merge_frames, validate_day,
)
from .sources.base import Source
from .store import Store

log = logging.getLogger("ewave.sync")
_digits = re.compile(r"\d+")

OVERLAP_MS = 180 * MINUTE_MS  # every sync re-fetches the last 3 hours; older holes can no longer self-heal
SYNC_BUDGET_S = 180.0
CLOSE_GRACE_MS = 10 * MINUTE_MS  # a day is closed only once the server clock is >= D+1 00:10
REFETCH_AGREE_MS = 60 * MINUTE_MS  # two identical full re-fetches at least this far apart close a day with missing minutes
MAX_COOLDOWN_S = 6 * 3600.0


class ClockSkewError(Exception):
    pass


@dataclass
class VenueReport:
    venue: str
    status: str  # ok | skipped_lock | cooldown | failed | no_data
    message: str = ""
    rows_added: int = 0
    days_touched: int = 0
    days_closed: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status in ("ok", "skipped_lock", "cooldown")

    def line(self) -> str:
        extra = f" (+{self.rows_added} rows, {self.days_touched} days touched, {self.days_closed} closed)" \
            if self.status == "ok" else ""
        return f"{self.venue}: {self.status}{extra}{' - ' + self.message if self.message else ''}"


@dataclass
class CommitResult:
    day: str
    failed: bool = False
    written: bool = False
    n_rows: int = 0
    added: int = 0
    changed: int = 0
    missing: int = 0
    ltc_changed: bool = False
    frame: pl.DataFrame | None = None
    note: str = ""


class Collector:
    def __init__(self, root: Path, *, sources: dict[str, Source], archive=None, clock=None):
        self.root = Path(root)
        self.store = Store(self.root)
        self.catalog = Catalog(self.store.state_dir / "catalog.sqlite")
        self.sources = sources
        self.archive = archive
        self.clock = clock or SystemClock()

    def close(self) -> None:
        for s in self.sources.values():
            s.close()
        if self.archive is not None:
            self.archive.close()
        self.catalog.close()

    # ---- locks & clock -----------------------------------------------------------------
    def venue_lock(self, vid: str) -> VenueLock:
        return VenueLock(self.store.state_dir, vid, command_label())

    def determine_last_closed(self, vid: str) -> tuple[int, int]:
        """(effective now, last closed minute-open). Uses the earlier of local and server time if they disagree."""
        local = self.clock.now_ms()
        server = self.sources[vid].server_now_ms()
        diff = abs(local - server)
        if diff > 60_000:
            raise ClockSkewError(f"local clock differs from {vid} server time by {diff / 1000:.0f}s")
        now_eff = local
        if diff > 5_000:
            now_eff = min(local, server)
            msg = f"local clock differs from {vid} server time by {diff / 1000:.1f}s; using the earlier one"
            log.warning(msg)
            self.catalog.add_check(vid, None, "clock", "warn", msg, local)
        return now_eff, floor_minute(now_eff) - MINUTE_MS

    # ---- committing one day ----------------------------------------------------------------
    def commit_day(self, vid: str, day: str, new: pl.DataFrame, *, source: str, last_closed_ms: int | None,
                   upto_ms: int | None) -> CommitResult:
        v = VENUES[vid]
        now = self.clock.now_ms()
        row = self.catalog.get_day(vid, day)
        existing = self.store.read_day(vid, day)

        # REST data never overwrites a day that came from the verified archive; it can only be compared with it.
        if row and row["source"] == "archive" and source == "rest" and row["status"] == "closed":
            if existing is not None and new.height:
                merged_check = merge_frames(existing, new)
                if content_hash(merged_check) != content_hash(existing):
                    added, changed = diff_frames(existing, merged_check)
                    self.catalog.add_check(vid, day, "rest_vs_archive", "flag",
                                           f"REST differs from the archive day: +{added} rows, {changed} values", now)
            return CommitResult(day, n_rows=existing.height if existing is not None else 0, frame=existing)

        merged = merge_frames(existing, new)
        if merged.height == 0:
            return CommitResult(day, frame=merged)

        prev_row = self.catalog.get_day(vid, prev_day(day))
        prev_close = None
        if prev_row and prev_row["last_ts"] == day_start_ms(day) - MINUTE_MS:
            prev_close = prev_row["last_traded_close"]
        val = validate_day(merged, v, day, last_closed_ms, prev_close=prev_close,
                           bybit_open_rule=vid.startswith("bybit"))
        if val.hard:
            detail = "; ".join(val.hard)
            log.error("%s %s: validation failed, nothing written: %s", vid, day, detail)
            self.catalog.add_check(vid, day, "validation", "fail", detail, now)
            return CommitResult(day, failed=True, n_rows=merged.height, frame=merged, note=detail)

        new_hash = content_hash(merged)
        old_hash = content_hash(existing) if existing is not None else None
        added, changed = diff_frames(existing, merged)
        carry_in = self.catalog.last_traded_close_before(vid, day)
        ltc = last_traded_close(merged, carry_in)
        ts = merged["ts"].to_list()
        bounds = grid_bounds(v, day, upto_ms)
        gaps = find_gaps(ts, *bounds) if bounds else []

        if new_hash == old_hash:
            if row is None:  # catalog lost track of an existing file
                self._upsert_meta(vid, day, merged, ts, gaps, bounds, ltc, new_hash, None, source, 0, now)
            return CommitResult(day, n_rows=merged.height, missing=sum(g[2] for g in gaps), frame=merged)

        revision = row["revision"] if row else 0
        if row and row["status"] == "closed" and existing is not None:
            self.store.supersede(vid, day, revision)
            revision += 1
            self.catalog.add_check(vid, day, "revision", "changed",
                                   f"closed day changed: +{added} rows, {changed} values (now revision {revision})", now)
            log.warning("%s %s: closed day changed (+%d rows, %d values); old version kept as revision %d",
                        vid, day, added, changed, revision - 1)
        elif existing is not None and changed:
            self.catalog.add_check(vid, day, "revision_open", "info",
                                   f"{changed} stored values changed on an open day (+{added} rows)", now)

        sha = self.store.write_day(vid, day, merged)
        self._upsert_meta(vid, day, merged, ts, gaps, bounds, ltc, new_hash, sha, source, revision, now)
        self.catalog.resolve_checks(vid, day, "validation")
        if val.soft:
            detail = "; ".join(val.soft)
            last = self.catalog.last_check_detail(vid, day, "soft")
            if last is None or _digits.sub("#", last) != _digits.sub("#", detail[:2000]):
                self.catalog.add_check(vid, day, "soft", "warn", detail, now)  # a recurring warning type is logged once
        return CommitResult(day, written=True, n_rows=merged.height, added=added, changed=changed,
                            missing=sum(g[2] for g in gaps), ltc_changed=(ltc != (row or {}).get("last_traded_close")),
                            frame=merged)

    def _upsert_meta(self, vid, day, frame, ts, gaps, bounds, ltc, chash, sha, source, revision, now) -> None:
        v = VENUES[vid]
        self.catalog.upsert_day(
            vid, day, n_rows=frame.height, expected_minutes=expected_minutes(v, day),
            missing_minutes=sum(g[2] for g in gaps), first_ts=ts[0], last_ts=ts[-1], last_traded_close=ltc,
            content_hash=chash, file_sha256=sha, source=source, revision=revision, fetched_at=now,
        )
        if bounds:
            self.catalog.replace_gaps(vid, bounds[0], bounds[1], gaps)

    def mark_closed(self, vid: str, day: str, frame: pl.DataFrame | None, *, source: str | None = None) -> None:
        v = VENUES[vid]
        exp = expected_minutes(v, day)
        n = 0 if frame is None else frame.height
        fields = dict(status="closed", pending_refetch_hash=None, pending_refetch_at=None, expected_minutes=exp,
                      n_rows=n, missing_minutes=exp - n, fetched_at=self.clock.now_ms())
        if source:
            fields["source"] = source
        row = self.catalog.get_day(vid, day)
        if row is None or n == 0:
            fields.setdefault("source", "rest")
        self.catalog.upsert_day(vid, day, **fields)
        bounds = grid_bounds(v, day)
        if bounds:
            ts = [] if frame is None else frame["ts"].to_list()
            self.catalog.replace_gaps(vid, bounds[0], bounds[1], find_gaps(ts, *bounds))

    # ---- derived bars --------------------------------------------------------------------------
    def refresh_bars(self, vid: str, days: Iterable[str], covered_until_ms: int | None) -> int:
        """Recompute and splice the bars of the given days into their year files."""
        v = VENUES[vid]
        n = 0
        for day in sorted(set(days)):
            frame = self.store.read_day(vid, day)
            row = self.catalog.get_day(vid, day)
            closed = bool(row and row["status"] == "closed")
            carry = self.catalog.last_traded_close_before(vid, day)
            for tf in TIMEFRAMES:
                self.store.splice_bars(vid, tf, day, resample_day(frame, v, day, tf, carry, covered_until_ms, closed))
            n += 1
        return n

    def propagate_carry(self, vid: str, day: str, covered_until_ms: int | None) -> None:
        """A day's last traded close changed: recompute following days until one contains a traded minute."""
        v = VENUES[vid]
        d = next_day(day)
        while self.catalog.get_day(vid, d) is not None:
            frame = self.store.read_day(vid, d)
            row = self.catalog.get_day(vid, d)
            carry = self.catalog.last_traded_close_before(vid, d)
            closed = row["status"] == "closed"
            for tf in TIMEFRAMES:
                self.store.splice_bars(vid, tf, d, resample_day(frame, v, d, tf, carry, covered_until_ms, closed))
            self.catalog.upsert_day(vid, d, last_traded_close=last_traded_close(frame, carry))
            if has_traded_minute(frame):
                return
            d = next_day(d)

    def rebuild_bars(self, vid: str, days: list[str], covered_until_ms: int | None) -> None:
        """Bulk rebuild of the bars for a list of days: each affected year file is written once per timeframe."""
        v = VENUES[vid]
        days = sorted(set(days))
        if not days:
            return
        carry = self.catalog.last_traded_close_before(vid, days[0])
        by_year: dict[str, dict[str, list[pl.DataFrame]]] = {}
        spans: dict[str, list[str]] = {}
        for day in days:
            frame = self.store.read_day(vid, day)
            row = self.catalog.get_day(vid, day)
            closed = bool(row and row["status"] == "closed")
            year = day[:4]
            spans.setdefault(year, []).append(day)
            for tf in TIMEFRAMES:
                by_year.setdefault(year, {}).setdefault(tf, []).append(
                    resample_day(frame, v, day, tf, carry, covered_until_ms, closed))
            carry = last_traded_close(frame, carry)
            if row is not None:
                self.catalog.upsert_day(vid, day, last_traded_close=carry)
        for year, per_tf in by_year.items():
            lo = day_start_ms(spans[year][0])
            hi = day_start_ms(spans[year][-1]) + DAY_MS
            for tf, frames in per_tf.items():
                self.store.replace_bars_range(vid, tf, year, pl.concat(frames), lo, hi)
        if days:
            last_row = self.catalog.get_day(vid, days[-1])
            if last_row is not None:
                self.propagate_carry(vid, days[-1], covered_until_ms)

    # ---- the 15-minute sync -------------------------------------------------------------------------
    def sync(self, venue_ids: list[str] | None = None) -> list[VenueReport]:
        run = self.catalog.start_run("sync", self.clock.now_ms())
        reports: list[VenueReport] = []
        for vid in venue_ids or list(self.sources):
            try:
                rep = self.sync_venue(vid)
            except Exception as e:  # never let one venue stop the others
                log.error("%s: unexpected error\n%s", vid, traceback.format_exc())
                self.catalog.update_venue(vid, last_error=f"unexpected: {type(e).__name__}: {e}")
                rep = VenueReport(vid, "failed", f"unexpected {type(e).__name__}: {e}")
            reports.append(rep)
            log.info(rep.line())
        ok = all(r.ok for r in reports)
        self.catalog.finish_run(run, self.clock.now_ms(), ok, "; ".join(r.line() for r in reports))
        return reports

    def sync_venue(self, vid: str, budget_s: float = SYNC_BUDGET_S) -> VenueReport:
        lock = self.venue_lock(vid)
        if not lock.acquire(0.0):
            n = self.catalog.bump_lock_skips(vid)
            return VenueReport(vid, "skipped_lock", f"lock busy ({read_holder(self.store.state_dir, vid)}); "
                                                    f"{n} skipped in a row")
        try:
            return self._sync_locked(vid, budget_s)
        finally:
            lock.release()

    def _set_cooldown(self, vid: str, seconds: float, why: str) -> None:
        vs = self.catalog.venue_state(vid)
        wait = min(seconds * (2 ** vs["cooldown_step"]), MAX_COOLDOWN_S)
        until = self.clock.now_ms() + int(wait * 1000)
        self.catalog.update_venue(vid, cooldown_until=until, cooldown_step=vs["cooldown_step"] + 1, last_error=why)
        log.error("%s: cooling down for %.0f s (%s)", vid, wait, why)

    def _sync_locked(self, vid: str, budget_s: float) -> VenueReport:
        v = VENUES[vid]
        src = self.sources[vid]
        now = self.clock.now_ms()
        self.catalog.update_venue(vid, last_attempt=now)
        self.store.cleanup_tmp(vid)
        vs = self.catalog.venue_state(vid)
        if vs["cooldown_until"] and vs["cooldown_until"] > now:
            return VenueReport(vid, "cooldown", f"cooling down until {iso_ms(vs['cooldown_until'])} UTC "
                                                f"({vs['last_error']})")
        last_stored = self.catalog.last_ts(vid)
        if last_stored is None:
            return VenueReport(vid, "no_data", f"no data yet: run `ewave-data backfill --venue {vid}`")
        deadline = self.clock.monotonic() + budget_s
        try:
            now_eff, last_closed = self.determine_last_closed(vid)
            start = floor_minute(max(v.first_minute_ms, last_stored - OVERLAP_MS))

            rows: list[Row] = []
            covered_to: int | None = None
            for page in src.iter_pages(start, last_closed):
                rows.extend(page.rows)
                covered_to = page.window_end_ms
                if self.clock.monotonic() > deadline:
                    log.warning("%s: time budget used up at %s; continuing next run", vid, iso_ms(covered_to))
                    break

            by_day: dict[str, list[Row]] = {}
            for r in rows:
                by_day.setdefault(day_of_ms(r[0]), []).append(r)
            touched: list[str] = []
            frames_ok: dict[str, pl.DataFrame] = {}
            added = 0
            ltc_days: list[str] = []
            for day in sorted(by_day):
                res = self.commit_day(vid, day, frame_from_rows(by_day[day]), source="rest",
                                      last_closed_ms=last_closed, upto_ms=covered_to)
                touched.append(day)
                added += res.added
                if not res.failed and res.frame is not None:
                    frames_ok[day] = res.frame
                if res.written and res.ltc_changed:
                    ltc_days.append(day)

            covered_until = self._covered_until(vid, v, start, covered_to, frames_ok)
            closed = self._close_open_days(vid, src, now_eff, last_closed, deadline)
            self.refresh_bars(vid, set(touched) | set(closed), covered_until)
            for d in ltc_days + closed:
                self.propagate_carry(vid, d, covered_until)
            self.catalog.update_venue(vid, covered_until=covered_until, last_ok_run=self.clock.now_ms(),
                                      consecutive_lock_skips=0, cooldown_step=0, cooldown_until=None, last_error=None)
            return VenueReport(vid, "ok", rows_added=added, days_touched=len(touched), days_closed=len(closed))
        except CooldownError as e:
            self._set_cooldown(vid, e.seconds, str(e))
            return VenueReport(vid, "failed", f"cooldown: {e}")
        except GeoBlockedError as e:
            self._set_cooldown(vid, 3600.0, str(e))
            return VenueReport(vid, "failed", f"geo-blocked: {e}")
        except (HttpError, ClockSkewError) as e:
            self.catalog.update_venue(vid, last_error=str(e)[:500])
            log.error("%s: %s", vid, e)
            return VenueReport(vid, "failed", str(e))

    def _covered_until(self, vid: str, v: Venue, start: int, covered_to: int | None,
                       frames_ok: dict[str, pl.DataFrame]) -> int | None:
        """End of what the last fetch really covered; for continuous-grid venues it stops at a recent hole."""
        prev = self.catalog.venue_state(vid)["covered_until"]
        if covered_to is None:
            return prev
        covered_end = covered_to + MINUTE_MS
        if v.continuous_grid:
            lo = max(v.first_minute_ms, start, covered_end - OVERLAP_MS)
            ts: list[int] = []
            for frame in frames_ok.values():
                ts.extend(t for t in frame["ts"].to_list() if lo <= t < covered_end)
            hole = first_missing_minute(sorted(ts), lo, covered_end - MINUTE_MS)
            if hole is not None:
                return hole
        return max(covered_end, prev or 0)

    # ---- closing days -------------------------------------------------------------------------------
    def _closing_candidates(self, vid: str, today: str) -> list[str]:
        v = VENUES[vid]
        days = {r["day"] for r in self.catalog.days(vid, status="open", before=today)}
        last_closed_day = self.catalog.max_closed_day(vid)
        first = day_of_ms(v.first_minute_ms) if last_closed_day is None else next_day(last_closed_day)
        if first <= prev_day(today):
            for d in days_between(first, prev_day(today)):
                if self.catalog.get_day(vid, d) is None:
                    days.add(d)
        return sorted(days)

    def _close_open_days(self, vid: str, src: Source, now_eff: int, last_closed: int, deadline: float) -> list[str]:
        today = day_of_ms(now_eff)
        closed: list[str] = []
        for day in self._closing_candidates(vid, today):
            if self.clock.monotonic() > deadline:
                break
            if now_eff < day_start_ms(day) + DAY_MS + CLOSE_GRACE_MS:
                continue
            res = self.refetch_day(vid, src, day, last_closed)
            if self.try_close(vid, day, res):
                closed.append(day)
        return closed

    def refetch_day(self, vid: str, src: Source, day: str, last_closed: int) -> CommitResult:
        bounds = grid_bounds(VENUES[vid], day, last_closed)
        rows = src.fetch_minutes(*bounds) if bounds else []
        return self.commit_day(vid, day, frame_from_rows(rows), source="rest", last_closed_ms=last_closed,
                               upto_ms=None)

    def try_close(self, vid: str, day: str, res: CommitResult) -> bool:
        """Close the day if complete, or if two full re-fetches >= 1 h apart returned the same rows."""
        if res.failed:
            return False
        v = VENUES[vid]
        now = self.clock.now_ms()
        frame = res.frame
        n = 0 if frame is None else frame.height
        if n == expected_minutes(v, day):
            self.mark_closed(vid, day, frame)
            return True
        h = content_hash(frame) if frame is not None else content_hash(frame_from_rows([]))
        row = self.catalog.get_day(vid, day)
        if row is None:
            self.catalog.upsert_day(vid, day, status="open", n_rows=n, expected_minutes=expected_minutes(v, day),
                                    missing_minutes=expected_minutes(v, day) - n)
            row = self.catalog.get_day(vid, day)
        if row["pending_refetch_hash"] == h and row["pending_refetch_at"] is not None \
                and now - row["pending_refetch_at"] >= REFETCH_AGREE_MS:
            if n == 0 and v.continuous_grid:
                self.catalog.add_check(vid, day, "empty_day", "warn",
                                       "no rows for the whole day; this venue returns a continuous grid so it "
                                       "looks like a fetch fault - day stays open", now)
                return False
            self.mark_closed(vid, day, frame)
            log.warning("%s %s closed with %d missing minutes (two identical re-fetches)", vid, day,
                        expected_minutes(v, day) - n)
            return True
        if row["pending_refetch_hash"] != h:
            self.catalog.upsert_day(vid, day, pending_refetch_hash=h, pending_refetch_at=now)
        return False
