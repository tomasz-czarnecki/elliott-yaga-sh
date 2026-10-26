"""Deterministic fake exchange + helpers shared by the tests."""
from __future__ import annotations

from collections.abc import Callable, Iterator

from ewave.ingest.config import MINUTE_MS, VENUES, Venue, utc_ms
from ewave.ingest.schema import Row, make_row
from ewave.ingest.sources.base import Page, Source

# a fixed "now" for the tests: Tuesday 2026-10-20 12:07:20 UTC
T0 = utc_ms(2026, 10, 20, 12, 7) + 20_000


def synth_row(venue: Venue, t: int, *, zero: bool = False) -> Row:
    """A valid, deterministic candle for the minute opening at t."""
    i = t // MINUTE_MS
    if zero:
        base = 1000.0 + (i // 1440) % 7  # flat at a day-dependent price
        return _fill(venue, t, base, base, base, base, 0.0)
    o = 1000.0 + i % 7
    c = 1000.0 + i % 5
    h = max(o, c) + 1.0 + (i % 3)
    l = min(o, c) - 1.0 - (i % 2)
    return _fill(venue, t, o, h, l, c, 1.0 + i % 3)


def _fill(venue: Venue, t: int, o, h, l, c, v) -> Row:
    return make_row(
        t, o, h, l, c, v,
        quote_volume=None if venue.id.startswith("bitstamp") else v * c,
        trades=(int(v * 3) if venue.id.startswith("binance") else None),
        taker_buy_volume=(v / 2 if venue.id.startswith("binance") else None),
        taker_buy_quote_volume=(v * c / 2 if venue.id.startswith("binance") else None),
        close_ts=(t + MINUTE_MS - 1 if venue.has_close_ts else None),
    )


class FakeSource(Source):
    """An in-memory exchange: a row exists for every minute except the holes."""

    def __init__(self, venue_id: str, clock, *, holes: Callable[[int], bool] | None = None,
                 zero: Callable[[int], bool] | None = None, page_minutes: int = 1000):
        self.venue = VENUES[venue_id]
        self.clock = clock
        self.holes = holes or (lambda t: False)
        self.zero = zero or (lambda t: False)
        self.page_minutes = page_minutes
        self.requests: list[tuple[int, int]] = []
        self.fail_with: Exception | None = None
        self.overrides: dict[int, Row] = {}
        self.server_offset_ms = 0

    def row(self, t: int) -> Row | None:
        if t < self.venue.first_minute_ms or self.holes(t):
            return None
        return self.overrides.get(t) or synth_row(self.venue, t, zero=self.zero(t))

    def server_now_ms(self) -> int:
        if self.fail_with:
            raise self.fail_with
        return self.clock.now_ms() + self.server_offset_ms

    def iter_pages(self, start_ms: int, end_ms: int) -> Iterator[Page]:
        self.requests.append((start_ms, end_ms))
        if self.fail_with:
            raise self.fail_with
        s = max(start_ms, self.venue.first_minute_ms)
        s -= s % MINUTE_MS
        while s <= end_ms:
            e = min(s + (self.page_minutes - 1) * MINUTE_MS, end_ms)
            rows = [r for t in range(s, e + 1, MINUTE_MS) if (r := self.row(t)) is not None]
            yield Page(rows, e)
            s = e + MINUTE_MS

    def native_candles(self, tf: str, start_ms: int, end_ms: int) -> list[tuple]:
        return []
