# 02. What BTC's own history says

Worker EMP, research round `elliott_research_r1`, 2026-10-30. Part of the question "how do we teach a model how BTC behaves". This file does not compare models; it measures the facts any of them would have to learn. I read "jev" in the voice note as JEPA (LeCun's Joint Embedding Predictive Architecture), and also keep in mind time-series foundation models such as Kronos, Chronos and TimesFM. **[assumed]**

Every number below comes from a script in `research/model-options/spikes/empirical/` run on our verified data, or is simple arithmetic I say is arithmetic. Tags: **[verified]** measured here, **[assumed]** a choice or premise not tested, **[unknown]** cannot be told yet.

## Summary

1. **Too few high-degree examples for any deep model on wave labels.** 13.7 years of Bitstamp hold about 17 independent rule-legal 5-wave structures at daily degree, 59 at 4H, 188 at 1H, 219 at 15m, plus 23 weekly cycles and 3 four-year lows. On 59 events you can only see an edge of 18 points or more. **[verified]**
2. **"BTC has its own Fibonacci" is not supported.** Of 3,696 tests of 11 levels on swing ratios, 264 read high against 235 (202 to 270) on random paths with BTC's own volatility. Inside 1,106 rule-legal impulses every NewWave window is hit as often as on random paths: W2 at 0.5-0.618 17.6% against 17.5%, W4 at 0.236-0.382 41.9% against 41.3%, W3 near 1.618 9.2% against 9.4%. The rules and the zigzag produce these numbers on their own. **[verified]**
3. **One faint Fibonacci lead.** Extensions in linear price near 1.618: 14% more than the neighbouring ratios on Bitstamp and Bybit, none on Binance; a dense scan puts its peak at 1.617 but with a family-wise p of 0.18 to 0.34. That is about 3 legs in 1,000. A lead, not a level to give weight. **[verified as measured, unconfirmed]**
4. **BTC's real swing fingerprint is a step at 1.0, not a Fibonacci level.** A leg stops short of the last pivot a little more often than chance and rarely stops just past it. This repeats by era and venue at 15m and 1H and mostly at 4H: about +3 points against +0.2 on random paths. The sharp spike at exactly 1.0 is old Bitstamp, and the average run after a break shows no edge since 2018. **[verified]**
5. **Rule-legal impulses look more common on BTC, but that is mostly trend.** Against volatility-only paths they are 1.1 to 1.4 times as common at 1H to 1D. Keep BTC's slow trend in the null and that falls to about 1.0 to 1.15. Binance and Bybit show nothing, and 6 of 24 scales stand out in 2014-2017 against 0 and 1 later. **[verified]**
6. **A growing count predicts little.** After a legal 1-2-3-4, W5 makes a new extreme 58-66% of the time against 64-68% on random paths. After a legal five, the next leg behaves as on random paths at every scale. **[verified]**
7. **His weekly-cycle hypothesis, first half: true but mechanical.** 75% of weekly lows have a legal 5-wave down ending within 14 days at one of six degrees, 100% if zigzags count. Random paths give 57-70% and 100%. **[verified]**
8. **Second half, the midpoint top: not shown.** Tops within 0.1 of the middle: 13% hindsight and 27% live, against 14-19% on random paths (n = 23 and 22). Pivot lows are as common there as pivot highs. Up-structures do land in the middle of live cycles more often than chance (53% against 22-26%, p 0.002 to 0.01), but that fails correction, runs the other way in hindsight, and in the causal test those tops hold worse, not better: 25% against 50% on 4H 5-waves, same sign at all 8 settings, p 0.05 at best. If anything, mid-cycle up-moves keep going. **[verified]**
9. **One rhythm is real as measured.** Daily returns have about twice the spectral power at 168-294 day periods (p about 0.02), which supports a soft 24-42 week rhythm, but it is absent in 2022-2026. It does not make lows land in the window more often (cycles-r1), and no causal test here turned it into an outcome. **[verified]**
10. **TDI shark in the water: no outcome value.** The pattern and the 3-5 divergence appear as often on random paths (divergence on 54-70% of legal impulses against 55-68%), and what looks like an edge is the barrier arithmetic of a short W5. **[verified]**
11. **What is learnable:** volatility (out-of-sample R2 0.35 to 0.56), slow trend (variance ratio 1.12 to 1.38 at 20-180 days), falls 1.2 to 1.3 times faster than rises, more extended third waves at 15m and 1H, the step at 1.0. All of it fits in a few simple features. **[verified]**
12. **For the model choice:** wave labels are not a usable training target, since a pivot with a legal count typically has a dozen legal ways to draw it. Start with a small calibrated model on barrier outcomes, and make any JEPA or foundation model beat it, and a volatility-plus-trend baseline, on the same walk-forward. Keep the rule checker as an annotation and accountability tool, which is what the October 23 note asked for. **[assumed, follows from the above]**

## 0. How this was measured

**Data.** `bitstamp_btcusd` from 2013-03-01 (the start cycles-r1 uses), through `ewave.data.load_bars`: 13.66 years, 479,214 15m bars, 119,803 1H, 29,950 4H, 4,991 1D. Binance and Bybit are run only as checks: they cover the same market after 2017 and 2020, so they rule out a Bitstamp artefact but are not independent evidence. **[verified]**

**Swings.** A causal zigzag in log price (`zigzag.py`). A pivot is the extreme of a leg and is confirmed on the bar where price has reversed by the threshold; the threshold for a bar uses only earlier bars; a bar's high and low are visited in the order they traded, from the 1-minute data. Pivots never repaint: a run on a prefix of the bars gives a prefix of the pivots, tested at 3 cut points on every scale of 1H, 4H and 1D (`check_tools.py`). On a fine driftless random walk the legs follow threshold x (1 + Exp(1)), as theory says, and the zigzag reproduces that law. **[verified]**

**Scales.** 24, written as bars and threshold: `4h_pct8` is 4H bars with an 8% reversal, `1h_atr4` is 1H bars with a reversal of 4 x ATR14 in log price. Fixed thresholds are what a trader's eye sees; ATR thresholds keep the swing rate steady across volatility regimes.

**Rule checker** (`impulse.py`). A candidate is six consecutive pivots, so each wave is one leg at that threshold and degree comes from the threshold. R1 W2 never beyond the start of W1, R2 W3 beyond the end of W1, R3 W3 never the shortest, R4 W4 never into W1 (rulebook sections 0-1). "Legal" also requires W5 beyond W3; truncation is a guideline in the rulebook and is counted apart. Fib pulls follow sections 1 and 4: W2 pull 0-1, W3 pull 0-1-2, W4 pull 2-3 only, W5 pull 0-1-4 and 0-1-2.

**Null paths** (`nulls.py`). Same start price, same bars, no order. Each statistic runs through the identical pipeline on these paths, and only the difference from them is evidence.

| Null | What it keeps | What it destroys | Why it is here |
|---|---|---|---|
| shuffle | each bar and its candle shape, total return | all time order, volatility clustering | the plainest random path, also used in cycles-r1 |
| block | runs of bars as long as one median leg of the scale tested | anything longer than one leg | keeps short volatility clustering; a longer block would keep the swings under test |
| signflip | every bar's size in its place, so the calm and wild periods stay where they were; each bar mirrored at random | all direction structure | the "volatility-only" baseline CLAUDE.md asks for |
| trendflip (trend +-60d) | the same, mirrored around BTC's own local drift (centred mean over +-60 days; also +-30 and +-120), so bull and bear phases stay at their dates; the price level still wanders | direction structure faster than the drift window | added after the first census, to ask whether a pattern exists beyond volatility and bull/bear regimes |

**Multiple testing.** There are thousands of tests, so a low p alone means little. p is a Monte Carlo rank among null paths (500 to 1,000 paths in most runs). On top of it: Benjamini-Hochberg q; Westfall-Young family-wise p (the share of null paths whose largest z over all tests beats this one), which handles the fact that scales overlap; omnibus counts of high readings against the same count on null paths; placebos, where null paths are treated as if they were BTC.

### Decisions and why

| Decision | Value | Why |
|---|---|---|
| Degree mapping | 15m_pct4, 4h_pct8, 1d_pct16 stand for 15m, 4H and D degree | Their median legs (7.2%, 15.0%, 33.3%) match the rulebook's expected move per signal timeframe (section 5: 5-7%, 12-15%, 20-30%). 1H is not in that table; I use 1h_pct4 (7.3%). |
| Ladder | 15m_pct2, 1h_pct4, 4h_pct8, 1d_pct16 | Thresholds 2x apart, for pooling across degrees: 1,106 impulses. Its null paths are independent across timeframes while BTC's are one market, so ladder p values may run a little low. |
| Bands | +-1.5% and +-4% of a level; +-5% for hit rates in impulses | Narrow: a fib drawn to the wick. Wide: the tolerance a person allows. |
| Local excess | count in the band against the shoulders out to 4 band-widths | The overall shape of the density cannot create a hit; only a feature at the level can. |
| R3 price scale | log; linear changes the legal count by at most 3 per ladder scale | It is the only rule where the price scale matters. |
| Weekly cycle | the 24-42 week low-to-low cycle of `ewave.cycles` (Camel Finance), hindsight and live | "Weekly cycle" is my reading of his term. The other reading, day of the week, is tested in C7. **[assumed]** |
| Primary settings for section C | 4h_pct8 and 1d_pct16, +-14 days, mid band 0.4-0.6 | Fixed from the census, before any section C outcome was seen. +-14 days is the weekly level's own `swing_k_days`. |
| TDI band width | 1.6185 standard deviations | The course gives the length (31), not the width; this is the TDI default. **[assumed]** |
| Trend window | +-60 days | Long against the 5-wave spans at 1H and 4H. At 1D it is close to the size of the largest structures, so trendflip may absorb real structure there: read 1D with signflip beside it. **[assumed]** |

## A. Sample-size census

### A0. The plain facts, before any waves

Direction has almost no memory, volatility has a lot. Everything else in this report sits on top of this. **[verified: `a4_facts.py`]**

| bars | lag | return autocorrelation | shuffled bars, 5-95% | absolute return autocorrelation |
|---|---|---|---|---|
| 1h | 1 | -0.076 | -0.005 to +0.005 | +0.446 |
| 1h | 24 | -0.006 | -0.004 to +0.004 | +0.249 |
| 4h | 1 | -0.032 | -0.009 to +0.008 | +0.375 |
| 4h | 42 | +0.019 | -0.008 to +0.010 | +0.141 |
| 1d | 1 | -0.024 | -0.024 to +0.019 | +0.336 |
| 1d | 30 | -0.009 | -0.023 to +0.021 | +0.113 |

| bars | lag-1 return autocorrelation, 2014-2017 | 2018-2021 | 2022-2026 |
|---|---|---|---|
| 1h | -0.065 | -0.027 | -0.009 |
| 4h | -0.049 | -0.033 | +0.001 |
| 1d | -0.009 | -0.091 | -0.027 |

The negative 1H value is a microstructure effect that fades by era. The next bar's log range, from the trailing 20-bar mean, fitted up to 2021 and scored on 2022-2026:

| bars | out-of-sample R2, 2022-2026 | test bars |
|---|---|---|
| 1h | 0.56 | 42,331 |
| 4h | 0.43 | 10,582 |
| 1d | 0.35 | 1,763 |

BTC does trend, slowly. Variance ratios of daily returns (above 1 means trending at that horizon):

| horizon, days | variance ratio | shuffled days, 5-95% | p high | 2014-2017 | 2018-2021 | 2022-2026 |
|---|---|---|---|---|---|---|
| 2 | 0.98 | 0.98 to 1.02 | 0.938 | 0.99 | 0.91 | 0.97 |
| 5 | 0.97 | 0.95 to 1.05 | 0.826 | 0.94 | 0.93 | 1.01 |
| 10 | 1.03 | 0.92 to 1.07 | 0.267 | 0.95 | 0.98 | 1.01 |
| 20 | 1.12 | 0.88 to 1.10 | 0.026 | 1.04 | 1.05 | 1.03 |
| 30 | 1.19 | 0.86 to 1.12 | 0.012 | 1.12 | 1.06 | 1.03 |
| 60 | 1.26 | 0.80 to 1.17 | 0.016 | 1.18 | 1.12 | 1.13 |
| 90 | 1.34 | 0.76 to 1.21 | 0.014 | 1.23 | 1.24 | 1.18 |
| 120 | 1.38 | 0.70 to 1.26 | 0.020 | 1.24 | 1.34 | 1.22 |
| 180 | 1.38 | 0.65 to 1.32 | 0.030 | 1.46 | 1.29 | 1.27 |

The ratios stay above 1 from 60 days up in every era. It is a weak effect to trade on, though. The sign of the last N days against the sign of the next N days, non-overlapping:

| N days | same sign | 95% CI | n | share of up windows | base if independent |
|---|---|---|---|---|---|
| 7 | 50.9% | 47% to 55% | 711 | 53.8% | 50.3% |
| 14 | 54.6% | 49% to 60% | 355 | 53.7% | 50.3% |
| 30 | 51.5% | 44% to 59% | 165 | 59.6% | 51.9% |
| 60 | 53.7% | 43% to 64% | 82 | 59.0% | 51.6% |
| 90 | 59.3% | 46% to 71% | 54 | 54.5% | 50.4% |
| 180 | 57.7% | 39% to 74% | 26 | 59.3% | 51.7% |

Falls are faster than rises, beyond what volatility and the slow trend give:

| scale | up / down legs | median up: size, days | median down: size, days | down speed / up speed | signflip, 5-95% | trend +-60d, 5-95% |
|---|---|---|---|---|---|---|
| 15m_pct2 | 10,229 / 10,228 | 3.6%, 0.06 | 3.5%, 0.06 | 1.16 | 0.99 to 1.06 | 0.98 to 1.07 |
| 1h_pct4 | 2,663 / 2,662 | 7.4%, 0.29 | 6.7%, 0.21 | 1.30 | 0.96 to 1.11 | 0.97 to 1.12 |
| 4h_pct8 | 692 / 691 | 15.6%, 1.50 | 12.6%, 1.00 | 1.31 | 0.96 to 1.23 | 0.98 to 1.24 |
| 1d_pct16 | 176 / 176 | 32.9%, 6.00 | 25.1%, 5.00 | 1.32 | 0.87 to 1.44 | 0.97 to 1.46 |

### A1. How many swings, how many impulses

Bitstamp from 2013-03-01. "Independent legal" is a greedy count of legal candidates that share no bar. **[verified: `a_census.py`]**

| scale | legs | legs a year | median leg, days | median leg size | legal 5-waves (up / down) | truncated | diagonal cand. | independent legal |
|---|---|---|---|---|---|---|---|---|
| 15m_pct1 | 64,904 | 4,749 | 0.02 | 1.8% | 2,459 (1301 / 1158) | 1513 | 2213 | 2,192 |
| 15m_pct2 | 20,457 | 1,497 | 0.06 | 3.6% | 795 (427 / 368) | 498 | 629 | 700 |
| 15m_pct4 | 6,109 | 447 | 0.18 | 7.2% | 250 (144 / 106) | 134 | 223 | 219 |
| 15m_atr2 | 56,377 | 4,125 | 0.06 | 1.3% | 1,960 (1079 / 881) | 1227 | 2011 | 1,717 |
| 15m_atr4 | 15,305 | 1,120 | 0.25 | 2.6% | 569 (329 / 240) | 402 | 532 | 484 |
| 15m_atr8 | 4,299 | 315 | 0.90 | 4.9% | 190 (125 / 65) | 154 | 119 | 157 |
| 1h_pct2 | 16,621 | 1,216 | 0.08 | 3.7% | 666 (378 / 288) | 401 | 535 | 586 |
| 1h_pct4 | 5,325 | 390 | 0.25 | 7.3% | 219 (133 / 86) | 107 | 192 | 188 |
| 1h_pct8 | 1,597 | 117 | 0.75 | 14.6% | 71 (42 / 29) | 48 | 50 | 58 |
| 1h_atr2 | 14,035 | 1,027 | 0.25 | 2.9% | 638 (351 / 287) | 312 | 518 | 541 |
| 1h_atr4 | 3,733 | 273 | 1.04 | 5.6% | 165 (117 / 48) | 115 | 121 | 137 |
| 1h_atr8 | 1,085 | 79 | 3.54 | 10.7% | 47 (30 / 17) | 40 | 28 | 37 |
| 4h_pct4 | 4,339 | 317 | 0.33 | 7.5% | 189 (120 / 69) | 100 | 150 | 157 |
| 4h_pct8 | 1,383 | 101 | 1.17 | 15.0% | 71 (40 / 31) | 45 | 48 | 59 |
| 4h_pct16 | 422 | 31 | 3.50 | 32.2% | 25 (18 / 7) | 13 | 12 | 20 |
| 4h_atr2 | 3,443 | 252 | 1.00 | 6.4% | 184 (123 / 61) | 79 | 103 | 151 |
| 4h_atr4 | 927 | 68 | 4.17 | 12.3% | 47 (32 / 15) | 36 | 36 | 38 |
| 4h_atr8 | 281 | 21 | 13.00 | 26.1% | 15 (10 / 5) | 15 | 4 | 13 |
| 1d_pct8 | 1,039 | 76 | 2.00 | 16.0% | 50 (27 / 23) | 39 | 34 | 44 |
| 1d_pct16 | 352 | 26 | 5.00 | 33.3% | 21 (16 / 5) | 13 | 14 | 17 |
| 1d_pct32 | 132 | 10 | 14.00 | 63.2% | 6 (6 / 0) | 4 | 5 | 5 |
| 1d_atr2 | 561 | 41 | 7.00 | 19.8% | 34 (24 / 10) | 16 | 19 | 30 |
| 1d_atr4 | 157 | 11 | 25.00 | 43.3% | 5 (5 / 0) | 8 | 4 | 4 |
| 1d_atr8 | 48 | 4 | 70.00 | 108.7% | 3 (2 / 1) | 2 | 0 | 2 |

Which rule kills a six-pivot window first, in the checking order of lesson 14:

| bars | six-pivot windows | R1 W2 beyond start | R2 W3 not beyond W1 | R3 W3 shortest | R4 W4 into W1 | truncated | legal |
|---|---|---|---|---|---|---|---|
| 15m | 167,427 | 47.7% | 20.5% | 7.0% | 18.7% | 2.3% | 3.7% |
| 1h | 42,372 | 47.5% | 19.9% | 7.1% | 18.8% | 2.4% | 4.3% |
| 4h | 10,771 | 47.3% | 19.6% | 7.3% | 18.1% | 2.7% | 4.9% |
| 1d | 2,265 | 47.5% | 19.1% | 6.7% | 17.9% | 3.6% | 5.3% |

Nearly half die at W2, which is close to a coin flip: on a random walk the next leg is shorter than the last one half the time. Only about 1 window in 20-25 survives. Three-leg correctives are far easier: 27-30% of three-leg windows on the ladder scales pass as legal zigzags and 55-57% as zigzag or flat, so "a legal three just ended" says very little. **[verified]**

### The plain verdict: what is trainable at which degree

The edge column is arithmetic: smallest difference from a 50% base visible at 80% power, two-sided 5%, is 1.4 / sqrt(n). The model column is a judgement, using the usual rule of thumb of 10-20 events per fitted parameter and the premise that a deep model needs thousands of independent labelled examples. **[assumed for the model column]**

| Degree | Independent legal 5-waves | Swings | Edge visible on those / on swings | What can be fitted |
|---|---|---|---|---|
| 4-year | 3 lows, 2 gaps (cycles-r1) | none | nothing | Nothing. A written prior, labelled n = 3. |
| Weekly | 23 hindsight cycles; 2-5 legal 5-waves (1d_atr8, 1d_pct32) | 48-132 | 29 points on cycles | One or two hand-set numbers. No fitting. |
| Daily, 1d_pct16 | 17 | 352 | 34 / 7.5 points | Shrunken rates (Beta-binomial). At most 2-3 features, on swings only. |
| 4H, 4h_pct8 | 59 | 1,383 | 18 / 3.8 points | Regularised logistic with a handful of features, on swings. |
| 1H, 1h_pct4 | 188 | 5,325 | 10 / 1.9 points | Logistic or a small gradient-boosted model, on swings. |
| 15m, 15m_pct4 and 15m_pct2 | 219 and 700 | 6,109 and 20,457 | 9.5 and 5.3 / 1.8 and 1.0 points | Gradient boosting on swings is fine. A deep model on wave labels still is not. |

- No degree has thousands of independent labelled wave examples. Only the 1% threshold on 15m reaches 2,192 candidates, and at that scale BTC's rule-legal rate is the same as a random path's.
- For a deep model that learns from unlabelled bars (JEPA and relatives) the count is windows, not swings: 479,214 15m bars are 1,871 non-overlapping windows of 256 bars; 1H 467, 4H 116, 1D 19. Overlapping windows add little independent information. 1-minute bars add detail inside the same market path.
- These counts are one market's single path. Null paths have about the same counts (4h_pct8: 59 against 50; 1h_pct4: 188 against 186), so the supply of candidates is not a BTC property. **[verified]**
- The same arithmetic backs his September note: 30-40 trades can only show an edge of about 22-26 points.

### A2. Are rule-legal impulses more common on BTC than on random paths?

The claim that real markets have "higher elliotticity" is made by EWAVES (see the master plan, unpublished). Here is the same question on BTC. The pools sum six scales of a timeframe. **[verified: `a2_legal_excess.py`, `a_census.py`]**

| pool of six scales | legal / windows | BTC | shuffle | signflip | trend +-30d | trend +-60d | trend +-120d |
|---|---|---|---|---|---|---|---|
| 15m | 6,223 / 167,427 | 3.72% | 3.68% (z 0.6) | 3.79% (z -1.2) | 3.90% (z -3.1) | 3.85% (z -2.3) | 3.82% (z -1.9) |
| 1h | 1,806 / 42,372 | 4.26% | 3.57% (z 6.0) | 3.76% (z 4.1) | 4.11% (z 1.2) | 3.96% (z 2.5) | 3.88% (z 3.1) |
| 4h | 531 / 10,771 | 4.93% | 3.53% (z 5.9) | 3.79% (z 4.6) | 4.56% (z 1.4) | 4.28% (z 2.6) | 4.13% (z 3.1) |
| 1d | 119 / 2,265 | 5.25% | 3.83% (z 2.9) | 4.23% (z 1.8) | 5.53% (z -0.4) | 5.13% (z 0.2) | 4.91% (z 0.5) |

Against volatility-only paths the excess is large at 1H to 1D: up to 1.4 times, z up to 6. Keep the slow trend and most of it goes, and the closer the trend window gets to the structures, the more goes. At 15m BTC has fewer legal impulses than the null. Family-wise over 24 scales:

| null | scales with family-wise p < 0.05 (of 24) |
|---|---|
| shuffle | 15m_atr8 (z 3.1), 1h_atr2 (z 7.9), 1h_atr4 (z 4.0), 4h_pct8 (z 3.4), 4h_atr2 (z 7.0), 4h_atr4 (z 3.4), 1d_atr2 (z 3.6) |
| signflip | 1h_atr2 (z 5.6), 4h_pct8 (z 3.4), 4h_atr2 (z 4.8) |
| trend +-30d | 1h_atr2 (z 3.7) |
| trend +-60d | 1h_atr2 (z 4.7), 4h_atr2 (z 3.4) |
| trend +-120d | 1h_atr2 (z 5.0), 4h_atr2 (z 3.9) |

The two survivors are the 2-ATR scales on 1H and 4H, and they are not stable. The excess sits in one era:

| scale | era | legal / windows | BTC | trend +-60d (5-95%) | p |
|---|---|---|---|---|---|
| 1h_atr2 | 2014-2017 | 206 / 3875 | 5.32% | 3.74% (3.25% to 4.20%) | <0.001 |
| 1h_atr2 | 2018-2021 | 158 / 3963 | 3.99% | 3.91% (3.45% to 4.39%) | 0.411 |
| 1h_atr2 | 2022-2026 | 228 / 5212 | 4.37% | 3.98% (3.55% to 4.40%) | 0.062 |
| 4h_atr2 | 2014-2017 | 66 / 921 | 7.17% | 4.18% (3.18% to 5.22%) | <0.001 |
| 4h_atr2 | 2018-2021 | 47 / 987 | 4.76% | 4.44% (3.42% to 5.54%) | 0.329 |
| 4h_atr2 | 2022-2026 | 54 / 1276 | 4.23% | 4.18% (3.34% to 5.12%) | 0.458 |

| era | scales with BTC above trend +-60d at p < 0.05 (of 24, about 1.2 by chance) | legal / windows, all scales |
|---|---|---|
| 2014-2017 | 6 | 2,641 / 66,778 |
| 2018-2021 | 0 | 2,712 / 68,115 |
| 2022-2026 | 1 | 2,282 / 57,552 |

And it does not appear on the other two venues, which cover 2017 on and 2020 on:

| venue | pool | legal / windows | BTC | signflip | trend +-60d |
|---|---|---|---|---|---|
| binance | 15m | 3,889 / 106,663 | 3.65% | 3.82% (z -2.1) | 3.88% (z -3.0) |
| binance | 1h | 1,080 / 26,602 | 4.06% | 3.84% (z 1.3) | 4.07% (z -0.1) |
| binance | 4h | 287 / 6,709 | 4.28% | 3.79% (z 1.4) | 4.38% (z -0.3) |
| binance | 1d | 63 / 1,355 | 4.65% | 4.04% (z 0.9) | 5.25% (z -0.7) |
| bybit | 15m | 2,525 / 68,290 | 3.70% | 3.79% (z -1.0) | 3.86% (z -1.8) |
| bybit | 1h | 656 / 17,195 | 3.82% | 3.76% (z 0.3) | 3.94% (z -0.7) |
| bybit | 4h | 167 / 4,331 | 3.86% | 3.79% (z 0.2) | 4.38% (z -1.2) |
| bybit | 1d | 37 / 825 | 4.48% | 4.06% (z 0.4) | 5.52% (z -1.0) |

**Reading.** A rule-legal impulse is mostly a run of higher highs and higher lows, and a market with bull and bear regimes makes more of those. What the rule checker measures is trend. Beyond trend there is an excess in Bitstamp 2014-2017 and none since. So I found no stable "elliotticity" in BTC. **[verified as measured]**

### A3. What does a growing count predict?

This is the causal version of the same question. Each stage is known when the previous pivot confirms. `**` marks a family-wise p under 0.05 over the 24 scales. **[verified: `a3_stages.py`]**

| stage | scale | n | BTC (95% CI) | signflip | trend +-60d |
|---|---|---|---|---|---|
| W2 holds above the start of W1 | 15m_pct2 | 20,456 | 51.5% (51% to 52%) | 50.4% ** | 50.4% ** |
| W2 holds above the start of W1 | 1h_pct4 | 5,324 | 51.7% (50% to 53%) | 50.4% ** | 50.4% ** |
| W2 holds above the start of W1 | 4h_pct8 | 1,382 | 51.8% (49% to 54%) | 50.4% | 50.4% |
| W2 holds above the start of W1 | 1d_pct16 | 351 | 52.4% (47% to 58%) | 50.9% | 50.9% |
| then W3 goes beyond W1 | 15m_pct2 | 10,529 | 62.7% (62% to 64%) | 65.4% ** | 65.6% ** |
| then W3 goes beyond W1 | 1h_pct4 | 2,752 | 63.5% (62% to 65%) | 65.3% | 65.6% ** |
| then W3 goes beyond W1 | 4h_pct8 | 716 | 65.5% (62% to 69%) | 65.4% | 66.3% |
| then W3 goes beyond W1 | 1d_pct16 | 184 | 64.7% (58% to 71%) | 65.8% | 66.7% |
| then W4 stays out of W1 | 15m_pct2 | 6,604 | 20.0% (19% to 21%) | 18.1% ** | 18.5% ** |
| then W4 stays out of W1 | 1h_pct4 | 1,747 | 19.1% (17% to 21%) | 17.5% | 18.3% |
| then W4 stays out of W1 | 4h_pct8 | 468 | 26.1% (22% to 30%) | 16.9% ** | 18.9% ** |
| then W4 stays out of W1 | 1d_pct16 | 119 | 29.4% (22% to 38%) | 18.2% ** | 22.1% |
| then W5 goes beyond W3 | 15m_pct2 | 1,318 | 60.3% (58% to 63%) | 64.2% ** | 64.4% ** |
| then W5 goes beyond W3 | 1h_pct4 | 334 | 65.6% (60% to 70%) | 64.8% | 65.3% |
| then W5 goes beyond W3 | 4h_pct8 | 122 | 58.2% (49% to 67%) | 64.2% | 66.0% |
| then W5 goes beyond W3 | 1d_pct16 | 35 | 60.0% (44% to 74%) | 66.7% | 67.9% |
| after a legal 5: A reaches end of W4 | 15m_pct2 | 795 | 40.3% (37% to 44%) | 38.0% | 37.4% |
| after a legal 5: A reaches end of W4 | 1h_pct4 | 219 | 32.0% (26% to 38%) | 37.8% | 36.3% |
| after a legal 5: A reaches end of W4 | 4h_pct8 | 71 | 32.4% (23% to 44%) | 35.3% | 33.3% |
| after a legal 5: A reaches end of W4 | 1d_pct16 | 21 | 23.8% (11% to 45%) | 33.3% | 28.0% |

Scales (of 24) with family-wise p under 0.05, BTC above / below the null:

| stage | signflip | trend +-30d | trend +-60d | trend +-120d |
|---|---|---|---|---|
| W2 holds above the start of W1 | 15 / 0 | 15 / 0 | 14 / 0 | 15 / 0 |
| then W3 goes beyond W1 | 0 / 11 | 0 / 14 | 0 / 13 | 0 / 12 |
| then W4 stays out of W1 | 14 / 0 | 3 / 0 | 7 / 0 | 11 / 0 |
| then W5 goes beyond W3 | 0 / 2 | 0 / 6 | 0 / 3 | 0 / 3 |
| after a legal 5: A reaches end of W4 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

- **W2 holds** slightly more than chance, and **W3 goes beyond W1** slightly less: both are the step at 1.0 of section B1 (legs stop short of the last pivot). Note the direction: a W3 fails to break the end of W1 more often than on a random path. The rule "W3 beyond W1" is a filter, not a tendency.
- **W4 stays out of W1** clearly more often at 4H and up, but mostly in 2014-2017, and the excess shrinks as the null keeps more of the trend (14 scales against signflip, 3 against trend +-30d):

| scale | era | n | BTC | trend +-60d (5-95%) | p two-sided |
|---|---|---|---|---|---|
| 4h_pct8 | 2014-2017 | 138 | 30.4% | 19.1% (14% to 24%) | 0.007 |
| 4h_pct8 | 2018-2021 | 160 | 23.8% | 19.5% (15% to 25%) | 0.246 |
| 4h_pct8 | 2022-2026 | 69 | 20.3% | 21.5% (14% to 30%) | 0.817 |
| 1d_pct16 | 2014-2017 | 32 | 28.1% | 21.6% (12% to 33%) | 0.379 |
| 1d_pct16 | 2018-2021 | 36 | 30.6% | 23.1% (13% to 33%) | 0.226 |
| 1d_pct16 | 2022-2026 | 22 | 27.3% | 26.3% (12% to 44%) | 0.937 |
| 4h_atr2 | 2014-2017 | 307 | 30.9% | 19.8% (16% to 23%) | 0.007 |
| 4h_atr2 | 2018-2021 | 326 | 20.2% | 20.5% (17% to 24%) | 0.884 |
| 4h_atr2 | 2022-2026 | 412 | 19.7% | 19.7% (17% to 23%) | 0.950 |

- **W5 goes beyond W3** no more often than chance, and less at fine scales. **After a legal five**, the next leg is no different at any scale. These two are the stages a trader acts on, and the count gives no edge there. **[verified]**

Most 1-2-3s never become a five, on BTC and on random paths: only 19-29% of legal 1-2-3s survive W4 (third block of the table above).

### A4. How ambiguous is a count?

A person is not tied to one threshold. So for each pivot of a fine zigzag taken as the end of wave 5, I enumerated every choice of p0 to p4 where each wave's ends are the real extremes of its stretch and the wave passes the rules, looking back 60 fine pivots. This is free degree, and it is an upper bound because sub-waves are not checked. **[verified: `a5_ambiguity.py`, enumeration matches brute force in `check_tools.py`]**

| fine scale | pivots | share with a legal count | shuffle | trend +-60d | median counts when any | shuffle | trend +-60d | distinct origins when any | trend +-60d |
|---|---|---|---|---|---|---|---|---|---|
| 15m_pct2 | 20,398 | 16.4% | 16.7% | 17.4% | 12 | 9 | 11 | 5.2 | 5.0 |
| 1h_pct2 | 16,562 | 16.5% | 16.4% | 17.4% | 12 | 9 | 12 | 5.3 | 5.1 |
| 4h_pct4 | 4,280 | 17.5% | 16.3% | 18.0% | 13 | 9 | 15 | 5.5 | 5.7 |
| 1d_pct8 | 980 | 17.1% | 17.0% | 19.7% | 16 | 12 | 25 | 5.6 | 6.6 |

About 1 pivot in 6 can end a legal 5-wave at all, and where one can, there are typically a dozen legal ways to draw it, from about 5 different origins. All of that is about the same on random paths (BTC's share sits slightly below trend +-60d). This is why "the true count" is not a label: the rules do not pick one. **[verified]**

### A5. "Only 3s and 5s exist"

This is the core claim of the theory, and the rulebook calls skipping the sub-wave check the number one beginner error. Inside each swing of a coarse zigzag, how many swings does a zigzag at half the threshold see? The count can only be odd. Share of coarse legs, BTC / trend +-60d. **[verified: `a6_subwaves.py`]**

| coarse | fine | 1 (BTC / null) | 3 | 5 | 7 | 9 or more |
|---|---|---|---|---|---|---|
| 15m_pct4 | 15m_pct2 | 39.1% / 42.1% | 30.3% / 28.1% | 14.7% / 13.5% | 7.5% / 7.3% | 8.3% / 9.0% |
| 1h_pct8 | 1h_pct4 | 40.0% / 43.0% | 29.4% / 28.2% | 14.7% / 13.1% | 7.5% / 7.1% | 8.5% / 8.7% |
| 4h_pct16 | 4h_pct8 | 37.0% / 43.2% | 33.2% / 28.3% | 14.0% / 12.8% | 7.1% / 6.9% | 8.8% / 8.7% |
| 1d_pct16 | 1d_pct8 | 40.6% / 46.3% | 32.1% / 29.0% | 13.1% / 12.0% | 7.7% / 6.0% | 6.5% / 6.5% |

BTC has somewhat fewer 1s and somewhat more 3s and 5s than the null, by 1 to 6 points. That is a real difference of shape (16 of 72 cells at p under 0.05, 3.6 by chance), but it is far from "only 3s and 5s": 7s and larger are as common as on random paths. Inside rule-legal impulses:

| coarse | fine | legal impulses | W3 subdivides into 5 (BTC vs null) | W2 and W4 in 1 or 3 | full 5-3-5-3-5 form |
|---|---|---|---|---|---|
| 15m_pct4 | 15m_pct2 | 250 | 21.2% vs 17.9% (p 0.153) | 78.8% vs 75.6% (p 0.213) | 2.4% vs 3.4% (p 0.339) |
| 1h_pct8 | 1h_pct4 | 71 | 22.5% vs 17.9% (p 0.379) | 84.5% vs 75.0% (p 0.080) | 1.4% vs 3.1% (p 0.266) |
| 4h_pct16 | 4h_pct8 | 25 | 24.0% vs 17.4% (p 0.432) | 76.0% vs 76.9% (p 0.910) | 16.0% vs 3.5% (p 0.027) |
| 1d_pct16 | 1d_pct8 | 21 | 4.8% vs 19.0% (p 0.086) | 71.4% vs 82.4% (p 0.312) | 4.8% vs 3.9% (p 0.850) |

The full 5-3-5-3-5 form is rare on BTC and on random paths alike. The only hit is 4 of 25 on 4h_pct16, uncorrected. At this resolution the sub-wave check does not separate BTC from the null. A person's reading of sub-waves may do better; that is **[unknown]** until his labelled counts exist.

## B. "Every asset has its own Fibonacci"

### B1. All swings: is any Fibonacci level over-represented?

Ratios on all consecutive zigzag legs: retracement |leg2| / |leg1|, split also into a down leg retracing an up leg and the reverse; extension |leg3| / |leg1| where leg2 was shorter than leg1. Levels 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.272, 1.618, 2, 2.236, 2.618. Log price everywhere, linear price from 1H up. That is 3,696 tests of local excess. **[verified: `b1_fib_unconditional.py`, 1,000 paths per null]**

**The density on a random walk.** The legs of a zigzag on a driftless walk follow threshold x (1 + Exp(1)), so the ratio of two legs has a smooth tent shape on a log axis, with its peak at 1 and no feature at any Fibonacci level. Measured on a simulated walk in `check_tools.py`. That is the shape to compare with; BTC starts very close to it.

Share of leg pairs by ratio. Figure: `/opt/data/cache/scratch/elliott_research_r1/emp/fig_b1_density.png`.

`1h_pct4`, 5,324 pairs:

| ratio | BTC | random-walk law | signflip (5-95%) | trend +-60d |
|---|---|---|---|---|
| 0.000 to 0.236 | 0.7% | 0.7% | 0.7% (0.6% to 0.9%) | 0.8% |
| 0.236 to 0.382 | 5.7% | 4.7% | 4.9% (4.4% to 5.3%) | 5.0% |
| 0.382 to 0.500 | 6.3% | 6.8% | 6.4% (5.9% to 6.9%) | 6.5% |
| 0.500 to 0.618 | 7.9% | 8.3% | 7.8% (7.3% to 8.4%) | 7.8% |
| 0.618 to 0.786 | 14.4% | 12.9% | 13.7% (12.9% to 14.4%) | 13.6% |
| 0.786 to 1.000 | 17.6% | 16.5% | 17.3% (16.5% to 18.2%) | 17.1% |
| 1.000 to 1.272 | 13.7% | 16.5% | 16.6% (15.8% to 17.4%) | 16.5% |
| 1.272 to 1.618 | 13.0% | 12.9% | 13.1% (12.5% to 13.8%) | 13.0% |
| 1.618 to 2.000 | 8.2% | 8.3% | 7.6% (7.0% to 8.1%) | 7.6% |
| 2.000 to 2.618 | 6.1% | 6.8% | 6.1% (5.6% to 6.6%) | 6.1% |
| 2.618 to 4.236 | 5.5% | 4.7% | 4.9% (4.5% to 5.3%) | 5.0% |
| 4.236 to up | 1.0% | 0.8% | 0.9% (0.7% to 1.1%) | 1.0% |

`4h_pct8`, 1,382 pairs:

| ratio | BTC | random-walk law | signflip (5-95%) | trend +-60d |
|---|---|---|---|---|
| 0.000 to 0.236 | 0.9% | 0.7% | 0.7% (0.4% to 1.1%) | 1.0% |
| 0.236 to 0.382 | 6.4% | 4.7% | 4.7% (3.8% to 5.5%) | 5.1% |
| 0.382 to 0.500 | 8.2% | 6.8% | 6.3% (5.3% to 7.3%) | 6.4% |
| 0.500 to 0.618 | 7.9% | 8.3% | 7.9% (6.9% to 9.1%) | 7.9% |
| 0.618 to 0.786 | 13.3% | 12.9% | 13.6% (12.3% to 15.0%) | 13.3% |
| 0.786 to 1.000 | 15.8% | 16.5% | 17.5% (15.8% to 19.1%) | 16.9% |
| 1.000 to 1.272 | 11.9% | 16.5% | 16.9% (15.2% to 18.4%) | 16.5% |
| 1.272 to 1.618 | 13.9% | 12.9% | 13.0% (11.6% to 14.5%) | 12.7% |
| 1.618 to 2.000 | 7.1% | 8.3% | 7.7% (6.7% to 8.9%) | 7.7% |
| 2.000 to 2.618 | 6.2% | 6.8% | 5.9% (5.0% to 6.8%) | 6.0% |
| 2.618 to 4.236 | 7.0% | 4.7% | 4.8% (3.9% to 5.7%) | 5.2% |
| 4.236 to up | 1.4% | 0.8% | 0.8% (0.5% to 1.2%) | 1.1% |

Against any null, BTC has less mass just above 1 and a bit more further out. 4H also has more shallow retracements (0.236-0.5: 14.6% against 11%). There is no step at 0.5, 0.618 or 0.786 at either scale.

**The omnibus test.** How many of the 3,696 tests read high, against the same count on null paths:

| null | paths | tests at z >= 1.645: BTC | same count on null paths, median (5-95%) | p | family-wise hits | of which at level 1.0 on 15m |
|---|---|---|---|---|---|---|
| shuffle | 1000 | 311 | 232 (198 to 275) | <0.001 | 13 | 11 |
| block | 1000 | 232 | 234 (205 to 265) | 0.536 | 5 | 4 |
| signflip | 1000 | 264 | 235 (202 to 270) | 0.088 | 10 | 9 |
| trendflip | 1000 | 252 | 235 (202 to 272) | 0.222 | 10 | 9 |

Against the nulls that keep volatility, the count is ordinary. It beats only the shuffle, which has no volatility clustering. All but one of the family-wise hits on block, signflip and trend are at level 1.0 on 15m bars (the other is 0.236 on `1d_pct32`, a handful of swings). Benjamini-Hochberg against trend +-60d finds 63 tests, 34 of them at 1.0; the other 29 are in line with placebos, where null paths are treated as BTC (median 21, 95th percentile 35).

**The level summary.** The mean z of one level across all 24 scales has the most power for a small effect present everywhere. Retracements, log price, +-4% band:

| level | BTC mean excess | signflip mean excess | mean z, signflip (p) | mean z, trend +-60d (p) |
|---|---|---|---|---|
| 0.236 | 0.892 | 1.060 | -0.28 (0.198) | -0.24 (0.338) |
| 0.382 | 0.958 | 1.030 | -0.11 (0.669) | -0.13 (0.619) |
| 0.5 | 0.992 | 1.009 | -0.14 (0.557) | -0.18 (0.474) |
| 0.618 | 1.028 | 1.006 | 0.07 (0.771) | 0.05 (0.837) |
| 0.786 | 0.984 | 1.009 | 0.58 (0.030) | 0.53 (0.046) |
| 1.0 | 1.045 | 1.059 | 1.12 (0.002) | 1.14 (0.002) |
| 1.272 | 1.029 | 1.017 | -0.19 (0.494) | -0.20 (0.476) |
| 1.618 | 0.967 | 1.008 | -0.27 (0.284) | -0.33 (0.208) |
| 2.0 | 1.054 | 1.014 | -0.21 (0.376) | -0.21 (0.400) |
| 2.236 | 0.934 | 1.016 | -0.13 (0.619) | -0.12 (0.645) |
| 2.618 | 1.147 | 1.014 | 0.23 (0.344) | 0.21 (0.428) |

Extensions, log price, +-4% band:

| level | BTC mean excess | signflip mean excess | mean z, signflip (p) | mean z, trend +-60d (p) |
|---|---|---|---|---|
| 0.236 | 1.157 | 1.013 | 0.17 (0.412) | 0.12 (0.563) |
| 0.382 | 0.992 | 1.036 | -0.26 (0.238) | -0.26 (0.244) |
| 0.5 | 1.182 | 1.045 | 0.39 (0.112) | 0.40 (0.098) |
| 0.618 | 1.013 | 1.037 | -0.05 (0.851) | -0.03 (0.919) |
| 0.786 | 0.853 | 1.037 | -0.35 (0.162) | -0.32 (0.196) |
| 1.0 | 0.947 | 1.034 | -0.38 (0.126) | -0.35 (0.152) |
| 1.272 | 1.079 | 1.023 | 0.00 (0.971) | 0.01 (0.951) |
| 1.618 | 0.958 | 1.032 | -0.35 (0.120) | -0.38 (0.108) |
| 2.0 | 1.257 | 1.038 | 0.27 (0.248) | 0.28 (0.258) |
| 2.236 | 1.045 | 1.034 | -0.07 (0.817) | -0.09 (0.723) |
| 2.618 | 1.340 | 1.046 | 0.26 (0.272) | 0.29 (0.222) |

- 0.618 reads 1.03 against a null of 1.01, z 0.05. 0.382 and 0.5 read below the null. **[verified]**
- Over all 176 combinations of level, ratio type, price scale and width, 12 reach q under 0.05 against trend +-60d: 6 at 1.0, 4 deficits (1.272, 1.618 and 2.618 reading low), and 2 on linear extensions (1.618 at +-4% and 0.236 at +-1.5%). The 1.618 one is the only one that matches a rulebook pull. See "the one Fibonacci lead" below. **[verified]**

What size of bump could this have seen? The narrower the scale, the better:

| scale | band half-width | sd of the excess on null paths | local bump needed for z = 2.5 |
|---|---|---|---|
| 15m_pct2 | 0.015 | 0.07 | +17% |
| 15m_pct2 | 0.04 | 0.04 | +11% |
| 1h_pct4 | 0.015 | 0.14 | +35% |
| 1h_pct4 | 0.04 | 0.08 | +21% |
| 4h_pct8 | 0.015 | 0.28 | +71% |
| 4h_pct8 | 0.04 | 0.16 | +40% |
| 1d_pct16 | 0.015 | 0.53 | +133% |
| 1d_pct16 | 0.04 | 0.31 | +78% |

So a Fibonacci bump of +20% or more would have been visible on 1H, and of +40% on 4H. Something smaller and specific to high degree cannot be excluded. **[verified as arithmetic on the null spread]**

**Other venues.** The same level summary, retracements, +-4% band, against trend +-60d, 300 paths. No test reaches q under 0.05 on either venue in any direction. 0.618 on Binance reads high at p 0.007, which Bybit and Bitstamp do not repeat, so I read it as noise. 1.0 reads low on both: see the spike below. **[verified: `b1c_venues.py`]**

| level | Bybit perp, mean z (p) | Binance spot, mean z (p) |
|---|---|---|
| 0.236 | -0.03 (0.937) | -0.35 (0.126) |
| 0.382 | -0.16 (0.565) | -0.05 (0.890) |
| 0.5 | 0.00 (0.904) | 0.03 (0.944) |
| 0.618 | 0.37 (0.193) | 0.90 (0.007) |
| 0.786 | -0.11 (0.651) | 0.21 (0.439) |
| 1.0 | -2.23 (0.007) | -1.77 (0.007) |
| 1.272 | -0.14 (0.598) | 0.31 (0.233) |
| 1.618 | -0.60 (0.020) | -0.42 (0.093) |
| 2.0 | -0.51 (0.033) | -0.20 (0.392) |
| 2.236 | 0.24 (0.392) | -0.34 (0.153) |
| 2.618 | 0.15 (0.505) | 0.32 (0.193) |

### The one Fibonacci lead: linear extensions at 1.618

It was found among hundreds of tests, and its b1 p value is too kind because those null paths are independent across timeframes. So two checks that could kill it. **[verified: `b1d_scan.py`, 300 paths]**

**A dense scan.** The same statistic on a grid of levels from 0.2 to 5 in 1% steps, 18 scales on 1H, 4H and 1D, with one null path being one market at all three timeframes. The highest peaks of each ratio type against trend +-60d:

| ratio | price | rank | level | standardised z | family-wise p for the scan |
|---|---|---|---|---|---|
| ret | log | 1 | 0.961 | 3.90 | 0.080 |
| ret | log | 2 | 1.186 | 2.57 | 0.797 |
| ret | log | 3 | 0.651 | 2.48 | 0.877 |
| ret | lin | 1 | 0.961 | 4.25 | 0.040 |
| ret | lin | 2 | 3.224 | 2.99 | 0.502 |
| ret | lin | 3 | 1.198 | 2.88 | 0.595 |
| ext | log | 1 | 2.056 | 4.64 | 0.020 |
| ext | log | 2 | 0.320 | 2.26 | 0.953 |
| ext | log | 3 | 0.887 | 1.63 | 1.000 |
| ext | lin | 1 | 1.617 | 3.55 | 0.183 |
| ext | lin | 2 | 0.507 | 2.89 | 0.568 |
| ext | lin | 3 | 4.575 | 2.63 | 0.787 |

- The top linear extension is at 1.617. Landing within 0.1% of 1.618 by chance is unlikely, but the family-wise p for the scan is 0.18 (0.34 against signflip): levels with no name reach this height on null paths.
- The top retracement peak is at 0.96, the step of the next section, not a Fibonacci level. It is the only retracement peak that clears the scan (p 0.04 in linear price).
- The top log extension is at 2.06 (p 0.02), which is in no NewWave pull list and has no linear twin. I have no explanation and would not use it.

**Replication.** Extension, linear price, 1.618, +-4%, counts over the same 18 scales:

| venue | period | in band | shoulders | excess | trend +-60d (5-95%) | p high |
|---|---|---|---|---|---|---|
| bitstamp | all | 786 | 2074 | 1.14 | 1.00 (0.91 to 1.10) | 0.020 |
| bitstamp | 2013-2017 | 344 | 959 | 1.08 | 1.01 (0.85 to 1.16) | 0.223 |
| bitstamp | 2018-2021 | 244 | 604 | 1.21 | 1.02 (0.84 to 1.20) | 0.050 |
| bitstamp | 2022-2026 | 198 | 511 | 1.16 | 0.99 (0.82 to 1.18) | 0.076 |
| binance | all | 433 | 1271 | 1.02 | 0.99 (0.87 to 1.13) | 0.342 |
| binance | 2013-2017 | 34 | 128 | 0.80 | 1.00 (0.65 to 1.49) | 0.821 |
| binance | 2018-2021 | 221 | 620 | 1.07 | 0.99 (0.81 to 1.19) | 0.269 |
| binance | 2022-2026 | 178 | 523 | 1.02 | 0.99 (0.81 to 1.19) | 0.412 |
| bybit | all | 294 | 774 | 1.14 | 0.99 (0.83 to 1.14) | 0.056 |
| bybit | 2020-2021 | 90 | 245 | 1.10 | 1.01 (0.75 to 1.30) | 0.286 |
| bybit | 2022-2026 | 204 | 529 | 1.16 | 0.97 (0.80 to 1.21) | 0.096 |

It sits near the top of the null's range in the last two eras on Bitstamp and in 2022-2026 on Bybit, and is absent on Binance. In size: about 97 extra legs among 29,103 extension pairs, so about 3 in 1,000 (arithmetic on the Bitstamp row). If it is real it may be traders acting on 1.618 on a linear chart, which would explain why log price shows nothing. That is **[unknown]**. Next test: the coming year of data, on a frozen statistic. Until then it gets no weight.

### The real fingerprint: a step at 1.0

The density tables and the figure show it at once. It is a hypothesis found by looking, so it has to survive what could still refute it: each era alone, and the other venues. **[verified: `b1b_barrier.py`, 300 paths]**

Asymmetry = share of ratios in 0.786-1.0 minus share in 1.0-1.272. The law on a random walk is symmetric, and trend +-60d paths average +0.2 points. Mean over the scales of each timeframe in points, and in brackets how many scales are above the null's 95th percentile:

| bars | Bitstamp 2014-17 | 2018-21 | 2022-26 | Binance 2018-21 | 2022-26 | Bybit 2020-21 | 2022-26 |
|---|---|---|---|---|---|---|---|
| 15m | +2.4 (5/6) | +2.6 (5/6) | +3.2 (5/6) | +3.2 (6/6) | +3.4 (6/6) | +2.2 (3/6) | +3.7 (6/6) |
| 1h | +4.0 (5/6) | +3.0 (3/6) | +2.9 (4/6) | +3.1 (3/6) | +2.7 (4/6) | +0.9 (1/6) | +3.0 (4/6) |
| 4h | +5.7 (4/6) | +3.0 (2/6) | +3.5 (3/6) | +4.1 (1/6) | +2.4 (3/6) | -5.3 (0/6) | +2.2 (2/6) |
| 1d | +5.3 (2/5) | +6.2 (1/5) | -0.1 (0/4) | +4.7 (1/5) | -1.4 (0/4) | -7.4 (0/3) | -2.6 (0/4) |

- It holds in every era and on every venue at 15m. It holds at 1H except Bybit 2020-2021, and on most periods at 4H, where the count of swings gets thin and Bybit 2020-2021 goes the other way (under two years of data). 1D has too few pairs to say.
- Fine structure, share of pairs by ln(r), BTC / null. The robust part is the hole above 1, from 1.5% to 20% past the pivot, at all three scales. The extra mass below 1 is small and shows at 10-40% short of the pivot at 15m and 1H:

| ln(r) | 15m_pct2: BTC / null | 1h_pct4 | 4h_pct8 |
|---|---|---|---|
| -0.400 to -0.200 | 12.15% / 11.66% | 12.72% / 11.79% | 10.93% / 11.64% |
| -0.200 to -0.100 | 7.22% / 6.66% | 6.44% / 6.72% | 5.93% / 6.65% |
| -0.100 to -0.050 | 3.29% / 3.48% | 3.57% / 3.50% | 3.18% / 3.51% |
| -0.050 to -0.030 | 1.24% / 1.44% | 1.43% / 1.44% | 1.01% / 1.40% |
| -0.030 to -0.015 | 0.94% / 1.09% | 1.01% / 1.07% | 1.23% / 1.06% |
| -0.015 to +0.000 | 1.32% / 1.22% | 1.01% / 1.09% | 0.94% / 1.11% |
| +0.000 to +0.015 | 1.90% / 1.23% | 1.28% / 1.17% | 1.16% / 1.17% |
| +0.015 to +0.030 | 0.78% / 1.11% | 0.90% / 1.06% | 0.51% / 1.11% |
| +0.030 to +0.050 | 0.98% / 1.39% | 1.09% / 1.41% | 1.23% / 1.44% |
| +0.050 to +0.100 | 2.79% / 3.44% | 2.69% / 3.47% | 2.24% / 3.48% |
| +0.100 to +0.200 | 5.62% / 6.48% | 5.80% / 6.49% | 4.49% / 6.35% |
| +0.200 to +0.400 | 10.97% / 11.22% | 10.42% / 11.32% | 11.79% / 11.29% |

**The exact spike at 1.0 is different and does not survive.** It is strongest in old Bitstamp, where thin markets gave exact price ties, fades through 2018-2021, and is below the null since 2022 on all three venues. So the "100% level" that shows up in the level summary, like the local significance Kempen (2016) reports for the 100% retracement on equities (via the master plan), is here a market-structure effect of an old era:

| venue | period | pairs | excess at exactly 1.0, +-1.5% | trend +-60d (5-95%) | exact price ties, whole venue history |
|---|---|---|---|---|---|
| bitstamp | 2014-2017 | 6,561 | 2.07 | 1.10 (0.95 to 1.25) | 0.91% |
| bitstamp | 2018-2021 | 6,402 | 1.19 | 1.05 (0.89 to 1.22) | 0.91% |
| bitstamp | 2022-2026 | 2,956 | 0.75 | 1.02 (0.80 to 1.26) | 0.91% |
| binance | 2018-2021 | 6,708 | 1.24 | 1.03 (0.90 to 1.19) | 0.36% |
| binance | 2022-2026 | 3,118 | 0.64 | 1.02 (0.82 to 1.27) | 0.36% |
| bybit | 2020-2021 | 2,574 | 0.92 | 1.00 (0.75 to 1.28) | 0.07% |
| bybit | 2022-2026 | 3,347 | 0.66 | 1.04 (0.81 to 1.23) | 0.07% |

**Does a break of the old pivot run on?** If a leg passes the previous pivot, how much further does it go, in thresholds? On a memoryless walk the overshoot is Exp(1), with mean 1 and 22% under 0.25. Buying the moment an old swing extreme breaks and leaving when the zigzag reverses earns overshoot minus 1 threshold, before costs and gaps.

| venue | period | scale | breaks | mean overshoot, thresholds | trend +-60d (5-95%) | share under 0.25 | null |
|---|---|---|---|---|---|---|---|
| bitstamp | 2014-2017 | 15m_pct2 | 3,129 | 1.08 | 1.04 (1.01 to 1.06) | 18.6% | 21.6% |
| bitstamp | 2014-2017 | 1h_pct4 | 784 | 1.14 | 1.03 (0.98 to 1.08) | 18.2% | 21.4% |
| bitstamp | 2014-2017 | 4h_pct8 | 180 | 1.37 | 1.04 (0.94 to 1.15) | 13.3% | 21.0% |
| bitstamp | 2018-2021 | 15m_pct2 | 3,161 | 1.09 | 1.06 (1.04 to 1.09) | 15.4% | 21.1% |
| bitstamp | 2018-2021 | 1h_pct4 | 816 | 1.07 | 1.06 (1.01 to 1.13) | 15.6% | 20.8% |
| bitstamp | 2018-2021 | 4h_pct8 | 233 | 1.08 | 1.06 (0.96 to 1.17) | 12.4% | 21.2% |
| bitstamp | 2022-2026 | 15m_pct2 | 1,440 | 1.09 | 1.03 (0.99 to 1.08) | 17.5% | 21.6% |
| bitstamp | 2022-2026 | 1h_pct4 | 390 | 1.06 | 1.05 (0.97 to 1.13) | 17.4% | 21.6% |
| bitstamp | 2022-2026 | 4h_pct8 | 110 | 1.01 | 1.09 (0.93 to 1.26) | 18.2% | 21.5% |
| bybit | 2022-2026 | 15m_pct2 | 1,626 | 1.04 | 1.00 (0.96 to 1.04) | 17.3% | 22.2% |
| bybit | 2022-2026 | 1h_pct4 | 415 | 1.04 | 1.01 (0.94 to 1.10) | 18.1% | 21.9% |
| bybit | 2022-2026 | 4h_pct8 | 113 | 1.00 | 1.06 (0.88 to 1.26) | 19.5% | 22.3% |

- It rarely stops within a quarter threshold of the break: 12-20% against 21-22%. That holds in every era and on Bybit.
- But the mean overshoot is above the null only in 2014-2017. From 2018 on it sits within the null's range or at its top edge (15m), and across all 24 scales it is above the null's 95th percentile about as often as below its 5th. The missing small overshoots do not add up to a bigger average, so this is not a trading edge as it stands. **[verified]**

**Reading.** BTC's swings have one robust feature that a no-memory path lacks: the previous swing extreme acts like a barrier, in that price more often stops short of it, and seldom stops just past it. That is an old idea from market structure, and it is not a Fibonacci property. A model can use the distance to the last same-scale pivot as a feature. It also explains two of the stage results in A3 (W2 holds more, W3 breaks W1 less), and it fits the longer W3s and W5s in B2, each of which has to pass a prior pivot.

### Is there a stable fingerprint, and can it be learned?

Shape of the whole density against each null, and a learnability test: a histogram on 12 bands, fitted on BTC up to 2021, against the null's pool, both scored on BTC 2022-2026. Null paths run the same way give the distribution of that gain. 48 histograms: 24 scales x retracement, extension. **[verified: `b1_fib_unconditional.py`]**

| null | histograms | shape differs, q < 0.05 | 12-band fit up to 2021 beats the null on 2022-2026, q < 0.05 | gain above zero |
|---|---|---|---|---|
| shuffle | 48 | 41 | 12 | 18 |
| block | 48 | 32 | 12 | 18 |
| signflip | 48 | 34 | 7 | 9 |
| trendflip | 48 | 31 | 7 | 12 |

The shape differs on most scales, and that is the step and the wider tails. But a fit up to 2021 beats the null on 2022-2026 at only 7 of 48, and the gains are small: typically 1-10 millinats per ratio, against about 2.25 nats of entropy in the 12 bands. So what the past teaches about the next ratio is worth well under 1% of what is unknown about it. **[verified]**

### B2. Inside rule-legal impulses

Prechter's objection to the all-swings test is that Fibonacci relations hold only between specific wave pairs (master plan, section 3). So here are the same ratios inside candidates that passed the rules, with the same detector on null paths, because the rules themselves shape these ratios: W2 under 1, W3 above W2, W4 kept shallow by the W1 rule. **[verified: `b2_fib_impulse.py`, 1,000 paths; 500 at 15m]**

Hit rates of the windows the rulebook names (sections 1, 4, 7). "Near" is +-5%. Ladder n = 1,106; 15m 6,223, 1H 1,806, 4H 531, 1D 119 (six scales each). Figure: `/opt/data/cache/scratch/elliott_research_r1/emp/fig_b2_impulse.png`.

| rulebook claim | BTC, ladder | trend +-60d (5-95%) | p | 15m BTC / null | 1h | 4h | 1d |
|---|---|---|---|---|---|---|---|
| W2 ends at 0.5-0.618 | 17.6% | 17.5% (16% to 19%) | 0.902 | 18.1% / 17.4% | 17.2% / 17.5% | 12.8% / 17.8% | 17.6% / 17.2% |
| W2 near 0.382 | 3.9% | 4.0% (3% to 5%) | 0.830 | 3.4% / 4.0% | 4.0% / 4.1% | 4.9% / 4.2% | 1.7% / 4.7% |
| W2 near 0.786 | 12.7% | 11.6% (10% to 13%) | 0.208 | 12.8% / 11.6% | 13.2% / 11.3% | 12.6% / 10.9% | 12.6% / 9.7% |
| W2 shallower than 0.382 | 10.1% | 13.0% (11% to 15%) | 0.004 | 9.8% / 13.0% | 11.2% / 13.6% | 15.6% / 15.0% | 15.1% / 18.1% |
| W2 deeper than 0.618 | 58.1% | 54.6% (52% to 57%) | 0.020 | 58.7% / 54.8% | 56.8% / 53.8% | 58.0% / 51.9% | 49.6% / 48.0% |
| W4 ends at 0.236-0.382 of W3 | 41.9% | 41.3% (39% to 44%) | 0.703 | 39.3% / 40.6% | 41.9% / 40.5% | 45.2% / 40.9% | 50.4% / 40.7% |
| W4 under 0.5 of W3 | 87.8% | 86.5% (85% to 88%) | 0.148 | 83.0% / 84.9% | 84.6% / 85.1% | 87.4% / 85.5% | 89.1% / 86.3% |
| W3 near 1.618, pull 0-1-2 | 9.2% | 9.4% (8% to 11%) | 0.866 | 9.2% / 9.0% | 9.3% / 8.9% | 9.8% / 8.9% | 7.6% / 7.8% |
| W3 near 2.618 | 5.6% | 5.4% (4% to 6%) | 0.762 | 6.1% / 5.4% | 5.6% / 5.2% | 6.2% / 5.0% | 8.4% / 4.9% |
| W3 beyond 2.618 | 14.7% | 14.7% (13% to 17%) | 0.998 | 18.8% / 15.9% | 19.4% / 15.8% | 16.8% / 15.9% | 19.3% / 18.2% |
| W5 near 2.236, pull 0-1-2 | 9.3% | 8.6% (7% to 10%) | 0.427 | 8.0% / 8.3% | 7.5% / 8.3% | 8.9% / 8.2% | 8.4% / 7.4% |
| W5 near 3.236 | 5.8% | 5.8% (5% to 7%) | 0.990 | 6.1% / 5.7% | 6.1% / 5.7% | 7.3% / 5.5% | 3.4% / 5.6% |
| W5 near 1.0, pull 0-1-4 | 6.0% | 6.6% (5% to 8%) | 0.427 | 5.6% / 6.2% | 5.5% / 6.2% | 6.6% / 6.1% | 5.9% / 5.5% |
| W5 near 0.618 | 4.3% | 4.7% (4% to 6%) | 0.571 | 3.9% / 4.6% | 4.2% / 4.6% | 4.1% / 4.6% | 2.5% / 4.2% |

**The honest answer to "own Fibonacci".** Every window the rulebook names is hit at about the rate of a random path once the rules are applied. W4 at 0.236-0.382 is a good description (about 4 in 10 candidates), but it is a good description of random paths too, so a W4 landing there is no evidence for the count. W2 at 0.5-0.618 is about 1 in 6, and the most common W2 is deeper than that (58% beyond 0.618, peak near 0.9). **[verified]**

Local excess at the rulebook's levels against shoulders (band +-5%): of 18 level tests on the ladder, the only one above the null's range is W5 = 1.618 of pull 0-1-4 (1.32, p 0.04; on 1H pool 1.42, p 0.006), which fits the longer W5s below and is uncorrected. W3 at 1.618 reads 0.97 and W2 at 0.618 reads 0.97, null about 1.0-1.07. Full list in `b2_excess.csv`. **[verified]**

**Where BTC does differ from the null, and how that holds up:**

- **W2 runs deeper:** under 0.382 is 10.1% against 13.0% (p 0.004), over 0.618 is 58.1% against 54.6% (p 0.02). The under-0.382 gap comes mostly from 2014-2017 (table below).
- **W3 extends more,** at 15m and 1H: beyond 2.618 is 18.8% and 19.4% against 15.9% and 15.8% (p 0.004 and 0.002), both directions, and in 2018-2021 and 2022-2026 alike. Not at 4H (16.8% against 15.9%).
- **W4 at 0.236-0.382 leans the rulebook's way only on up-impulses at high degree:** 1H 44.1% against 40.9% (p 0.04), 4H 49.0% against 41.1% (p 0.01), 1D 65.0% against 41.0% (p 0.002, n 80), and it does not show in linear price (all directions: 4H 42.4% against 40.1%, 1D 37.8% against 36.3%). Down-impulses go the other way (1D 20.5% against 40.0%, n 39). Uncorrected and thin at 4H and up: a lead, and the only one in the rulebook's favour besides alternation.
- **W2 at 0.5-0.618 on 4H is less common than chance:** 12.8% against 17.8% (p 0.006). Not at other scales.

Which wave is longest, and the claim "0.382 in a strong uptrend" (W2 under 0.45 after the 90 days before p0 rose over 30%, up-impulses):

| pool | n | W1 longest, BTC / null | W3 longest | W5 longest | W2 under .45 after a strong uptrend, BTC / null | W2 under .45 otherwise |
|---|---|---|---|---|---|---|
| ladder_pct | 1106 | 10.9% / 12.4% | 74.9% / 74.5% | 14.2% / 13.1% | 16.8% / 21.8% (n 286) | 18.3% / 20.4% (n 279) |
| pool_15m | 6223 | 8.9% / 12.5% | 74.5% / 73.8% | 16.6% / 13.6% | 19.5% / 21.7% (n 1458) | 17.5% / 20.6% (n 1776) |
| pool_1h | 1806 | 9.7% / 12.8% | 71.8% / 73.3% | 18.4% / 13.9% | 21.2% / 22.9% (n 424) | 21.6% / 21.5% (n 564) |
| pool_4h | 531 | 11.1% / 13.3% | 68.9% / 71.9% | 20.0% / 14.6% | 21.7% / 25.0% (n 138) | 29.3% / 23.9% (n 174) |

- W1 is the least often longest, as the rulebook says, and on BTC even less than chance (15m, 1H). W5 is the longest more often than chance, at the expense of W1.
- A shallow W2 is **not** more common after a strong uptrend: 16.8% against 18.3% otherwise on the ladder. The claim is not supported. **[verified]**

The add-one rule of lesson 14 is not distinguishable from chance on these n:

| pool | W3 near 1.618, then W5 near 2.236: BTC / null | W3 near 2.618, then W5 near 3.236: BTC / null |
|---|---|---|
| ladder_pct | 13.7% / 12.5% (n 102) | 24.2% / 18.8% (n 62) |
| pool_15m | 13.6% / 12.6% (n 572) | 19.8% / 18.6% (n 379) |
| pool_1h | 10.7% / 12.6% (n 168) | 17.8% / 18.2% (n 101) |
| pool_4h | 11.5% / 11.9% (n 52) | 15.2% / 17.4% (n 33) |

**Alternation.** Rulebook section 1: a shallow W2 means a deeper W4. The rules alone couple them a little, so the null is not zero, but BTC sits below it in every era at 15m, 1H and 4H (p 0.003 overall at 15m and 1H). It is small: r about -0.1 explains 1% of the variation. This is the one rulebook guideline in this report that holds up, and it is too small to trade on. **[verified: `b3_alternation.py`]**

| bars | period | n | Spearman W2, W4: BTC | trend +-60d (5-95%) | p low |
|---|---|---|---|---|---|
| 15m | all | 6223 | -0.08 | -0.03 (-0.06 to -0.02) | 0.003 |
| 15m | 2014-2017 | 1841 | -0.08 | -0.03 (-0.07 to 0.02) | 0.047 |
| 15m | 2018-2021 | 1973 | -0.14 | -0.04 (-0.09 to 0.00) | 0.003 |
| 15m | 2022-2026 | 1704 | -0.07 | -0.02 (-0.07 to 0.03) | 0.063 |
| 1h | all | 1806 | -0.11 | -0.04 (-0.08 to 0.01) | 0.003 |
| 1h | 2014-2017 | 592 | -0.09 | -0.04 (-0.13 to 0.05) | 0.176 |
| 1h | 2018-2021 | 536 | -0.15 | -0.04 (-0.13 to 0.06) | 0.030 |
| 1h | 2022-2026 | 446 | -0.08 | -0.03 (-0.13 to 0.07) | 0.179 |
| 4h | all | 531 | -0.08 | -0.02 (-0.12 to 0.08) | 0.146 |
| 4h | 2014-2017 | 178 | -0.08 | -0.03 (-0.21 to 0.15) | 0.326 |
| 4h | 2018-2021 | 159 | -0.11 | -0.00 (-0.19 to 0.15) | 0.183 |
| 4h | 2022-2026 | 109 | -0.15 | -0.05 (-0.25 to 0.16) | 0.183 |

**Era fingerprint.** Rate by era on the ladder, BTC / trend +-60d:

| window | 2014-2017 (n 363), BTC / null (5-95%) | 2018-2021 (n 365) | 2022-2026 (n 162) |
|---|---|---|---|
| W2 at 0.5-0.618 | 17.4% / 17.6% (15% to 21%) | 17.0% / 17.6% (14% to 21%) | 13.6% / 17.1% (13% to 22%) |
| W2 under 0.382 | 6.9% / 12.4% (10% to 15%) | 12.6% / 12.2% (9% to 15%) | 12.3% / 12.9% (9% to 17%) |
| W4 at 0.236-0.382 | 39.9% / 41.3% (38% to 46%) | 46.6% / 42.0% (38% to 46%) | 42.6% / 42.9% (36% to 49%) |
| W3 near 1.618 | 11.3% / 9.4% (7% to 12%) | 7.1% / 9.3% (7% to 12%) | 10.5% / 9.1% (6% to 13%) |
| W3 near 2.618 | 5.5% / 5.2% (4% to 7%) | 6.0% / 5.5% (4% to 8%) | 7.4% / 5.3% (3% to 9%) |
| W5 near 2.236 | 11.6% / 8.7% (7% to 11%) | 7.7% / 8.5% (6% to 11%) | 7.4% / 8.8% (5% to 13%) |
| W5 near 1.0 | 7.2% / 6.8% (5% to 9%) | 4.9% / 6.6% (4% to 9%) | 6.2% / 6.7% (4% to 10%) |

No stable BTC value stands apart from the null in all three eras. Eras move inside the null's range; 2014-2017 is the odd one (W2 under 0.382, W5 near 2.236). Shape and learnability, of 24 scales per ratio, q under 0.05:

| ratio | signflip: shape differs / fit beats null, of 24 scales, q < 0.05 | trend +-60d |
|---|---|---|
| W2 | 3 / 0 | 4 / 0 |
| W3 | 3 / 2 | 7 / 2 |
| W4 | 6 / 1 | 6 / 1 |
| W5, pull 0-1-4 | 10 / 2 | 10 / 3 |
| W5, pull 0-1-2 | 8 / 2 | 8 / 2 |
| time W2/W1 | 3 / 0 | 4 / 0 |
| time W3/W1 | 5 / 2 | 5 / 1 |
| time W4/W3 | 7 / 0 | 6 / 0 |
| time W5/W1 | 9 / 0 | 9 / 0 |

The W5 ratios and the time ratios differ in shape on many scales, which is the longer W5 and quick W4 of B2 and B3. Almost nothing learned before 2022 beats the null after it. **[verified]**

**Verdict on "every asset has its own Fibonacci".** Tested on one asset only, since we hold BTC data only: BTC's swing ratios differ from random in shape, but not at Fibonacci levels. What is BTC-specific and stable is small: the step at 1.0, longer W3 and W5 at 15m and 1H, mild alternation. A model trained to learn "BTC's Fibonacci levels" would mostly learn the shape that any rule-filtered zigzag produces. Whether other assets differ from BTC is **[unknown]** and cheap to test with this same code; I would run ETH next.

### B3. Time ratios

NewWave Fib time (rulebook sections 1 and 4). Bars between pivots, same candidates, same null. Near is +-10%.

| rulebook claim | BTC, ladder | trend +-60d (5-95%) | p | 15m BTC / null | 1h | 4h | 1d |
|---|---|---|---|---|---|---|---|
| W2 does not outlast W1 | 64.0% | 64.2% (62% to 67%) | 0.898 | 62.5% / 64.3% | 65.1% / 64.6% | 66.7% / 66.8% | 68.1% / 69.4% |
| W2 takes at least 0.25 of W1 | 66.0% | 65.3% (63% to 67%) | 0.587 | 69.6% / 66.7% | 65.9% / 65.7% | 62.5% / 63.8% | 53.8% / 58.4% |
| W2 takes at least 0.33 of W1 | 59.5% | 58.9% (56% to 61%) | 0.687 | 63.4% / 60.1% | 60.1% / 59.1% | 56.7% / 57.0% | 44.5% / 51.7% |
| W4 does not outlast W3 | 90.3% | 86.0% (84% to 88%) | 0.004 | 85.6% / 84.7% | 86.7% / 84.9% | 91.5% / 87.8% | 96.6% / 89.8% |
| W4 takes at least 0.25 of W3 | 36.8% | 47.3% (45% to 50%) | 0.004 | 47.3% / 50.8% | 44.0% / 49.6% | 34.5% / 45.7% | 26.1% / 40.0% |
| W4 takes about as long as W2 (0.8-1.25) | 19.3% | 20.8% (19% to 23%) | 0.200 | 20.6% / 21.2% | 19.7% / 20.6% | 18.6% / 19.2% | 21.0% / 20.0% |
| W3 time near 1.0 of W1 | 8.3% | 7.3% (6% to 9%) | 0.196 | 9.0% / 8.1% | 9.1% / 7.7% | 7.5% / 6.9% | 6.7% / 7.0% |
| W3 time near 1.618 | 7.1% | 5.9% (5% to 7%) | 0.136 | 6.6% / 6.5% | 6.8% / 6.5% | 5.3% / 6.5% | 6.7% / 6.2% |
| W3 time near 2.236 | 4.6% | 4.7% (4% to 6%) | 0.918 | 4.5% / 4.7% | 4.2% / 4.8% | 5.5% / 5.1% | 5.0% / 4.5% |
| W5 time near 1.0 of W1 | 8.0% | 8.3% (7% to 9%) | 0.719 | 8.8% / 9.1% | 9.3% / 8.6% | 6.2% / 7.8% | 10.1% / 7.8% |
| W5 time near 0.618 | 5.3% | 4.2% (3% to 5%) | 0.064 | 5.2% / 4.7% | 4.7% / 4.6% | 5.5% / 4.6% | 4.2% / 4.5% |

- W3 and W5 time near the named Fibonacci multiples: same as random. W4 about as long as W2: 19% against 21%, same as random, so the equality claim is no more than chance either.
- The minimum rule ("any correction takes at least 25% of the wave it corrects"): on the ladder about a third of W2 and nearly two thirds of W4 break it, on random paths too (a third and about half). As a hard rule it would kill most mechanical candidates. A person would reject some of those as wrong pivots, so this does not refute it, but it is a filter, not a market fact.
- W4 is quicker against W3 than chance (36.8% against 47.3% reach 0.25 of W3, p 0.004), but that comes from 2014-2017 (4H 26% against 45%); 2018-2021 and 2022-2026 sit inside the null's range at 15m, 1H and 4H. **[verified]**

## C. His hypothesis: structures finish at weekly cycle lows, and the weekly midpoint is a top

Verbatim: "very often the Elliott Wave structure finishes on the weekly cycles. Very often the weekly cycle is a low or something and the middle of the weekly cycle is a top of something." Neither the Camel book nor the rulebook links waves to timing cycles: this is his own observation. The Camel book in fact expects a half-cycle *low* near the middle, and calls a mid-translated top neutral to bullish. **[verified: text search of the sources]**

**Why this needs care.** The cycle DP picks swing lows by construction, so "cycle lows are pivot lows" proves nothing. And low-to-low marking shapes where tops can sit. So every test here runs the identical pipeline on null paths: `ewave.cycles` hindsight and live marks, plus zigzag and rule checker with no cycle input, on one market at 1D and 4H (whole days as the null's unit; bars before 2013-03-01 stay as they were, as in cycles-r1). Only the difference counts. The marks on null paths match cycles-r1: median 21 hindsight and 19 live weekly cycles on shuffled and block paths, 23 and 22 on BTC. **[verified: `c_weekly_cycles.py`, `c2_followups.py`, 1,000 paths per null]**

### C1. Where inside the cycle does the top sit?

Figure: `/opt/data/cache/scratch/elliott_research_r1/emp/fig_c1_top_position.png`.

| metric | BTC | block | signflip | trend +-60d |
|---|---|---|---|---|
| hindsight: top within 0.05 of the middle (uniform 10%) | 4.3% | 8.7% (0% to 19%) p 0.432 | 5.3% (0% to 19%) p 0.454 | 5.0% (0% to 17%) p 0.591 |
| hindsight: within 0.10 (uniform 20%) | 13.0% | 15.8% (5% to 32%) p 0.669 | 15.0% (5% to 29%) p 0.793 | 13.6% (4% to 29%) p 0.905 |
| hindsight: within 0.15 (uniform 30%) | 26.1% | 23.8% (10% to 43%) p 0.883 | 21.1% (10% to 38%) p 0.687 | 20.8% (9% to 37%) p 0.593 |
| hindsight: left of the middle | 39.1% | 31.8% (18% to 48%) p 0.474 | 28.6% (15% to 43%) p 0.218 | 40.0% (27% to 52%) p 0.981 |
| hindsight: median position | 0.61 | 0.69 (0.53 to 0.82) p 0.466 | 0.73 (0.59 to 0.84) p 0.180 | 0.63 (0.47 to 0.77) p 0.837 |
| live: within 0.05 | 13.6% | 9.5% (0% to 21%) p 0.553 | 6.7% (0% to 21%) p 0.507 | 7.1% (0% to 22%) p 0.438 |
| live: within 0.10 | 27.3% | 19.0% (6% to 37%) p 0.434 | 16.7% (5% to 33%) p 0.304 | 17.6% (5% to 35%) p 0.354 |
| live: within 0.15 | 40.9% | 29.7% (14% to 47%) p 0.320 | 26.1% (11% to 44%) p 0.168 | 27.8% (12% to 45%) p 0.252 |
| live: left of the middle | 31.8% | 31.6% (16% to 48%) p 0.907 | 25.0% (11% to 40%) p 0.480 | 35.7% (21% to 53%) p 0.705 |
| live: median position | 0.61 | 0.67 (0.52 to 0.79) p 0.472 | 0.71 (0.57 to 0.81) p 0.184 | 0.63 (0.48 to 0.75) p 0.741 |

| percent of cycles, by position | 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
|---|---|---|---|---|---|---|---|---|---|---|
| hindsight tops, BTC (23) | 9 | 13 | 4 | 4 | 9 | 4 | 17 | 4 | 9 | 26 |
| hindsight tops, shuffled days | 8 | 4 | 5 | 5 | 7 | 8 | 10 | 12 | 15 | 25 |
| hindsight tops, trend +-60d | 10 | 9 | 7 | 6 | 7 | 8 | 9 | 10 | 13 | 21 |
| live tops, BTC (22) | 5 | 5 | 9 | 5 | 9 | 18 | 23 | 14 | 0 | 14 |
| live tops, shuffled days | 5 | 3 | 5 | 6 | 8 | 10 | 12 | 15 | 18 | 16 |
| live tops, trend +-60d | 4 | 7 | 8 | 8 | 9 | 10 | 12 | 13 | 16 | 13 |

- On random paths tops pile up late (drift, and the marking), and the middle holds less than uniform: 14-19% within 0.1, not 20%. So "the top is near the middle" is no natural default.
- Hindsight: 3 of 23 tops within 0.1 of the middle. No clustering.
- Live: 6 of 22, with the mass at 0.5-0.7. That leans his way, but sits well inside the null's range (p 0.30 to 0.43).
- n is small. Wilson interval on 6 of 22: 13% to 48%. **[verified]**

### C2. A "top of something" need not be the cycle's top

All pivot highs of an independent zigzag by phase, and where the biggest pullback inside each cycle starts. If the middle were a top zone, pivot highs would sit there more than pivot lows.

| metric | BTC | block | signflip | trend +-60d |
|---|---|---|---|---|
| hindsight 4h_pct8: pivot highs in 0.4-0.6 | 10.6% | 16.7% (13% to 21%) p 0.010 | 15.7% (12% to 21%) p 0.020 | 17.3% (13% to 23%) p 0.010 |
| hindsight 4h_pct8: pivot lows in 0.4-0.6 | 10.9% | 16.7% (13% to 21%) p 0.008 | 15.7% (12% to 21%) p 0.028 | 17.4% (13% to 23%) p 0.010 |
| hindsight 4h_pct8: biggest pullback starts in 0.4-0.6 | 4.3% | 11.1% (0% to 25%) p 0.190 | 11.1% (0% to 25%) p 0.120 | 14.3% (4% to 27%) p 0.122 |
| hindsight 1d_pct16: pivot highs in 0.4-0.6 | 12.0% | 16.8% (12% to 22%) p 0.082 | 16.0% (11% to 22%) p 0.150 | 17.5% (12% to 24%) p 0.078 |
| hindsight 1d_pct16: pivot lows in 0.4-0.6 | 10.2% | 16.2% (12% to 22%) p 0.036 | 15.6% (11% to 21%) p 0.028 | 17.1% (12% to 23%) p 0.028 |
| hindsight 1d_pct16: biggest pullback starts in 0.4-0.6 | 13.0% | 13.6% (0% to 26%) p 0.927 | 14.3% (5% to 26%) p 0.939 | 15.0% (5% to 29%) p 0.727 |
| live 4h_pct8: pivot highs in 0.4-0.6 | 28.9% | 18.4% (14% to 24%) p 0.008 | 17.8% (13% to 24%) p 0.010 | 20.8% (15% to 29%) p 0.098 |
| live 4h_pct8: pivot lows in 0.4-0.6 | 28.4% | 18.4% (14% to 24%) p 0.010 | 17.7% (13% to 24%) p 0.014 | 20.8% (15% to 29%) p 0.110 |
| live 4h_pct8: biggest pullback starts in 0.4-0.6 | 18.2% | 15.0% (4% to 29%) p 0.679 | 13.6% (0% to 29%) p 0.595 | 15.8% (0% to 33%) p 0.785 |
| live 1d_pct16: pivot highs in 0.4-0.6 | 28.9% | 18.7% (13% to 25%) p 0.012 | 17.9% (12% to 24%) p 0.012 | 20.5% (14% to 29%) p 0.104 |
| live 1d_pct16: pivot lows in 0.4-0.6 | 24.8% | 18.0% (13% to 25%) p 0.100 | 17.5% (12% to 24%) p 0.058 | 19.8% (13% to 28%) p 0.300 |
| live 1d_pct16: biggest pullback starts in 0.4-0.6 | 18.2% | 15.8% (5% to 32%) p 0.767 | 15.0% (5% to 30%) p 0.717 | 16.7% (5% to 33%) p 0.891 |

- **Pivot highs and pivot lows have the same profile.** Hindsight 10.6% and 10.9% on 4h_pct8, live 28.9% and 28.4%. The middle is not a "top" zone rather than a "low" zone. The Camel half-cycle low and his mid-cycle top are not told apart either.
- The level differs with the marks. Hindsight has *fewer* swings in the middle than random paths (11-12% against 16-19%). Live has more (25-29% against 18-21%). That is swing density, not tops: hindsight lows sit where swings are dense, and the live machine, which cannot take a low inside its minimum gap, leaves some of those dense stretches in the middle of its cycles. Trend +-60d keeps the volatility path and reduces the live gap to p about 0.1-0.3. **[assumed reading, numbers verified]**
- The biggest pullback starts in the middle no more often than chance. **[verified]**

### C3. Do structures finish at the lows and in the middle?

**At weekly lows.** Down-structures are legal 5-waves down, or legal zigzags down (B not beyond the start of A, C beyond A, C at least 0.618 of A). The odds ratio is inside the path: among pivot lows, is one that ends a legal down-structure more often at a weekly low than one that does not? That controls for the plain fact that big lows are big lows.

| metric | BTC | block | signflip | trend +-60d |
|---|---|---|---|---|
| hindsight 4h_pct8 5-wave: weekly lows with a down-structure end within 14d | 37.5% | 31.2% (15% to 48%) p 0.521 | 23.8% (10% to 38%) p 0.144 | 26.1% (13% to 40%) p 0.184 |
| hindsight 4h_pct8 5-wave: any day with one within 14d | 14.2% | 11.6% (8% to 15%) p 0.326 | 9.7% (7% to 13%) p 0.030 | 11.6% (8% to 15%) p 0.238 |
| hindsight 4h_pct8 5-wave: odds ratio among pivot lows | 2.10 | 1.80 (0.75 to 3.94) p 0.757 | 1.65 (0.69 to 3.50) p 0.639 | 1.56 (0.73 to 3.20) p 0.527 |
| hindsight 4h_pct8 zigzag: weekly lows with a down-structure end within 14d | 83.3% | 85.0% (70% to 96%) p 0.917 | 76.0% (61% to 90%) p 0.402 | 76.2% (62% to 90%) p 0.382 |
| hindsight 4h_pct8 zigzag: any day with one within 14d | 50.0% | 53.8% (47% to 60%) p 0.368 | 48.5% (44% to 53%) p 0.625 | 50.1% (46% to 55%) p 0.973 |
| hindsight 4h_pct8 zigzag: odds ratio among pivot lows | 1.36 | 1.29 (0.96 to 1.74) p 0.779 | 1.26 (0.90 to 1.75) p 0.651 | 1.23 (0.90 to 1.72) p 0.639 |
| hindsight 1d_pct16 5-wave: weekly lows with a down-structure end within 14d | 8.3% | 8.7% (0% to 18%) p 0.929 | 5.6% (0% to 18%) p 0.999 | 9.1% (0% to 21%) p 0.725 |
| hindsight 1d_pct16 5-wave: any day with one within 14d | 3.0% | 2.2% (1% to 4%) p 0.513 | 2.1% (1% to 4%) p 0.408 | 3.3% (1% to 5%) p 0.789 |
| hindsight 1d_pct16 5-wave: odds ratio among pivot lows | 1.51 | 2.33 (0.40 to 13.99) p 0.645 | 2.66 (0.43 to 14.89) p 0.587 | 2.07 (0.42 to 7.82) p 0.659 |
| hindsight 1d_pct16 zigzag: weekly lows with a down-structure end within 14d | 66.7% | 61.5% (45% to 78%) p 0.699 | 50.0% (35% to 67%) p 0.124 | 50.0% (33% to 67%) p 0.126 |
| hindsight 1d_pct16 zigzag: any day with one within 14d | 22.7% | 22.7% (18% to 28%) p 0.969 | 20.0% (16% to 24%) p 0.320 | 20.7% (17% to 25%) p 0.444 |
| hindsight 1d_pct16 zigzag: odds ratio among pivot lows | 1.55 | 1.86 (1.16 to 3.26) p 0.563 | 1.73 (0.96 to 3.20) p 0.769 | 1.66 (0.88 to 3.06) p 0.827 |
| live 4h_pct8 5-wave: weekly lows with a down-structure end within 14d | 26.1% | 31.6% (15% to 48%) p 0.629 | 22.2% (10% to 39%) p 0.737 | 26.3% (11% to 43%) p 0.959 |
| live 4h_pct8 5-wave: any day with one within 14d | 13.5% | 11.6% (8% to 15%) p 0.460 | 9.3% (6% to 13%) p 0.042 | 11.2% (8% to 15%) p 0.282 |
| live 4h_pct8 5-wave: odds ratio among pivot lows | 1.49 | 2.02 (0.87 to 4.35) p 0.505 | 1.99 (0.73 to 4.24) p 0.585 | 2.15 (0.84 to 4.50) p 0.482 |
| live 4h_pct8 zigzag: weekly lows with a down-structure end within 14d | 82.6% | 85.0% (70% to 95%) p 0.831 | 76.2% (60% to 90%) p 0.474 | 76.5% (59% to 93%) p 0.535 |
| live 4h_pct8 zigzag: any day with one within 14d | 49.3% | 53.7% (47% to 60%) p 0.276 | 47.6% (42% to 53%) p 0.557 | 49.4% (44% to 55%) p 0.945 |
| live 4h_pct8 zigzag: odds ratio among pivot lows | 1.29 | 1.35 (0.98 to 1.87) p 0.845 | 1.39 (0.99 to 2.07) p 0.763 | 1.44 (0.97 to 2.28) p 0.669 |
| live 1d_pct16 5-wave: weekly lows with a down-structure end within 14d | 13.0% | 9.1% (0% to 20%) p 0.543 | 5.9% (0% to 19%) p 0.398 | 11.1% (0% to 25%) p 0.793 |
| live 1d_pct16 5-wave: any day with one within 14d | 2.8% | 2.2% (1% to 4%) p 0.599 | 1.9% (1% to 4%) p 0.434 | 3.3% (1% to 5%) p 0.705 |
| live 1d_pct16 5-wave: odds ratio among pivot lows | 5.62 | 2.94 (0.45 to 18.25) p 0.500 | 3.33 (0.54 to 19.43) p 0.549 | 3.06 (0.57 to 12.05) p 0.438 |
| live 1d_pct16 zigzag: weekly lows with a down-structure end within 14d | 60.9% | 63.4% (45% to 80%) p 0.839 | 52.2% (35% to 70%) p 0.416 | 52.9% (35% to 72%) p 0.549 |
| live 1d_pct16 zigzag: any day with one within 14d | 22.0% | 22.7% (18% to 28%) p 0.793 | 19.3% (15% to 24%) p 0.330 | 20.1% (16% to 24%) p 0.448 |
| live 1d_pct16 zigzag: odds ratio among pivot lows | 2.64 | 2.16 (1.28 to 3.82) p 0.565 | 2.10 (1.10 to 3.96) p 0.523 | 2.23 (1.14 to 4.37) p 0.693 |

Now as a person counts, with any of six degrees accepted:

| metric | BTC | block | signflip | trend +-60d |
|---|---|---|---|---|
| hindsight: weekly lows with a legal 5-wave down ending within 14d, any of six scales | 75.0% | 69.6% (52% to 86%) p 0.573 | 61.9% (45% to 77%) p 0.206 | 65.2% (50% to 78%) p 0.288 |
| hindsight: any day with one | 34.6% | 36.4% (31% to 42%) p 0.581 | 34.9% (30% to 40%) p 0.925 | 38.4% (33% to 44%) p 0.224 |
| hindsight: weekly lows with a 5-wave or zigzag down ending within 14d | 100.0% | 100.0% (95% to 100%) p 1.000 | 100.0% (91% to 100%) p 1.000 | 100.0% (91% to 100%) p 1.000 |
| hindsight: any day with one | 84.5% | 89.2% (85% to 93%) p 0.052 | 85.7% (82% to 89%) p 0.625 | 86.5% (83% to 90%) p 0.376 |
| live: weekly lows with a legal 5-wave down ending within 14d, any of six scales | 65.2% | 70.6% (53% to 86%) p 0.621 | 62.5% (47% to 79%) p 0.775 | 66.7% (47% to 82%) p 0.891 |
| live: any day with one | 33.6% | 36.4% (31% to 42%) p 0.442 | 34.0% (29% to 39%) p 0.905 | 37.8% (33% to 43%) p 0.178 |
| live: weekly lows with a 5-wave or zigzag down ending within 14d | 100.0% | 100.0% (95% to 100%) p 1.000 | 100.0% (94% to 100%) p 1.000 | 100.0% (94% to 100%) p 1.000 |
| live: any day with one | 84.3% | 89.2% (85% to 93%) p 0.036 | 85.3% (81% to 89%) p 0.645 | 86.1% (83% to 90%) p 0.384 |

- **So his observation is right, and it is not evidence.** 18 of 24 weekly lows have a legal 5-wave down ending within two weeks at some degree, and all 24 do if zigzags count. But 34% of all days have such a 5-wave within two weeks, and 85% have a 5-wave or zigzag; and the lows on random paths score 57-70% and 100%. The eye that goes looking for a completed structure at a cycle low will find one, on any path. **[verified]**
- At one fixed degree BTC leans above the null on most rows (for example 37.5% of lows at 4h_pct8 against 20-31%), and the odds ratios are in line with the null. No row clears correction.

**In the middle.**

| metric | BTC | block | signflip | trend +-60d |
|---|---|---|---|---|
| hindsight 4h_pct8 5-wave: up-structure ends in 0.4-0.6 | 16.2% | 18.5% (8% to 31%) p 0.771 | 18.4% (7% to 32%) p 0.749 | 20.5% (9% to 35%) p 0.617 |
| hindsight 4h_pct8 5-wave: odds ratio among pivot highs | 1.78 | 1.19 (0.47 to 2.35) p 0.374 | 1.30 (0.53 to 2.54) p 0.452 | 1.28 (0.56 to 2.46) p 0.406 |
| hindsight 4h_pct8 zigzag: up-structure ends in 0.4-0.6 | 12.5% | 17.2% (12% to 23%) p 0.124 | 16.4% (11% to 23%) p 0.214 | 18.0% (12% to 26%) p 0.138 |
| hindsight 4h_pct8 zigzag: odds ratio among pivot highs | 1.31 | 1.07 (0.74 to 1.53) p 0.352 | 1.09 (0.73 to 1.57) p 0.392 | 1.08 (0.71 to 1.56) p 0.378 |
| hindsight 1d_pct16 5-wave: up-structure ends in 0.4-0.6 | 0.0% | 21.4% (0% to 45%) p 0.196 | 20.0% (0% to 43%) p 0.244 | 21.4% (0% to 45%) p 0.156 |
| hindsight 1d_pct16 5-wave: odds ratio among pivot highs | 0.22 | 1.54 (0.27 to 4.91) p 0.048 | 1.53 (0.26 to 4.46) p 0.058 | 1.43 (0.26 to 4.21) p 0.076 |
| hindsight 1d_pct16 zigzag: up-structure ends in 0.4-0.6 | 14.6% | 19.0% (11% to 28%) p 0.396 | 17.7% (10% to 26%) p 0.561 | 18.5% (10% to 29%) p 0.503 |
| hindsight 1d_pct16 zigzag: odds ratio among pivot highs | 1.43 | 1.27 (0.60 to 2.51) p 0.773 | 1.22 (0.58 to 2.34) p 0.705 | 1.13 (0.58 to 2.29) p 0.545 |
| live 4h_pct8 5-wave: up-structure ends in 0.4-0.6 | 52.9% | 22.3% (12% to 36%) p 0.004 | 22.2% (10% to 36%) p 0.002 | 25.9% (13% to 41%) p 0.010 |
| live 4h_pct8 5-wave: odds ratio among pivot highs | 2.96 | 1.34 (0.65 to 2.67) p 0.058 | 1.41 (0.52 to 2.73) p 0.068 | 1.42 (0.64 to 2.71) p 0.080 |
| live 4h_pct8 zigzag: up-structure ends in 0.4-0.6 | 32.1% | 19.7% (14% to 26%) p 0.010 | 19.3% (13% to 27%) p 0.012 | 22.7% (15% to 32%) p 0.108 |
| live 4h_pct8 zigzag: odds ratio among pivot highs | 1.24 | 1.14 (0.81 to 1.57) p 0.645 | 1.16 (0.79 to 1.67) p 0.779 | 1.18 (0.79 to 1.65) p 0.777 |
| live 1d_pct16 5-wave: up-structure ends in 0.4-0.6 | 64.3% | 25.0% (0% to 50%) p 0.026 | 23.1% (0% to 50%) p 0.014 | 28.6% (7% to 55%) p 0.038 |
| live 1d_pct16 5-wave: odds ratio among pivot highs | 5.08 | 1.67 (0.34 to 4.88) p 0.082 | 1.61 (0.30 to 4.76) p 0.086 | 1.71 (0.41 to 5.03) p 0.096 |
| live 1d_pct16 zigzag: up-structure ends in 0.4-0.6 | 39.5% | 22.2% (13% to 32%) p 0.010 | 20.6% (12% to 31%) p 0.008 | 24.0% (14% to 37%) p 0.048 |
| live 1d_pct16 zigzag: odds ratio among pivot highs | 2.01 | 1.42 (0.73 to 2.72) p 0.350 | 1.37 (0.67 to 2.80) p 0.322 | 1.33 (0.70 to 2.70) p 0.352 |

- Hindsight: fewer up-structure ends in the middle than chance (0 of 14 5-waves at 1d_pct16, 6 of 37 at 4h_pct8).
- Live: more, on every null. 18 of 34 5-waves at 4h_pct8 and 9 of 14 at 1d_pct16 end in 0.4-0.6, against 22-29%, and the odds ratios lean the same way (3.0 and 5.1 against about 1.4 and 1.7, p 0.04 to 0.1). This is the strongest number for his idea. Part of it is the swing density of C2, and hindsight points the other way. The 18 are about 14 separate occasions, since overlapping candidates end together: 2013-11-07, 2013-11-18, 2015-01-26, 2015-11-04, 2017-06-12, 2017-12-07, 2019-05-13, 2019-06-26, 2020-05-07, 2021-01-02, 2021-02-14, 2021-10-20, 2023-03-24, 2024-12-05. Some are real tops and some are not, which is what C5 goes on to test.

Multiple tests over all settings, and over the 138 primary rows:

| null | C3 tests, all settings | p < 0.05 (33 by chance) | BTC above / below null | q < 0.05 | primary rows | primary, smallest q |
|---|---|---|---|---|---|---|
| shuffle | 656 | 121 | 84 / 37 | 56 | 138 | 0.016 |
| block | 656 | 52 | 41 / 11 | 0 | 138 | 0.138 |
| signflip | 656 | 61 | 58 / 3 | 0 | 138 | 0.214 |
| trendflip | 656 | 54 | 52 / 2 | 0 | 138 | 0.460 |

Above-null readings outnumber below-null ones, and the tests overlap heavily. Nothing clears correction against block, signflip or trend. **[verified]**

### C4. Causal: after a live-confirmed weekly low

| metric | BTC | block | signflip | trend +-60d |
|---|---|---|---|---|
| 4h_pct8: a legal up 5-wave starts from a pivot low at a live weekly low | 6.6% | 5.9% (3% to 10%) p 0.673 | 5.8% (3% to 10%) p 0.733 | 6.2% (2% to 12%) p 0.903 |
| 4h_pct8: the same from any other pivot low | 5.7% | 5.9% (5% to 8%) p 0.773 | 4.6% (3% to 6%) p 0.200 | 5.1% (4% to 7%) p 0.490 |
| 4h_pct8: next completed legal 5-wave after confirmation is up | 68.0% | 70.0% (53% to 85%) p 0.869 | 70.5% (52% to 88%) p 0.849 | 64.3% (44% to 83%) p 0.713 |
| 4h_pct8: share up among all legal 5-waves | 56.3% | 63.6% (55% to 72%) p 0.192 | 63.4% (54% to 73%) p 0.212 | 61.1% (52% to 70%) p 0.414 |
| 1d_pct16: a legal up 5-wave starts from a pivot low at a live weekly low | 17.1% | 7.1% (2% to 14%) p 0.024 | 7.7% (2% to 16%) p 0.066 | 8.6% (2% to 18%) p 0.128 |
| 1d_pct16: the same from any other pivot low | 7.2% | 5.7% (3% to 9%) p 0.468 | 5.3% (3% to 8%) p 0.272 | 6.3% (3% to 10%) p 0.645 |
| 1d_pct16: next completed legal 5-wave after confirmation is up | 80.0% | 75.9% (45% to 97%) p 0.829 | 80.7% (48% to 100%) p 0.989 | 66.7% (40% to 92%) p 0.470 |
| 1d_pct16: share up among all legal 5-waves | 76.2% | 75.0% (56% to 91%) p 0.925 | 75.0% (57% to 92%) p 0.897 | 66.7% (50% to 83%) p 0.392 |
| 2R barrier from the confirmation close (driftless walk 33%) | 43.8% | 48.4% (34% to 63%) p 0.603 | 54.8% (41% to 71%) p 0.210 | 46.7% (33% to 60%) p 0.735 |
| forward 60 days, mean log return | 0.04 | 0.11 (0.03 to 0.20) p 0.146 | 0.09 (0.01 to 0.18) p 0.284 | 0.05 (-0.03 to 0.16) p 0.779 |
| forward 60 days, share positive | 53.1% | 62.1% (48% to 77%) p 0.294 | 64.7% (50% to 79%) p 0.194 | 57.1% (43% to 72%) p 0.673 |

There is one lead: from a pivot low at a live weekly low on 1d_pct16, a legal up 5-wave starts 17.1% of the time (6 of 35) against 7-9%, p 0.02 to 0.13. Nothing similar at 4h_pct8 (6.6% against 6%). The next completed 5-wave is up about as often as on random paths. A 2R trade from the confirmation close wins 44% (n 32), below the null's 47-55% and above the 33% of a driftless walk: that gap is drift, not the low. **[verified]**

### C5. Confluence, causal

If a legal down-structure confirms with the live weekly window open (151-323 days since the live low standing at that moment), does it reach the start of its last leg before undercutting its end more often than with the window closed?

| metric | BTC | block | signflip | trend +-60d |
|---|---|---|---|---|
| 4h_pct8: reaches start of last leg, window open (n 81) | 45.7% | 51.3% (42% to 61%) p 0.326 | 52.1% (42% to 63%) p 0.324 | 47.4% (38% to 58%) p 0.729 |
| 4h_pct8: window closed (n 123) | 47.2% | 51.3% (44% to 58%) p 0.360 | 52.5% (45% to 61%) p 0.260 | 48.7% (40% to 58%) p 0.779 |
| 4h_pct8: difference | -1.5% | -0.3% (-12% to 13%) p 0.863 | -0.6% (-14% to 15%) p 0.941 | -1.1% (-14% to 13%) p 0.957 |
| 1d_pct16: reaches start of last leg, window open (n 25) | 44.0% | 60.7% (42% to 78%) p 0.150 | 56.0% (36% to 80%) p 0.326 | 45.8% (26% to 69%) p 0.883 |
| 1d_pct16: window closed (n 22) | 59.1% | 62.1% (47% to 78%) p 0.771 | 58.1% (42% to 76%) p 0.925 | 50.0% (33% to 68%) p 0.432 |
| 1d_pct16: difference | -15.1% | -2.2% (-26% to 23%) p 0.394 | -0.7% (-30% to 26%) p 0.444 | -3.1% (-33% to 25%) p 0.541 |

No, on either scale. **[verified]**

And the mirror for his midpoint: a legal up-structure taken at its confirmation, with the live low standing then, phase = days since it / 231 (the middle of the window). Is it likelier to land at 0.4-0.6, and does the top hold better there (price reaches the start of the last leg before a new high)? The barrier law column removes what a short last leg gives on any path. **[verified: `c2_followups.py`]**

| scale | n mid / elsewhere | share mid | trend +-60d | top holds, mid | top holds, elsewhere | difference, pp | trend null, pp | after barrier law, pp |
|---|---|---|---|---|---|---|---|---|
| 4h_pct8 5-wave | 12 / 22 | 35.3% | 20.0% (p 0.122) | 25.0% | 50.0% | -25 | -4 (p 0.355) | -13 (p 0.616) |
| 4h_pct8 zigzag | 48 / 118 | 28.9% | 17.3% (p 0.044) | 27.1% | 51.7% | -25 | -4 (p 0.052) | -19 (p 0.084) |
| 1d_pct16 5-wave | 4 / 10 | 28.6% | 17.6% (p 0.464) | 0.0% | 40.0% | -40 | -9 (p 0.340) | -29 (p 0.458) |
| 1d_pct16 zigzag | 11 / 32 | 25.6% | 18.2% (p 0.256) | 18.2% | 40.6% | -22 | -5 (p 0.312) | -11 (p 0.587) |
| 4h_atr4 5-wave | 6 / 24 | 20.0% | 20.0% (p 1.000) | 16.7% | 45.8% | -29 | -2 (p 0.242) | -14 (p 0.531) |
| 4h_atr4 zigzag | 35 / 103 | 25.4% | 17.8% (p 0.052) | 22.9% | 43.7% | -21 | -4 (p 0.108) | -20 (p 0.054) |
| 1d_atr2 5-wave | 7 / 16 | 30.4% | 22.2% (p 0.438) | 28.6% | 50.0% | -21 | -6 (p 0.556) | -20 (p 0.408) |
| 1d_atr2 zigzag | 16 / 68 | 19.0% | 18.5% (p 0.907) | 31.2% | 41.2% | -10 | -4 (p 0.621) | -10 (p 0.519) |

- Slightly more of them land there than chance: 29% of zigzags at 4h_pct8 against 17%, p 0.04; 5-waves 35% against 20%, p 0.12.
- **But the top holds worse, not better, at all eight settings:** 25% against 50% on 4H 5-waves, 27% against 52% on 4H zigzags. The nulls also show a small negative gap, and BTC's is larger, at p 0.05 at best. So the causal version of "the middle of the cycle is a top" points the other way: an up-structure finishing around day 92-139 after a live low more often means the move keeps going. This fits right-translated cycles: most tops come later. The n are small and this is not a tested trade. **[verified as measured]**

### C6. Is there a rhythm at all? No marks involved

Mean spectral power of daily returns per period band, against the mean over periods of 30-1000 days:

| span | period, days | BTC | signflip | block |
|---|---|---|---|---|
| all | 30-60 | 0.83 | 1.01 (0.83 to 1.17) p 0.122 | 0.96 (0.81 to 1.10) p 0.182 |
| all | 60-100 | 1.10 | 0.98 (0.74 to 1.27) p 0.501 | 1.02 (0.79 to 1.29) p 0.643 |
| all | 100-168 | 0.95 | 1.00 (0.64 to 1.38) p 0.847 | 1.03 (0.72 to 1.41) p 0.653 |
| all | 168-294 | 1.90 | 0.97 (0.55 to 1.56) p 0.020 | 1.04 (0.62 to 1.58) p 0.018 |
| all | 294-500 | 0.58 | 0.94 (0.45 to 1.69) p 0.288 | 1.04 (0.50 to 1.87) p 0.168 |
| all | 500-1000 | 1.51 | 0.93 (0.39 to 1.92) p 0.290 | 0.98 (0.43 to 1.89) p 0.288 |
| 2013-2017 | 168-294 | 2.28 | 0.92 (0.32 to 2.04) p 0.052 | 1.01 (0.36 to 2.04) p 0.062 |
| 2018-2021 | 168-294 | 1.77 | 0.93 (0.36 to 1.81) p 0.116 | 1.01 (0.36 to 1.96) p 0.184 |
| 2022-2026 | 168-294 | 0.69 | 0.94 (0.41 to 1.84) p 0.494 | 1.00 (0.41 to 1.86) p 0.470 |

The 168-294 day band, which I fixed in advance from Camel's 24-42 week window, carries about twice its share (p 0.02 against signflip and block). It is the only band of six outside the null's range, and it fits the variance ratios levelling off at 120-180 days. By era it is 2.28, 1.77 and 0.69: present in two eras at weak p and absent in the latest. Trendflip cannot test this because it keeps much of that slow component by construction. This is the one result that favours a weekly-cycle rhythm in BTC without using the marks, but cycles-r1 found plain swing lows do not land in the window more often than on random paths, and C4 and C5 found no outcome to attach to it. **[verified]**

### C7. The other reading: "weekly" as day of the week

Share of pivots by UTC weekday, against signflip, which keeps each bar's size in place:

| scale | pivot | n | Mon | Tue | Wed | Thu | Fri | Sat | Sun | p against signflip |
|---|---|---|---|---|---|---|---|---|---|---|
| 4h_pct4 | low | 2170 | 16% | 14% | 16% | 16% | 17% | 10% | 11% | 0.119 |
| 4h_pct4 | high | 2170 | 16% | 15% | 15% | 16% | 15% | 12% | 11% | 0.423 |
| 4h_atr4 | low | 464 | 17% | 15% | 15% | 18% | 17% | 7% | 11% | 0.473 |
| 4h_atr4 | high | 464 | 20% | 16% | 17% | 13% | 14% | 9% | 11% | 0.542 |
| 1h_pct4 | low | 2663 | 15% | 14% | 16% | 16% | 17% | 10% | 11% | 0.199 |
| 1h_pct4 | high | 2663 | 15% | 15% | 16% | 16% | 16% | 12% | 11% | 0.592 |
| 1h_atr4 | low | 1867 | 16% | 14% | 14% | 14% | 16% | 10% | 16% | 0.045 |
| 1h_atr4 | high | 1867 | 17% | 14% | 14% | 14% | 14% | 12% | 15% | 0.050 |

Weekends hold fewer pivots because they are quieter; signflip reproduces that. Nothing like "low on Monday, top mid-week". **[verified]**

### Verdict on the hypothesis

| Claim | Verdict | Effect | n |
|---|---|---|---|
| Structures finish at weekly lows | **True as an observation, not evidence.** Random paths do the same. | 18 of 24 lows, 75% (95% CI 55 to 88), 5-waves at any degree, against 57-70%; 100% with zigzags against 100% | 24 lows |
| Weekly midpoint is the cycle's top | **Not shown.** | Within 0.1 of the middle: hindsight 3 of 23, 13% (5 to 32); live 6 of 22, 27% (13 to 48); against 14-19% | 23 and 22 |
| Weekly midpoint is a top of something | **Not shown.** Highs and lows have the same profile there. | Up-structure ends in 0.4-0.6: live 18 of 34, 53% (37 to 69), against 22-26% (p 0.002 to 0.01, q at best 0.14); hindsight 6 of 37, 16% (8 to 31), against 18-20% | 34 and 37 |
| A mid-cycle up-structure is a good top | **Points the other way.** | Top holds 3 of 12, 25% (9 to 53), against 11 of 22, 50% (31 to 69) on 4H 5-waves; same sign at all 8 settings; p 0.05 at best | 12 against 22 |
| After a live low, the next structure is up | **Same as random.** | Next 5-wave up: 68% and 80% against 64-72% and 67-81% | 32 lows |
| Structures confirmed with the window open do better | **No.** | -2 and -15 points, null medians -1 and -3 | 204 and 47 |
| A 24-42 week rhythm exists | **Weak yes, as a spectral bump, not in the latest era, no outcome attached.** | 1.90 against 0.97, p 0.02 | 13.7 years |

**What would change this.** At about 1.7 weekly cycles a year, this data cannot be hurried.

- The live up-structure lean (53% against 25%) is large enough that about 20 new events would confirm it at 80% power (arithmetic): at the past rate of 2.5 a year, about 8 years. Freeze the definition now and let it run.
- A midpoint-top effect of 27% against 18% needs about 150 cycles to confirm (arithmetic), nearly a century of BTC. It cannot be shown or refuted on BTC alone in useful time, though other assets could add cycles.
- A sharper test is possible now, from his side: his own hand-marked weekly lows and structure ends, logged before the fact, scored against these nulls. If his reading adds information it will show as a gap between his marks and the mechanical ones. **[unknown until logged]**

## D. TDI: "shark in the water" at 4H

RSI(11) on closes, bands over 31 bars at 1.6185 standard deviations **[assumed width]**. W3 pushes RSI outside the band; W5 fails to; the RSI peak of W5 is below that of W3 (rulebook section 1, "Shark in the water"). Leg-level peaks, not the indicator's pivot detector. Known at the bar that confirms p5, and read from the next bar. Mirrored for down-impulses. **[verified: `d_tdi_shark.py`, 500 paths]**

| scale | metric | BTC | signflip (5-95%) | trend +-60d (5-95%) | p trend |
|---|---|---|---|---|---|
| 4h_pct4 | legal impulses | 189 | 168 (150 to 190) | 177 (157 to 200) | 0.391 |
| 4h_pct4 | 3-5 divergence | 54.0% | 55.0% (49.2% to 61.2%) | 56.0% (49.2% to 62.2%) | 0.595 |
| 4h_pct4 | shark | 31.2% | 33.3% (27.9% to 39.1%) | 33.7% (27.9% to 39.6%) | 0.511 |
| 4h_pct4 | shark: reaches end of W4 before a new high | 42.4% | 53.7% (41.3% to 64.2%) | 50.0% (40.4% to 60.6%) | 0.220 |
| 4h_pct4 | no shark: the same | 46.2% | 43.8% (35.6% to 51.1%) | 41.0% (34.7% to 48.7%) | 0.299 |
| 4h_pct4 | difference | -3.8% | 10.3% (-4.1% to 22.5%) | 9.0% (-2.6% to 22.1%) | 0.084 |
| 4h_pct4 | shark, minus barrier law | -8.2% | -2.5% (-13.0% to 7.1%) | -4.8% (-14.5% to 5.1%) | 0.603 |
| 4h_pct4 | no shark, minus barrier law | 2.0% | -1.8% (-9.2% to 5.3%) | -3.8% (-9.8% to 3.1%) | 0.196 |
| 4h_atr2 | legal impulses | 184 | 140 (120 to 159) | 156 (137 to 174) | 0.012 |
| 4h_atr2 | 3-5 divergence | 65.8% | 68.0% (61.8% to 73.9%) | 68.2% (62.7% to 73.3%) | 0.495 |
| 4h_atr2 | shark | 51.6% | 51.8% (45.7% to 58.1%) | 50.7% (45.5% to 56.8%) | 0.774 |
| 4h_atr2 | shark: reaches end of W4 before a new high | 54.7% | 52.7% (43.0% to 62.0%) | 49.3% (39.5% to 58.1%) | 0.303 |
| 4h_atr2 | no shark: the same | 29.2% | 42.6% (33.3% to 52.5%) | 38.5% (29.4% to 47.5%) | 0.096 |
| 4h_atr2 | difference | 25.5% | 9.9% (-3.5% to 23.7%) | 10.1% (-2.9% to 23.8%) | 0.056 |
| 4h_atr2 | shark, minus barrier law | -6.1% | -3.7% (-12.7% to 5.6%) | -6.4% (-14.7% to 2.4%) | 0.954 |
| 4h_atr2 | no shark, minus barrier law | -13.0% | -2.8% (-11.6% to 6.0%) | -5.9% (-14.0% to 2.9%) | 0.160 |
| 4h_pct8 | legal impulses | 71 | 53 (43 to 64) | 60 (48 to 72) | 0.160 |
| 4h_pct8 | 3-5 divergence | 70.4% | 65.2% (55.6% to 74.5%) | 66.7% (58.2% to 75.5%) | 0.527 |
| 4h_pct8 | shark | 39.4% | 32.1% (22.2% to 41.7%) | 32.8% (24.5% to 42.2%) | 0.263 |
| 4h_pct8 | shark: reaches end of W4 before a new high | 53.6% | 55.6% (35.3% to 75.0%) | 50.0% (30.8% to 70.6%) | 0.762 |
| 4h_pct8 | no shark: the same | 37.2% | 42.1% (30.0% to 56.4%) | 38.5% (25.7% to 51.7%) | 0.894 |
| 4h_pct8 | difference | 16.4% | 12.9% (-9.6% to 35.9%) | 11.9% (-12.7% to 35.7%) | 0.739 |
| 4h_pct8 | shark, minus barrier law | 1.3% | -2.3% (-19.6% to 15.7%) | -5.9% (-23.7% to 12.6%) | 0.503 |
| 4h_pct8 | no shark, minus barrier law | -1.7% | -2.5% (-14.8% to 9.8%) | -4.6% (-16.1% to 6.3%) | 0.651 |

Multiple tests over all 132 rows:

| null | rows | p < 0.05 | q < 0.05 |
|---|---|---|---|
| shuffle | 132 | 29 | 0 |
| block | 132 | 29 | 0 |
| signflip | 132 | 23 | 0 |
| trendflip | 132 | 10 | 0 |

- **"3-5 divergence almost always" is not what the data shows,** on BTC or on random paths: 54-70% of legal impulses, against 55-68%. My reading: divergence is largely a side effect of a W5 that is short against W3.
- The shark appears as often as on random paths (31-52% against 32-52%).
- Sharks do reach the end of W4 before a new high more often than non-sharks on two of three scales, but random paths show the same gap (+9 to +13 points), because a short W5 leaves the barrier nearer. Minus the barrier law the gap mostly goes. The one larger reading, 4h_atr2 at +25 points, is p about 0.06 and comes with no effect on the other two scales.
- No outcome value shown. **[verified]**

## What this means for choosing a model

**The tension, named.** His October 23 note says a tool should never count waves for people, only hold the trader's own count to account. Today he asks for a model that learns waves from history. This report says both can stand, and how. History can be studied for what it does say, and that is mostly about volatility, slow trend and barriers. It does not supply a count: the rules leave a dozen legal ways to draw a typical pivot, and mechanical counts carry no edge at the stages that matter. So learn from history, and let the tool hold his counts to account, not make them.

| Option | What the measurements here say | Call |
|---|---|---|
| Rule engine plus statistic tables (master plan) | Works at any n. Its tables must be null-corrected: most rulebook windows equal the null, so they carry no evidence for a count. | Do it. As annotation and accountability, and as the source of checkable events. |
| Small calibrated model on barrier outcomes (logistic, then gradient boosting) | Trainable on swings at 1H and 15m, thin at 4H, not at D. The signal it can reach is what is listed below. | **Start here.** It is also the baseline every other option has to beat. |
| Deep model, supervised on wave labels | No degree has thousands of independent examples, and the label is not unique. | No. |
| Self-supervised sequence model on bars (JEPA, TS foundation models such as Kronos) | Unlabelled bars are plentiful, but 1,871 256-bar 15m windows are one market path. What is stable to learn is volatility and regime, which a simple model already gets (R2 0.35-0.56). Direction memory is near zero. | Only as a dated experiment against the baseline, on the same walk-forward. Nothing measured here predicts it will win. The bake-off and literature workers cover cost and evidence. |
| LLM reading the history (Opus) | Not tested here. The ambiguity in A4 means it could always find a legal count, on random paths too. | Narrator of the engine's JSON, as CLAUDE.md says. |

**What a model should be given** (each stable and measured here):

- Volatility state, which is the strongest predictable quantity. Every target and stop should be measured in it.
- Slow trend at 20-180 days (variance ratio 1.12-1.38). Keep this honest: non-overlapping sign tests are weak at every horizon up to 60 days, so it is a tilt, not a signal.
- Distance to the last same-scale pivot, for the step at 1.0.
- Direction of the leg: falls run 1.2-1.3 times faster than rises.
- The count state, only as a feature that must earn its place. On this report's evidence it adds little beyond the items above. Test it, do not assume it.

**What it should not be given as truth:** Fibonacci levels as probability sources. Keep them as his language for targets and invalidations. Probabilities come from the outcome model. Where a prior for a ratio is needed, use the null-corrected distribution, which here is close to the random-walk law.

**Targets and baselines.** Any target should be a barrier outcome (target before invalidation within H), with the driftless barrier law and a volatility-plus-trend model as the baselines. Several apparent edges in this report were barrier arithmetic, like the shark. Use trendflip as the standard null from here on: signflip and shuffle would have made the rule-legal excess look like a discovery.

**Sample discipline.** I have now looked at all the data, so everything here is exploration. The real out-of-sample test starts today: freeze the statistics that matter (the step at 1.0, linear 1.618, W4 on up-impulses, live mid-cycle up-structures, alternation) and score them on bars from 2026-10-31 on.

## Known weaknesses

- **A zigzag is not a person's count.** Each wave is one leg at one threshold and sub-waves are unchecked in A1 to A3, B and C. The results say the simplest mechanical form of the rules shows nothing beyond trend, volatility and a barrier. They do not say a skilled count adds nothing. A4 and A5 narrow this gap and do not close it. **[unknown]**
- **No gold set.** His hand-labelled swings (master plan, Phase 1) do not exist yet, so nothing here measures his reading.
- **Nulls keep and destroy different things.** Trendflip uses future bars for the trend, by design, which can absorb real structure at 1D. No null here models a stochastic drift regime as such.
- **Pools overlap.** Scales share swings and venues share a market. Family-wise tests handle the overlap within a timeframe; ladder p values do not fully.
- **Monte Carlo p has a floor** of about 0.002 at 1,000 paths and 0.007 at 300, which limits q values in small families.
- **Selection.** The barrier test and the 1.618 follow-up were designed after seeing the first tables. I ran them on eras and venues for that reason, but those eras had already been seen in pooled form.
- **The C3 live lean could be partly the live machine's minimum gap**, as C2 suggests. I did not rerun it with the gap changed.
- **Bitstamp's early years** have thin markets and exact ties, which is visible in several 2014-2017 results. Starting at 2018 would remove most of what stood out. Bitstamp 2014-2017 is kept because cycles-r1 uses it and because it shows the effect of the era.
- **Costs are ignored everywhere.** No result here is a backtest.

## Reproduce

From the repo root, no network. Total about 45 minutes on this machine. All scratch output goes to `/opt/data/cache/scratch/elliott_research_r1/emp/`.

```
export PATH=/opt/data/.local/bin:$PATH
RUN="uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical"
$RUN/check_tools.py
$RUN/a_census.py --paths 1000
$RUN/a2_legal_excess.py --paths 500
$RUN/a3_stages.py --paths 300
$RUN/a4_facts.py --paths 500
$RUN/a5_ambiguity.py --paths 200
$RUN/a6_subwaves.py --paths 300
for tf in 1d 4h 1h 15m; do $RUN/b1_fib_unconditional.py --tf $tf --paths 1000; done
$RUN/b1_fib_unconditional.py --report
$RUN/b1b_barrier.py --paths 300
$RUN/b1c_venues.py --paths 300
$RUN/b1d_scan.py --paths 300
for tf in 1d 4h 1h; do $RUN/b2_fib_impulse.py --tf $tf --paths 1000; done
$RUN/b2_fib_impulse.py --tf 15m --paths 500
$RUN/b2_fib_impulse.py --report
$RUN/b3_alternation.py --paths 300
$RUN/c_weekly_cycles.py --paths 1000 --workers 2 --weekday-paths 200
$RUN/c2_followups.py --paths 1000 --workers 2
$RUN/d_tdi_shark.py --paths 500
uv run --with numpy --with scipy --with numba --with matplotlib python research/model-options/spikes/empirical/plots.py
python3 research/model-options/spikes/empirical/make_tables.py
```

The result tables come straight from `make_tables.py`, which reads the result files. The two verdict tables (trainability, weekly hypothesis) and the prose quote those numbers by hand, and I checked them against the tables. Seeds are fixed in each script. The data grows every 15 minutes, so a rerun will move the last bars and a few counts slightly.

`common.py`, `zigzag.py`, `nulls.py` and `impulse.py` are the shared tools; `check_tools.py` tests them. Full results are in the scratch CSVs: `census_*.csv`, `a2_*.csv`, `a3_*.csv`, `a4_*`, `a5_ambiguity.csv`, `a6_subwaves.csv`, `b1_*.csv`, `b1b_*.csv`, `b1c_levels.csv`, `b1d_*.csv`, `b2_*.csv`, `b3_alternation.csv`, `c_*.csv`, `c2_*.csv`, `d_metrics.csv`, and `tables.md` holds every table including those left out here.

## Claims by status

**Verified, measured here:**
- All tools pass `check_tools.py`: causality on real bars, rule checker, leg law on a random walk, null paths, free-degree enumeration against brute force.
- The census, legal-rate, stage, ambiguity and sub-wave tables of section A.
- No Fibonacci level over-represented on swings beyond volatility-preserving nulls, and rulebook windows inside impulses at null rates.
- The step at 1.0 by era and venue at 15m and 1H. The spike at exactly 1.0 confined to old venues.
- All section C and D tables.

**Verified as measured, unconfirmed as real:** the linear 1.618 extension; W4 at 0.236-0.382 on up-impulses at 4H and 1D; live mid-cycle up-structures; mid-cycle tops holding worse; the 24-42 week spectral bump; the 1d_pct16 up-impulse from a live low.

**Assumed:** "jev" means JEPA. "Weekly cycle" means Camel's 24-42 week cycle. The degree mapping. The trend window. The TDI band width. Rules of thumb in the trainability table. My reading of the live swing density in C2. The model recommendations follow from the measurements but were not themselves tested here.

**Unknown:** Whether his own counts carry information the mechanical form lacks. Whether other assets differ from BTC. Whether any of this pays after costs. Whether the leads above survive the next few years.
