from __future__ import annotations

import os
import signal
import subprocess
import sys
import textwrap
import time

import polars as pl
import pytest

from ewave.ingest.config import MINUTE_MS, VENUES, day_start_ms
from ewave.ingest.locks import VenueLock, is_held, read_holder
from ewave.ingest.schema import frame_from_rows
from ewave.ingest.store import Store, atomic_write

from .fakes import synth_row

V = VENUES["bybit_btcusdt_perp"]
DAY = "2026-10-20"


def frame(n=10, shift=0):
    d0 = day_start_ms(DAY)
    return frame_from_rows([synth_row(V, d0 + i * MINUTE_MS) for i in range(n)])


def test_atomic_write_failure_leaves_the_old_file_and_no_temp_file(tmp_path):
    store = Store(tmp_path)
    store.write_day(V.id, DAY, frame(10))
    path = store.raw_path(V.id, DAY)
    before = path.read_bytes()

    def boom(f):
        f.write(b"partial garbage")
        raise RuntimeError("disk full")

    with pytest.raises(RuntimeError):
        atomic_write(path, boom)
    assert path.read_bytes() == before
    assert not [p for p in path.parent.iterdir() if ".tmp-" in p.name]


def test_cleanup_removes_temp_files_of_dead_processes_only(tmp_path):
    store = Store(tmp_path)
    store.write_day(V.id, DAY, frame())
    d = store.raw_path(V.id, DAY).parent
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    (d / f".{DAY}.parquet.tmp-{dead.pid}").write_bytes(b"x")
    alive = d / f".other.parquet.tmp-{os.getpid()}"
    alive.write_bytes(b"x")
    assert store.cleanup_tmp(V.id) == 1
    assert alive.exists() and not list(d.glob(f".{DAY}.parquet.tmp-*"))
    assert store.raw_path(V.id, DAY).exists()  # real files untouched


def test_sigterm_during_a_write_leaves_no_partial_file(tmp_path):
    """The CLI turns SIGTERM into SystemExit; the writer must clean up its temp file when that happens."""
    ready = tmp_path / "ready"
    script = textwrap.dedent(f"""
        import signal, sys, time
        from pathlib import Path
        from ewave.ingest.store import atomic_write
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
        target = Path({str(tmp_path / 'out' / 'x.parquet')!r})
        def writer(f):
            f.write(b"half a file")
            Path({str(ready)!r}).write_text("go")
            time.sleep(30)
        atomic_write(target, writer)
    """)
    p = subprocess.Popen([sys.executable, "-c", script])
    for _ in range(100):
        if ready.exists():
            break
        time.sleep(0.1)
    assert ready.exists()
    p.send_signal(signal.SIGTERM)
    assert p.wait(timeout=10) == 143
    out = tmp_path / "out"
    assert not (out / "x.parquet").exists()
    assert not [x for x in out.iterdir() if ".tmp-" in x.name]


def test_supersede_keeps_the_old_content_after_the_file_is_replaced(tmp_path):
    store = Store(tmp_path)
    store.write_day(V.id, DAY, frame(10))
    store.supersede(V.id, DAY, 0)
    store.write_day(V.id, DAY, frame(20))
    assert store.read_day(V.id, DAY).height == 20
    old = pl.read_parquet(store.superseded_path(V.id, DAY, 0))
    assert old.height == 10


def test_splice_bars_replaces_one_day_and_reports_no_change_when_equal(tmp_path):
    from ewave.ingest.resample import resample_day

    store = Store(tmp_path)
    d19, d20 = "2026-10-19", "2026-10-20"
    f19 = frame_from_rows([synth_row(V, day_start_ms(d19) + i * MINUTE_MS) for i in range(1440)])
    f20 = frame_from_rows([synth_row(V, day_start_ms(d20) + i * MINUTE_MS) for i in range(1440)])
    b19 = resample_day(f19, V, d19, "1h", 1000.0, 10**15, True)
    b20 = resample_day(f20, V, d20, "1h", 1000.0, 10**15, True)
    assert store.splice_bars(V.id, "1h", d19, b19) is True
    assert store.splice_bars(V.id, "1h", d20, b20) is True
    assert store.splice_bars(V.id, "1h", d20, b20) is False  # unchanged -> no write
    assert store.read_bars_year(V.id, "1h", 2026).height == 48
    changed = resample_day(f20.head(600), V, d20, "1h", 1000.0, day_start_ms(d20) + 600 * MINUTE_MS, False)
    assert store.splice_bars(V.id, "1h", d20, changed) is True
    year = store.read_bars_year(V.id, "1h", 2026)
    assert year.height == 24 + changed.height and year["ts"].is_sorted()


def test_lock_blocks_a_second_holder_reports_the_holder_and_is_never_deleted(tmp_path):
    a = VenueLock(tmp_path, V.id, "ewave-data backfill")
    assert a.acquire(0)
    b = VenueLock(tmp_path, V.id, "ewave-data sync")
    assert not b.acquire(0)
    assert is_held(tmp_path, V.id) and "backfill" in read_holder(tmp_path, V.id)
    a.release()
    assert not is_held(tmp_path, V.id)
    assert (tmp_path / f"{V.id}.lock").exists()  # the lock file stays
    assert b.acquire(0)
    b.release()


def test_lock_is_released_when_the_holder_process_dies(tmp_path):
    script = textwrap.dedent(f"""
        import time
        from pathlib import Path
        from ewave.ingest.locks import VenueLock
        l = VenueLock(Path({str(tmp_path)!r}), {V.id!r}, "crashy")
        assert l.acquire(0)
        Path({str(tmp_path / 'held')!r}).write_text("1")
        time.sleep(60)
    """)
    p = subprocess.Popen([sys.executable, "-c", script])
    for _ in range(100):
        if (tmp_path / "held").exists():
            break
        time.sleep(0.1)
    assert is_held(tmp_path, V.id)
    p.kill()
    p.wait()
    assert not is_held(tmp_path, V.id)  # kill -9 leaves no stale lock
