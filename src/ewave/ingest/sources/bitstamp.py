"""Bitstamp BTC/USD spot 1m candles.

GET /api/v2/ohlc/btcusd/?step=60&limit=1000&start=<unix s>&exclude_current_candle=true
  * Paginate with ``start`` only: when both start and end are sent, start is ignored.
  * Each request covers the fixed window [start, start + 1000 min); an empty or short page does NOT mean the
    data has ended (windows before the first trade come back empty).
  * No-trade minutes come back as flat candles at the previous close with volume 0 (a continuous grid).
  * The just-closed minute can be missing for 1-6 s after a minute boundary; syncs run at :20 and re-fetch an overlap.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator

import httpx

from ..config import MINUTE_MS, VENUES, floor_minute
from ..http import CooldownError, FatalError, HttpClient, RetryableError
from ..schema import Row, make_row
from .base import Page, Source, dedupe_sorted, json_body

log = logging.getLogger("ewave.sources.bitstamp")

BASE = "https://www.bitstamp.net"
PATH = "/api/v2/ohlc/btcusd/"
PAGE_MINUTES = 1000
STEP_SECONDS = {"15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}


def interpret_ohlc(resp: httpx.Response) -> list[dict]:
    if resp.status_code == 200:
        body = json_body(resp)
        try:
            ohlc = body["data"]["ohlc"]
        except (KeyError, TypeError):
            raise RetryableError(f"unexpected JSON shape: {str(body)[:120]}") from None
        if not isinstance(ohlc, list):
            raise RetryableError("ohlc is not a list")
        return ohlc
    if resp.status_code == 400:
        text = resp.text[:300]
        if "400.002" in text:  # documented rate-limit code
            raise RetryableError("Bitstamp rate limit (400.002)", retry_after=5.0)
        raise FatalError(f"HTTP 400: {text}")
    if resp.status_code == 403:
        raise CooldownError("HTTP 403 (blocked by the CDN?)", 600.0)
    if 400 <= resp.status_code < 500:
        raise FatalError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    raise RetryableError(f"HTTP {resp.status_code}")


def parse_candle(c: dict) -> Row:
    return make_row(
        int(c["timestamp"]) * 1000,
        float(c["open"]), float(c["high"]), float(c["low"]), float(c["close"]), float(c["volume"]),
    )


class BitstampSource(Source):
    venue = VENUES["bitstamp_btcusd"]

    def __init__(self, http: HttpClient | None = None, *, clock=None, transport=None, rate_per_s: float = 2.0):
        self.http = http or HttpClient("bitstamp", [BASE], rate_per_s, clock=clock, transport=transport)

    def close(self) -> None:
        self.http.close()

    def server_now_ms(self) -> int:
        self.http.get(PATH, {"step": 60, "limit": 1, "exclude_current_candle": "true"}, interpret=interpret_ohlc)
        if self.http.last_date_ms is None:
            raise RetryableError("no Date header in the Bitstamp response")
        return self.http.last_date_ms + 500  # Date has 1 s resolution

    def iter_pages(self, start_ms: int, end_ms: int) -> Iterator[Page]:
        s = floor_minute(max(start_ms, self.venue.first_minute_ms))
        while s <= end_ms:
            page_last = s + (PAGE_MINUTES - 1) * MINUTE_MS
            ohlc = self.http.get(
                PATH,
                {"step": 60, "limit": PAGE_MINUTES, "start": s // 1000, "exclude_current_candle": "true"},
                interpret=interpret_ohlc,
            )
            rows: list[Row] = []
            stray = 0
            for c in ohlc:
                try:
                    r = parse_candle(c)
                except (KeyError, ValueError, TypeError) as e:
                    raise RetryableError(f"bad candle {c!r}: {e}") from e
                if r[0] % MINUTE_MS or r[0] < s or r[0] > page_last:
                    stray += 1
                    continue
                if r[0] > end_ms:
                    continue  # beyond the requested range (never the forming minute: that one is excluded server-side)
                rows.append(r)
            if stray:
                log.warning("bitstamp: dropped %d candles outside the requested window starting %d", stray, s)
            yield Page(dedupe_sorted(rows), min(page_last, end_ms))
            s = page_last + MINUTE_MS

    def native_candles(self, tf: str, start_ms: int, end_ms: int) -> list[tuple]:
        step = STEP_SECONDS[tf]
        out: list[tuple] = []
        s = start_ms // (step * 1000) * (step * 1000)
        while s <= end_ms:
            ohlc = self.http.get(
                PATH, {"step": step, "limit": 1000, "start": s // 1000, "exclude_current_candle": "true"},
                interpret=interpret_ohlc)
            for c in ohlc:
                ts = int(c["timestamp"]) * 1000
                if s <= ts <= end_ms:
                    out.append((ts, float(c["open"]), float(c["high"]), float(c["low"]), float(c["close"]),
                                float(c["volume"])))
            s += 1000 * step * 1000
        return sorted(set(out))
