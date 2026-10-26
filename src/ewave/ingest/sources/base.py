"""Common interface for the exchange sources."""
from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx

from ..config import Venue
from ..http import RetryableError
from ..schema import Row

log = logging.getLogger("ewave.sources")


@dataclass
class Page:
    rows: list[Row]  # ascending by ts, closed minutes only
    window_end_ms: int  # last minute-open covered by the request(s) behind this page (rows may be fewer: gaps/empty)


@dataclass
class FetchStats:
    stray_rows: int = 0
    notes: list[str] = field(default_factory=list)


class Source:
    venue: Venue

    def server_now_ms(self) -> int:
        raise NotImplementedError

    def iter_pages(self, start_ms: int, end_ms: int) -> Iterator[Page]:
        """Pages of closed minutes covering [start_ms, end_ms]. Never stops on a short or empty page."""
        raise NotImplementedError

    def fetch_minutes(self, start_ms: int, end_ms: int) -> list[Row]:
        rows: list[Row] = []
        for page in self.iter_pages(start_ms, end_ms):
            rows.extend(page.rows)
        return rows

    def native_candles(self, tf: str, start_ms: int, end_ms: int) -> list[tuple]:
        """The exchange's own candles as (ts_ms, open, high, low, close, volume) - used to audit our resampler."""
        raise NotImplementedError

    def close(self) -> None:
        pass


def json_body(resp: httpx.Response) -> Any:
    """Parse a JSON body; HTML (CDN challenge pages) or empty bodies become retryable errors, never data."""
    ctype = resp.headers.get("content-type", "")
    if not resp.content:
        raise RetryableError(f"HTTP {resp.status_code} with an empty body")
    if "json" not in ctype.lower():
        raise RetryableError(f"HTTP {resp.status_code} with non-JSON content-type {ctype!r}: {resp.text[:80]!r}")
    try:
        return resp.json()
    except ValueError as e:
        raise RetryableError(f"HTTP {resp.status_code} with invalid JSON: {e}") from e


def dedupe_sorted(rows: list[Row]) -> list[Row]:
    seen: dict[int, Row] = {}
    for r in rows:
        seen[r[0]] = r
    return [seen[k] for k in sorted(seen)]
