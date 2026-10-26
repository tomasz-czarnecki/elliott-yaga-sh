# Test fixtures

Real responses, recorded from the live APIs on 2026-10-26:

| file | what |
|---|---|
| `bitstamp_ohlc_2012.json` | Bitstamp `ohlc/btcusd` step=60 limit=5 start=2012-01-01 (flat zero-volume candles at 4.58) |
| `bybit_kline_launch.json` | Bybit v5 kline, the first five candles of BTCUSDT linear (2020-03-25 10:36..10:40), newest first |
| `bybit_404_empty.body` | the (empty) body Bybit returns with HTTP 404 for a wrong path |
| `binance_klines_2017.json` | Binance REST klines, the first five minutes (2017-08-17 04:00) |
| `binance_listing.xml` | S3 ListObjectsV2 result for the 2017-08-17 archive (zip + CHECKSUM objects) |
| `BTCUSDT-1m-2017-08-17.zip` + `.CHECKSUM` | the real first daily archive (1,200 rows) and its sha256 |

Failure cases (CDN challenge page, Bitstamp `400.002`, Binance `429`/`418` with Retry-After, `451`) are constructed
inside `tests/test_sources.py` because they cannot be recorded on demand; they follow the documented shapes.
