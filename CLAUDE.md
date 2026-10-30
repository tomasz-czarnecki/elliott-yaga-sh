# Elliott Wave Analyzer for BTC

## Goal
Build a system that studies the full Bitcoin price history, counts Elliott waves on it, and keeps a live hourly forecast of the most likely current counts.

1. **Build the dataset.** Collect BTC history from 2011/2012 to today. Mark Elliott waves on the **1D, 4H and 1H** charts, using 15m bars to see inside the most recent move. Record how often each pattern, retracement, extension and wave duration occurs. Outside material, such as research papers and published analyst counts, can be used as an input.
2. **Run the live loop.** After each 1H candle closes, load the previous forecast and look at what the new bar changed. Use the historical statistics to update the forecast, then report the **1–2 most probable counts with probabilities** (e.g. 30% / 20%), plus the share left for "other/unclear".

## Status
- **Phase 0 (data collector): built** — `src/ewave/ingest/`, run by systemd timers. See "Data collector" below.
- Phases 1–5 (pivots/grammar, statistics, scoring, live loop, evaluation): not started.
- **Site: built**: static landing page and candlestick chart in `site/`. See "Site" below.

## Reference docs (read before designing anything)
- `research/probabilistic-elliott-wave-engine-plan.md`: architecture, data structures, Phases 0–5, evaluation, and where LLMs fit. **This is the master plan.**
- `research/btc-15m-history-data-sources.md`: where the data comes from, sources ranked, the limits of each.

## Non-negotiable principles
- **Counting is deterministic code, never the LLM.** Pivots, labels, ratios and probabilities come from the engine. An LLM may only narrate the engine's JSON, and every number it writes must match a number in that JSON.
- **Causal only.** A pivot can be used only after its `ts_confirmed`. The in-progress leg is always provisional. Statistics and calibrators are fitted on past data only (walk-forward). Any lookahead is a bug.
- **Probabilities describe outcomes you can check later**, e.g. "target zone hit before invalidation within horizon H". They never claim a count is "true". Probabilities must be calibrated: check Brier score, log loss and reliability diagrams.
- **Always report an "other/unclear" share.** The top counts must not be forced to add up to 100%.
- **Compare against baselines.** Measure every statistic against a null model run on random or reshuffled price paths, and every forecast against a model that uses volatility only, with no wave structure. If the engine doesn't beat these, say so plainly.
- **Rules are versioned config (YAML), not code branches.** Store the engine version with every snapshot.
- **Parquet cannot be appended to.** The planned predictions log is therefore one file per run/day (or SQLite), never appends to one Parquet file.

## Elliott Wave rules
Rules, Fibonacci levels, TDI readings, invalidations and targets come from the user's **NewWave rulebook**: load the `newwave-rulebook` skill. Do not use textbook Elliott Wave values. The course's numbers differ in many places. When the rulebook is silent, say so and ask the user before inventing a rule.

## Data collector (Phase 0)
Three venues are collected and stored **separately**: `bitstamp_btcusd` (spot, from 2011-08-18 12:37), `binance_btcusdt` (spot, from 2017-08-17 04:00), `bybit_btcusdt_perp` (linear perp, from 2020-03-25 10:36). How to join them for analysis is **still open**: decide after an overlap report. The working recommendation is Bitstamp → Binance spot as the analysis series and Bybit perp kept separate as the live/trading series.

### Layout (`data/`, gitignored; `EWAVE_DATA` overrides the root; resolved from the project dir, never the cwd)
```
data/raw/{venue}/1m/{YYYY}/{YYYY-MM-DD}.parquet   source of truth: one UTC day of 1m bars
data/raw/_superseded/{venue}/{day}.r{N}.parquet   previous version of a closed day whose rows changed
data/bars/{venue}/{15m,1h,4h,1d}/{YYYY}.parquet   derived bars, rebuildable (`ewave-data rebuild`)
data/sources/binance/…                            every Binance archive version seen (+ .CHECKSUM)
data/state/catalog.sqlite                         days, gaps, archive versions, checks, runs (rebuildable: `reindex`)
```
Read it with `ewave.data`: `load_1m(venue, start, end)` and `load_bars(venue, tf, start, end, complete_only=True)` (UTC, end exclusive; only the needed day files are opened). Never glob the raw tree by hand.

### Commands (`ewave-data`, installed in `.venv`; run with `uv run ewave-data …`)
`sync` (timer, every 15 min) · `backfill --venue V [--since D]` · `audit` (timer, daily 04:37 UTC; `--native` compares our bars with each exchange's own candles) · `status [--check]` · `gaps [--no-trades MIN]` · `show VENUE DAY [--tf 15m] [--csv]` · `rebuild` · `reindex` · `export-site [--out DIR]`. Tests: `uv run pytest` (`-m network` for the live smoke tests). Timers live in `deploy/systemd/`; logs: `journalctl --user -u ewave-sync`.

### Data rules (verified against the live APIs; do not "simplify" these)
- All timestamps are **UTC bar open time**; internally Int64 epoch **ms**. Bars are left-closed, labelled by open time, and never cross a day boundary.
- **Never store the forming minute.** `last_closed` = floor(now) − 1 min, from the earlier of local/server time. Raw rows are exactly what the exchange returned; missing minutes are recorded (catalog `gaps`), never filled in raw.
- **Bars are built from traded minutes only (volume > 0)** for every venue; a bar with none is flat at the carried close. Exchanges return no-trade minutes as flat candles at the previous close, and including them invents opens/extremes. `hl_order` says whether the high or the low came first (minute resolution; `same_minute` when unknown).
- **`complete`** on a bar comes from the venue's `covered_until` (what a successful fetch really covered), never from the wall clock; a 1d bar also needs its day closed. The live loop must use `complete_only=True`.
- A day is **closed** only after a full re-fetch after D+1 00:10 UTC returns all expected minutes, or two identical re-fetches ≥1 h apart (then the missing minutes are recorded as gaps). A closed day that later changes keeps its old file in `_superseded` and bumps `revision`. A completely empty day never closes by itself on Bitstamp/Bybit (fetch fault); it does on Binance.
- **Bitstamp**: paginate with `start` only (when `end` is also sent, `start` is ignored); max 1000 rows; a short/empty page is not the end of data.
- **Bybit**: rows come newest first; a start/end window over 1000 minutes silently drops its oldest rows; an empty page for a past window is an error; each open equals the previous close.
- **Binance**: use the **daily** archives (monthly ones are stale/misaligned). Timestamps are **µs from 2025-01-01**, ms before — detect by size. Archives are sometimes re-published: ETags are recorded and a new version is reconciled (an archive with fewer minutes never replaces ours; REST never overwrites an archive day). Missing minutes are real exchange outages.
- The venue lock (`data/state/{venue}.lock`) must be held by anything that writes a venue's data; the timer's sync skips a busy venue.

### What the full backfill produced (2026-10-26) and how it was verified
| venue | days | 1m rows | missing minutes | verification |
|---|---|---|---|---|
| `bitstamp_btcusd` | 5,549 (from 2011-08-18) | 7.99 M | **0** (a continuous 15-year grid) | == ff137 snapshot on all 7,757,279 minutes (0 mismatches); own candles: 80 days / 10,160 bars, 0 mismatches; TradingView 2011–2025: all prices match |
| `binance_btcusdt` | 3,358 (from 2017-08-17) | 4.83 M | 8,632 in 37 real exchange outages (`ewave-data gaps`) | all 3,357 archive checksums verified; own candles: 9,978 bars, 0 mismatches; TradingView 2017-10–2025: all prices match |
| `bybit_btcusdt_perp` | 2,407 (from 2020-03-25) | 3.46 M | **0** | own candles: 80 days / 10,160 bars (see quirks); TradingView 2020–2025 + 4h/1h/15m windows: all prices **and volumes** match |

### Known data quirks (exchange-side, not bugs)
- **Bybit 1m klines do not chain "open = previous close" on ~70 days between 2021-02-03 and 2021-05-16** (plus 2020-03-31); logged as `soft` checks. On those days Bybit's own REST 1h/4h/1d candles differ from the aggregate of its 1m candles (mostly volume, a few closes by a few USDT); 2021-12-01 differs in volume only. TradingView's `BYBIT:BTCUSDT.P` bars equal the 1m-derived ones, so our series matches the user's chart.
- **TradingView's Bitstamp and Binance *volumes* differ slightly (≤ ~1%) from the exchanges' data**; prices are identical. Our minutes equal the exchanges' own API/archives (and ff137 for Bitstamp).
- Bitstamp: 2011–2013 is mostly no-trade minutes (thin market) and Jan 2015 has a 6,472-minute halt (flat zero-volume rows). Consider starting statistics at 2013-03.
- Binance bars that span an outage have `n_minutes` below the bar length; check it before trusting such a bar.

## Site
Static frontend, no build step, for elliott.yaga.sh: `index.html` (landing, its numbers come from `data/stats.json`), `chart.html` (TradingView Lightweight Charts, vendored in `vendor/`; keep its attribution logo enabled). Style follows yaga.sh, re-tinted to navy.
- **Export:** `uv run ewave-data export-site [--out DIR]` writes complete bars only to `site/data/` (gitignored): `stats.json` and `bars/{venue}/{tf}.json`. Format is in `src/ewave/ingest/export.py`. 15m is capped to the last 365 days.
- **Preview:** `python3 -m http.server 8082 --bind 127.0.0.1 --directory site`
- **Checks:** `cd tools && npm install && node shots_site.mjs` (screenshots, console errors, failed requests; dev only, not needed to deploy).

## Stack
Python 3.12, **uv** (`uv sync`; `exclude-newer` pins packages to releases ≥14 days old), Polars 2.0, httpx, SQLite (stdlib), pytest + Hypothesis. DuckDB/Numba are not needed yet. Plotly or Lightweight Charts for charts later.

## Planned layout (later phases)
```
src/ewave/ingest/      # Phase 0: DONE
src/ewave/pivots/      # Phase 1: causal multi-scale zigzag pivots
src/ewave/grammar/     # Phase 1: wave-pattern grammar, beam search, hard/soft rules
src/ewave/stats/       # Phase 2: ratio/frequency distributions + null model
src/ewave/scoring/     # Phase 3: Bayesian update, calibration, "other" share
src/ewave/live/        # Phase 4: hourly loop (run right after the hh:00:20 sync), snapshots, reports
src/ewave/eval/        # Phase 5: walk-forward replay, baselines
rules/newwave.yaml     # versioned rulebook
gold/                  # user's hand-labelled swings (a regression test, not ground truth)
```

## Build order
Start with the MVP: a Phase 1 engine on 1H/4H that handles only impulses, zigzags and flats, with hand-set weights. Log predictions from the first week. Add triangles, combinations, 1D nesting and learned weights later. Treat the Phase 5 evaluation as the go/no-go point for trusting the probabilities. Do not start the wave engine before the Bitstamp pre-2013 data (thin, mostly no-trade minutes) has been judged: consider starting statistics at 2013-03.

## Working conventions
- Commit only when asked. Keep large data files out of git. Keep scripts outside the data directories.
- Each step of the live loop must be safe to rerun and keyed by bar timestamp.
- Report results honestly. If something has no edge, is unverified, or was skipped, say so.
