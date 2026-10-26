"""Binance BTCUSDT spot 1m candles: REST for the recent minutes, official daily archives for history.

REST  GET /api/v3/klines?symbol=BTCUSDT&interval=1m&startTime&endTime&limit=1000
  * Weight 2 of 6000/min per IP. The newest row without an endTime is the still-open minute.
  * Gaps (exchange outages) are skipped silently; no-trade minutes are not filler rows - missing minutes are absent.
Archive  data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-YYYY-MM-DD.zip (+ .CHECKSUM)
  * 12 columns, no header; timestamps are microseconds from 2025-01-01 and milliseconds before (detected by size).
  * Daily files appear ~1.5-3 h after the day ends and are sometimes re-published; monthly files are NOT used
    (the pre-2021 ones are stale and 2018-02 is shifted 14.8 s off the minute grid).
"""
from __future__ import annotations

import csv
import hashlib
import io
import logging
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass

import httpx

from ..config import MINUTE_MS, VENUES, floor_minute, prev_day
from ..http import CooldownError, FatalError, GeoBlockedError, HttpClient, RetryableError
from ..schema import Row, make_row
from .base import Page, Source, dedupe_sorted, json_body

log = logging.getLogger("ewave.sources.binance")

REST_BASES = ["https://data-api.binance.vision", "https://api.binance.com"]
ARCHIVE_BASE = "https://data.binance.vision"
S3_LIST_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
PREFIX = "data/spot/daily/klines/BTCUSDT/1m/"
PAGE_MINUTES = 1000
INTERVALS = {"15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
MICROSECOND_THRESHOLD = 10**14


# ---- REST --------------------------------------------------------------------


def interpret_klines(resp: httpx.Response) -> list:
    if resp.status_code == 200:
        body = json_body(resp)
        if not isinstance(body, list):
            raise RetryableError(f"unexpected JSON shape: {str(body)[:120]}")
        return body
    if resp.status_code == 451:
        raise GeoBlockedError("HTTP 451: restricted location")
    if resp.status_code == 403:
        raise CooldownError("HTTP 403 (WAF limit)", 600.0)
    if 400 <= resp.status_code < 500:
        raise FatalError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    raise RetryableError(f"HTTP {resp.status_code}")


def interpret_time(resp: httpx.Response) -> int:
    body = interpret_json_dict(resp)
    return int(body["serverTime"])


def interpret_json_dict(resp: httpx.Response) -> dict:
    if resp.status_code != 200:
        if resp.status_code == 451:
            raise GeoBlockedError("HTTP 451: restricted location")
        raise RetryableError(f"HTTP {resp.status_code}")
    body = json_body(resp)
    if not isinstance(body, dict):
        raise RetryableError("unexpected JSON shape")
    return body


def parse_kline(k: list, *, unit_div: int = 1) -> Row:
    """[open_time, o, h, l, c, volume, close_time, quote_volume, trades, taker_base, taker_quote, ignore]"""
    return make_row(
        int(k[0]) // unit_div,
        float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]),
        quote_volume=float(k[7]),
        trades=int(k[8]),
        taker_buy_volume=float(k[9]),
        taker_buy_quote_volume=float(k[10]),
        close_ts=int(k[6]) // unit_div,
    )


class BinanceSource(Source):
    venue = VENUES["binance_btcusdt"]

    def __init__(self, http: HttpClient | None = None, *, clock=None, transport=None, rate_per_s: float = 5.0):
        self.http = http or HttpClient("binance-rest", REST_BASES, rate_per_s, clock=clock, transport=transport)

    def close(self) -> None:
        self.http.close()

    def server_now_ms(self) -> int:
        return self.http.get("/api/v3/time", interpret=interpret_time)

    def iter_pages(self, start_ms: int, end_ms: int) -> Iterator[Page]:
        s = floor_minute(max(start_ms, self.venue.first_minute_ms))
        while s <= end_ms:
            last_open = min(s + (PAGE_MINUTES - 1) * MINUTE_MS, end_ms)
            data = self.http.get(
                "/api/v3/klines",
                {"symbol": "BTCUSDT", "interval": "1m", "startTime": s,
                 "endTime": last_open + MINUTE_MS - 1, "limit": PAGE_MINUTES},
                interpret=interpret_klines,
            )
            rows: list[Row] = []
            stray = forming = 0
            known_now = self.http.last_date_ms
            for k in data:
                try:
                    r = parse_kline(k)
                except (ValueError, IndexError, TypeError) as e:
                    raise RetryableError(f"bad kline {k!r}: {e}") from e
                if r[0] % MINUTE_MS or r[0] < s or r[0] > last_open:
                    stray += 1
                    continue
                if known_now is not None and r[10] > known_now:  # close_ts still in the future: forming minute
                    forming += 1
                    continue
                rows.append(r)
            if stray or forming:
                log.warning("binance: dropped %d stray and %d forming candles in window %d..%d", stray, forming, s, last_open)
            yield Page(dedupe_sorted(rows), last_open)
            s = last_open + MINUTE_MS

    def native_candles(self, tf: str, start_ms: int, end_ms: int) -> list[tuple]:
        data = self.http.get(
            "/api/v3/klines",
            {"symbol": "BTCUSDT", "interval": INTERVALS[tf], "startTime": start_ms, "endTime": end_ms, "limit": 1000},
            interpret=interpret_klines,
        )
        return sorted((int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])) for k in data)


# ---- daily archives -----------------------------------------------------------


class ArchiveError(Exception):
    pass


class ChecksumPending(ArchiveError):
    """The zip exists but its .CHECKSUM is not published yet (up to a second apart): retry later, never finalise."""


class ChecksumMismatch(ArchiveError):
    pass


@dataclass
class ArchiveEntry:
    day: str
    key: str
    etag: str
    last_modified: str
    size: int


@dataclass
class ArchiveDay:
    day: str
    etag: str
    last_modified: str
    size: int
    zip_bytes: bytes
    checksum_text: str
    zip_sha256: str
    rows: list[Row]


def day_from_key(key: str) -> str | None:
    name = key.rsplit("/", 1)[-1]
    if name.startswith("BTCUSDT-1m-") and name.endswith(".zip"):
        return name[len("BTCUSDT-1m-"):-len(".zip")]
    return None


def parse_listing(xml_bytes: bytes) -> tuple[list[ArchiveEntry], str | None]:
    root = ET.fromstring(xml_bytes)
    ns = {"s3": root.tag.split("}")[0].strip("{")} if root.tag.startswith("{") else {}
    q = (lambda t: f"s3:{t}") if ns else (lambda t: t)
    entries: list[ArchiveEntry] = []
    for c in root.findall(q("Contents"), ns):
        key = c.findtext(q("Key"), namespaces=ns) or ""
        day = day_from_key(key)
        if day is None:
            continue  # .CHECKSUM objects and anything else
        entries.append(ArchiveEntry(
            day=day, key=key,
            etag=(c.findtext(q("ETag"), namespaces=ns) or "").strip('"'),
            last_modified=c.findtext(q("LastModified"), namespaces=ns) or "",
            size=int(c.findtext(q("Size"), namespaces=ns) or 0),
        ))
    truncated = (root.findtext(q("IsTruncated"), namespaces=ns) or "").lower() == "true"
    token = root.findtext(q("NextContinuationToken"), namespaces=ns) if truncated else None
    return entries, token


def parse_archive_zip(day: str, zip_bytes: bytes) -> list[Row]:
    """Rows of one daily zip, held in memory (never extracted to disk). Handles ms/us timestamps and a stray header."""
    expected = f"BTCUSDT-1m-{day}.csv"
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            names = z.namelist()
            if names != [expected]:
                raise ArchiveError(f"unexpected zip members {names!r}, expected [{expected!r}]")
            raw = z.read(expected)
    except zipfile.BadZipFile as e:
        raise ArchiveError(f"bad zip for {day}: {e}") from e
    rows: list[Row] = []
    for rec in csv.reader(io.StringIO(raw.decode("utf-8"))):
        if not rec or not rec[0].strip().isdigit():
            continue  # tolerate a header row
        if len(rec) < 11:
            raise ArchiveError(f"short record in {day}: {rec!r}")
        div = 1000 if int(rec[0]) >= MICROSECOND_THRESHOLD else 1
        rows.append(parse_kline(rec, unit_div=div))
    return dedupe_sorted(rows)


class BinanceArchive:
    def __init__(self, http: HttpClient | None = None, *, clock=None, transport=None, rate_per_s: float = 4.0):
        self.http = http or HttpClient("binance-archive", [ARCHIVE_BASE], rate_per_s, clock=clock, transport=transport)

    def close(self) -> None:
        self.http.close()

    def list_days(self, start_day: str | None = None) -> list[ArchiveEntry]:
        """Zip entries (ETag, size, last-modified) from ``start_day`` on, or all of them (7 requests)."""
        params: dict = {"list-type": 2, "prefix": PREFIX}
        if start_day:
            params["start-after"] = f"{PREFIX}BTCUSDT-1m-{prev_day(start_day)}.zip.CHECKSUM"
        out: list[ArchiveEntry] = []
        while True:
            xml = self.http.get(S3_LIST_URL, params, absolute=True, interpret=_interpret_xml)
            entries, token = parse_listing(xml)
            out.extend(entries)
            if not token:
                return out
            params = {"list-type": 2, "prefix": PREFIX, "continuation-token": token}

    def fetch_day(self, day: str) -> ArchiveDay | None:
        """Download, verify and parse one day. None if the zip is not published yet; ChecksumPending if its CHECKSUM isn't."""
        base = f"/{PREFIX}BTCUSDT-1m-{day}.zip"
        got = self.http.get(base, interpret=_interpret_binary)
        if got is None:
            return None
        data, etag, last_modified = got
        sums = self.http.get(base + ".CHECKSUM", interpret=_interpret_text)
        if sums is None:
            raise ChecksumPending(f"{day}: zip is published but its CHECKSUM is not yet")
        expected = sums.split()[0].lower() if sums.split() else ""
        actual = hashlib.sha256(data).hexdigest()
        if expected != actual:
            raise ChecksumMismatch(f"{day}: sha256 {actual} != CHECKSUM {expected}")
        rows = parse_archive_zip(day, data)
        return ArchiveDay(day, etag, last_modified, len(data), data, sums, actual, rows)


def _interpret_xml(resp: httpx.Response) -> bytes:
    if resp.status_code == 200 and resp.content:
        return resp.content
    if 400 <= resp.status_code < 500 and resp.status_code != 429:
        raise FatalError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    raise RetryableError(f"HTTP {resp.status_code}")


def _interpret_binary(resp: httpx.Response):
    if resp.status_code == 200:
        return resp.content, resp.headers.get("etag", "").strip('"'), resp.headers.get("last-modified", "")
    if resp.status_code == 404:
        return None
    if resp.status_code == 403:
        raise CooldownError("HTTP 403 from the archive host", 600.0)
    raise RetryableError(f"HTTP {resp.status_code}")


def _interpret_text(resp: httpx.Response) -> str | None:
    if resp.status_code == 200:
        return resp.text
    if resp.status_code == 404:
        return None
    if resp.status_code == 403:
        raise CooldownError("HTTP 403 from the archive host", 600.0)
    raise RetryableError(f"HTTP {resp.status_code}")
