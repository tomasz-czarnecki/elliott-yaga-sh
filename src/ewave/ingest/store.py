"""File layout and crash-safe writes.

    raw/{venue}/1m/{YYYY}/{YYYY-MM-DD}.parquet     one UTC day of 1m bars (source of truth)
    raw/_superseded/{venue}/{day}.r{N}.parquet     previous version of a closed day whose rows changed
    bars/{venue}/{tf}/{YYYY}.parquet               derived bars (rebuildable cache)
    sources/binance/BTCUSDT-1m-{day}.{etag}.zip    every Binance archive version seen (+ .CHECKSUM)
    state/                                         catalog.sqlite and the venue lock files
"""
from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import BinaryIO

import polars as pl

from .config import UTC, day_start_ms
from .schema import from_disk, to_disk

_TMP_RE = re.compile(r"^\..*\.tmp-(\d+)$")


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def ensure_dir(path: Path) -> None:
    """mkdir -p, fsyncing the parent of every directory that had to be created."""
    missing: list[Path] = []
    p = path
    while not p.exists():
        missing.append(p)
        p = p.parent
    for d in reversed(missing):
        try:
            d.mkdir()
        except FileExistsError:
            pass
        fsync_dir(d.parent)


def atomic_write(path: Path, writer: Callable[[BinaryIO], None]) -> str:
    """temp file in the same directory -> fsync -> os.replace -> fsync directory. Returns sha256 of the file."""
    ensure_dir(path.parent)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        try:
            os.unlink(tmp)  # leftover from an earlier crash of a process that reused this pid
        except FileNotFoundError:
            pass
        with open(tmp, "xb") as f:
            writer(f)
            f.flush()
            os.fsync(f.fileno())
        sha = hashlib.sha256(tmp.read_bytes()).hexdigest()
        os.replace(tmp, path)
        fsync_dir(path.parent)
        return sha
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _write_parquet(df: pl.DataFrame) -> Callable[[BinaryIO], None]:
    def w(f: BinaryIO) -> None:
        df.write_parquet(f, compression="zstd", compression_level=3, statistics=True, row_group_size=262_144)

    return w


class Store:
    def __init__(self, root: Path):
        self.root = Path(root)

    # ---- paths ----------------------------------------------------------------
    @property
    def state_dir(self) -> Path:
        return self.root / "state"

    def raw_dir(self, venue: str) -> Path:
        return self.root / "raw" / venue / "1m"

    def raw_path(self, venue: str, day: str) -> Path:
        return self.raw_dir(venue) / day[:4] / f"{day}.parquet"

    def superseded_path(self, venue: str, day: str, revision: int) -> Path:
        return self.root / "raw" / "_superseded" / venue / f"{day}.r{revision}.parquet"

    def bars_path(self, venue: str, tf: str, year: int | str) -> Path:
        return self.root / "bars" / venue / tf / f"{year}.parquet"

    def binance_sources_dir(self) -> Path:
        return self.root / "sources" / "binance"

    # ---- raw days -------------------------------------------------------------------
    def read_day(self, venue: str, day: str) -> pl.DataFrame | None:
        p = self.raw_path(venue, day)
        if not p.exists():
            return None
        return from_disk(pl.read_parquet(p))

    def write_day(self, venue: str, day: str, df: pl.DataFrame) -> str:
        return atomic_write(self.raw_path(venue, day), _write_parquet(to_disk(df)))

    def supersede(self, venue: str, day: str, revision: int) -> Path | None:
        """Keep the current file of a day as a superseded copy (hard link: no copy, survives the replace)."""
        src = self.raw_path(venue, day)
        if not src.exists():
            return None
        dst = self.superseded_path(venue, day, revision)
        ensure_dir(dst.parent)
        if dst.exists():
            return dst
        os.link(src, dst)
        fsync_dir(dst.parent)
        return dst

    def list_days(self, venue: str) -> list[str]:
        base = self.raw_dir(venue)
        if not base.exists():
            return []
        return sorted(p.stem for p in base.glob("*/*.parquet") if not p.name.startswith("."))

    # ---- derived bars ----------------------------------------------------------------
    def read_bars_year(self, venue: str, tf: str, year: int | str) -> pl.DataFrame | None:
        p = self.bars_path(venue, tf, year)
        return pl.read_parquet(p) if p.exists() else None

    def write_bars_year(self, venue: str, tf: str, year: int | str, df: pl.DataFrame) -> None:
        atomic_write(self.bars_path(venue, tf, year), _write_parquet(df.sort("ts")))

    def splice_bars(self, venue: str, tf: str, day: str, new_disk: pl.DataFrame) -> bool:
        """Replace the bars of one day inside its year file. Returns False if nothing changed."""
        year = day[:4]
        d0 = datetime.fromtimestamp(day_start_ms(day) / 1000, tz=UTC)
        d1 = d0 + timedelta(days=1)
        in_day = (pl.col("ts") >= d0) & (pl.col("ts") < d1)
        existing = self.read_bars_year(venue, tf, year)
        if existing is None:
            if new_disk.height == 0:
                return False
            self.write_bars_year(venue, tf, year, new_disk)
            return True
        old_day = existing.filter(in_day)
        if old_day.height == new_disk.height and old_day.equals(new_disk):
            return False
        out = pl.concat([existing.filter(~in_day), new_disk]).sort("ts")
        self.write_bars_year(venue, tf, year, out)
        return True

    def replace_bars_range(self, venue: str, tf: str, year: int | str, new_disk: pl.DataFrame,
                           lo_ms: int, hi_ms: int) -> bool:
        """Replace every bar with lo_ms <= ts < hi_ms in a year file by ``new_disk`` (written once). False if unchanged."""
        d0 = datetime.fromtimestamp(lo_ms / 1000, tz=UTC)
        d1 = datetime.fromtimestamp(hi_ms / 1000, tz=UTC)
        in_rng = (pl.col("ts") >= d0) & (pl.col("ts") < d1)
        new_disk = new_disk.sort("ts")
        existing = self.read_bars_year(venue, tf, year)
        if existing is None:
            if new_disk.height == 0:
                return False
            self.write_bars_year(venue, tf, year, new_disk)
            return True
        old = existing.filter(in_rng)
        if old.height == new_disk.height and old.equals(new_disk):
            return False
        self.write_bars_year(venue, tf, year, pl.concat([existing.filter(~in_rng), new_disk]))
        return True

    # ---- binance source archives ----------------------------------------------------------
    def save_source(self, name: str, data: bytes) -> Path:
        path = self.binance_sources_dir() / name
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == hashlib.sha256(data).hexdigest():
            return path
        atomic_write(path, lambda f: f.write(data))
        return path

    # ---- housekeeping ---------------------------------------------------------------------
    def cleanup_tmp(self, venue: str) -> int:
        """Delete temp files left by dead processes (call while holding the venue lock)."""
        dirs = [self.root / "raw" / venue, self.root / "bars" / venue]
        if venue.startswith("binance"):
            dirs.append(self.binance_sources_dir())
        removed = 0
        for base in dirs:
            if not base.exists():
                continue
            for p in base.rglob(".*.tmp-*"):
                m = _TMP_RE.match(p.name)
                if m and not _pid_alive(int(m.group(1))):
                    try:
                        p.unlink()
                        removed += 1
                    except FileNotFoundError:
                        pass
        return removed
