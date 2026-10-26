"""Static configuration: venues, derived timeframes, time helpers and the data root."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

MINUTE_MS = 60_000
HOUR_MS = 3_600_000
DAY_MS = 86_400_000
UTC = timezone.utc

# derived timeframes: name -> length in minutes
TIMEFRAMES: dict[str, int] = {"15m": 15, "1h": 60, "4h": 240, "1d": 1440}


def utc_ms(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp()) * 1000


@dataclass(frozen=True)
class Venue:
    id: str
    title: str
    first_minute_ms: int  # open time of the venue's first 1m candle
    continuous_grid: bool  # exchange returns flat zero-volume candles for no-trade minutes, so a missing minute is a fetch fault
    has_close_ts: bool  # exchange reports a candle close time (Binance), kept to expose short candles at outage edges


VENUES: dict[str, Venue] = {
    v.id: v
    for v in (
        Venue("bitstamp_btcusd", "Bitstamp BTC/USD spot", utc_ms(2011, 8, 18, 12, 37), True, False),
        Venue("binance_btcusdt", "Binance BTCUSDT spot", utc_ms(2017, 8, 17, 4, 0), False, True),
        Venue("bybit_btcusdt_perp", "Bybit BTCUSDT linear perpetual", utc_ms(2020, 3, 25, 10, 36), True, False),
    )
}


def resolve_venue(name: str) -> Venue:
    """Accept a full id or an unambiguous prefix such as 'bybit'."""
    if name in VENUES:
        return VENUES[name]
    hits = [v for k, v in VENUES.items() if k.startswith(name)]
    if len(hits) == 1:
        return hits[0]
    raise KeyError(f"unknown venue {name!r}; choose from {', '.join(VENUES)}")


# ---- time helpers (all UTC) -------------------------------------------------


def day_start_ms(day: str) -> int:
    d = date.fromisoformat(day)
    return int(datetime(d.year, d.month, d.day, tzinfo=UTC).timestamp()) * 1000


def day_of_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=UTC).strftime("%Y-%m-%d")


def next_day(day: str) -> str:
    return (date.fromisoformat(day) + timedelta(days=1)).isoformat()


def prev_day(day: str) -> str:
    return (date.fromisoformat(day) - timedelta(days=1)).isoformat()


def days_between(first: str, last: str) -> list[str]:
    """Inclusive list of ISO days."""
    a, b = date.fromisoformat(first), date.fromisoformat(last)
    return [(a + timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]


def iso_ms(ms: int | None) -> str:
    if ms is None:
        return "-"
    return datetime.fromtimestamp(ms / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")


def floor_minute(ms: int) -> int:
    return ms - ms % MINUTE_MS


def raise_nofile_limit(target: int = 65536) -> int:
    """Raise this process's soft open-file limit (services and shells start at 1024). Returns the new soft limit."""
    import resource

    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    want = target if hard == resource.RLIM_INFINITY else min(hard, target)
    if soft < want:
        resource.setrlimit(resource.RLIMIT_NOFILE, (want, hard))
        soft = want
    return soft


# ---- paths ------------------------------------------------------------------


def project_root() -> Path:
    # src/ewave/ingest/config.py -> project root; never depends on the current directory
    return Path(__file__).resolve().parents[3]


def data_root() -> Path:
    env = os.environ.get("EWAVE_DATA")
    return Path(env).expanduser().resolve() if env else project_root() / "data"
