"""Live smoke tests against the real exchanges. Run with:  uv run pytest -m network"""
from __future__ import annotations

import time

import pytest

from ewave.ingest.config import MINUTE_MS, VENUES, day_of_ms, day_start_ms
from ewave.ingest.schema import frame_from_rows, validate_day
from ewave.ingest.sources.binance import BinanceArchive, BinanceSource
from ewave.ingest.sources.bitstamp import BitstampSource
from ewave.ingest.sources.bybit import BybitSource

pytestmark = pytest.mark.network


def recent_window(src, n=5):
    server = src.server_now_ms()
    assert abs(server - time.time() * 1000) < 5_000, "local clock and exchange clock disagree"
    last_closed = (server - 15_000) // MINUTE_MS * MINUTE_MS - MINUTE_MS  # stay clear of the roll-over lag
    return last_closed - (n - 1) * MINUTE_MS, last_closed


@pytest.mark.parametrize("make", [BitstampSource, BybitSource, BinanceSource], ids=["bitstamp", "bybit", "binance"])
def test_last_five_closed_minutes(make):
    src = make()
    try:
        start, end = recent_window(src)
        rows = src.fetch_minutes(start, end)
        assert [r[0] for r in rows] == [start + i * MINUTE_MS for i in range(5)], "every closed minute, none forming"
        day = day_of_ms(end)
        df = frame_from_rows([r for r in rows if day_of_ms(r[0]) == day])
        assert validate_day(df, src.venue, day, end).ok
        assert all(60_000 < r[4] < 500_000 for r in rows), "BTC price sanity"
    finally:
        src.close()


def test_prices_agree_across_the_three_venues():
    closes = {}
    for make in (BitstampSource, BybitSource, BinanceSource):
        src = make()
        try:
            start, end = recent_window(src, 1)
            closes[src.venue.id] = src.fetch_minutes(start, end)[0][4]
        finally:
            src.close()
    lo, hi = min(closes.values()), max(closes.values())
    assert hi / lo < 1.01, closes


def test_first_candles_exist_at_each_venues_first_minute():
    for make in (BitstampSource, BybitSource, BinanceSource):
        src = make()
        try:
            first = src.venue.first_minute_ms
            rows = src.fetch_minutes(first, first + 2 * MINUTE_MS)
            assert rows and rows[0][0] == first and rows[0][5] > 0, (src.venue.id, rows[:1])
        finally:
            src.close()


def test_binance_archive_listing_and_a_verified_download():
    arch = BinanceArchive()
    try:
        day = day_of_ms(time.time() * 1000 - 5 * 86_400_000)
        entries = arch.list_days(day)
        assert entries and entries[0].day == day and entries[0].etag
        ad = arch.fetch_day(day)
        assert ad is not None and len(ad.rows) == 1440
        assert validate_day(frame_from_rows(ad.rows), VENUES["binance_btcusdt"], day, None).ok
    finally:
        arch.close()
