"""SQLite catalog: per-day status, gaps, Binance archive versions, checks, venue state and runs.

The Parquet files are the source of truth; ``days`` and ``gaps`` can be rebuilt from them (``ewave-data reindex``).
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS days (
    venue TEXT NOT NULL,
    day TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',          -- open | closed
    n_rows INTEGER NOT NULL DEFAULT 0,
    expected_minutes INTEGER,
    missing_minutes INTEGER,
    first_ts INTEGER,
    last_ts INTEGER,
    last_traded_close REAL,
    content_hash TEXT,
    file_sha256 TEXT,
    source TEXT,                                  -- rest | archive
    revision INTEGER NOT NULL DEFAULT 0,
    pending_refetch_hash TEXT,
    pending_refetch_at INTEGER,
    fetched_at INTEGER,
    PRIMARY KEY (venue, day)
);
CREATE TABLE IF NOT EXISTS gaps (
    venue TEXT NOT NULL,
    start_ts INTEGER NOT NULL,
    end_ts INTEGER NOT NULL,
    minutes INTEGER NOT NULL,
    PRIMARY KEY (venue, start_ts)
);
CREATE TABLE IF NOT EXISTS binance_archive (
    day TEXT NOT NULL,
    etag TEXT NOT NULL,
    last_modified TEXT,
    size INTEGER,
    zip_sha256 TEXT,
    checksum_ok INTEGER,
    n_rows INTEGER,
    missing_minutes INTEGER,
    first_seen_at INTEGER,
    checked_at INTEGER,
    outcome TEXT,
    PRIMARY KEY (day, etag)
);
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue TEXT,
    day TEXT,
    kind TEXT NOT NULL,
    result TEXT NOT NULL,                         -- ok | info | warn | fail | flag | changed
    detail TEXT,
    at INTEGER NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS checks_venue_day ON checks (venue, day, kind);
CREATE TABLE IF NOT EXISTS venues (
    venue TEXT PRIMARY KEY,
    covered_until INTEGER,
    cooldown_until INTEGER,
    cooldown_step INTEGER NOT NULL DEFAULT 0,
    consecutive_lock_skips INTEGER NOT NULL DEFAULT 0,
    last_ok_run INTEGER,
    last_attempt INTEGER,
    last_error TEXT
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,                           -- sync | audit | backfill
    venue TEXT,
    started_at INTEGER NOT NULL,
    finished_at INTEGER,
    ok INTEGER,
    summary TEXT
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

DAY_FIELDS = {
    "status", "n_rows", "expected_minutes", "missing_minutes", "first_ts", "last_ts", "last_traded_close",
    "content_hash", "file_sha256", "source", "revision", "pending_refetch_hash", "pending_refetch_at", "fetched_at",
}
VENUE_FIELDS = {
    "covered_until", "cooldown_until", "cooldown_step", "consecutive_lock_skips", "last_ok_run", "last_attempt",
    "last_error",
}


class Catalog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("PRAGMA busy_timeout=30000")
        self.con.execute("PRAGMA synchronous=NORMAL")
        self.con.executescript(SCHEMA)

    def close(self) -> None:
        self.con.close()

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        """One short write transaction."""
        self.con.execute("BEGIN IMMEDIATE")
        try:
            yield self.con
        except BaseException:
            self.con.execute("ROLLBACK")
            raise
        else:
            self.con.execute("COMMIT")

    # ---- days ---------------------------------------------------------------
    def get_day(self, venue: str, day: str) -> dict[str, Any] | None:
        r = self.con.execute("SELECT * FROM days WHERE venue=? AND day=?", (venue, day)).fetchone()
        return dict(r) if r else None

    def upsert_day(self, venue: str, day: str, **fields: Any) -> None:
        bad = set(fields) - DAY_FIELDS
        if bad:
            raise KeyError(f"unknown days fields: {sorted(bad)}")
        with self.tx() as con:
            con.execute("INSERT OR IGNORE INTO days (venue, day) VALUES (?, ?)", (venue, day))
            if fields:
                sets = ", ".join(f"{k}=?" for k in fields)
                con.execute(f"UPDATE days SET {sets} WHERE venue=? AND day=?", (*fields.values(), venue, day))

    def days(self, venue: str, *, status: str | None = None, before: str | None = None,
             after: str | None = None) -> list[dict[str, Any]]:
        q, args = "SELECT * FROM days WHERE venue=?", [venue]
        if status:
            q += " AND status=?"
            args.append(status)
        if before:
            q += " AND day<?"
            args.append(before)
        if after:
            q += " AND day>?"
            args.append(after)
        return [dict(r) for r in self.con.execute(q + " ORDER BY day", args)]

    def delete_days(self, venue: str) -> None:
        with self.tx() as con:
            con.execute("DELETE FROM days WHERE venue=?", (venue,))
            con.execute("DELETE FROM gaps WHERE venue=?", (venue,))

    def last_ts(self, venue: str) -> int | None:
        r = self.con.execute("SELECT MAX(last_ts) AS m FROM days WHERE venue=?", (venue,)).fetchone()
        return r["m"]

    def max_closed_day(self, venue: str) -> str | None:
        r = self.con.execute("SELECT MAX(day) AS m FROM days WHERE venue=? AND status='closed'", (venue,)).fetchone()
        return r["m"]

    def last_traded_close_before(self, venue: str, day: str) -> float | None:
        r = self.con.execute(
            "SELECT last_traded_close FROM days WHERE venue=? AND day<? AND last_traded_close IS NOT NULL "
            "ORDER BY day DESC LIMIT 1", (venue, day)).fetchone()
        return r["last_traded_close"] if r else None

    # ---- gaps ---------------------------------------------------------------
    def replace_gaps(self, venue: str, lo_ms: int, hi_ms: int, gaps: list[tuple[int, int, int]]) -> None:
        """Replace all recorded gaps that start within [lo_ms, hi_ms]."""
        with self.tx() as con:
            con.execute("DELETE FROM gaps WHERE venue=? AND start_ts BETWEEN ? AND ?", (venue, lo_ms, hi_ms))
            con.executemany("INSERT OR REPLACE INTO gaps (venue, start_ts, end_ts, minutes) VALUES (?,?,?,?)",
                            [(venue, s, e, m) for s, e, m in gaps])

    def gaps(self, venue: str | None = None, since_ms: int | None = None) -> list[dict[str, Any]]:
        q, args = "SELECT * FROM gaps WHERE 1=1", []
        if venue:
            q += " AND venue=?"
            args.append(venue)
        if since_ms is not None:
            q += " AND end_ts>=?"
            args.append(since_ms)
        return [dict(r) for r in self.con.execute(q + " ORDER BY venue, start_ts", args)]

    # ---- checks ---------------------------------------------------------------
    def add_check(self, venue: str | None, day: str | None, kind: str, result: str, detail: str, at: int) -> None:
        with self.tx() as con:
            con.execute("INSERT INTO checks (venue, day, kind, result, detail, at) VALUES (?,?,?,?,?,?)",
                        (venue, day, kind, result, detail[:2000], at))

    def last_check_detail(self, venue: str, day: str, kind: str) -> str | None:
        r = self.con.execute("SELECT detail FROM checks WHERE venue=? AND day=? AND kind=? ORDER BY id DESC LIMIT 1",
                             (venue, day, kind)).fetchone()
        return r["detail"] if r else None

    def resolve_checks(self, venue: str, day: str, kind: str) -> None:
        with self.tx() as con:
            con.execute("UPDATE checks SET resolved=1 WHERE venue=? AND day=? AND kind=? AND resolved=0",
                        (venue, day, kind))

    def checks(self, *, venue: str | None = None, kind: str | None = None, unresolved_only: bool = False,
               result: str | None = None, since_ms: int | None = None, limit: int = 200) -> list[dict[str, Any]]:
        q, args = "SELECT * FROM checks WHERE 1=1", []
        for col, val in (("venue", venue), ("kind", kind), ("result", result)):
            if val:
                q += f" AND {col}=?"
                args.append(val)
        if unresolved_only:
            q += " AND resolved=0"
        if since_ms is not None:
            q += " AND at>=?"
            args.append(since_ms)
        return [dict(r) for r in self.con.execute(q + " ORDER BY id DESC LIMIT ?", (*args, limit))]

    # ---- venues -------------------------------------------------------------------
    def venue_state(self, venue: str) -> dict[str, Any]:
        with self.tx() as con:
            con.execute("INSERT OR IGNORE INTO venues (venue) VALUES (?)", (venue,))
        return dict(self.con.execute("SELECT * FROM venues WHERE venue=?", (venue,)).fetchone())

    def update_venue(self, venue: str, **fields: Any) -> None:
        bad = set(fields) - VENUE_FIELDS
        if bad:
            raise KeyError(f"unknown venues fields: {sorted(bad)}")
        with self.tx() as con:
            con.execute("INSERT OR IGNORE INTO venues (venue) VALUES (?)", (venue,))
            if fields:
                sets = ", ".join(f"{k}=?" for k in fields)
                con.execute(f"UPDATE venues SET {sets} WHERE venue=?", (*fields.values(), venue))

    def bump_lock_skips(self, venue: str) -> int:
        with self.tx() as con:
            con.execute("INSERT OR IGNORE INTO venues (venue) VALUES (?)", (venue,))
            con.execute("UPDATE venues SET consecutive_lock_skips=consecutive_lock_skips+1 WHERE venue=?", (venue,))
        return self.venue_state(venue)["consecutive_lock_skips"]

    # ---- binance archive ---------------------------------------------------------------
    def archive_rows(self, day: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self.con.execute("SELECT * FROM binance_archive WHERE day=? ORDER BY first_seen_at",
                                                  (day,))]

    def archive_verified(self, day: str, etag: str) -> bool:
        """True if this exact archive version (ETag) was already downloaded and its checksum verified."""
        return self.con.execute("SELECT 1 FROM binance_archive WHERE day=? AND etag=? AND checksum_ok=1",
                                (day, etag)).fetchone() is not None

    def upsert_archive(self, day: str, etag: str, **fields: Any) -> None:
        with self.tx() as con:
            con.execute("INSERT OR IGNORE INTO binance_archive (day, etag) VALUES (?, ?)", (day, etag))
            if fields:
                sets = ", ".join(f"{k}=?" for k in fields)
                con.execute(f"UPDATE binance_archive SET {sets} WHERE day=? AND etag=?", (*fields.values(), day, etag))

    def verified_archive_days(self) -> set[str]:
        return {r["day"] for r in self.con.execute("SELECT DISTINCT day FROM binance_archive WHERE checksum_ok=1")}

    # ---- runs & meta ---------------------------------------------------------------
    def start_run(self, kind: str, at: int, venue: str | None = None) -> int:
        with self.tx() as con:
            cur = con.execute("INSERT INTO runs (kind, venue, started_at) VALUES (?,?,?)", (kind, venue, at))
            return int(cur.lastrowid)

    def finish_run(self, run_id: int, at: int, ok: bool, summary: str) -> None:
        with self.tx() as con:
            con.execute("UPDATE runs SET finished_at=?, ok=?, summary=? WHERE id=?",
                        (at, 1 if ok else 0, summary[:4000], run_id))

    def last_run(self, kind: str, *, ok_only: bool = False) -> dict[str, Any] | None:
        q = "SELECT * FROM runs WHERE kind=? AND finished_at IS NOT NULL"
        if ok_only:
            q += " AND ok=1"
        r = self.con.execute(q + " ORDER BY id DESC LIMIT 1", (kind,)).fetchone()
        return dict(r) if r else None

    def first_run_at(self) -> int | None:
        return self.con.execute("SELECT MIN(started_at) AS m FROM runs").fetchone()["m"]

    def get_meta(self, key: str) -> str | None:
        r = self.con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return r["value"] if r else None

    def set_meta(self, key: str, value: str) -> None:
        with self.tx() as con:
            con.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)", (key, value))
