# Getting the Full 15-Minute Bitcoin History Into Claude: What Works, What Doesn't, and the Best Path

Yes. Claude can download and analyze the whole Bitcoin history from 2012 to today on 15-minute bars without you doing anything. The way to do it is the free Bitstamp BTC/USD 1-minute dataset kept on GitHub (GitHub is on the sandbox allowlist), resampled to 15m in Python. The TradingView connector is not that route, because it caps out at about 52 days of 15m bars. Getting your exact chart (BYBIT:BTCUSDT.P) back to its 2020 launch takes one small step through your browser or your computer.

## TL;DR
- **Best route (Claude does it alone):** Claude clones `ff137/bitstamp-btcusd-minute-data` from GitHub. That gives Bitstamp BTC/USD 1-minute candles from 1 Jan 2012 with a daily update file and monthly full-history releases. Claude resamples them to about 520,000 15m bars and analyzes them in code. TradingView MCP pulls (max 5,000 bars) fill and check only the last few weeks.
- **TradingView MCP is not a full-history tool:** `get_ohlcv` returns at most 5,000 bars per call and takes no start or end date, so it can't page backwards. On 15m that is the last ~52 days only.
- **For your Bybit perpetual specifically:** BTCUSDT.P exists only from March 2020. Full Bybit history needs either a short script run from your browser or PC against Bybit's API (about 230 requests of 1,000 candles each), followed by an upload, or Binance's bulk archives downloaded through your browser. Claude then splices Bybit (2020→) onto Bitstamp (2012→2020) and labels each row's source.

## Key Findings

### 1. Ranked options

| Rank | Route | Coverage | Works from Claude's sandbox? | Your effort | Cost |
|---|---|---|---|---|---|
| 1 | **ff137/bitstamp-btcusd-minute-data (GitHub)**, 1m → resample to 15m | 1 Jan 2012 → yesterday (daily updates) | **Yes**, via `git clone` from github.com | None | Free (CC BY-SA 4.0 / CC BY 4.0) |
| 2 | **Bybit v5 API** `/v5/market/kline`, category=linear, interval=15 | ~March 2020 → now (native BTCUSDT.P) | No (api.bybit.com not allowlisted); run in your browser or on your PC | Run a script, upload a ~5–15 MB file | Free |
| 3 | **Binance data.binance.vision** monthly 15m kline ZIPs (spot BTCUSDT; also USDⓈ-M futures) | Spot from Aug 2017 | No; download via browser (Claude in Chrome can click through) | Upload the ZIPs/merged CSV | Free |
| 4 | **TradingView MCP `get_ohlcv`** (BYBIT:BTCUSDT.P, BITSTAMP:BTCUSD, BINANCE:BTCUSDT) | Last 5,000 bars (~52 days of 15m) | Yes (connector) | None | Needs TradingView Essential+ |
| 5 | Kaggle mczielinski "Bitcoin Historical Data" (Bitstamp 1m since 2012) | 2012 → present | No (kaggle.com login + not allowlisted) | Download + upload | Free, CC BY-SA 4.0 |
| 6 | Kraken downloadable OHLCVT ZIPs (include 15-min files from each market's start) | Kraken XBTUSD from market start; quarterly releases | No; browser download | Download large ZIP + upload | Free |
| 7 | CryptoDataDownload (Bitstamp minute data by year) | Multi-year minute files | No | Free registration + upload | Free tier |
| 8 | Coinbase Exchange API (900s granularity) | BTC-USD from Coinbase's start | No | Script + upload | Free; 300 candles/request, no bulk archive |
| 9 | CryptoCompare/CoinDesk Data API, Kaiko, CoinAPI, etc. | Varies | No | API key | Free minute data limited to 7 days at CryptoCompare; others paid. Not needed |

### 2. What the TradingView MCP can and cannot do
- The official TradingView MCP `get_ohlcv` tool takes `symbol` (EXCHANGE:TICKER), `interval` (1m, 5m, **15m**, 30m, 1h, 4h, 1D, 1W, M), `count` ("Number of bars, max 5000", default 300) and `summary`. It has **no `from`/`to`/`end` parameter**, so you always get the most recent N bars. Bars come back as `{t (unix sec UTC), o, h, l, c, v}`.
- 5,000 × 15 min = 75,000 minutes ≈ **52 days**. Changing the symbol doesn't help. BITSTAMP:BTCUSD has 2011-era history on TradingView's charts, but the MCP still gives only the latest 5,000 bars.
- Tool calls are rate-limited to about 100 requests per minute per user, and MCP access needs TradingView Essential or higher.
- **Good uses:** (a) topping up the last days after the GitHub file ends, (b) cross-checking the spliced dataset against your actual BYBIT:BTCUSDT.P chart over the overlap window, (c) quick 1D/1W full-range context. 1D × 5,000 bars covers ~13.7 years and 1W covers the whole history.
- Some third-party TradingView MCP servers (e.g., WebSocket-based or TradingView Desktop/CDP bridges) advertise "up to 5000 OHLCV bars" as well. None of the ones reviewed offers deep backward pagination.

### 3. What works from the sandbox vs. what needs you
- **Works directly:** pip/npm installs (pandas, polars, duckdb, pyarrow, ccxt) and **GitHub**. Anthropic's help article lists the default "package managers only" egress as covering npm, PyPI and GitHub. Claude Code's cloud allowlist additionally names `raw.githubusercontent.com`, `objects.githubusercontent.com`, `release-assets.githubusercontent.com` and `codeload.github.com`. In the claude.ai chat sandbox, `git clone` via github.com is the most reliable path. Release-asset and raw hosts should work but may vary by surface.
- **Installs but cannot fetch:** `ccxt`, `pybit`, `binance-historical-data` and similar install fine, but the exchange hosts they call (api.bybit.com, www.bitstamp.net, data.binance.vision, api.exchange.coinbase.com) are generally **not** on the allowlist. Expect proxy blocks from the shell. An admin can add domains, but anthropics/claude-code issues #19087, #86977 (allowlist "not enforced in plain claude.ai chat code execution (403 host_not_allowed)"), #51400, #30112 and #93589 report that "Additional allowed domains" entries were not enforced, so don't count on it.
- **WebFetch/WebSearch** read pages but can't save big files to disk, so they are useless for bulk data.
- **Needs your browser or PC:** Bybit, Binance and Kraken bulk pulls. Claude in Chrome can drive the download in *your* browser, but the file lands on your machine. You then attach it to the chat (CSV/Parquet/ZIP), or put it in Google Drive for Claude to pick up through the connector. Uploading directly in chat is the more reliable of the two for binary files.
- **Regional caveat:** on the PythonAnywhere forum (topic 35940), a US user's call to Bybit's /v5/market/tickers returned a 403 reading "The Amazon CloudFront distribution is configured to block access from your country," while the same code worked from PythonAnywhere's EU system. If you're in Poland, your home connection should be fine.

### 4. Source details (start dates, limits, quality)
- **Bitstamp (via ff137 GitHub repo).** The bulk file `btcusd_bitstamp_1min_2012-2025.csv.gz` covers 1 Jan 2012–7 Jan 2025: 6,847,200 rows, about 89 MB gzipped and 327 MB unzipped, "no duplicates and no null values". A daily GitHub Action appends to `data/updates/btcusd_bitstamp_1min_latest.csv`. Monthly full-history releases (e.g., `bitstamp-btcusd-1m-2026-09`, "Full Bitstamp BTC/USD 1-minute history from January 2012 through September 2026") include CSV and Parquet assets, and a companion PR reports 7,714,079 rows in that release. Timestamps are the **UTC open time**. Missing minutes are filled with flat zero-volume candles, and a provenance file flags outages. The longest outage is **108 hours from 5 Jan 2015** (Bitstamp hot-wallet incident). Liquidity in 2012 was thin. The maintainer notes that 30-minute zero-volume stretches become rare from 2013, and that after March 2013 every 4h+ zero-volume period matches a flagged incident. Bitstamp's own API allows 1–1,000 candles per call with steps of 60…259200 s (900 = 15m). If you set both `start` and `end`, the API honours `end` and ignores `start`, so paginate with `start` only.
- **Bybit.** Bybit's 24 March 2020 press release announced USDT perpetuals "with immediate effect," though CoinDesk later amended its story to clarify the launch date and the exact go-live day is unresolved; Bybit's public trade archive for BTCUSDT starts with `BTCUSDT2020-03-25.csv.gz`. The instruments endpoint's `launchTime` is inconsistent across sources: 15 March 2020 in one developer's live capture, 30 March 2020 in the docs' example. Treat **25 March 2020** as the practical first day. `/v5/market/kline` returns max **1,000** candles per request (default 200), newest first. Bybit's V5 "Rate Limit Rules" page says: "You are allowed to send 600 requests within a 5-second window per IP by default." Full 15m history is about 230,000 bars, so roughly 230 requests: seconds of work. `public.bybit.com` also hosts `kline_for_metatrader4/` files, but their coverage of BTCUSDT 15m and their 2026 freshness are unverified.
- **Binance.** data.binance.vision publishes daily and monthly ZIPs for every symbol and interval including 15m. Monthly files appear on the first Monday of the month and daily files the next day, each with checksums. Spot BTCUSDT 1m archives run from August 2017. The REST cap is 1,000 klines per request.
- **Coinbase.** 300 candles max per request, granularity 900 = 15m, and no bulk archive.
- **Kraken.** The OHLC REST endpoint returns only the most recent 720 candles. Kraken does publish full-history OHLCVT CSV ZIPs (1/5/15/60/240/720/1440-minute) per pair, refreshed quarterly.
- **Kaggle/other datasets.** The mczielinski Kaggle set is the upstream of the ff137 repo. A Kaggle "15-minute since 2012" set holds only price (no OHLCV) to end-2021, with interpolated gaps, so avoid it. A Hugging Face "binance_btcusdt_perp_15m_klines" set is a dollar-bar construction (2.37M rows), not standard 15m candles, so avoid that too.
- **CryptoCompare/CoinDesk.** Minute data is stored for only 7 days on the free API, at max 2,000 points per call. Paid vendors (Kaiko, CoinAPI, Tiingo, Polygon) are unnecessary here.

## Details

### Size and format
- **Row counts (15m):** 35,040 bars/year. Bitstamp 2012-01-01 → 2026-10-26 ≈ **519,000 rows**. Binance spot from Aug 2017 ≈ 322,000. Bybit BTCUSDT.P from Mar 2020 ≈ 231,000.
- **File sizes (estimates):** 15m OHLCV CSV is roughly 30–40 MB for the full history, Parquet (zstd) roughly 8–15 MB, and gzip CSV about 10 MB. The 1-minute source is what's large (327 MB unzipped). Everything fits easily in sandbox RAM and disk.
- **Context reality:** at roughly 30–40 tokens per CSV row, 519k rows would be about 15–20 million tokens. That is far beyond any context window, so Claude can never literally "read every row" as text.

### Stitching a continuous history for BYBIT:BTCUSDT.P
1. **Segments:** Bitstamp BTC/USD 15m from 2012-01-01 up to a splice date, then Bybit BTCUSDT.P 15m from the splice date onward. Pick the splice after a few weeks of overlap, e.g., 2020-05-01, to avoid launch-week illiquidity.
2. **Price level:** measure the median `close_bybit / close_bitstamp` ratio over the overlap. Perp-vs-spot basis is usually small: Bybit's Help Center defines funding as "Average Premium Index (P) + clamp (Interest Rate (I) − Average Premium Index (P), 0.05%, −0.05%)" with an interest rate of 0.03% per day, so small premiums land on a 0.01%/8h baseline, and Coincub reports BitMEX BTC perp funding "printed exactly 0.01% for 78.19% of the third quarter of 2025". USDT-vs-USD also adds a small varying offset. For swing, pivot and Fibonacci work the gap is negligible. If you want the joined series to sit exactly on the Bybit level, multiply the pre-splice Bitstamp prices by the overlap ratio (back-adjustment). Don't add funding payments into prices: funding is a cash flow between traders, not a price adjustment.
3. **Volume:** not comparable. Bitstamp volume is in BTC on a spot venue, Bybit's is contracts on a far larger derivatives venue. Keep a `source` column and use volume only *within* a segment, or normalize it (e.g., rolling z-score or percentile per source).
4. **Gaps and outages:** reindex to a full 15m UTC grid. Mark synthetic (zero-volume or forward-filled) bars with a flag, and exclude them from pattern statistics. Known flags include the Bitstamp Jan 2015 outage and thin 2012 trading.
5. **Timestamps:** use UTC bar **open time** everywhere. Bitstamp (seconds), Bybit/Binance (milliseconds) and TradingView MCP (seconds) are all open-time epochs. Check units before merging, and resample with `closed='left', label='left'` so 15m bars match TradingView/exchange bars.
6. **Validation:** pull the last 5,000 BYBIT:BTCUSDT.P 15m bars through the MCP and diff them against the stitched file. Every OHLC should match to tick size on the Bybit segment.

### Recommended analysis workflow (what "reading the whole history" honestly means)
- **Load:** `polars` or `duckdb` on Parquet (fast). Use pandas if you prefer.
- **Resample** 15m → 1h, 4h, 1D, 1W, and keep all of them.
- **Scan in code, summarize to text:** fractal swing highs and lows (e.g., N-bar pivots), ZigZag at %/ATR thresholds, classic and Fibonacci pivots, Fibonacci retracements/extensions between major swings, regime and volatility tables, drawdowns, and per-year or per-cycle statistics.
- **Chunk:** iterate by month or year and write a compact digest (e.g., each month's range, major swings and key levels hit). Claude reads the digests, which add up to tens of thousands of tokens rather than millions, and drills into any raw window on demand.
- **What this means honestly:** Claude "reads" the whole history the way a quant does. Every bar is processed by code, and Claude reasons over the computed results. It does not hold 519k rows in its head at once.

## Recommendations

**Best route: Claude does all of it.**
1. `git clone --depth 1 https://github.com/ff137/bitstamp-btcusd-minute-data`, or fetch the latest monthly release Parquet.
2. Concatenate the bulk and update files, check for gaps, resample 1m → 15m (UTC, left-closed), and save `btc_15m_bitstamp.parquet`.
3. Top up any days after the file's last row with the TradingView MCP (`BITSTAMP:BTCUSD`, 15m, count 5,000).
4. Run the analysis pipeline above.

This gives about 519k bars from 2012 to today on Bitstamp's chart, which is close to but not identical to your Bybit chart.

**Fallback / upgrade to native Bybit (needs ~5 minutes from you).**
1. Claude writes a small script. Either it's a Python script using `ccxt` or plain `requests` that pages `/v5/market/kline?category=linear&symbol=BTCUSDT&interval=15&limit=1000` from 2020-03-25 to now, or a browser-console version that Claude in Chrome runs on a bybit.com tab.
2. You run it (or let Claude in Chrome run it) and **attach** the resulting `bybit_btcusdt_p_15m.csv/parquet` to the chat.
3. Claude splices it onto Bitstamp, validates against the TradingView MCP, and analyzes.

**Second fallback.** Download Binance monthly 15m ZIPs (spot BTCUSDT, Aug 2017→) from data.binance.vision in your browser and upload them. Use this if Bybit's API is blocked for you.

**Not worth it:** paginating TradingView (impossible), Kaggle downloads (login and allowlist friction for the same Bitstamp data), and paid APIs.

## Caveats
- The sandbox allowlist differs by Claude surface and admin settings. The GitHub route is the most reliable but not guaranteed, so if a clone fails, the fallback is uploading the same file.
- The ff137 dataset is community-maintained. It is validated and fully documented, but it's not an official Bitstamp product. Licence: CC BY-SA 4.0 for the combined history, so keep attribution.
- Bybit's exact launch timestamp is unresolved (15 March vs. 30 March 2020 in different sources, with the trade archive starting 25 March). Treat the first few weeks as illiquid.
- File-size and token figures are estimates. Row counts are arithmetic from bar frequency.
- Pre-2013 Bitstamp data is thin and gappy. Patterns found there carry less weight.
