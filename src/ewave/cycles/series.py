"""Day bars as plain lists: the DP and the walk-forward replay index them millions of times."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import polars as pl

from ..data import load_bars
from .config import DAY_MS


@dataclass(frozen=True)
class Bars:
    """Consecutive 1D bars: the bar index is a day count, so a gap between two indices is a length in days."""
    ts: list[int]  # UTC bar open, ms
    open: list[float]
    high: list[float]
    low: list[float]
    close: list[float]

    def __post_init__(self):
        if any(b - a != DAY_MS for a, b in zip(self.ts, self.ts[1:])):
            raise ValueError("cycle analysis needs consecutive days without holes")

    def __len__(self) -> int:
        return len(self.ts)

    def upto(self, n: int) -> "Bars":
        """The first n bars: what was known once bar n-1 had closed."""
        return Bars(self.ts[:n], self.open[:n], self.high[:n], self.low[:n], self.close[:n])

    def index_of(self, ts: int) -> int:
        return (ts - self.ts[0]) // DAY_MS


def to_ms(day: str) -> int:
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1000)


def day_str(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date().isoformat()


def from_frame(df: pl.DataFrame) -> Bars:
    return Bars(df["ts"].dt.epoch("ms").to_list(), df["open"].to_list(), df["high"].to_list(), df["low"].to_list(),
                df["close"].to_list())


def load_daily(venue: str, root=None) -> Bars:
    """Complete 1D bars of a venue, the whole history."""
    return from_frame(load_bars(venue, "1d", "2000-01-01", "2100-01-01", complete_only=True, root=root))


def percentile(values: list[float], q: float) -> float:
    """Linear interpolation, q in 0..100."""
    s = sorted(values)
    pos = (len(s) - 1) * q / 100
    i = int(pos)
    return s[i] if i + 1 >= len(s) else s[i] + (s[i + 1] - s[i]) * (pos - i)


def median(values: list[float]) -> float:
    return percentile(values, 50)
