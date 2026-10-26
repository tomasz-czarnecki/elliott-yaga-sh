from __future__ import annotations

import hashlib

import polars as pl

from ewave.ingest import health
from ewave.ingest.audit import run_audit
from ewave.ingest.backfill import backfill
from ewave.ingest.cli import main as cli_main
from ewave.ingest.config import DAY_MS, MINUTE_MS, VENUES, day_start_ms
from ewave.ingest.maintenance import rebuild, reindex
from ewave.ingest.sources.binance import ArchiveDay, ArchiveEntry, ChecksumPending

from .fakes import T0, synth_row

BN = "binance_btcusdt"
V = VENUES[BN]
D19, D20 = day_start_ms("2026-10-19"), day_start_ms("2026-10-20")


class FakeArchive:
    def __init__(self):
        self.days: dict[str, tuple[str, list]] = {}
        self.pending: set[str] = set()
        self.fetches: list[str] = []

    def set_day(self, day, etag, rows):
        self.days[day] = (etag, rows)

    def full_day(self, day, drop=lambda t: False, tweak=None):
        d0 = day_start_ms(day)
        rows = []
        for t in range(d0, d0 + DAY_MS, MINUTE_MS):
            if drop(t):
                continue
            r = synth_row(V, t)
            rows.append(tweak(r) if tweak else r)
        return rows

    def list_days(self, start_day=None):
        return [ArchiveEntry(d, f"data/.../BTCUSDT-1m-{d}.zip", etag, "Tue, 20 Oct 2026 01:41:38 GMT", 1000)
                for d, (etag, _) in sorted(self.days.items()) if not start_day or d >= start_day]

    def fetch_day(self, day):
        self.fetches.append(day)
        if day in self.pending:
            raise ChecksumPending(day)
        if day not in self.days:
            return None
        etag, rows = self.days[day]
        data = f"zip-{day}-{etag}".encode()
        sha = hashlib.sha256(data).hexdigest()
        return ArchiveDay(day, etag, "Tue, 20 Oct 2026 01:41:38 GMT", len(data), data, f"{sha}  BTCUSDT-1m-{day}.zip", sha, rows)

    def close(self):
        pass


def setup(make_collector, clock, **kw):
    c = make_collector([BN], **kw)
    c.archive = FakeArchive()
    return c, c.archive, c.sources[BN]


def test_backfill_uses_the_archive_for_history_and_rest_only_for_today(make_collector, clock):
    c, arch, rest = setup(make_collector, clock)
    arch.set_day("2026-10-18", "etag18", arch.full_day("2026-10-18"))
    arch.set_day("2026-10-19", "etag19", arch.full_day("2026-10-19"))
    rep = backfill(c, BN, since="2026-10-18")
    assert rep.status == "ok", rep.line()
    for day in ("2026-10-18", "2026-10-19"):
        row = c.catalog.get_day(BN, day)
        assert row["source"] == "archive" and row["status"] == "closed" and row["n_rows"] == 1440
    assert all(s >= D20 for s, _ in rest.requests)  # REST was used for today only
    ar = c.catalog.archive_rows("2026-10-19")
    assert len(ar) == 1 and ar[0]["etag"] == "etag19" and ar[0]["checksum_ok"] == 1 and ar[0]["missing_minutes"] == 0
    assert (c.store.binance_sources_dir() / "BTCUSDT-1m-2026-10-19.etag19.zip").exists()
    assert (c.store.binance_sources_dir() / "BTCUSDT-1m-2026-10-19.etag19.zip.CHECKSUM").exists()
    assert c.catalog.get_day(BN, "2026-10-20")["status"] == "open"


def test_a_truncated_archive_is_completed_from_rest_but_a_real_outage_is_not_invented(make_collector, clock):
    outage = lambda t: D19 + 900 * MINUTE_MS <= t < D19 + 910 * MINUTE_MS  # real: REST lacks these too
    c, arch, rest = setup(make_collector, clock, **{BN: dict(holes=outage)})
    truncated = lambda t: D19 + 100 * MINUTE_MS <= t < D19 + 110 * MINUTE_MS  # archive-only damage
    arch.set_day("2026-10-18", "e18", arch.full_day("2026-10-18"))
    arch.set_day("2026-10-19", "e19", arch.full_day("2026-10-19", drop=lambda t: truncated(t) or outage(t)))
    backfill(c, BN, since="2026-10-18")
    row = c.catalog.get_day(BN, "2026-10-19")
    assert row["n_rows"] == 1430 and row["missing_minutes"] == 10 and row["status"] == "closed"
    assert row["source"] == "rest"  # the more complete copy
    assert [(g["start_ts"], g["minutes"]) for g in c.catalog.gaps(BN) if g["start_ts"] >= D19] == [(D19 + 900 * MINUTE_MS, 10)]
    assert any(k["kind"] == "archive" and "more complete" in k["detail"] for k in c.catalog.checks(venue=BN))


def test_audit_stores_a_new_archive_version_and_keeps_the_old_day(make_collector, clock):
    c, arch, rest = setup(make_collector, clock)
    for d in ("2026-10-18", "2026-10-19"):
        arch.set_day(d, f"e-{d}", arch.full_day(d))
    backfill(c, BN, since="2026-10-18")
    old = c.store.read_day(BN, "2026-10-19")

    rep = run_audit(c, [BN])
    assert rep.ok and "nothing new" in rep.lines[0]  # same ETags -> nothing to do
    fetched = len(arch.fetches)

    # Binance silently re-publishes 2026-10-19 with a corrected volume
    arch.set_day("2026-10-19", "e-new", arch.full_day("2026-10-19", tweak=lambda r: r[:5] + (r[5] + 0.25,) + r[6:]))
    c.catalog.set_meta("binance_full_listing_at", "0")  # force the weekly full listing
    rep = run_audit(c, [BN])
    assert rep.ok and len(arch.fetches) == fetched + 1
    row = c.catalog.get_day(BN, "2026-10-19")
    assert row["revision"] == 1 and row["source"] == "archive"
    assert pl.read_parquet(c.store.superseded_path(BN, "2026-10-19", 0)).height == 1440
    assert c.store.read_day(BN, "2026-10-19")["volume"][0] == old["volume"][0] + 0.25
    assert {r["etag"] for r in c.catalog.archive_rows("2026-10-19")} == {"e-2026-10-19", "e-new"}
    assert (c.store.binance_sources_dir() / "BTCUSDT-1m-2026-10-19.e-new.zip").exists()
    assert (c.store.binance_sources_dir() / "BTCUSDT-1m-2026-10-19.e-2026-10-19.zip").exists()  # old version kept too


def test_an_archive_with_fewer_minutes_never_replaces_ours(make_collector, clock):
    c, arch, rest = setup(make_collector, clock)
    for d in ("2026-10-18", "2026-10-19"):
        arch.set_day(d, f"e-{d}", arch.full_day(d))
    backfill(c, BN, since="2026-10-18")
    before = c.store.read_day(BN, "2026-10-19")
    arch.set_day("2026-10-19", "e-trunc", arch.full_day("2026-10-19", drop=lambda t: t >= D19 + 1000 * MINUTE_MS))
    c.catalog.set_meta("binance_full_listing_at", "0")
    run_audit(c, [BN])
    assert c.store.read_day(BN, "2026-10-19").equals(before)
    assert c.catalog.get_day(BN, "2026-10-19")["revision"] == 0
    assert any(k["result"] == "flag" and "kept ours" in k["detail"] for k in c.catalog.checks(venue=BN, kind="archive"))
    assert [r["outcome"] for r in c.catalog.archive_rows("2026-10-19") if r["etag"] == "e-trunc"] == ["kept_stored_archive_fewer_minutes"]


def test_checksum_not_published_yet_is_retried_never_finalised(make_collector, clock):
    c, arch, rest = setup(make_collector, clock)
    arch.set_day("2026-10-18", "e18", arch.full_day("2026-10-18"))
    arch.pending.add("2026-10-18")
    backfill(c, BN, since="2026-10-18")
    assert not c.catalog.archive_rows("2026-10-18")  # nothing recorded as verified
    assert c.catalog.get_day(BN, "2026-10-18")["source"] == "rest"  # came from the REST sweep in the meantime
    arch.pending.clear()
    c.catalog.set_meta("binance_full_listing_at", "0")
    run_audit(c, [BN])
    assert c.catalog.get_day(BN, "2026-10-18")["source"] == "archive"
    assert c.catalog.archive_rows("2026-10-18")[0]["checksum_ok"] == 1


def test_rest_never_overwrites_an_archive_day_it_only_flags_differences(make_collector, clock):
    c, arch, rest = setup(make_collector, clock)
    arch.set_day("2026-10-19", "e19", arch.full_day("2026-10-19"))
    backfill(c, BN, since="2026-10-19")
    t = D19 + 50 * MINUTE_MS
    rest.overrides[t] = tuple(list(synth_row(V, t))[:5] + [99.0] + list(synth_row(V, t))[6:])
    before = c.store.read_day(BN, "2026-10-19")
    res = c.refetch_day(BN, rest, "2026-10-19", T0)
    assert c.store.read_day(BN, "2026-10-19").equals(before) and not res.written
    assert any(k["kind"] == "rest_vs_archive" for k in c.catalog.checks(venue=BN))


def test_status_complains_about_old_days_without_a_verified_archive(make_collector, clock):
    c, arch, rest = setup(make_collector, clock)
    arch.set_day("2026-10-18", "e18", arch.full_day("2026-10-18"))
    backfill(c, BN, since="2026-10-18")
    assert not [p for p in health.problems(c, [BN]) if "archive" in p]
    clock.advance(9 * 86400)  # nine days later the unarchived 2026-10-19 is "pending" for too long
    c.catalog.update_venue(BN, last_ok_run=clock.now_ms())
    c.catalog.upsert_day(BN, "2026-10-19", status="closed")
    probs = health.problems(c, [BN])
    assert any("no verified archive" in p and "2026-10-19" in p for p in probs)


def test_reindex_and_rebuild_restore_the_catalog_and_bars_from_the_files(make_collector, clock):
    c, arch, rest = setup(make_collector, clock)
    for d in ("2026-10-18", "2026-10-19"):
        arch.set_day(d, f"e-{d}", arch.full_day(d))
    backfill(c, BN, since="2026-10-18")
    # supersede one day so reindex can recover the revision
    c.catalog.set_meta("binance_full_listing_at", "0")
    arch.set_day("2026-10-19", "e-new", arch.full_day("2026-10-19", tweak=lambda r: r[:5] + (r[5] + 1.0,) + r[6:]))
    run_audit(c, [BN])
    want = {r["day"]: (r["status"], r["source"], r["revision"], r["n_rows"], r["content_hash"]) for r in c.catalog.days(BN)}

    clock.advance(3 * 86400)  # reindex treats days older than two days as settled
    msg = reindex(c, BN)
    assert "reindexed 3 day files" in msg
    got = {r["day"]: (r["status"], r["source"], r["revision"], r["n_rows"], r["content_hash"]) for r in c.catalog.days(BN)}
    assert got["2026-10-19"] == want["2026-10-19"] and got["2026-10-18"][0] == "closed"
    assert got["2026-10-20"][0] == "open"  # only data until 12:06 exists, so it is not inferred as closed
    assert c.catalog.verified_archive_days() >= {"2026-10-18", "2026-10-19"}

    bars_before = c.store.read_bars_year(BN, "1h", 2026)
    for p in (c.root / "bars").rglob("*.parquet"):
        p.unlink()
    assert "rebuilt" in rebuild(c, BN)
    bars_after = c.store.read_bars_year(BN, "1h", 2026)
    assert bars_after.select(pl.exclude("complete")).equals(bars_before.select(pl.exclude("complete")))


def test_cli_status_show_and_gaps(make_collector, clock, monkeypatch, capsys):
    c, arch, rest = setup(make_collector, clock, **{BN: dict(holes=lambda t: D19 + 5 * MINUTE_MS <= t < D19 + 8 * MINUTE_MS)})
    arch.set_day("2026-10-19", "e19", arch.full_day("2026-10-19", drop=lambda t: D19 + 5 * MINUTE_MS <= t < D19 + 8 * MINUTE_MS))
    backfill(c, BN, since="2026-10-19")
    monkeypatch.setattr("ewave.ingest.cli.build_collector", lambda: c)
    monkeypatch.setattr(c, "close", lambda: None)
    assert cli_main(["gaps", "--venue", "binance"]) == 0
    assert "3 min" in capsys.readouterr().out
    assert cli_main(["show", "binance", "2026-10-19", "--tf", "1h", "--csv"]) == 0
    assert capsys.readouterr().out.count("\n") == 25  # header + 24 bars
    assert cli_main(["status"]) == 0
    assert "binance_btcusdt" in capsys.readouterr().out
    c.catalog.update_venue(BN, last_ok_run=None)
    assert cli_main(["status", "--check"]) == 1  # silent when fine, one line per problem otherwise
    assert "no successful sync yet" in capsys.readouterr().out
