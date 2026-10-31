"""The versioned rules file (rules/cycles.yaml). Nothing in this package hard-codes a window or a threshold."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import yaml

from ..ingest.config import project_root

DAY_MS = 86_400_000
LEVELS = ("daily", "weekly")  # the levels with a timing window; "fouryear" has its own detector


def rules_path() -> Path:
    return project_root() / "rules" / "cycles.yaml"


@dataclass(frozen=True)
class Level:
    name: str
    lo: int  # timing window, days
    hi: int
    tol: float
    swing_k: int
    depth_window: int
    snap_days: int
    count_min: int
    count_max: int
    min_gap_fraction: float
    lookback_fraction: float
    revise_fraction: float
    match_tol: int

    @property
    def centre(self) -> float:
        return (self.lo + self.hi) / 2

    @property
    def lo_tol(self) -> float:
        return self.lo * (1 - self.tol)

    @property
    def hi_tol(self) -> float:
        return self.hi * (1 + self.tol)

    @property
    def min_gap(self) -> int:
        """No live low before last low + this many days."""
        return round(self.lo * self.min_gap_fraction)

    @property
    def lookback_days(self) -> int:
        """A live candidate must be the lowest low of this many days."""
        return round(self.centre * self.lookback_fraction)

    @property
    def revise_days(self) -> int:
        """An undercut this soon after a confirmed low revises it; a later one is a failed cycle."""
        return round(self.lo * self.revise_fraction)


class Rules:
    def __init__(self, raw: dict, digest: str = ""):
        self.raw = raw
        self.version: str = raw["version"]
        self.digest = digest or hashlib.sha256(yaml.safe_dump(raw, sort_keys=True).encode()).hexdigest()[:12]

    @cached_property
    def levels(self) -> dict[str, Level]:
        live = self.raw["live"]
        out = {}
        for name in LEVELS:
            r = self.raw["levels"][name]
            lo, hi = r["window_days"]
            count_min, count_max = r["cycles_per_parent"]
            out[name] = Level(
                name=name, lo=lo, hi=hi, tol=r["tolerance"], swing_k=r["swing_k_days"],
                depth_window=r["depth_window_days"], snap_days=r["snap_days"], count_min=count_min, count_max=count_max,
                min_gap_fraction=live["min_gap_fraction"], lookback_fraction=live["candidate_lookback_fraction"],
                revise_fraction=live["revise_within_fraction"], match_tol=live["match_tolerance_days"][name],
            )
        return out

    @property
    def fouryear(self) -> dict:
        return self.raw["levels"]["fouryear"]

    @property
    def dp(self) -> dict:
        return self.raw["dp"]

    @property
    def cycle(self) -> dict:
        return self.raw["cycle"]

    @property
    def live(self) -> dict:
        return self.raw["live"]

    @property
    def zones(self) -> dict:
        return self.raw["zones"]

    @property
    def null(self) -> dict:
        return self.raw["null_model"]

    @property
    def series(self) -> dict:
        return self.raw["series"]

    def replaced(self, **sections) -> "Rules":
        """A copy with whole top-level sections merged over; for tests and sensitivity runs."""
        raw = {**self.raw}
        for key, value in sections.items():
            raw[key] = {**raw[key], **value}
        return Rules(raw)


def load_rules(path: Path | str | None = None) -> Rules:
    p = Path(path) if path else rules_path()
    data = p.read_bytes()
    return Rules(yaml.safe_load(data), hashlib.sha256(data).hexdigest()[:12])
