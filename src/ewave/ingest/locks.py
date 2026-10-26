"""Per-venue file locks (``fcntl.flock``). The lock file is never deleted and records who holds it."""
from __future__ import annotations

import fcntl
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


class LockBusy(RuntimeError):
    pass


def lock_path(state_dir: Path, venue: str) -> Path:
    return Path(state_dir) / f"{venue}.lock"


def read_holder(state_dir: Path, venue: str) -> str | None:
    """Text written by the current/last holder, or None if the lock file does not exist."""
    try:
        text = lock_path(state_dir, venue).read_text().strip()
    except FileNotFoundError:
        return None
    return text or None


def is_held(state_dir: Path, venue: str) -> bool:
    """Probe the lock without keeping it (a stale holder text from a killed process does not count)."""
    path = lock_path(state_dir, venue)
    if not path.exists():
        return False
    fd = os.open(path, os.O_RDWR)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return True
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


class VenueLock:
    def __init__(self, state_dir: Path, venue: str, command: str):
        self.path = lock_path(state_dir, venue)
        self.command = command
        self._fd: int | None = None

    def acquire(self, wait_s: float = 0.0, poll_s: float = 0.5) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        deadline = time.monotonic() + wait_s
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    os.close(fd)
                    return False
                time.sleep(poll_s)
        self._fd = fd
        started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        info = f"pid={os.getpid()} cmd={self.command!r} since={started}\n".encode()
        os.ftruncate(fd, 0)
        os.pwrite(fd, info, 0)
        return True

    def release(self) -> None:
        if self._fd is not None:
            try:
                os.ftruncate(self._fd, 0)  # leave the file, drop the holder text
            except OSError:
                pass
            os.close(self._fd)  # closing releases the flock
            self._fd = None

    def __enter__(self) -> "VenueLock":
        if not self.acquire(0.0):
            raise LockBusy(f"{self.path.name} is held by another process")
        return self

    def __exit__(self, *exc) -> None:
        self.release()


def command_label() -> str:
    return " ".join(["ewave-data", *sys.argv[1:]]) if sys.argv else "ewave-data"
