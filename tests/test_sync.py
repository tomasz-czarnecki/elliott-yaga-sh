from __future__ import annotations

from datetime import UTC, datetime

import polars as pl

from ewave.data import load_bars, load_1m
from ewave.ingest import health
from ewave.ingest.audit import run_audit
from ewave.ingest.backfill import backfill
from ewave.ingest.config import DAY_MS, MINUTE_MS, day_start_ms, utc_ms
from ewave.ingest.http import CooldownError, RetryableError
from ewave.ingest.locks import VenueLock
from ewave.ingest.schema import make_row

from .fakes import T0, synth_row

BYBIT = "bybit_btcusdt_perp"
BINANCE = "binance_btcusdt"
BITSTAMP = "bitstamp_btcusd"
D18, D19, D20, D21 = (day_start_ms(f"2026-10-{d}") for d in (18, 19, 20, 21))


def seed(c, vid, since="2026-10-18"):
    rep = backfill(c, vid, since=since)
    assert rep.status == "ok", rep.line()
    return rep


def day_ts(c, vid, day):
    df = c.store.read_day(vid, day)
    return [] if df is None else df["ts"].to_list()


def contiguous(ts):
    return all(b - a == MINUTE_MS for a, b in zip(ts, ts[1:]))


def last_closed_of(now_ms):
    return now_ms - now_ms % MINUTE_MS - MINUTE_MS


# ---- backfill + sync basics ------------------------------------------------------------------------


def test_backfill_closes_complete_days_and_leaves_today_open(make_collector, clock):
    c = make_collector([BYBIT])
    seed(c, BYBIT)
    st = {r["day"]: r["status"] for r in c.catalog.days(BYBIT)}
    assert st == {"2026-10-18": "closed", "2026-10-19": "closed", "2026-10-20": "open"}
    assert len(day_ts(c, BYBIT, "2026-10-19")) == 1440
    assert c.catalog.last_ts(BYBIT) == last_closed_of(T0)  # never the forming minute
    assert c.catalog.venue_state(BYBIT)["covered_until"] == last_closed_of(T0) + MINUTE_MS
    # bars exist for every timeframe and the closed days are complete
    for tf in ("15m", "1h", "4h", "1d"):
        b = c.store.read_bars_year(BYBIT, tf, 2026)
        assert b is not None and b.height > 0
    assert load_bars(BYBIT, "1d", "2026-10-18", "2026-10-20", root=c.root)["complete"].all()


def test_backfill_is_resumable_and_skips_closed_days(make_collector):
    c = make_collector([BYBIT])
    seed(c, BYBIT)
    src = c.sources[BYBIT]
    n = len(src.requests)
    seed(c, BYBIT)
    new = src.requests[n:]
    assert all(s >= D20 for s, _ in new), new  # only today is fetched again


def test_sync_adds_new_minutes_and_never_stores_the_forming_minute(make_collector, clock):
    c = make_collector([BYBIT])
    seed(c, BYBIT)
    clock.advance(15 * 60)  # 12:22:20 -> last closed minute 12:21
    [rep] = c.sync([BYBIT])
    assert rep.status == "ok"
    src = c.sources[BYBIT]
    assert src.requests[-1][1] == last_closed_of(clock.now_ms())
    ts = day_ts(c, BYBIT, "2026-10-20")
    assert ts[-1] == last_closed_of(clock.now_ms()) and contiguous(ts) and ts[0] == D20
    # overlap: the sync re-fetched the last 3 hours
    assert src.requests[-1][0] == last_closed_of(T0) - 180 * MINUTE_MS


def test_sync_refuses_to_run_without_a_backfill(make_collector):
    c = make_collector([BYBIT])
    [rep] = c.sync([BYBIT])
    assert rep.status == "no_data" and "backfill" in rep.message


def test_catch_up_after_30_hours_loses_nothing(make_collector, clock):
    c = make_collector([BYBIT])
    seed(c, BYBIT)
    clock.advance(30 * 3600)  # 2026-10-21 18:07:20
    [rep] = c.sync([BYBIT])
    assert rep.status == "ok"
    assert len(day_ts(c, BYBIT, "2026-10-20")) == 1440 and contiguous(day_ts(c, BYBIT, "2026-10-20"))
    ts21 = day_ts(c, BYBIT, "2026-10-21")
    assert ts21[0] == D21 and ts21[-1] == last_closed_of(clock.now_ms()) and contiguous(ts21)
    assert c.catalog.get_day(BYBIT, "2026-10-20")["status"] == "closed"


# ---- closing days ---------------------------------------------------------------------------------------


def test_yesterday_closes_only_after_the_grace_period(make_collector, clock):
    c = make_collector([BYBIT])
    seed(c, BYBIT)
    clock.set(D21 + 5 * MINUTE_MS + 20_000)  # 00:05:20
    c.sync([BYBIT])
    assert c.catalog.get_day(BYBIT, "2026-10-20")["status"] == "open"
    assert len(day_ts(c, BYBIT, "2026-10-20")) == 1440  # data complete, but not closed before 00:10
    clock.set(D21 + 15 * MINUTE_MS + 20_000)
    [rep] = c.sync([BYBIT])
    assert c.catalog.get_day(BYBIT, "2026-10-20")["status"] == "closed" and rep.days_closed >= 1
    bars = load_bars(BYBIT, "1d", "2026-10-20", "2026-10-21", root=c.root)
    assert bars.height == 1 and bars["complete"][0] is True


def test_day_with_missing_minutes_closes_after_two_agreeing_refetches_an_hour_apart(make_collector, clock):
    hole = lambda t: D19 + 600 * MINUTE_MS <= t < D19 + 620 * MINUTE_MS  # a real 20-minute outage
    c = make_collector([BINANCE], **{BINANCE: dict(holes=hole)})
    seed(c, BINANCE)
    row = c.catalog.get_day(BINANCE, "2026-10-19")
    assert row["status"] == "open" and row["n_rows"] == 1420 and row["pending_refetch_hash"]
    clock.advance(10 * 60)
    c.sync([BINANCE])
    assert c.catalog.get_day(BINANCE, "2026-10-19")["status"] == "open"  # < 1 h since the first fetch
    clock.advance(55 * 60)
    c.sync([BINANCE])
    row = c.catalog.get_day(BINANCE, "2026-10-19")
    assert row["status"] == "closed" and row["missing_minutes"] == 20
    gaps = [g for g in c.catalog.gaps(BINANCE) if g["start_ts"] >= D19]
    assert [(g["start_ts"], g["minutes"]) for g in gaps] == [(D19 + 600 * MINUTE_MS, 20)]


def test_a_changed_refetch_restarts_the_wait(make_collector, clock):
    c = make_collector([BINANCE], **{BINANCE: dict(holes=lambda t: D19 + 600 * MINUTE_MS <= t < D19 + 620 * MINUTE_MS)})
    seed(c, BINANCE)
    clock.advance(40 * 60)
    c.sync([BINANCE])
    c.sources[BINANCE].holes = lambda t: D19 + 600 * MINUTE_MS <= t < D19 + 610 * MINUTE_MS  # half of it appears
    clock.advance(40 * 60)
    c.sync([BINANCE])
    assert c.catalog.get_day(BINANCE, "2026-10-19")["status"] == "open"  # content changed -> not "two agreeing"
    clock.advance(65 * 60)
    c.sync([BINANCE])
    row = c.catalog.get_day(BINANCE, "2026-10-19")
    assert row["status"] == "closed" and row["missing_minutes"] == 10


def test_empty_day_never_closes_on_a_continuous_grid_venue_but_does_on_binance(make_collector, clock):
    empty19 = lambda t: D19 <= t < D20
    c = make_collector([BYBIT, BINANCE], **{BYBIT: dict(holes=empty19), BINANCE: dict(holes=empty19)})
    seed(c, BYBIT)
    seed(c, BINANCE)
    for _ in range(3):
        clock.advance(65 * 60)
        c.sync([BYBIT, BINANCE])
    assert c.catalog.get_day(BYBIT, "2026-10-19")["status"] == "open"  # a whole missing day on a continuous grid = fetch fault
    assert any(k["kind"] == "empty_day" for k in c.catalog.checks(venue=BYBIT))
    row = c.catalog.get_day(BINANCE, "2026-10-19")
    assert row["status"] == "closed" and row["n_rows"] == 0 and row["missing_minutes"] == 1440
    assert c.store.read_day(BINANCE, "2026-10-19") is None  # catalog-only row, no file


# ---- idempotency and revisions -----------------------------------------------------------------------------


def test_running_sync_twice_changes_nothing(make_collector, clock):
    c = make_collector([BYBIT])
    seed(c, BYBIT)
    clock.set(D21 + 30 * MINUTE_MS + 20_000)
    c.sync([BYBIT])
    before = {r["day"]: (r["content_hash"], r["revision"], r["file_sha256"]) for r in c.catalog.days(BYBIT)}
    mtimes = {p: p.stat().st_mtime_ns for p in c.root.rglob("*.parquet")}
    c.sync([BYBIT])
    after = {r["day"]: (r["content_hash"], r["revision"], r["file_sha256"]) for r in c.catalog.days(BYBIT)}
    assert before == after
    assert all(p.stat().st_mtime_ns == m for p, m in mtimes.items() if "2026-10-19" in p.name or "2026-10-18" in p.name)
    assert not c.catalog.checks(kind="revision")


def test_closed_day_that_changes_keeps_the_old_version(make_collector, clock):
    c = make_collector([BYBIT])
    seed(c, BYBIT)
    old = c.store.read_day(BYBIT, "2026-10-19")
    t = D19 + 300 * MINUTE_MS
    src = c.sources[BYBIT]
    r = list(synth_row(src.venue, t))
    r[5] += 5.0  # exchange corrects a volume after the fact
    src.overrides[t] = tuple(r)
    rep = run_audit(c, [BYBIT])
    assert rep.ok
    row = c.catalog.get_day(BYBIT, "2026-10-19")
    assert row["revision"] == 1 and row["status"] == "closed"
    sup = c.store.superseded_path(BYBIT, "2026-10-19", 0)
    assert sup.exists()
    import polars as pl
    from ewave.ingest.schema import from_disk
    assert from_disk(pl.read_parquet(sup)).equals(old)
    assert c.catalog.checks(kind="revision")


# ---- failure handling ---------------------------------------------------------------------------------------------


def test_a_failed_fetch_leaves_the_forming_bar_incomplete(make_collector, clock):
    c = make_collector([BYBIT])
    seed(c, BYBIT)
    src = c.sources[BYBIT]
    src.fail_with = RetryableError("network down")
    clock.advance(4 * 3600)  # 16:07:20
    [rep] = c.sync([BYBIT])
    assert rep.status == "failed"
    last = load_bars(BYBIT, "1h", "2026-10-20", "2026-10-21", root=c.root)
    assert last["ts"].dt.hour().max() == 11  # the 12:00 bar was incomplete when covered_until stopped at 12:07
    full = load_bars(BYBIT, "1h", "2026-10-20", "2026-10-21", complete_only=False, root=c.root)
    assert full["complete"].to_list()[-1] is False
    src.fail_with = None
    [rep] = c.sync([BYBIT])
    assert rep.status == "ok"
    assert load_bars(BYBIT, "1h", "2026-10-20", "2026-10-21", root=c.root)["ts"].dt.hour().max() == 15


def test_one_venue_failing_does_not_block_the_others(make_collector, clock):
    c = make_collector([BYBIT, BITSTAMP])
    seed(c, BYBIT)
    seed(c, BITSTAMP)
    c.sources[BYBIT].fail_with = RetryableError("bybit is down")
    clock.advance(15 * 60)
    reports = {r.venue: r for r in c.sync()}
    assert reports[BYBIT].status == "failed" and reports[BITSTAMP].status == "ok"
    assert c.catalog.last_ts(BITSTAMP) == last_closed_of(clock.now_ms())
    assert c.catalog.last_ts(BYBIT) == last_closed_of(T0)
    assert "bybit is down" in c.catalog.venue_state(BYBIT)["last_error"]


def test_cooldown_is_respected_and_doubles(make_collector, clock):
    c = make_collector([BYBIT])
    seed(c, BYBIT)
    src = c.sources[BYBIT]
    src.fail_with = CooldownError("HTTP 403", 600.0)
    clock.advance(15 * 60)
    [rep] = c.sync([BYBIT])
    assert rep.status == "failed"
    until1 = c.catalog.venue_state(BYBIT)["cooldown_until"]
    assert until1 == clock.now_ms() + 600_000
    n = len(src.requests)
    src.fail_with = None
    clock.advance(5 * 60)
    [rep] = c.sync([BYBIT])
    assert rep.status == "cooldown" and len(src.requests) == n  # no request while cooling down
    clock.advance(6 * 60)
    [rep] = c.sync([BYBIT])
    assert rep.status == "ok" and c.catalog.venue_state(BYBIT)["cooldown_step"] == 0
    # a repeated ban doubles
    src.fail_with = CooldownError("HTTP 403", 600.0)
    clock.advance(15 * 60)
    c.sync([BYBIT])
    src.fail_with = CooldownError("HTTP 403", 600.0)
    clock.advance(11 * 60)
    c.sync([BYBIT])
    assert c.catalog.venue_state(BYBIT)["cooldown_until"] - clock.now_ms() == 600_000 * 2


def test_a_busy_lock_skips_the_venue_and_is_reported_after_four_in_a_row(make_collector, clock):
    c = make_collector([BYBIT])
    seed(c, BYBIT)
    holder = VenueLock(c.store.state_dir, BYBIT, "ewave-data backfill --venue bybit")
    assert holder.acquire(0)
    try:
        for i in range(4):
            clock.advance(15 * 60)
            [rep] = c.sync([BYBIT])
            assert rep.status == "skipped_lock" and "backfill" in rep.message
        assert any("lock was busy" in p for p in health.problems(c, [BYBIT]))
    finally:
        holder.release()
    clock.advance(15 * 60)
    [rep] = c.sync([BYBIT])
    assert rep.status == "ok" and c.catalog.venue_state(BYBIT)["consecutive_lock_skips"] == 0


def test_hard_validation_failure_blocks_only_that_day(make_collector, clock):
    c = make_collector([BYBIT])
    seed(c, BYBIT)
    src = c.sources[BYBIT]
    clock.advance(30 * 60)
    t = last_closed_of(clock.now_ms()) - 10 * MINUTE_MS
    bad = list(synth_row(src.venue, t))
    bad[2], bad[3] = 1.0, 2.0  # high < low
    src.overrides[t] = tuple(bad)
    before = c.store.read_day(BYBIT, "2026-10-20")
    [rep] = c.sync([BYBIT])
    assert c.store.read_day(BYBIT, "2026-10-20").equals(before)  # nothing written for the bad day
    assert c.catalog.checks(venue=BYBIT, kind="validation", unresolved_only=True)
    assert any("validation failure" in p for p in health.problems(c, [BYBIT]))
    # the exchange fixes the row -> the next sync writes the day and clears the failure
    del src.overrides[t]
    c.sync([BYBIT])
    assert c.catalog.last_ts(BYBIT) == last_closed_of(clock.now_ms())
    assert not c.catalog.checks(venue=BYBIT, kind="validation", unresolved_only=True)


def test_covered_until_stops_at_a_recent_hole_but_not_an_old_one(make_collector, clock):
    hole_t = utc_ms(2026, 10, 20, 12, 40)
    c = make_collector([BYBIT], **{BYBIT: dict(holes=lambda t: t == hole_t)})
    seed(c, BYBIT)
    clock.advance(40 * 60)  # 12:47:20, the hole at 12:40 is recent
    c.sync([BYBIT])
    assert c.catalog.venue_state(BYBIT)["covered_until"] == hole_t
    bars = load_bars(BYBIT, "15m", "2026-10-20 12:00", "2026-10-20 13:00", root=c.root)
    assert bars["ts"].dt.minute().to_list() == [0, 15]  # the 12:30 bar contains the hole -> not complete
    c.sources[BYBIT].holes = lambda t: False  # the exchange fills it in
    clock.advance(15 * 60)
    c.sync([BYBIT])
    assert c.catalog.venue_state(BYBIT)["covered_until"] == last_closed_of(clock.now_ms()) + MINUTE_MS
    # a hole older than the 3-hour overlap can no longer be healed by sync: recorded as a gap, does not block
    c.sources[BYBIT].holes = lambda t: t == utc_ms(2026, 10, 20, 12, 5)
    clock.advance(4 * 3600)
    c.sync([BYBIT])
    assert c.catalog.venue_state(BYBIT)["covered_until"] == last_closed_of(clock.now_ms()) + MINUTE_MS


def test_clock_skew_between_local_and_server(make_collector, clock):
    c = make_collector([BYBIT])
    seed(c, BYBIT)
    src = c.sources[BYBIT]
    clock.advance(15 * 60)
    src.server_offset_ms = -10_000  # server 10 s behind: use the earlier time, warn
    [rep] = c.sync([BYBIT])
    assert rep.status == "ok"
    assert src.requests[-1][1] == last_closed_of(clock.now_ms() - 10_000)
    assert c.catalog.checks(kind="clock")
    src.server_offset_ms = 90_000
    [rep] = c.sync([BYBIT])
    assert rep.status == "failed" and "differs" in rep.message


def test_loader_reads_only_the_requested_period(make_collector, clock):
    c = make_collector([BITSTAMP])
    seed(c, BITSTAMP)
    df = load_1m(BITSTAMP, "2026-10-19 23:30", "2026-10-20 00:30", root=c.root, warn=False)
    assert df.height == 60 and df["ts"].dt.date().n_unique() == 2
    assert df["ts"][0] == datetime(2026, 10, 19, 23, 30, tzinfo=UTC)
    full = load_bars(BITSTAMP, "1h", "2026-10-19", "2026-10-20", root=c.root)
    assert full.height == 24 and full["n_minutes"].to_list() == [60] * 24


def test_a_persistent_soft_warning_is_logged_once_not_every_run(make_collector, clock):
    c = make_collector([BYBIT])
    seed(c, BYBIT)  # the synthetic Bybit candles do not chain open == previous close, so soft warnings occur
    for _ in range(3):
        clock.advance(15 * 60)
        c.sync([BYBIT])
    soft = [k for k in c.catalog.checks(venue=BYBIT, kind="soft") if k["day"] == "2026-10-20"]
    assert len(soft) == 1  # the same warning type with a growing count is not logged again on every run
