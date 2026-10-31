# Cycles r1: 4-year, weekly and daily cycles on BTC

Rules `cycles-r1.0` (`rules/cycles.yaml`, digest `33b3a952f2bc`). Series: `bitstamp_btcusd` 1D, last complete bar 2026-10-29. Method: Camel Finance, "An Introduction to Trading Cycles" (section numbers refer to it). Every number below comes from `ewave-cycles report` and `ewave-cycles evaluate` on this code; both are reproducible and need no network. Tags: **[verified]** measured here, **[assumed]** a choice or premise not tested, **[unknown]** cannot be told yet.

## The result in short

- **The 4-year lows are real marks and their spacing is unusual.** Lows on 2015-01-14, 2018-12-15 and 2022-11-21, gaps 1,431 and 1,437 days. Out of 400 random paths, 9 had three such bears and 1 had gaps this even. But n = 3 and the thresholds were set after seeing BTC: this is a pattern, not a statistic. **[verified, with that limit]**
- **At the daily and weekly levels the cycle rules did not beat random paths.** Run the same pipeline on BTC's own days reshuffled and it finds the same number of cycles, the same lengths, the same in-window rates and the same translation odds. Of 172 BTC-against-null comparisons, 17 fall outside the null's 5-95% range; chance alone gives about 17. **[verified]**
- **Marking cycles is possible; predicting with them is not shown.** The lows on the chart look right because the marking picks real swing lows at a chosen spacing, and it would look just as right on a random path. The prediction boxes hit no more often than boxes on random paths (daily 7% against 7-8%). Read the overlay as a map of the chart, not as a forecast. **[verified]**
- **Live is much weaker than hindsight.** Daily: 56% of hindsight lows were found live, 48% of lows confirmed live were later revised, median confirmation lag 4 days. Weekly: 50%, 28%, 21 days. BTC does no better here than the random paths either. **[verified]**
- **One lead worth following:** at the weekly level, a top left of the midpoint by the first day the cycle can end was followed by a lower low in 64% of cases (n = 14), against 36-38% on random paths. It is causal, so it could be used live, but n is small and it clears only the shuffled null's range, not the block null's. **[verified as measured, unconfirmed as an edge]**

## How the marks are made

Three levels, top down, each cycle running from low to low. Everything configurable is in `rules/cycles.yaml`.

| Level | Hindsight (all data, may repaint) | Live (walk-forward, never looks ahead) |
|---|---|---|
| 4-year | Lowest low between an all-time high and the day price trades above it again; the bear must reach at least 70% depth with the low at least 300 days after the ATH | The same bear, confirmed by a weekly close above the 10-week SMA after the lowest low |
| Weekly | DP over swing lows between consecutive 4-year lows, window 168-294 days +-10% | Lowest low of the pullback, at least 126 days after the last low, confirmed by a swing-low candle or a cross of the 10-week SMA, on Monday-based UTC weeks |
| Daily | DP over swing lows between consecutive weekly lows, window 54-66 days +-10%, 3-6 per weekly | The same at 40 days and a 10-day SMA |

### Decisions and why

| Decision | Value | Why |
|---|---|---|
| Statistics start | 2013-03-01 | Before it, mostly no-trade minutes (CLAUDE.md). The 4-year level uses all the data. |
| 4-year thresholds | 70%, 300 days | With the age at 300 days, any depth up to 77.6% gives the same three bears; with the depth at 70%, any age from 63 to 363 days does. The 2011 and April 2013 crashes are deep but took 2-62 days; the 2021 bear was 69 days and -56%. |
| Pre-2015 troughs | Not counted | The Bitstamp series starts after the June 2011 ATH, so the 2011 bear cannot be measured. n stays 3. |
| DP score | sum(depth) - penalties, in log price | As agreed. Depth is the smaller rise to the highest high on each side, capped at 30 days (daily) or 100 days (weekly): true prominence would count a never-undercut low for the whole bull market after it. |
| Gap penalty | 3.0 per (distance outside the tolerated window / window centre) | Soft, so out-of-window lows stay possible (section 2). Being 6 days outside costs 0.3 log units at the daily level. |
| Undercut penalty | 5.0 per log unit | A cycle low is the lowest point of its stretch (section 3). At 1.0 the DP skipped the plain 2025-11-21 low. |
| Node cost | 35th percentile of candidate depths | Without it every extra low adds score and lows pile up at the short end of the window. At the 50th percentile the DP dropped 2022-06-18 and 2026-07-01, which are obvious weekly lows. |
| Snap | Chosen low moves to the lowest low within +-7 days (daily), +-14 (weekly) | The gap penalty could prefer 2026-09-11 to the lower 2026-09-15, four days later. Gaps are measured after the snap, so a few lows sit slightly outside the DP's window. |
| Failed | A close below the start low, up to and including the end bar | Section 2. Including the end bar catches a one-day plunge into the low. |
| Mid translated | Top within +-5% of the length around the midpoint | The book says "at the midpoint"; a band is needed for that to ever happen. |
| Half-cycle low | Lowest low in the middle 25-75%, must be the lowest within +-3 days | The book asks for a clear low near the middle. If the slope is still running at the band's edge there is no HCL. |
| Live signals | Swing-low candle or SMA cross | Section 6 allows any one of four. Oscillator and trendline are left out: more choices, more ways to fool ourselves. |
| Swing-low candle | Requires the close above the low candle's high, not the open above its body | The book's open condition is usual, not required. On BTC a day opens at the previous close, so it can hardly hold: of the next candles closing above the low candle's high, only 9 of 41 (daily) and 3 of 11 (weekly) also opened above its body. |
| SMA signal | A close at or below the SMA since the top, then a close above it | A V-shaped low (section 11.3) can close above the SMA on its own bar. A previous-bar rule could never confirm that low; a test found this. |
| Live minimum gap | 0.75 x window start (40 and 126 days) | A low before it is treated as a half-cycle low. Costs rare early lows and inversions (section 7). |
| Candidate | Lowest low since the top, and of the last 0.17 x window centre (10 days, about 6 weeks) | See the comparison below. |
| Revision | Undercut within 0.5 x window start (27 and 84 days) revises the low; later it stands and the cycle is failed | Never redrawn: a revised low stays in the log, the cycle reverts to the low before it. |
| Levels live | Three independent machines | Hindsight nests by construction. Live is measured instead of forced: 20 of 23 standing weekly lows are within 3 days of a standing daily low. |
| Null models | 200 shuffled, 200 block-bootstrapped (20 days); bars before 2013-03 untouched | Each day keeps its candle shape relative to the previous close. Same config, same code. |

**Selection honesty.** The DP settings and the live candidate rule were picked while looking at BTC, by judging marks on the chart and agreement with hindsight, never by a return or by a null result. The nulls run with the final config, so this tilts the test in BTC's favour. BTC still does not stand out.

Live settings compared (agreement with hindsight, all on BTC):

| Candidate lookback | Rule | Daily: cycles, median d, in window, revised, hindsight found | Weekly: cycles, median d, in window, revised, hindsight found |
|---|---|---|---|
| 0.50 | no top reset | 50, 85.5, 16%, 38/89, 37/87 | 13, 245, 31%, 4/18, 10/24 |
| 0.33 | top reset | 58, 77, 21%, 49/108, 43/87 | 17, 216, 41%, 5/23, 11/24 |
| 0.25 | top reset | 64, 73.5, 25%, 52/117, 48/87 | 19, 235, 42%, 8/28, 12/24 |
| **0.17** | **top reset (used)** | **68, 70, 26%, 63/132, 49/87** | **22, 195, 55%, 9/32, 12/24** |

The tradeoff is real: a shorter lookback finds more lows and also confirms more false ones.

## 4-year level

| Low | Price | ATH | ATH price | Drop | ATH to low | Confirmed live | Top position in the cycle that follows |
|---|---|---|---|---|---|---|---|
| 2015-01-14 | $152.40 | 2013-11-30 | $1,163.00 | -86.9% | 410 d | 2015-03-02 | 0.75, RT (1,431 d) |
| 2018-12-15 | $3,122.28 | 2017-12-17 | $19,666.00 | -84.1% | 363 d | 2019-02-11 | 0.74, RT (1,437 d) |
| 2022-11-21 | $15,479.00 | 2021-11-10 | $69,000.00 | -77.6% | 376 d | 2023-01-16 | top on 2025-10-06, day 1,050 |

- Live also confirmed 2014-10-05 $275.00 on 2014-11-17, undercut 91 days later and logged as revised. That is the only 4-year revision. **[verified]**
- Random paths: at least 3 qualifying bears in 3 of 200 shuffled and 6 of 200 block paths; three bears with gaps within 6 days of each other in 0 and 1. **[verified]**
- That rarity does not prove a 4-year clock: n = 3, the thresholds were fitted after the fact, and a 4-year spacing could also come from the halving schedule, which this test cannot separate. The next low is the first real out-of-sample test. **[unknown]**

## Weekly and daily lows, 2023-2026 (hindsight)

Weekly (the cycle before these starts at the 2022-11-21 low and ends 2023-06-15):

| start low | end low | days | top position | translation | failed | status |
|---|---|---|---|---|---|---|
| 2023-06-15 $24,756.00 | 2024-01-23 $38,505.00 | 222 | 0.95 | RT |  | confirmed |
| 2024-01-23 $38,505.00 | 2024-08-05 $49,577.00 | 195 | 0.26 | LT |  | confirmed |
| 2024-08-05 $49,577.00 | 2025-04-07 $74,434.00 | 245 | 0.69 | RT |  | confirmed |
| 2025-04-07 $74,434.00 | 2026-02-06 $59,930.00 | 305 | 0.60 | RT | yes | confirmed |
| 2026-02-06 $59,930.00 | 2026-07-01 $57,734.63 | 145 | 0.61 | RT | yes | confirmed |
| 2026-07-01 $57,734.63 | open | 120 | 0.35 | LT |  | in progress |

Daily:

| start low | end low | days | top position | translation | failed | status |
|---|---|---|---|---|---|---|
| 2023-01-11 $17,318.00 | 2023-03-10 $19,569.00 | 58 | 0.62 | RT |  | confirmed |
| 2023-03-10 $19,569.00 | 2023-04-24 $26,981.00 | 45 | 0.78 | RT |  | confirmed |
| 2023-04-24 $26,981.00 | 2023-06-15 $24,756.00 | 52 | 0.04 | LT | yes | confirmed |
| 2023-06-15 $24,756.00 | 2023-08-22 $25,350.00 | 68 | 0.41 | LT |  | confirmed |
| 2023-08-22 $25,350.00 | 2023-10-11 $26,533.00 | 50 | 0.82 | RT | yes | confirmed |
| 2023-10-11 $26,533.00 | 2023-11-22 $35,651.00 | 42 | 0.69 | RT |  | confirmed |
| 2023-11-22 $35,651.00 | 2024-01-23 $38,505.00 | 62 | 0.81 | RT |  | confirmed |
| 2024-01-23 $38,505.00 | 2024-03-20 $60,760.00 | 57 | 0.89 | RT |  | confirmed |
| 2024-03-20 $60,760.00 | 2024-05-24 $66,623.00 | 65 | 0.29 | LT | yes | confirmed |
| 2024-05-24 $66,623.00 | 2024-08-05 $49,577.00 | 73 | 0.19 | LT | yes | confirmed |
| 2024-08-05 $49,577.00 | 2024-10-10 $58,867.00 | 66 | 0.80 | RT |  | confirmed |
| 2024-10-10 $58,867.00 | 2024-12-05 $92,092.00 | 56 | 1.00 | RT |  | confirmed |
| 2024-12-05 $92,092.00 | 2025-02-03 $91,530.00 | 60 | 0.77 | RT |  | confirmed |
| 2025-02-03 $91,530.00 | 2025-04-07 $74,434.00 | 63 | 0.00 | LT | yes | confirmed |
| 2025-04-07 $74,434.00 | 2025-06-05 $100,426.00 | 59 | 0.76 | RT |  | confirmed |
| 2025-06-05 $100,426.00 | 2025-08-03 $111,919.00 | 59 | 0.66 | RT |  | confirmed |
| 2025-08-03 $111,919.00 | 2025-09-25 $108,652.00 | 53 | 0.21 | LT | yes | confirmed |
| 2025-09-25 $108,652.00 | 2025-11-21 $80,537.00 | 57 | 0.19 | LT | yes | confirmed |
| 2025-11-21 $80,537.00 | 2026-02-06 $59,930.00 | 77 | 0.70 | RT | yes | confirmed |
| 2026-02-06 $59,930.00 | 2026-03-29 $64,955.00 | 51 | 0.76 | RT |  | confirmed |
| 2026-03-29 $64,955.00 | 2026-05-23 $74,192.21 | 55 | 0.69 | RT |  | confirmed |
| 2026-05-23 $74,192.21 | 2026-07-01 $57,734.63 | 39 | 0.08 | LT | yes | confirmed |
| 2026-07-01 $57,734.63 | 2026-09-15 $74,913.43 | 76 | 0.84 | RT |  | confirmed |
| 2026-09-15 $74,913.43 | open | 44 | 0.10 | LT |  | in progress |

Checked against the bars and the 1D chart by eye: 2023-03-10 $19,569, 2024-08-05 $49,577, 2025-04-07 $74,434, 2025-11-21 $80,537, 2026-02-06 $59,930 and 2026-07-01 $57,734.63 are the bars' own lows and the swing lows a reader would point at. On Bybit's 1D chart the low falls on the same day for 10 of 11 weekly and 35 of 41 daily lows since 2020-03, and 4 more daily lows are one day off. **[verified]**

The newest marks repaint. Rebuilding on data cut every 90 days from 2016, 77% of daily and 74% of weekly lows marked in the last 180 days of each cut are still marked on all the data. **[verified]**

## BTC against random paths

How to read the tables: BTC, then each null's median and 5-95% range across 200 paths. "outside" flags BTC outside a range: S shuffled, B block, + above, - below. With this many rows some flags are expected by chance: 17 of 172 rate cells are outside, and about 17 would be at the 10% this range leaves open. The rows also share cycles, so they are not independent.

### Daily level: Cycle length and timing window

| metric | BTC | shuffled, median (5-95%) | block, median (5-95%) | outside |
|---|---|---|---|---|
| cycles, hindsight | 86 | 85 (82 to 88) | 84 (81 to 87) |  |
| median length, hindsight (d) | 58 | 58 (55 to 61) | 58 (55 to 61) |  |
| in window, hindsight (constrained by the DP) | 45% | 40% (31% to 48%) | 40% (31% to 49%) |  |
| in window +-10%, hindsight (constrained) | 67% | 71% (62% to 79%) | 69% (61% to 78%) |  |
| gaps between plain swing lows | 106 | 119 (109 to 128) | 112 (103 to 122) | S- |
| in window, plain swing lows (unconstrained) | 11% | 11% (7% to 15%) | 11% (7% to 17%) |  |
| in window +-10%, plain swing lows | 21% | 20% (14% to 26%) | 22% (15% to 28%) |  |
| cycles, live | 68 | 70 (65 to 75) | 69 (64 to 74) |  |
| median length, live (d) | 70 | 64 (59 to 70) | 65 (60 to 71) |  |
| in window, live (only a minimum gap) | 26% | 23% (15% to 32%) | 24% (15% to 31%) |  |
| in window +-10%, live | 43% | 42% (34% to 53%) | 43% (32% to 51%) |  |

### Daily level: Translation and failure

| metric | BTC | shuffled, median (5-95%) | block, median (5-95%) | outside |
|---|---|---|---|---|
| share LT, hindsight | 43% | 35% (28% to 41%) | 36% (29% to 46%) | S+ |
| share RT, hindsight | 51% | 58% (51% to 65%) | 56% (47% to 64%) |  |
| share failed, hindsight | 33% | 31% (25% to 37%) | 35% (26% to 43%) |  |
| P(end below start | LT), hindsight | 68% | 67% (56% to 81%) | 64% (52% to 78%) |  |
| P(end below start | RT), hindsight | 7% | 19% (12% to 27%) | 23% (13% to 31%) | S- B- |
| P(next low lower | LT), hindsight | 32% | 36% (21% to 50%) | 39% (25% to 52%) |  |
| P(next low lower | RT), hindsight | 40% | 39% (30% to 49%) | 41% (30% to 51%) |  |
| P(end below start | LT), live | 63% | 63% (48% to 77%) | 61% (44% to 78%) |  |
| P(end below start | RT), live | 16% | 18% (9% to 28%) | 23% (12% to 33%) |  |
| P(next low lower | LT), live | 44% | 34% (17% to 50%) | 38% (21% to 52%) |  |
| P(next low lower | RT), live | 28% | 36% (26% to 46%) | 37% (26% to 49%) |  |
| P(end below start | top left of the midpoint when the cycle can first end), causal | 47% | 50% (37% to 62%) | 48% (33% to 66%) |  |
| P(end below start | top not left of it), causal | 24% | 25% (16% to 36%) | 29% (18% to 41%) |  |
| n, top left of the midpoint | 34 | 28 (22 to 35) | 30 (24 to 37) |  |
| n, top not left of it | 33 | 40 (33 to 46) | 37 (31 to 45) |  |
| P(end below start | failed), hindsight | 93% | 97% (91% to 100%) | 97% (90% to 100%) |  |
| P(end below start | failed), live | 96% | 100% (89% to 100%) | 95% (87% to 100%) |  |

### Daily level: Half-cycle low

| metric | BTC | shuffled, median (5-95%) | block, median (5-95%) | outside |
|---|---|---|---|---|
| P(end above start | HCL above start), hindsight | 79% | 80% (70% to 88%) | 76% (67% to 85%) |  |
| P(end above start | HCL below start), hindsight | 18% | 11% (0% to 25%) | 10% (0% to 25%) |  |
| P(end above start | HCL above start), live | 79% | 74% (63% to 84%) | 69% (58% to 80%) |  |
| P(end above start | HCL below start), live | 7% | 21% (7% to 43%) | 18% (0% to 43%) |  |

### Daily level: Alternation

| metric | BTC | shuffled, median (5-95%) | block, median (5-95%) | outside |
|---|---|---|---|---|
| lag-1 correlation of lengths, hindsight | +0.06 | +0.00 (-0.14 to +0.18) | -0.01 (-0.14 to +0.18) |  |
| P(long | previous short), hindsight | 42% | 41% (31% to 56%) | 44% (31% to 55%) |  |
| P(long | previous long), hindsight | 49% | 47% (32% to 59%) | 47% (34% to 60%) |  |
| lag-1 correlation of lengths, live | -0.11 | -0.02 (-0.21 to +0.16) | -0.01 (-0.19 to +0.19) |  |
| P(long | previous short), live | 82% | 59% (45% to 74%) | 58% (45% to 75%) | S+ B+ |
| P(long | previous long), live | 58% | 58% (44% to 69%) | 59% (46% to 71%) |  |

### Daily level: Live against hindsight

| metric | BTC | shuffled, median (5-95%) | block, median (5-95%) | outside |
|---|---|---|---|---|
| lows ever confirmed live | 132 | 144 (133 to 156) | 139 (126 to 151) | S- |
| of those, later revised | 48% | 51% (45% to 57%) | 49% (42% to 56%) |  |
| median confirmation lag (d) | 4 | 4 (3 to 5) | 4 (3 to 4) |  |
| hindsight lows also found live | 56% | 54% (46% to 63%) | 55% (46% to 65%) |  |
| standing live lows also in hindsight | 71% | 66% (54% to 75%) | 68% (56% to 78%) |  |
| confirmed lows never traded below before the next | 33% | 32% (27% to 37%) | 31% (24% to 38%) |  |
| standing lows not traded below before the next | 63% | 64% (58% to 71%) | 60% (52% to 69%) |  |
| standing lows not closed below before the next | 66% | 73% (67% to 80%) | 68% (59% to 79%) | S- |

### Daily level: Prediction box, taken on the first day the cycle can end, scored on the next low

| metric | BTC | shuffled, median (5-95%) | block, median (5-95%) | outside |
|---|---|---|---|---|
| boxes scored | 67 | 69 (63 to 74) | 68 (63 to 72) |  |
| next low inside the time range | 27% | 23% (15% to 32%) | 24% (15% to 31%) |  |
| next low inside the price range | 34% | 32% (21% to 41%) | 32% (23% to 42%) |  |
| next low inside the box | 7% | 7% (3% to 13%) | 8% (3% to 13%) |  |

### Weekly level: Cycle length and timing window

| metric | BTC | shuffled, median (5-95%) | block, median (5-95%) | outside |
|---|---|---|---|---|
| cycles, hindsight | 23 | 21 (19 to 23) | 21 (19 to 23) |  |
| median length, hindsight (d) | 205 | 225 (195 to 263) | 224 (200 to 265) |  |
| in window, hindsight (constrained by the DP) | 61% | 67% (50% to 81%) | 70% (53% to 84%) |  |
| in window +-10%, hindsight (constrained) | 83% | 91% (81% to 100%) | 90% (80% to 100%) |  |
| gaps between plain swing lows | 24 | 26 (22 to 30) | 27 (22 to 32) |  |
| in window, plain swing lows (unconstrained) | 33% | 34% (19% to 48%) | 31% (17% to 48%) |  |
| in window +-10%, plain swing lows | 38% | 44% (29% to 60%) | 41% (27% to 57%) |  |
| cycles, live | 22 | 19 (16 to 23) | 19 (16 to 22) |  |
| median length, live (d) | 195 | 215 (185 to 269) | 219 (190 to 268) |  |
| in window, live (only a minimum gap) | 55% | 53% (30% to 73%) | 55% (37% to 71%) |  |
| in window +-10%, live | 64% | 70% (47% to 84%) | 68% (52% to 85%) |  |

### Weekly level: Translation and failure

| metric | BTC | shuffled, median (5-95%) | block, median (5-95%) | outside |
|---|---|---|---|---|
| share LT, hindsight | 35% | 25% (14% to 37%) | 29% (13% to 45%) |  |
| share RT, hindsight | 61% | 67% (55% to 80%) | 63% (45% to 80%) |  |
| share failed, hindsight | 39% | 21% (10% to 33%) | 25% (10% to 41%) | S+ |
| P(end below start | LT), hindsight | 88% | 67% (33% to 100%) | 67% (33% to 100%) |  |
| P(end below start | RT), hindsight | 14% | 14% (0% to 27%) | 14% (0% to 29%) |  |
| P(next low lower | LT), hindsight | 38% | 22% (0% to 60%) | 29% (0% to 57%) |  |
| P(next low lower | RT), hindsight | 46% | 31% (17% to 50%) | 31% (14% to 58%) |  |
| P(end below start | LT), live | 100% | 67% (25% to 100%) | 60% (25% to 100%) |  |
| P(end below start | RT), live | 23% | 14% (0% to 27%) | 15% (0% to 36%) |  |
| P(next low lower | LT), live | 67% | 25% (0% to 67%) | 31% (0% to 67%) |  |
| P(next low lower | RT), live | 33% | 29% (10% to 50%) | 29% (10% to 55%) |  |
| P(end below start | top left of the midpoint when the cycle can first end), causal | 64% | 36% (12% to 56%) | 38% (14% to 67%) | S+ |
| P(end below start | top not left of it), causal | 0% | 17% (0% to 38%) | 17% (0% to 40%) |  |
| n, top left of the midpoint | 14 | 10 (7 to 13) | 10 (7 to 14) | S+ |
| n, top not left of it | 7 | 9 (5 to 12) | 7 (5 to 11) |  |
| P(end below start | failed), hindsight | 100% | 100% (100% to 100%) | 100% (100% to 100%) |  |
| P(end below start | failed), live | 90% | 100% (67% to 100%) | 100% (67% to 100%) |  |

### Weekly level: Half-cycle low

| metric | BTC | shuffled, median (5-95%) | block, median (5-95%) | outside |
|---|---|---|---|---|
| P(end above start | HCL above start), hindsight | 67% | 81% (67% to 100%) | 82% (62% to 100%) |  |
| P(end above start | HCL below start), hindsight | 0% | 0% (0% to 33%) | 0% (0% to 25%) |  |
| P(end above start | HCL above start), live | 53% | 80% (67% to 94%) | 79% (60% to 95%) | S- B- |
| P(end above start | HCL below start), live | 33% | 25% (0% to 100%) | 18% (0% to 100%) |  |

### Weekly level: Alternation

| metric | BTC | shuffled, median (5-95%) | block, median (5-95%) | outside |
|---|---|---|---|---|
| lag-1 correlation of lengths, hindsight | +0.08 | -0.01 (-0.33 to +0.33) | -0.01 (-0.31 to +0.32) |  |
| P(long | previous short), hindsight | 21% | 48% (25% to 80%) | 45% (25% to 67%) | S- B- |
| P(long | previous long), hindsight | 50% | 50% (17% to 70%) | 50% (14% to 73%) |  |
| lag-1 correlation of lengths, live | +0.30 | -0.08 (-0.36 to +0.27) | -0.07 (-0.35 to +0.28) | S+ B+ |
| P(long | previous short), live | 25% | 44% (23% to 75%) | 48% (24% to 75%) |  |
| P(long | previous long), live | 56% | 43% (12% to 70%) | 43% (12% to 71%) |  |

### Weekly level: Live against hindsight

| metric | BTC | shuffled, median (5-95%) | block, median (5-95%) | outside |
|---|---|---|---|---|
| lows ever confirmed live | 32 | 31 (26 to 35) | 29 (25 to 35) |  |
| of those, later revised | 28% | 33% (21% to 46%) | 32% (19% to 45%) |  |
| median confirmation lag (d) | 21 | 18 (12 to 25) | 20 (13 to 32) |  |
| hindsight lows also found live | 50% | 61% (43% to 80%) | 62% (45% to 76%) |  |
| standing live lows also in hindsight | 52% | 64% (45% to 85%) | 67% (48% to 84%) |  |
| confirmed lows never traded below before the next | 41% | 47% (37% to 60%) | 47% (30% to 63%) |  |
| standing lows not traded below before the next | 55% | 69% (58% to 81%) | 68% (48% to 82%) | S- |
| standing lows not closed below before the next | 64% | 80% (67% to 90%) | 79% (61% to 91%) | S- |

### Weekly level: Prediction box, taken on the first day the cycle can end, scored on the next low

| metric | BTC | shuffled, median (5-95%) | block, median (5-95%) | outside |
|---|---|---|---|---|
| boxes scored | 21 | 18 (15 to 22) | 18 (15 to 21) |  |
| next low inside the time range | 52% | 53% (29% to 71%) | 53% (33% to 71%) |  |
| next low inside the price range | 14% | 23% (10% to 44%) | 29% (12% to 47%) |  |
| next low inside the box | 5% | 12% (0% to 28%) | 16% (5% to 31%) | B- |

### Where BTC differs and where it does not

**No difference found [verified]:**
- Timing windows. Plain swing lows land in the window as often on BTC as on random paths: daily 11% against 11% and 11%, weekly 33% against 34% and 31%. So there is no clustering at the book's windows to find.
- The book's 70-80% in-window claim (section 2). With the DP's constraint BTC reaches 67% (daily, +-10%) and 83% (weekly), and random paths reach 69-71% and 90-91%. The claim is reproduced by the method of marking, not by the market.
- Cycle lengths and counts, once marked.
- LT against RT as a guide to the next low. In all versions BTC and the nulls agree, and LT does "predict" a lower end low on random data just as well: daily 68% against 64-67%. It is mechanical: an early top leaves more time to fall.
- Half-cycle lows. HCL above start then end above start: daily 79% against 76-80%. Also mechanical.
- Failure. A failed cycle ended below its start in 93% (daily), against 97% on both nulls. Hindsight marks are built that way.
- Live against hindsight: found, revised and lag all match the nulls at the daily level.
- Prediction boxes: daily 7% inside against 7% and 8%.

**BTC differs, in a direction that helps the method [verified as measured, not as an edge]:**
- RT daily cycles rarely end below their start in hindsight: 7% against 19% and 23%. The causal version shows nothing (24% against 25% and 29%), so this cannot be traded as it stands.
- Weekly LT by the first day the cycle can end: 64% lower end low against 36% and 38% (n = 14).

**BTC differs, against the method [verified as measured]:**
- Weekly live lows hold worse than on random paths: not traded below before the next low 55% against 69% and 68%; not closed below 64% against 80% and 79%.
- Weekly HCL above start leads to an end above start less often, 53% against 80% and 79%.
- Weekly failure is more common: 39% against 21% and 25%. Bear markets are longer and deeper than shuffling allows.
- Weekly boxes do worse: 5% inside against 12% and 16%.

**Alternation (section 11.1) is not supported [verified]:**
- Hindsight, daily: lag-1 correlation of lengths +0.06, null about 0. Weekly: +0.08.
- Weekly hindsight runs the wrong way: P(long after short) 21% against 48% and 45%. Weekly live correlation +0.30, the opposite of alternation.
- The only row in favour is daily live, P(long after short) 82% against 59% and 58%. Its correlation stays inside the null (-0.11), and that machine has a minimum gap and revisions that shape lengths.

**The boxes are not calibrated [verified].** A 25-75% price range should catch about half of the next lows. It catches 34% (daily) and 14% (weekly). The time range catches 27% and 52%. The boxes show where the rules point, and no one should size a position from them.

## Current state, last complete bar 2026-10-29 (close $77,792.67)

| Level | Open cycle | Translation so far | Failed | Box: time | Box: price | Basis |
|---|---|---|---|---|---|---|
| 4-year | Since 2022-11-21, day 1,438; bear since ATH 2025-10-06 $126,272.00 | RT (top on day 1,050 of the expected 1,434) | no | 2026-10-04 to 2026-11-20 | $16,547 to $28,327 | 3 bears, 2 gaps, min to max. Label it n = 3. |
| Weekly (live) | Since 2026-07-01 $57,734.63, day 120, confirmed 2026-08-10 | LT, top 2026-09-21 $87,373.64 | no | 2026-12-16 to 2027-04-21 | $38,977 to $58,445 | 22 past cycles, all translations (fewer than 8 LT) |
| Daily (live) | Since 2026-08-14 $62,470.00, day 76, confirmed 2026-08-18 | RT, top 2026-09-21 $87,373.64 | no | 2026-10-30 to 2026-11-11 (window passed on 2026-10-19, box moved forward) | $62,470 to $71,905 | 32 past RT cycles |

- Overlap: the daily and 4-year windows share 2026-10-30 to 2026-11-11, the shaded band. **[verified]**
- Unconfirmed daily candidate: 2026-10-29 $77,718.78. **[verified, may be replaced tomorrow]**
- Hindsight sees the daily level differently: last low 2026-09-15 $74,913.43, day 44. Live could not take it: it sits 32 days after the 2026-08-14 live low, inside the minimum gap. Hindsight weekly agrees with live: 2026-07-01. **[verified]**
- The 4-year box sits 64-79% below the last close. Lowest low of this bear so far: 2026-07-01 $57,734.63, -54.3%, 268 days after the ATH, which passes neither threshold. If that is the low, it would be the shallowest and earliest of the four, and the rule would not call it. Which of those happens: **[unknown]**.
- The same spacing in time, 1,431-1,437 days, would have put the low at 2026-10-22 to 2026-10-28. That has passed with no signal. **[verified]**

These are the rules' outputs. Measured above, they carry no shown edge over random paths at the daily and weekly levels.

## How to read the overlay

Press **Cycles** in the chart's toolbar. It appears only when `site/data/local/cycles.json` loads, so only on a preview, never on elliott.yaga.sh. All marks come from Bitstamp 1D; on other venues and timeframes a low is placed on that day's lowest bar.

- **Levels:** 4Y amber, Weekly blue, Daily pink, each with its own size and letter. The buttons switch each level on and off.
- **Hindsight** arrows under the low. Fainter with a `?`: the DP marked it but no signal has fired. They can repaint.
- **Live** rings at the low, with a line along its price to the bar that confirmed it. Dim and crossed out: revised. Dotted: a candidate still waiting for its signal. On the whole history the daily rings are hidden until you zoom in.
- **LT / RT / MT** in small grey text above each finished cycle's top, where the cycle is wide enough to hold it. Prefix W or 4Y for the bigger levels.
- **Failed cycle:** a dashed coral line along the start low up to the first close below it, ending in a cross.
- **Boxes:** the next low's time range and price range at each level. A dashed outline means the window has already passed. A shaded band over the full height means two windows overlap.
- **Info** lists the state of each level; the crosshair on a low explains that low.

## Claims by status

**Verified:**
- `uv run pytest -q` passes: 88 existing tests and 29 new ones.
- Causality: state and zones at t equal a fresh run on the bars up to t (about 120 sampled days on 2 paths), and rewriting all bars after t changes nothing at t. A deliberate same-bar confirmation bug makes `test_a_low_never_confirms_on_its_own_bar` fail.
- The public page is pixel-identical to git HEAD at desktop and phone widths and makes no request for the private file.

**Assumed:**
- Bitstamp is the right analysis series for all levels. Other venues are not run through the pipeline.
- Shuffled and 20-day block paths are a fair null. They destroy long-range structure, so they cannot rule out everything, and they keep BTC's total return, which favours long bull runs.
- Every "ours" choice in `rules/cycles.yaml`.

**Unknown:**
- Whether the 4-year pattern is a real clock. Next test: this bear.
- Whether the weekly LT lead survives more data. At about two weekly cycles a year it will take a long time.
- Whether any of this would pay after costs. No trades were simulated.

## Known weaknesses

- Live daily and weekly levels ignore the level above them, and the weekly machine knows nothing of the 4-year state.
- Timing-based lows (section 8), inversions (section 7) and fake-out failed cycles (section 11.4) are not modelled. A rally with no pullback under the SMA simply runs on: the longest live weekly cycle is 368 days.
- Translation at the moment a low is confirmed uses the finished cycle's length, known only at that point. Only the "first day the cycle can end" rows are usable before it ends.
- The DP's stretch at the right edge has no end anchor, so the newest lows are the least stable.
- The percentile ranges behind each weekly box come from few cycles (22).
- A preview server without the private file logs the browser's own 404 line; the public hosts make no request at all.

## Reproduce

```
uv run ewave-cycles report [--since 2023-01-01]
uv run ewave-cycles export     # site/data/local/cycles.json, gitignored
uv run ewave-cycles evaluate   # tables; JSON in data/derived/cycles/
cd tools && npm install && node shots_cycles.mjs   # overlay and public-site checks, preview server running
```
