"""Bybit BTCUSDT linear perpetual 1m candles (REST v5).

GET /v5/market/kline?category=linear&symbol=BTCUSDT&interval=1&start=<ms>&end=<ms>&limit=1000
  * Rows come newest first; start and end are inclusive and filter on the candle's startTime.
  * A window longer than 1000 minutes silently drops its OLDEST rows, so windows are at most 1000 minutes.
  * Bad parameters return retCode 0 with an empty list; an empty page for a past window is therefore an error.
  * Each open equals the previous close; volume is in BTC and turnover in USDT.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator

import httpx

from ..config import MINUTE_MS, VENUES, floor_minute
from ..http import CooldownError, FatalError, GeoBlockedError, HttpClient, RetryableError
from ..schema import Row, make_row
from .base import Page, Source, dedupe_sorted, json_body

log = logging.getLogger("ewave.sources.bybit")

BASE = "https://api.bybit.com"
FALLBACK = "https://api.bytick.com"
PAGE_MINUTES = 1000
INTERVALS = {"15m": "15", "1h": "60", "4h": "240", "1d": "D"}

RETRY_CODES = {10000, 10016, 10006}  # server timeout, server error, per-UID rate limit
COOLDOWN_CODES = {10018}  # IP rate limit
GEO_CODES = {10009}


def interpret_bybit(resp: httpx.Response) -> dict:
    if resp.status_code == 403:
        raise CooldownError("HTTP 403 (IP rate-limit ban or geo-block)", 600.0)
    if resp.status_code != 200:
        # 404 comes with an empty body; never parse it as data
        raise RetryableError(f"HTTP {resp.status_code} (body {resp.text[:80]!r})")
    body = json_body(resp)
    if not isinstance(body, dict) or "retCode" not in body:
        raise RetryableError(f"unexpected JSON shape: {str(body)[:120]}")
    code = body["retCode"]
    if code == 0:
        return body
    msg = f"retCode {code}: {body.get('retMsg')}"
    if code in RETRY_CODES:
        raise RetryableError(msg)
    if code in COOLDOWN_CODES:
        raise CooldownError(msg, 600.0)
    if code in GEO_CODES:
        raise GeoBlockedError(msg)
    raise FatalError(msg)  # 10001 (parameter error) and anything unknown: a bug, do not retry


def parse_kline(k: list) -> Row:
    # [startTime ms, open, high, low, close, volume (BTC), turnover (USDT)]
    return make_row(int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]), quote_volume=float(k[6]))


class BybitSource(Source):
    venue = VENUES["bybit_btcusdt_perp"]

    def __init__(self, http: HttpClient | None = None, *, clock=None, transport=None, rate_per_s: float = 4.0):
        self.http = http or HttpClient("bybit", [BASE, FALLBACK], rate_per_s, clock=clock, transport=transport)

    def close(self) -> None:
        self.http.close()

    def server_now_ms(self) -> int:
        body = self.http.get("/v5/market/time", interpret=interpret_bybit)
        return int(body["time"])

    def _klines(self, interval: str, s: int, e: int) -> list[list]:
        body = self.http.get(
            "/v5/market/kline",
            {"category": "linear", "symbol": "BTCUSDT", "interval": interval, "start": s, "end": e, "limit": 1000},
            interpret=interpret_bybit,
        )
        res = body.get("result") or {}
        if res.get("symbol") != "BTCUSDT" or res.get("category") != "linear":
            raise FatalError(f"unexpected symbol/category in response: {res.get('symbol')}/{res.get('category')}")
        return res.get("list") or []

    def iter_pages(self, start_ms: int, end_ms: int) -> Iterator[Page]:
        s = floor_minute(max(start_ms, self.venue.first_minute_ms))
        while s <= end_ms:
            e = min(s + (PAGE_MINUTES - 1) * MINUTE_MS, end_ms)
            klist = self._klines("1", s, e)
            if not klist:
                raise FatalError(f"Bybit returned an empty page for the past window {s}..{e}")
            rows: list[Row] = []
            for k in klist:
                try:
                    r = parse_kline(k)
                except (ValueError, IndexError, TypeError) as ex:
                    raise RetryableError(f"bad kline {k!r}: {ex}") from ex
                if r[0] % MINUTE_MS or not (s <= r[0] <= e):
                    raise FatalError(f"Bybit row {r[0]} lies outside the requested window {s}..{e}")
                rows.append(r)
            yield Page(dedupe_sorted(rows), e)  # newest-first list is sorted ascending here
            s = e + MINUTE_MS

    def native_candles(self, tf: str, start_ms: int, end_ms: int) -> list[tuple]:
        interval = INTERVALS[tf]
        out = []
        for k in self._klines(interval, start_ms, end_ms):
            out.append((int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])))
        return sorted(out)
