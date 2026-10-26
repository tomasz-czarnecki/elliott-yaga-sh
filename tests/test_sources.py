from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import httpx
import pytest

from ewave.ingest.clock import FakeClock
from ewave.ingest.config import MINUTE_MS, utc_ms
from ewave.ingest.http import CooldownError, FatalError, GeoBlockedError, HttpClient, RetryableError
from ewave.ingest.sources.binance import (
    ArchiveError, BinanceArchive, BinanceSource, ChecksumMismatch, ChecksumPending, parse_archive_zip, parse_listing,
)
from ewave.ingest.sources.bitstamp import BitstampSource
from ewave.ingest.sources.bybit import BybitSource

FIX = Path(__file__).parent / "fixtures"
T = 1325376000_000  # Bitstamp fixture start (2012-01-01 00:00 UTC) in ms


def client(handler, name="t", bases=("https://example.test",), rate=1000.0, attempts=4):
    clock = FakeClock(0)
    return HttpClient(name, list(bases), rate, clock=clock, transport=httpx.MockTransport(handler), max_attempts=attempts), clock


def json_resp(body, status=200, **headers):
    return httpx.Response(status, json=body, headers=headers)


# ---- Bitstamp ----------------------------------------------------------------------------------------------


def test_bitstamp_parses_the_real_fixture_and_paginates_with_start_only():
    seen = []

    def handler(req: httpx.Request):
        seen.append(dict(req.url.params))
        if len(seen) == 1:
            return httpx.Response(200, content=(FIX / "bitstamp_ohlc_2012.json").read_bytes(),
                                  headers={"content-type": "application/json"})
        return json_resp({"data": {"pair": "BTC/USD", "ohlc": []}})

    http, _ = client(handler)
    src = BitstampSource(http)
    pages = list(src.iter_pages(T, T + 1500 * MINUTE_MS))
    assert len(pages) == 2  # the empty second page does not stop the sweep
    rows = pages[0].rows
    assert [r[0] for r in rows] == [T + i * MINUTE_MS for i in range(5)]
    assert rows[0][1:6] == (4.58, 4.58, 4.58, 4.58, 0.0)
    assert pages[0].window_end_ms == T + 999 * MINUTE_MS
    for p in seen:
        assert "end" not in p and p["step"] == "60" and p["limit"] == "1000" and p["exclude_current_candle"] == "true"
    assert int(seen[1]["start"]) == int(seen[0]["start"]) + 60_000  # start advances by 1000 minutes


def test_bitstamp_drops_rows_outside_the_window_and_beyond_the_end():
    def handler(req):
        return json_resp({"data": {"pair": "BTC/USD", "ohlc": [
            {"timestamp": str(T // 1000 - 60), "open": "1", "high": "1", "low": "1", "close": "1", "volume": "0"},  # before start
            {"timestamp": str(T // 1000), "open": "2", "high": "2", "low": "2", "close": "2", "volume": "1"},
            {"timestamp": str(T // 1000 + 60), "open": "3", "high": "3", "low": "3", "close": "3", "volume": "1"},
            {"timestamp": str(T // 1000 + 600), "open": "4", "high": "4", "low": "4", "close": "4", "volume": "1"},  # after end
        ]}})

    http, _ = client(handler)
    [page] = BitstampSource(http).iter_pages(T, T + 60_000)
    assert [r[0] for r in page.rows] == [T, T + 60_000]


@pytest.mark.parametrize("response", [
    httpx.Response(200, text="<html>Please complete the challenge</html>", headers={"content-type": "text/html"}),
    httpx.Response(200, content=b"", headers={"content-type": "application/json"}),
    httpx.Response(200, json={"unexpected": True}),
    httpx.Response(400, json={"code": "400.002", "errors": []}),
    httpx.Response(503),
])
def test_bitstamp_bad_responses_are_retried_then_raise_and_are_never_data(response):
    calls = []

    def handler(req):
        calls.append(1)
        return response

    http, clock = client(handler)
    with pytest.raises(RetryableError):
        list(BitstampSource(http).iter_pages(T, T + 60_000))
    assert len(calls) == 4
    assert clock.monotonic() > 5  # it backed off (1+2+4 s with jitter) instead of hammering


def test_bitstamp_403_is_a_cooldown_and_other_4xx_are_fatal():
    http, _ = client(lambda req: httpx.Response(403, text="Forbidden"))
    with pytest.raises(CooldownError):
        list(BitstampSource(http).iter_pages(T, T + 60_000))
    http, _ = client(lambda req: httpx.Response(400, json={"code": "validation-error"}))
    with pytest.raises(FatalError):
        list(BitstampSource(http).iter_pages(T, T + 60_000))


def test_bitstamp_server_time_comes_from_the_date_header():
    http, _ = client(lambda req: json_resp({"data": {"pair": "BTC/USD", "ohlc": []}},
                                           date="Mon, 26 Oct 2026 06:00:10 GMT"))
    assert BitstampSource(http).server_now_ms() == utc_ms(2026, 10, 26, 6, 0) + 10_500


# ---- Bybit ---------------------------------------------------------------------------------------------------


def test_bybit_reverses_the_newest_first_fixture():
    def handler(req):
        return httpx.Response(200, content=(FIX / "bybit_kline_launch.json").read_bytes(),
                              headers={"content-type": "application/json"})

    http, _ = client(handler)
    first = utc_ms(2020, 3, 25, 10, 36)  # the fixture holds the first five candles, newest first
    [page] = BybitSource(http).iter_pages(first, first + 4 * MINUTE_MS)
    ts = [r[0] for r in page.rows]
    assert ts == [first + i * MINUTE_MS for i in range(5)]
    traded = [r for r in page.rows if r[5] > 0]
    assert len(traded) == 1 and traded[0][5] == 0.001 and traded[0][6] == 6.5  # volume BTC, turnover USDT


def test_bybit_windows_never_exceed_1000_minutes_and_cover_the_range():
    reqs = []

    def handler(req):
        p = dict(req.url.params)
        reqs.append(p)
        s, e = int(p["start"]), int(p["end"])
        lst = [[str(t), "1", "2", "1", "2", "1", "2"] for t in range(e, s - 1, -MINUTE_MS)]
        return json_resp({"retCode": 0, "retMsg": "OK", "result": {"symbol": "BTCUSDT", "category": "linear", "list": lst}})

    http, _ = client(handler)
    start = utc_ms(2026, 10, 20)
    rows = BybitSource(http).fetch_minutes(start, start + 2499 * MINUTE_MS)
    assert len(rows) == 2500 and [r[0] for r in rows] == [start + i * MINUTE_MS for i in range(2500)]
    spans = [(int(p["start"]), int(p["end"])) for p in reqs]
    assert spans == [(start, start + 999 * MINUTE_MS), (start + 1000 * MINUTE_MS, start + 1999 * MINUTE_MS),
                     (start + 2000 * MINUTE_MS, start + 2499 * MINUTE_MS)]
    assert all(p["category"] == "linear" and p["limit"] == "1000" for p in reqs)


def test_bybit_empty_list_for_a_past_window_is_an_error_not_no_data():
    http, _ = client(lambda req: json_resp({"retCode": 0, "result": {"symbol": "BTCUSDT", "category": "linear", "list": []}}))
    with pytest.raises(FatalError, match="empty page"):
        list(BybitSource(http).iter_pages(utc_ms(2026, 10, 20), utc_ms(2026, 10, 20, 1)))


def test_bybit_rows_outside_the_window_are_rejected():
    s = utc_ms(2026, 10, 20)
    http, _ = client(lambda req: json_resp({"retCode": 0, "result": {"symbol": "BTCUSDT", "category": "linear",
                                                                        "list": [["1585132560", "1", "1", "1", "1", "1", "1"]]}}))
    with pytest.raises(FatalError, match="outside the requested window"):
        list(BybitSource(http).iter_pages(s, s + 60_000))


def test_bybit_error_codes():
    def with_code(code, status=200):
        return lambda req: httpx.Response(status, json={"retCode": code, "retMsg": "x"})

    for code, exc in ((10001, FatalError), (10018, CooldownError), (10009, GeoBlockedError), (10016, RetryableError)):
        http, _ = client(with_code(code))
        with pytest.raises(exc):
            list(BybitSource(http).iter_pages(utc_ms(2026, 10, 20), utc_ms(2026, 10, 20, 0, 5)))
    http, _ = client(lambda req: httpx.Response(403, text=""))
    with pytest.raises(CooldownError):
        list(BybitSource(http).iter_pages(utc_ms(2026, 10, 20), utc_ms(2026, 10, 20, 0, 5)))


def test_bybit_404_with_an_empty_body_is_retried_and_never_parsed():
    calls = []
    http, _ = client(lambda req: (calls.append(1), httpx.Response(404, content=(FIX / "bybit_404_empty.body").read_bytes()))[1])
    with pytest.raises(RetryableError):
        list(BybitSource(http).iter_pages(utc_ms(2026, 10, 20), utc_ms(2026, 10, 20, 0, 5)))
    assert len(calls) == 4


def test_fallback_host_is_used_only_after_connect_or_5xx_failures():
    hosts = []

    def handler(req):
        hosts.append(req.url.host)
        if req.url.host == "api.bybit.com":
            return httpx.Response(503)
        s, e = int(req.url.params["start"]), int(req.url.params["end"])
        return json_resp({"retCode": 0, "result": {"symbol": "BTCUSDT", "category": "linear",
                                                   "list": [[str(t), "1", "1", "1", "1", "1", "1"] for t in range(e, s - 1, -MINUTE_MS)]}})

    http = HttpClient("bybit", ["https://api.bybit.com", "https://api.bytick.com"], 1000.0, clock=FakeClock(0),
                      transport=httpx.MockTransport(handler))
    s = utc_ms(2026, 10, 20)
    assert len(BybitSource(http).fetch_minutes(s, s + 2 * MINUTE_MS)) == 3
    assert hosts == ["api.bybit.com", "api.bybit.com", "api.bytick.com"]

    # a rate-limit / ban must NOT move to the fallback host (they share limits)
    hosts.clear()
    http = HttpClient("bybit", ["https://api.bybit.com", "https://api.bytick.com"], 1000.0, clock=FakeClock(0),
                      transport=httpx.MockTransport(lambda req: (hosts.append(req.url.host), httpx.Response(403))[1]))
    with pytest.raises(CooldownError):
        BybitSource(http).fetch_minutes(s, s + 2 * MINUTE_MS)
    assert set(hosts) == {"api.bybit.com"}


# ---- Binance REST ---------------------------------------------------------------------------------------------


def test_binance_rest_parses_the_real_fixture():
    def handler(req):
        return httpx.Response(200, content=(FIX / "binance_klines_2017.json").read_bytes(),
                              headers={"content-type": "application/json"})

    http, _ = client(handler)
    first = utc_ms(2017, 8, 17, 4, 0)
    [page] = BinanceSource(http).iter_pages(first, first + 4 * MINUTE_MS)
    r0 = page.rows[0]
    assert r0[0] == first and r0[1:6] == (4261.48, 4261.48, 4261.48, 4261.48, 1.775183)
    assert r0[7] == 3 and r0[10] == first + MINUTE_MS - 1  # trades, close_ts


def test_binance_pages_across_an_outage_longer_than_one_page():
    reqs = []
    start = utc_ms(2018, 2, 8)

    def handler(req):
        p = dict(req.url.params)
        reqs.append(p)
        s, e = int(p["startTime"]), int(p["endTime"])
        # a 2011-minute outage: no candles from minute 29 to minute 2039
        rows = []
        for t in range(s - s % MINUTE_MS, e + 1, MINUTE_MS):
            i = (t - start) // MINUTE_MS
            if i < 29 or i >= 2040:
                rows.append([t, "1", "2", "1", "2", "1", t + 59999, "2", 1, "1", "1", "0"])
        return json_resp(rows[:1000])

    http, _ = client(handler)
    rows = BinanceSource(http).fetch_minutes(start, start + 2999 * MINUTE_MS)
    idx = [(r[0] - start) // MINUTE_MS for r in rows]
    assert idx == list(range(29)) + list(range(2040, 3000))
    assert len(reqs) == 3  # empty middle window did not stop the paging


def test_binance_drops_the_forming_minute_using_the_servers_date_header():
    now = utc_ms(2026, 10, 20, 12, 7, )

    def handler(req):
        t_closed, t_forming = now - MINUTE_MS, now
        rows = [[t, "1", "2", "1", "2", "1", t + 59999, "2", 1, "1", "1", "0"] for t in (t_closed, t_forming)]
        return httpx.Response(200, json=rows, headers={"date": "Tue, 20 Oct 2026 12:07:03 GMT"})

    http, _ = client(handler)
    [page] = BinanceSource(http).iter_pages(now - MINUTE_MS, now)
    assert [r[0] for r in page.rows] == [now - MINUTE_MS]


def test_binance_rate_limits():
    calls = []

    def limited(req):
        calls.append(1)
        return httpx.Response(429, json={"code": -1003}, headers={"retry-after": "30"}) if len(calls) < 3 else \
            httpx.Response(200, json=[[1502942400000, "1", "1", "1", "1", "1", 1502942459999, "1", 1, "1", "1", "0"]])

    http, clock = client(limited)
    first = utc_ms(2017, 8, 17, 4, 0)
    rows = BinanceSource(http).fetch_minutes(first, first)
    assert len(rows) == 1 and clock.monotonic() >= 60  # waited for Retry-After twice (30 s each)

    http, _ = client(lambda req: httpx.Response(429, headers={"retry-after": "300"}))
    with pytest.raises(CooldownError) as e:
        BinanceSource(http).fetch_minutes(first, first)
    assert e.value.seconds == 300
    http, _ = client(lambda req: httpx.Response(418, headers={"retry-after": "7200"}))
    with pytest.raises(CooldownError) as e:
        BinanceSource(http).fetch_minutes(first, first)
    assert e.value.seconds == 7200
    http, _ = client(lambda req: httpx.Response(451, text="restricted"))
    with pytest.raises(GeoBlockedError):
        BinanceSource(http).fetch_minutes(first, first)


# ---- Binance archive ------------------------------------------------------------------------------------------------


def make_zip(day, lines, name=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name or f"BTCUSDT-1m-{day}.csv", "\n".join(lines) + "\n")
    return buf.getvalue()


def kline_line(open_ms, unit=1, price="100.00"):
    o = open_ms * unit
    return f"{o},{price},{price},{price},{price},1.0,{o + 59999 * unit},{price},2,0.5,50,0"


def test_archive_parses_the_real_zip():
    data = (FIX / "BTCUSDT-1m-2017-08-17.zip").read_bytes()
    rows = parse_archive_zip("2017-08-17", data)
    assert len(rows) == 1200  # trading began at 04:00 that day
    assert rows[0][0] == utc_ms(2017, 8, 17, 4, 0) and rows[-1][0] == utc_ms(2017, 8, 17, 23, 59)
    assert all(r[10] - r[0] == 59_999 for r in rows)
    assert hashlib.sha256(data).hexdigest() == (FIX / "BTCUSDT-1m-2017-08-17.zip.CHECKSUM").read_text().split()[0]


def test_archive_handles_milliseconds_microseconds_and_a_header_row():
    t = utc_ms(2025, 1, 1)
    ms = parse_archive_zip("2025-01-01", make_zip("2025-01-01", [kline_line(t, 1), kline_line(t + 60_000, 1)]))
    us = parse_archive_zip("2025-01-01", make_zip("2025-01-01", [kline_line(t, 1000), kline_line(t + 60_000, 1000)]))
    assert ms == us and [r[0] for r in ms] == [t, t + 60_000] and ms[0][10] == t + 59_999
    hdr = parse_archive_zip("2025-01-01", make_zip("2025-01-01", ["open_time,open,high,low,close,volume,close_time,q,n,tb,tq,ign",
                                                                 kline_line(t, 1000)]))
    assert len(hdr) == 1
    with pytest.raises(ArchiveError):
        parse_archive_zip("2025-01-01", make_zip("2025-01-01", [kline_line(t)], name="evil/../x.csv"))
    with pytest.raises(ArchiveError):
        parse_archive_zip("2025-01-01", b"not a zip")


def test_archive_download_verifies_the_checksum():
    day = "2017-08-17"
    data = (FIX / f"BTCUSDT-1m-{day}.zip").read_bytes()
    good = (FIX / f"BTCUSDT-1m-{day}.zip.CHECKSUM").read_text()

    def make(checksum_status=200, checksum_text=good, zip_status=200):
        def handler(req):
            if req.url.path.endswith(".CHECKSUM"):
                return httpx.Response(checksum_status, text=checksum_text)
            return httpx.Response(zip_status, content=data, headers={"etag": '"abc123"', "last-modified": "Tue, 18 Jul 2023 04:11:20 GMT"})
        http, _ = client(handler, bases=("https://data.binance.vision",))
        return BinanceArchive(http)

    ad = make().fetch_day(day)
    assert ad.etag == "abc123" and len(ad.rows) == 1200 and ad.zip_sha256 in good
    assert make(zip_status=404).fetch_day(day) is None  # not published yet
    with pytest.raises(ChecksumPending):
        make(checksum_status=404).fetch_day(day)
    with pytest.raises(ChecksumMismatch):
        make(checksum_text="0" * 64 + "  x.zip").fetch_day(day)


def test_archive_listing_parses_zip_entries_and_skips_checksum_objects():
    entries, token = parse_listing((FIX / "binance_listing.xml").read_bytes())
    assert token is None and len(entries) == 1
    e = entries[0]
    assert e.day == "2017-08-17" and e.etag == "014a8d177da3bf9839c293f341804d26" and e.size == 29761

    def handler(req):
        if "continuation-token" in req.url.params:
            return httpx.Response(200, content=(FIX / "binance_listing.xml").read_bytes())
        xml = (FIX / "binance_listing.xml").read_text().replace("<IsTruncated>false</IsTruncated>",
                                                                  "<IsTruncated>true</IsTruncated><NextContinuationToken>tok</NextContinuationToken>")
        return httpx.Response(200, content=xml.encode())

    http, _ = client(handler, bases=("https://data.binance.vision",))
    assert len(BinanceArchive(http).list_days("2017-08-17")) == 2  # followed the continuation token
