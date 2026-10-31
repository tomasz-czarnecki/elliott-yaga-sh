# Bake-off: does Opus count, does simple ML learn

Research round `elliott_research_r1`, worker BAKE, 2026-10-30. Scripts: [`spikes/bakeoff/`](spikes/bakeoff/README.md). Raw answers and CSVs: `/opt/data/cache/scratch/elliott_research_r1/bake/`. Tags: **[verified]** measured here, **[assumed]** a choice or premise not tested, **[unknown]** cannot be told yet.

**How I read "jev".** Most likely JEPA (Joint Embedding Predictive Architecture, LeCun, Meta), possibly a time-series foundation model such as Chronos, TimesFM or Kronos. None of those is run here: they need a GPU or rented compute, and they belong to the literature report, [`01-literature.md`](01-literature.md). This report tests the two options that run on this server today: "the Opus version" and "the math model version". It ends with what the results imply for JEPA, which is an inference, not a test.

## Summary

1. **Opus follows the rulebook far better than the master plan assumed.** 59 of 59 answers were valid JSON. 0 hard-rule breaks (sections 0 to 3) in 114 counts, where a random labelling breaks one 75% of the time. All 380 prices it cited from raw bars are real highs or lows. Its invalidations sit on a rule level 90% of the time on a pivot table, against 5% for a random price. **[verified]**
2. **But an Opus count is a story, not a measurement.** Ask again about the same chart and the state of the count (pattern, direction, wave reached) matches 62% of the time on a pivot table and 33% on raw bars. Pivot table against raw bars on the same chart: 30%. On today's 4H chart two runs say down to about $75-76k, one says up to $87-93k. **[verified]**
3. **It counts noise like it counts BTC.** On BTC's own bars shuffled into random paths it gave a primary count 15 times out of 15, confidence 0.43 against 0.46 on BTC, other/unclear 0.30 against 0.27. It never refused, and it never said the data might not be real. It was more stable from run to run on noise than on BTC. **[verified]**
4. **It cannot be tested on history, because it remembers history.** With dates moved and prices rescaled it still named the period in 17 of 18 calls on the three famous windows, and several times it worked out the hidden price factor ("a scale near 0.0748"; true value 0.0748). With real dates all 3 runs switched to the count that fits what came next, and all 3 of those primaries break the section 4 time minimum (one says so). "Let Opus run through the whole history and learn" cannot produce evidence of anything. **[verified]**
5. **The rules are not what decides a count.** A BTC window has 200 to 1,100 rule-legal readings, about 20 distinct states, with both up and down structures in every window, and a random path has at least as many. Opus picks one or two states, and nothing shows it picks well: on its own target and invalidation levels, its probabilities scored Brier 0.181 against 0.171 for volatility alone (lower is better; few windows, so a hint and not a result). **[verified]**
6. **Simple ML: volatility is the floor, and Fib, TDI and rule flags add nothing to it.** Reaching the 1.618 extension before the origin happens 24-31% of the time. A formula with no training, from distances and volatility alone, gets AUC 0.63 to 0.72, and the same or better on random paths. Adding Fib and leg features, TDI or rule flags: 0 of 60 comparisons beat the null. Feeding logistic regression everything makes it worse and badly overconfident. **[verified]**
7. **No Fibonacci structure showed up.** The 0.5-0.618 pullback zone does no better than others once volatility is accounted for. Moves do not stop at Fibonacci multiples more often than random paths do. BTC's own extension curve (1.618 reached 24-31% of the time, 2.618 11-15%) comes out almost the same from random paths built from 20-day blocks of its own days. **[verified]**
8. **One real lead, on your weekly-cycle idea.** Inside the live weekly window (day 168 to 294 after the last weekly low), setups reached 1.618 only 14-19% of the time against 27-33% outside, with volatility saying no difference. It showed at every scale, and on 2013-2016, which I had not looked at when I wrote the test down. At both 4H scales the flag alone improved walk-forward Brier more than any of 600 random paths did. It is a warning about late-cycle follow-through, not an edge: setups outside the window do not beat random paths. **[verified as measured, found by exploring, unconfirmed live]**
9. **Cost.** Opus: $0.22 per call at list price (no per-call charge on the Max plan), 83 s median. One call per zigzag pivot over the history: about $250 and 9 hours at 3 parallel calls. One call per 1H bar: about $29,000. Simple ML: about a minute of CPU for BTC, a few seconds per random path, no GPU. **[verified]**
10. **What this means.** The learner should be simple statistics on a deterministic engine's output, because that is the only option here that can be tested causally and against random paths. Opus belongs at the edges: narrating, reviewing, turning rules into code. JEPA or any bigger model should only be tried as one more feature column in this same test, against this same null.

## A. Opus as the wave counter

### What was built

| Piece | File | What it does |
|---|---|---|
| Causal zigzag | `zigzag.py` | A swing is a pivot only after a reversal of k x ATR(14) in log price. `conf_i` is the bar whose close first shows it. High or low first inside a bar comes from `hl_order`. |
| Rule checker | `rules.py` | Sections 0 to 3: impulse, diagonal, zigzag, flat, triangle and combination rules, each with its section. Names the rule a count breaks. Length rules are lenient: a count breaks one only if it does on both linear and log scale. |
| Rule levels | `rules.py` | Where the book puts the invalidation and the next targets, given the last printed label. |
| Enumerator | `enumerator.py` | Every rule-legal reading of a pivot window, with nesting (a wave may span several legs if those legs parse as what it claims to be). Strict: a 5 must show 1, 5 or 9 legs. Loose: it may also show 3, a 5 whose second correction stayed under the threshold. |

What the checker cannot see: whether a single zigzag leg is a 3 or a 5, order blocks, or the TDI rules. Those are not claimed. The section 4 time minimum (a correction takes at least 25% of the time of the wave it corrects) is reported separately, because section 1 calls it a convention and section 4 calls it a rule.

### The test

Each call: `claude -p "<prompt>" --model opus --effort high --tools "" --output-format json`, run from the scratch folder with no tools. It resolved to `claude-opus-5-5`. **[verified]**

The prompt holds the whole compact rulebook, the chart, and a strict JSON shape: primary and alternate count with labels mapped to pivots or bars, degree, invalidation, target zone, P(target before invalidation within H bars), confidence, an other/unclear share, plus two free fields: `recognised_period` and `data_note`. It may set `primary` to null. BTC and random windows get the same text, and nothing mentions random paths.

| Window | TF | Real dates | Kind | Bars | Pivots | Why |
|---|---|---|---|---|---|---|
| D1 | 1D | 2020-03-01 to 2021-04-25 | bull, famous | 420 | 19 | crash low to the April 2021 top and the first drop |
| D2 | 1D | 2021-10-25 to 2022-12-15 | bear, famous | 416 | 20 | November 2021 top to the 2022 low |
| D3 | 1D | 2015-01-01 to 2015-11-20 | messy | 323 | 15 | base after the 2015 low; honest answer: unclear |
| H1 | 4H | 2017-10-20 to 2017-12-22 | bull, famous | 378 | 12 | the 2017 blow-off and the first drop |
| H2 | 4H | 2025-10-02 to 2025-12-01 | bear | 360 | 11 | October 2025 top to the November low |
| H3 | 4H | 2023-06-20 to 2023-08-20 | messy | 366 | 18 | tight range, sudden drop at the end; honest answer: unclear |
| L1 | 4H | 2026-08-10 to 2026-10-30 | today | 486 | 19 | after the model's training data; pivot table only; no future to score yet |
| N1 | 1D | D1's bars shuffled | random | 420 | 33 | same bars, same net move, no time order |
| N2 | 4H | H2's bars shuffled | random | 360 | 18 | same |
| N3 | 1D | D3's bars shuffled | random | 323 | 26 | same; pivot table only |

Budget: 60 calls, all used, 0 transport errors. 1 smoke test, 36 on D1-H3 (pivot table and raw bars, 3 runs each), 3 on L1, 15 on the random windows, 3 on D1 with real dates, 2 chart images. **[verified]**

Every window is **masked**: prices times a hidden constant, dates moved by years. Without that the model can recall what came next, and the random windows could not pass as BTC. Window edges do not sit on the exact top or low, because a window ending on the famous top hands over the answer. Each random path is the first draw of a fixed seed, never redrawn.

### Rule following: better than expected

| Group | Counts | Any hard break, sec 0-3 | W2 or W4 under the 25% time minimum, sec 4 (primary only) | Guideline flag | Price or pivot not on the chart |
|---|---|---|---|---|---|
| BTC, pivot table | 42 | 0% | 21% (19%) | 36% | 0% |
| BTC, raw bars | 36 | 0% | 56% (56%) | 61% | 0% |
| Random, pivot table | 18 | 0% | 28% (33%) | 78% | 0% |
| Random, raw bars | 12 | 0% | 42% (50%) | 92% | 0% |
| BTC with real dates, pivot table | 6 | 0% | 83% (100%) | 100% | 0% |

- 59 of 59 answers parsed as strict JSON with no repair, and every set of probabilities summed to 1. Opus never used the null option. **[verified]**
- 824 labels checked, 0 hard breaks. A random labelling of the same pattern and length on the same pivot table breaks a hard rule 75% of the time, so zero is a real result. **[verified]**
- Raw bars: all 380 cited prices are exact highs or lows of the cited bar. **[verified]**
- The master plan says LLMs "can violate hard rules or invent levels". On this model, at this effort, with the rulebook in the prompt, that did not happen. The plan's conclusion still holds, for the reasons below. **[verified]**
- The rule it does break is the time minimum, in about half of its raw-bar primaries, sometimes with a line admitting it in `reasoning` or `data_note`. **[verified]**
- It reads data closely. On D3's raw bars it spotted the real January 2015 Bitstamp halt ("zero range, likely an exchange halt"), a quirk noted in `CLAUDE.md`. **[verified]**
- One degree down: 21% of its pivot-table counts on BTC lump legs into a wave that do not parse as that wave even on the loose grammar (48% on the strict one). H3 is the clearest case: a "W1" over five legs that do not form a five. The book calls this the top beginner error. **[verified]**

**Rulebook math, with a chance control:**

| Group | Counts | Invalidation within 0.5% of a rule level | A random price would | Target zone holds a rule level | Both zone edges within 0.3% of one | A random edge would (one edge) |
|---|---|---|---|---|---|---|
| BTC, pivot table | 42 | 90% | 5% | 93% | 76% | 16% |
| BTC, raw bars | 36 | 75% | 7% | 97% | 67% | 17% |
| Random | 30 | 77% | 6% | 100% | 50% | 16% |

The misses I read by hand were sub-degree levels with correct arithmetic and a section cited (for example a contracting-diagonal limit worked out as 1157.11 + 247.88). They are gaps in my candidate list rather than errors. I checked the arithmetic of the H2 example below by hand and it is exact. **[verified on the examples read; the rest not read one by one]**

### Repeatability: the weak point

| Group | Condition | Windows | Same state | Same next move | Label overlap | Invalidation within 1% | Target zones overlap |
|---|---|---|---|---|---|---|---|
| BTC | pivot table, run to run | 7 | 62% | 71% | 0.61 | 57% | 71% |
| BTC | raw bars, run to run | 6 | 33% | 67% | 0.46 | 56% | 61% |
| Random | pivot table, run to run | 3 | 78% | 100% | 0.58 | 56% | 89% |
| Random | raw bars, run to run | 2 | 50% | 100% | 0.73 | 50% | 100% |
| BTC | pivot table against raw bars | 6 | 30% | 69% | 0.41 | 43% | 39% |
| Random | pivot table against raw bars | 2 | 0% | 50% | 0.12 | 17% | 33% |

State = pattern family, direction and last printed wave. All pairs of 3 runs per window. **[verified]**

- Full agreement across 3 runs (same state and same next move): 2 of 13 BTC cells (H1 and H2 on the pivot table), 3 of 5 random cells. Stability is not a sign of signal. **[verified]**
- Changing only the format of the same data changes the count most of the time. Part of that is fair, since raw bars show swings the pivot table hides. But the run-to-run row on one fixed format is low too, and a measuring instrument should not do that. **[verified]**

### How ambiguous a window really is

| Window | Kind | Pivots | Readings, one leg per wave | Strict | Loose | Nested fillings, loose | States | Up / down structures | Invalidation levels | Opus in the strict / loose list | Distinct primary states from Opus |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D1 | bull | 19 | 32 | 852 | 1,096 | 1,419,319 | 20 | 1014 / 82 | 55 | 6 / 6 of 6 | 1 |
| D2 | bear | 20 | 27 | 604 | 742 | 563,718 | 22 | 137 / 605 | 64 | 4 / 5 of 6 | 2 |
| D3 | messy | 15 | 27 | 372 | 394 | 30,700 | 20 | 296 / 98 | 49 | 4 / 6 of 6 | 2 |
| H1 | bull | 12 | 32 | 198 | 233 | 1,958 | 20 | 187 / 46 | 32 | 3 / 5 of 6 | 1 |
| H2 | bear | 11 | 30 | 180 | 197 | 3,798 | 19 | 34 / 163 | 21 | 6 / 6 of 6 | 1 |
| H3 | messy | 18 | 24 | 838 | 851 | 952,793 | 22 | 203 / 648 | 52 | 1 / 1 of 6 | 2 |
| L1 | today | 19 | 16 | 810 | 822 | 951,858 | 20 | 406 / 416 | 91 | 5 / 5 of 6 | 2 |
| N1 | random | 33 | 30 | 7,160 | 7,630 | 1.7e10 | 22 | 6621 / 1009 | 121 | 4 / 6 of 6 | 2 |
| N2 | random | 18 | 27 | 683 | 707 | 1,225,863 | 21 | 123 / 584 | 52 | 6 / 6 of 6 | 1 |
| N3 | random | 26 | 31 | 3,285 | 3,343 | 8.0e8 | 21 | 1421 / 1922 | 176 | 1 / 2 of 6 | 1 |

A reading is a top-level structure whose last label sits on the last pivot. Opus lists: last segment only, primary and alternate of the 3 pivot-table runs. **[verified]**

- Every window, bull or bear, famous or not, has legal structures in both directions. Rules eliminate; here they do not get close to deciding. **[verified]**
- Opus mostly picks from the legal list (34 of 42 BTC counts on the loose list, 29 of 42 on the strict one) and invents nothing. It settles on 1 or 2 of about 20 states. **[verified]**
- On the whole 4H history, a 12-pivot window has a median of 100 strict readings on BTC, against 111 (shuffled) and 98 (block) on random paths, with 19, 18 and 18 distinct states. The share of 6-pivot runs that form a legal impulse is higher on BTC: 9.2% against 5.4% and 7.2%, above both nulls' ranges. The empirical report tests that excess properly, with a trend-preserving null. **[verified, `ambiguity_null.py`, 20 paths each]**

### Noise: the key test

| Group | Calls | Mean confidence | Mean other/unclear | Mean P(target first) | Refused | Said the data might be fake |
|---|---|---|---|---|---|---|
| BTC, recognised the period | 22 | 0.46 | 0.28 | 0.52 | 0 | 0 |
| BTC, did not | 17 | 0.46 | 0.27 | 0.47 | 0 | 0 |
| BTC, all | 39 | 0.46 | 0.27 | 0.50 | 0 | 0 |
| Random paths | 15 | 0.43 | 0.30 | 0.54 | 0 | 0 |

| Matched pair | Confidence, BTC / shuffled | Other, BTC / shuffled |
|---|---|---|
| D1 / N1 | 0.45 / 0.41 | 0.28 / 0.33 |
| H2 / N2 | 0.44 / 0.45 | 0.28 / 0.28 |
| D3 / N3 | 0.43 / 0.43 | 0.27 / 0.28 |

- Yes, it confidently counts waves in noise. It never refused, and it gave the same kind of answer with the same kind of numbers. **[verified]**
- There is a small gap: confidence separates BTC from random calls with AUC 0.71, and the other share with AUC 0.67. Most of it comes from one of three pairs (D1/N1), and with 3 random paths the calls are not independent. The two ranges overlap almost fully (0.40-0.55 on BTC, 0.40-0.50 on random). It is not usable as a detector. **[verified]**
- It did notice odd things on random paths: "unusually wide for daily BTC", "several one-bar 20% moves". It treated them as a limit on reading sub-waves and never as a reason to doubt the structure. It named no period for any of the 15 random calls: it did not take the shape for a known chart, and it counted it anyway. **[verified]**

### Memory: why history cannot test it

| Window | Named the period, of 6 masked calls |
|---|---|
| D1 (2020-21) | 6, all correct |
| D2 (2021-22) | 6, all correct |
| H1 (2017) | 6: 5 correct, 1 wrong ("possibly early 2013") |
| D3 (2015) | 3, all correct |
| H2 (2025) | 1, correct |
| H3 (2023 range) | 0 |
| L1 (today, 3 calls) | 0 |
| N1, N2, N3 (15 calls) | 0 |

Its own words, with dates moved and prices rescaled: "pivots match with a scale near 0.0748" (D2, true factor 0.0748). "crash low bar 12 is 2020-03-13, price scale about 0.146" (D1, true 0.1464). "scale about 10.5x; I recall later prices, so my primary choice and probabilities may be biased" (D3, true 10.45). It is honest about this. That does not remove the problem. **[verified]**

**The same chart, D1, under four presentations:**

| Presentation | Primary | Next move, each run | Primary's W4 under the time minimum |
|---|---|---|---|
| Masked, pivot table, 3 runs | W3 at pivot 15, W4 still open as a flat | down, down, up | 0 of 3 |
| Masked, raw bars, 3 runs | five complete with A down (2), W4 after a long W3 (1) | up, down, up | 2 of 3 |
| Masked, chart image, 1 run | five complete, A down | down | 1 of 1 |
| Real dates, pivot table, 3 runs | five complete at $64,895, A down | down, down, down | 3 of 3 |

With real dates, all 3 runs give the count that fits what came next, and all 3 of those primaries break the time minimum. One says so: "Primary W4 (14 bars) fails §4 time minimum, capping confidence". Another says "later price is known to me". Memory beats the rulebook here. **[verified]**

The only clean test uses bars after the model's training data. At its June 2026 cutoff that is about 4 months of history today, L1 is inside it, and it would reset with every new model. **[assumed: the cutoff is the one stated for this model]**

### Forecast check: its own target against its own invalidation

Scored on the window's own future (H bars; real bars for BTC, shuffled for random). The volatility column is the barrier formula of part B, applied to Opus's own levels. Timeouts count as not reached.

| Group | Calls | Windows | Target first | Opus P | Volatility P | Brier Opus | Brier volatility |
|---|---|---|---|---|---|---|---|
| BTC, recognised | 22 | 5 | 77% | 0.52 | 0.49 | 0.186 | 0.202 |
| BTC, not recognised | 13 | 3 | 15% | 0.43 | 0.39 | 0.173 | 0.119 |
| BTC, all masked | 35 | 6 | 54% | 0.48 | 0.45 | 0.181 | 0.171 |
| Random | 15 | 3 | 33% | 0.54 | 0.50 | 0.200 | 0.164 |

Volatility alone beats Opus's probabilities in every group except the one where Opus recognised the chart. The 77% against 15% could be memory, or those windows could simply have had bigger moves after them, and with 3 to 6 windows it cannot be separated. Treat all of this as a hint. Like your 30-40 trades over three months, this many windows cannot separate skill from luck. **[verified as measured; too few windows to conclude]**

### Examples

**Good.** H2, pivot table, not recognised. All 3 runs gave the same skeleton and the same levels. It also names what it rejected: "Dead: W3 at p7 (shortest, W4 overlap)".

```json
{"segments":[{"pattern":"impulse","direction":"down","degree":"Minor",
  "labels":[{"label":"0","pivot":0},{"label":"1","pivot":1},{"label":"2","pivot":4},{"label":"3","pivot":9},{"label":"4","pivot":10}]}],
 "current_wave":"5","next_move":"down",
 "invalidation":{"price":10996.56,"side":"above","rule":"S1 R: W4 never enters W1 territory (W1 low)"},
 "target_zone":{"low":7472.2,"high":8394.97,"rule":"S1 pull 0-1-4: W5 at 0.618 to 1.0 of W1"},
 "p_target_before_invalidation":0.42,"confidence":0.45}
```

The arithmetic is exact: W1 = 2415.57, from W4 at 9887.77 that gives 8394.97 and 7472.20. In the next 150 bars price reached neither level.

**Bad: a confident count of noise.** N2 is H2's bars shuffled. All 3 runs give this, with P(target first) up to 0.70 and a fluent argument from the rules.

```json
{"segments":[{"pattern":"zigzag","direction":"down","degree":"intermediate",
  "labels":[{"label":"0","pivot":10},{"label":"A","pivot":11},{"label":"B","pivot":14},{"label":"C","pivot":17}]}],
 "current_wave":"C","next_move":"down",
 "invalidation":{"price":273757.73,"side":"above","rule":"§1 sub-W4 of C cannot enter sub-W1 territory (pivot 15)"},
 "target_zone":{"low":226000.0,"high":233821.0,"rule":"§3 pull 10-11-14 ext 1.236; §1 pull 14-15-16 ext 1.618"},
 "p_target_before_invalidation":0.7,"confidence":0.45}
```

"Corrective preferred because W3 barely exceeds W1 and C already reached 1:1." This is an unbroken chain of correct rule reasoning about a random path. The fluency says nothing about whether structure is there.

**Bad: the same chart, opposite calls.** L1, today's chart, same prompt, same data. Prices are masked here; real USD in the table further down.

```json
{"pattern":"flat_regular","labels":"... A at pivot 12, B at 17, C at 18","current_wave":"C","next_move":"down",
 "invalidation":{"price":13607.98,"side":"above"},"target_zone":{"low":12015.0,"high":12210.0},"p_target_before_invalidation":0.7,"confidence":0.5}
{"pattern":"flat_regular","labels":"... A at pivot 16, B at 17, C at 18","current_wave":"C","next_move":"up",
 "invalidation":{"price":12015.42,"side":"below"},"target_zone":{"low":14013.93,"high":14933.0},"p_target_before_invalidation":0.25,"confidence":0.4}
```

Note what happened: the invalidation of the first run sits above where the second expects to go, and the second run's invalidation sits at the first run's target. Both are rule-legal.

### Chart image

`claude -p` with a file path gives the model nothing when tools are off. The image does go through as a base64 block with `--input-format stream-json --output-format stream-json --verbose`. **[verified: `llm_image.py`]**

Two calls, one each on H2 and D1 (chart from `render_chart.mjs`: candles on a log scale, RSI below). Both returned valid JSON with no hard break. It read levels well: 25 labels, mean price error 0.1%, worst 0.22%. On D1 it recognised the period from the picture alone ("inferred from chart shape"). On H2 it gave a different primary from the 3 pivot-table runs: a finished zigzag and a new impulse up, in W2. So a third format gave a third reading. With 2 calls this is a capability check, not a statistic. **[verified]**

### Cost

| Calls | Median s | Slowest s | Mean output tokens | Of which thinking | Mean USD, list | Total USD, list |
|---|---|---|---|---|---|---|
| 59 | 83 | 138 | 7,711 | 6,805 | $0.22 | $12.92 |

Pivot table $0.20 and 74 s, raw bars $0.24 and 89 s, image $0.26 and 69 s. The first call with a cold cache cost $0.41. The dollar figures are what the CLI reports at list price; on the Max plan there is no per-call charge, only usage limits. 60 calls at 3 in parallel, with two other agents running, hit no limit. How far the limit stretches: **[unknown]**.

| Job | Calls | USD at list | Wall time at 3 parallel |
|---|---|---|---|
| One call per 4H zigzag pivot, whole history | 1,117 | about $250 | about 9 hours |
| One call per 4H bar | 33,313 | about $7,300 | about 11 days |
| One call per 1H bar | 133,254 | about $29,000 | about 43 days |
| Live hourly loop, one year | 8,760 | about $1,900 | keeps up |

### Opus on today's chart, for the forward log

4H, last bar 2026-10-29 20:00 UTC, close $77,793, real USD. Weekly and daily cycle state is in `research/cycles-r1.md`. This is a test artefact, not a call.

| Run | Role | State | Next | Confidence | Invalidation | Target zone | P(target first) |
|---|---|---|---|---|---|---|---|
| 1 | primary | combination, Y running | down | 0.50 | $84,843 | $74,911 to $76,109 | 0.70 |
| 1 | alternate | impulse up, W2 | up | 0.25 | $62,470 | $87,374 to $89,375 | 0.35 |
| 2 | primary | flat, C running | down | 0.50 | $84,843 | $74,911 to $76,127 | 0.70 |
| 2 | alternate | combination up, X | up | 0.20 | $62,470 | $93,104 to $102,618 | 0.20 |
| 3 | primary | flat, C at its end | up | 0.40 | $74,913 | $87,374 to $93,104 | 0.25 |
| 3 | alternate | combination, Y running | down | 0.35 | $84,843 | $72,423 to $75,360 | 0.55 |

## B. Simple machine learning

### Outcome and scale

**Outcome.** At each confirmed zigzag pivot P2, with P0 and P1 the two pivots before it: from the close of the bar that confirmed P2, does price reach T = P2 + 1.618 x |P1 - P0| before it breaks P0, within H bars? Up and down setups are mirrored. Timeouts count as not reached, as the brief words it. If P2 already passed P0 there is no legal 0-1-2, and the setup is left out and counted. A bar touching both barriers is settled by `hl_order`; if unknown, the origin goes first.

**Scale.** Main: 4H, k = 4 x ATR(14), median leg 11.6% over the whole history and 10.1% since 2020, just under the 4H move size of section 5 (12-15%). k = 5 would match it exactly but leaves too few setups to walk forward. H = 150 bars (25 days), about 2.236 x the 90th percentile leg. Also run, all reported, none chosen by result: 4H k = 3, 4H k = 6, 1H k = 6, and the main scale with a log target. **[assumed: the scale is a judgement; verified: the leg sizes]**

| Scale | Pivots | Origin already passed | Setups, 2013-03 on | Out of sample, 2017 on | Target first | Origin first | Timeout | Base rate, all | Base rate, 2017 on |
|---|---|---|---|---|---|---|---|---|---|
| 4H k4 (main) | 1,117 | 405 | 516 | 380 | 162 | 170 | 184 | 31.4% | 29.5% |
| 4H k3 | 1,895 | 742 | 869 | 634 | 236 | 298 | 335 | 27.2% | 24.9% |
| 4H k6 | 569 | 201 | 244 | 159 | 68 | 83 | 93 | 27.9% | 25.8% |
| 1H k6 | 2,299 | 799 | 966 | 735 | 232 | 340 | 394 | 24.0% | 23.9% |
| 4H k4, log target | 1,117 | 405 | 522 | 382 | 149 | 174 | 199 | 28.5% | 25.9% |

The base rate moves a lot from year to year. Main scale, 2017 to 2026: 45, 22, 36, 33, 16, 29, 38, 23, 26, 23 percent. Ignoring timeouts, target against origin is about 41-49%. About 44% of 0-1-2 candidates at this scale already broke the origin. **[verified]**

### Features and models

All features are known at the close of the deciding bar. `check_causal.py` truncates the data at 6 random cuts, rewrites the future with garbage, and confirms nothing changes; a planted future feature takes AUC from 0.68 to 0.99, so the pipeline would show a leak. **[verified]**

| Group | Features |
|---|---|
| V, volatility | Barrier probability, distances to target and origin in sigma, log volatility, volatility regime |
| D, trend | Direction, 14-day and 90-day returns, against the 90-day mean, its slope, distance from the all-time high |
| F, Fib and legs | Retracement (linear, log), distance to 0.382, 0.5, 0.618, 0.786, zone flags, time ratio and time-rule flag, leg speed, leg size in ATR, against the prior leg, engulfs the prior swing, origin is a 100-bar extreme |
| T, TDI | RSI(11) at the bar, at P1 and at P2, aligned to direction; P2 in the support or resistance zone; P1 through 70; hidden divergence 0-2; regular divergence at P0; band and signal position |
| R, rule flags | Legal opposite five before P0; P2 as a legal W4; as a legal C of a zigzag or flat; number of W4 and W2 readings; sub-leg counts one degree down (k/3); do the legs parse as a 5 and a 3 |
| C, cycles | From `ewave.cycles` live state, last closed day: phase since the last daily, weekly and 4-year low; in the timing window; top position so far; failed flag; direction x phase; P2 at a cycle low; origin aligned with low or midpoint |

The **barrier baseline**: the chance that a driftless random walk with today's volatility (14-day realised) hits the target before the origin within H bars, from the two-barrier formula, checked against Monte Carlo. No training at all. It is run raw and recalibrated on past data.

Models: logistic regression (L2, C = 0.1, standardised) and LightGBM (200 trees, depth 3, 7 leaves, min 25 per leaf, fixed in advance). Walk-forward by year, 2017 onward. Training uses only setups whose label was known before 1 January of the test year, so a setup still open at the turn of the year cannot leak. **[verified]**

Null paths: the same pipeline, same settings, on BTC's own 4H or 1H bars from 2013-03 reshuffled (`shuffled`: no time order at all; `block`: 20-day blocks on day boundaries, which keeps volatility clustering). 40 paths of each per main scale, 20 for the side variants. Cycle features are recomputed on each path. **[verified]**

### Results

| Scale | n | Hit rate | Base rate | Barrier, raw | Logistic V | Logistic V+D | Logistic all | LightGBM V+D | LightGBM all | AUC barrier | AUC logistic V | AUC LightGBM all |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4H k4 | 380 | 29.5% | 0.2105 | 0.2019 | **0.1942** | 0.1981 | 0.2300 | 0.2041 | 0.2057 | 0.661 | 0.713 | 0.646 |
| 4H k3 | 634 | 24.9% | 0.1894 | **0.1695** | 0.1741 | 0.1738 | 0.1757 | 0.1849 | 0.1738 | 0.698 | 0.719 | 0.719 |
| 4H k6 | 159 | 25.8% | 0.1936 | 0.1926 | **0.1811** | 0.1828 | 0.2217 | 0.1950 | 0.1931 | 0.626 | 0.731 | 0.670 |
| 1H k6 | 735 | 23.9% | 0.1824 | **0.1611** | 0.1634 | 0.1640 | 0.1742 | 0.1675 | 0.1619 | 0.721 | 0.729 | 0.722 |
| 4H k4, log target | 382 | 25.9% | 0.1954 | **0.1779** | 0.1791 | 0.1828 | 0.2087 | 0.1937 | 0.1930 | 0.695 | 0.743 | 0.655 |

Out-of-sample Brier, lower is better; best of these columns in bold. **The volatility-only models win or tie at every scale among these columns.** A formula with no training is the best of them at 3 of 5. The one model that beats them anywhere in the full tables adds cycles at 4H k3 (logistic 0.1686). **[verified]**

Main scale, full ladder:

| Model | Brier | Log loss | AUC | ECE | Calibration slope |
|---|---|---|---|---|---|
| Base rate (past mean) | 0.2105 | 0.6123 | 0.529 | 0.051 | 0.51 |
| Barrier, raw formula | 0.2019 | 0.6385 | 0.661 | 0.081 | 0.36 |
| Barrier, recalibrated | 0.2000 | 0.5832 | 0.671 | 0.080 | 1.19 |
| Logistic: volatility | 0.1942 | 0.5706 | 0.713 | 0.088 | 1.84 |
| Logistic: + trend | 0.1981 | 0.5784 | 0.684 | 0.094 | 1.19 |
| Logistic: + Fib and legs | 0.2034 | 0.5900 | 0.660 | 0.091 | 0.88 |
| Logistic: + TDI | 0.2045 | 0.5923 | 0.649 | 0.087 | 0.87 |
| Logistic: + rule flags | 0.2059 | 0.5956 | 0.645 | 0.089 | 0.77 |
| Logistic: + cycles | 0.2130 | 0.6164 | 0.642 | 0.102 | 0.52 |
| Logistic: everything | 0.2300 | 0.6646 | 0.620 | 0.147 | 0.33 |
| LightGBM: volatility | 0.2008 | 0.5825 | 0.680 | 0.092 | 0.94 |
| LightGBM: + trend | 0.2041 | 0.5930 | 0.675 | 0.091 | 0.80 |
| LightGBM: + Fib and legs | 0.2047 | 0.5939 | 0.670 | 0.103 | 0.80 |
| LightGBM: + TDI | 0.2041 | 0.5923 | 0.665 | 0.094 | 0.81 |
| LightGBM: + rule flags | 0.2042 | 0.5936 | 0.670 | 0.095 | 0.78 |
| LightGBM: + cycles | 0.2085 | 0.6051 | 0.643 | 0.079 | 0.59 |
| LightGBM: everything | 0.2057 | 0.5977 | 0.646 | 0.072 | 0.65 |
| LightGBM: everything, Platt | 0.2054 | 0.5990 | 0.610 | 0.047 | 0.58 |

### Does any group add anything, against random paths?

Gain in Brier x 1000 when a group is added to volatility + trend. Positive is better. Bold: above the 95th percentile of both nulls. (s) or (b): above one of them.

| Scale | Model | Fib and legs | TDI | Rule flags | Cycles | Everything |
|---|---|---|---|---|---|---|
| 4H k4 | logistic | -5.4 | -6.4 | -7.8 | -14.9 | -31.9 |
| 4H k4 | LightGBM | -0.6 | +0.0 | -0.0 | -4.4 | -1.5 |
| 4H k3 | logistic | -2.9 | -2.8 | -3.0 | **+5.3** | **-1.8** |
| 4H k3 | LightGBM | -1.3 | -2.5 | -1.3 | **+13.7** | **+11.1** |
| 4H k6 | logistic | -18.1 | -9.7 | -12.4 | -1.3 (b) | -39.0 |
| 4H k6 | LightGBM | -1.2 | +5.3 | +0.5 | +3.9 | +1.9 |
| 1H k6 | logistic | -2.4 | -1.8 | -3.7 | -4.9 | -10.1 |
| 1H k6 | LightGBM | +1.2 | +1.8 | +1.0 | **+2.5** | +5.6 (s) |
| 4H k4, log target | logistic | -4.5 | -8.3 | -7.0 | -10.1 | -25.9 |
| 4H k4, log target | LightGBM | -0.1 | +1.1 | +0.9 | -0.5 | +0.7 |

Typical null, main scale: LightGBM steps have a median near 0 and a 5-95% range of about +-5 for Fib, TDI and rules, about +-8 for cycles. Logistic steps have a negative median (-3 to -23), because extra features hurt a small sample on any path. Row by row in `ml_report.py`.

- **Fib and legs, TDI, rule flags: 0 of 60 comparisons above the null's 95th percentile.** Chance alone gives about 3. **[verified]**
- **Cycles: the only group that ever stands out.** All 12 of the 100 flags involve it (chance gives about 5). Clear at 4H k3 and in one model at 1H, absent at the main scale. Testing the whole group of 16 features dilutes it; the targeted test below does not. **[verified]**
- Trend on top of volatility adds nothing reliable either: -3.9, +0.2, -1.7, -0.6 (logistic), -3.3, -1.5, -5.1, +4.0 (LightGBM). **[verified]**

### AUC is not evidence of structure

| Model, main scale | BTC AUC | Shuffled, median (5-95%) | Block, median (5-95%) |
|---|---|---|---|
| Barrier, raw formula | 0.661 | 0.746 (0.713 to 0.774) | 0.697 (0.645 to 0.747) |
| Logistic, volatility | 0.713 | 0.740 (0.712 to 0.778) | 0.706 (0.659 to 0.763) |
| Logistic, everything | 0.620 | 0.688 (0.621 to 0.722) | 0.639 (0.595 to 0.716) |
| LightGBM, volatility | 0.680 | 0.722 (0.679 to 0.756) | 0.687 (0.642 to 0.743) |
| LightGBM, everything | 0.646 | 0.710 (0.659 to 0.749) | 0.672 (0.634 to 0.723) |

AUC 0.7 sounds like skill. It is arithmetic: a target close to the entry and an origin far away gets hit more often, on any path. Random paths score the same or better, so any model claiming AUC around 0.7 on this kind of target has shown nothing yet. **[verified]**

### Calibration

Main scale, out of sample. Mean predicted against hit rate:

| Predicted | Barrier, recalibrated: n, hit | Logistic, everything: n, hit | LightGBM, everything: n, hit |
|---|---|---|---|
| 0.0-0.1 | 19, 0.00 | 41, 0.15 | 15, 0.07 |
| 0.1-0.2 | 27, 0.15 | 70, 0.23 | 48, 0.12 |
| 0.2-0.3 | 43, 0.23 | 48, 0.29 | 85, 0.24 |
| 0.3-0.4 | 101, 0.23 | 47, 0.28 | 87, 0.33 |
| 0.4-0.5 | 141, 0.35 | 48, 0.27 | 63, 0.30 |
| 0.5-0.6 | 49, 0.53 | 47, 0.34 | 36, 0.39 |
| 0.6-0.7 | | 37, 0.38 | 30, 0.53 |
| 0.7-0.8 | | 28, 0.46 | 10, 0.40 |
| 0.8-0.9 | | 12, 0.50 | 6, 0.50 |
| 0.9-1.0 | | 2, 0.50 | |

- The barrier runs a few points high in the middle, because hit rates fell after the training years (2013-2016 are richer). It keeps its order and never claims more than it can deliver. **[verified]**
- Logistic with everything is badly overconfident: when it says 0.75, price delivers 0.46; slope 0.33. LightGBM is better but flat above 0.6; slope 0.65. Neither should be read as a probability. **[verified]**

### Feature importance

Permutation importance by group, out of sample: log loss increase x 1000 when the group is shuffled inside each test year, LightGBM all / logistic all.

| Group | 4H k4 | 4H k3 | 4H k6 | 1H k6 |
|---|---|---|---|---|
| V, volatility | +45.1 / +73.9 | +37.4 / +56.8 | +51.4 / +69.9 | +71.1 / +70.8 |
| D, trend | +4.5 / +18.6 | -0.7 / +15.4 | +3.2 / +13.8 | +0.9 / +9.1 |
| F, Fib and legs | -1.4 / +15.2 | +24.8 / +18.3 | +1.7 / +7.5 | +17.1 / +13.2 |
| T, TDI | +15.1 / -10.9 | +5.0 / +16.6 | -1.3 / -20.7 | +7.3 / -1.6 |
| R, rule flags | +0.4 / -1.4 | +1.0 / +17.7 | +1.5 / +10.7 | -1.1 / +7.1 |
| C, cycles | -1.1 / +28.1 | +26.2 / +56.8 | +18.1 / +27.1 | +8.8 / +21.0 |

This shows what a fitted model leans on, not whether leaning on it helps. On BTC the big F numbers come from `leg01_atr`, which is leg size in ATR, so geometry and not Fibonacci. The top features across scales are `logit_p`, `log_sigma`, `up_sig`, `leg01_atr` (all geometry and volatility), then `w_phase` and `s_y_cos` (cycles) and `rsi_t_a` (where RSI is now). No Fib-zone or rule-legality flag is in any top list. **[verified]**

### Fibonacci: does BTC have its own?

**Pullback depth.** Hit rate against the recalibrated barrier, each bucket relative to the feature's overall gap (the barrier's level error is common to all buckets). Points, BTC with the shuffled and block 5-95% ranges.

| Retracement | 4H k4: n, hit, relative | Ranges | 4H k3: n, hit, relative | Ranges | 1H k6: n, hit, relative | Ranges |
|---|---|---|---|---|---|---|
| 0.236-0.382 | 31, 32%, +13.2 | -8.5 to +4.2; -6.2 to +10.3 | 66, 15%, +3.2 | -5.5 to +3.6; -5.9 to +7.6 | 79, 19%, +2.9 | -5.3 to +4.9; -4.2 to +7.5 |
| 0.382-0.5 | 65, 23%, +2.3 | -6.3 to +5.8; -7.4 to +8.9 | 97, 23%, +4.6 | -3.7 to +3.8; -3.0 to +6.9 | 108, 19%, +0.3 | -4.2 to +3.9; -4.6 to +5.4 |
| **0.5-0.618** | 61, 33%, +3.9 | -5.6 to +8.3; -7.0 to +6.8 | 109, 19%, -4.2 | -3.6 to +6.6; -7.4 to +5.1 | 123, 20%, -3.6 | -4.7 to +4.9; -6.9 to +1.4 |
| 0.618-0.786 | 111, 28%, -4.8 | -3.5 to +5.6; -5.0 to +4.8 | 150, 19%, -8.9 | -2.1 to +6.0; -5.0 to +3.9 | 181, 23%, -3.9 | -3.9 to +4.8; -5.3 to +3.2 |
| 0.786-1.0 | 108, 32%, -3.3 | -4.0 to +2.7; -6.1 to +4.2 | 205, 37%, +5.2 | -3.8 to +2.0; -2.9 to +3.7 | 227, 33%, +4.2 | -2.5 to +3.1; -1.3 to +5.9 |

The textbook W2 zone flips sign across scales and stays inside the null. 0.618-0.786 is low at all three, which is the opposite of what a "golden pocket" would give. **[verified]**

**How far the next move runs**, as a multiple of the last leg, before the origin breaks or time runs out. These are BTC's own numbers, and they are the honest answer to "every asset has its own extension":

| Extension | 4H k4 BTC | Shuffled | Block | 1H k6 BTC | Block |
|---|---|---|---|---|---|
| 0.618 | 72.7% | 79.4% (77.4 to 81.0) | 73.3% (70.6 to 76.0) | 71.6% | 69.9% (68.1 to 72.1) |
| 1.0 | 49.4% | 53.3% (50.1 to 54.8) | 48.4% (46.2 to 51.5) | 46.0% | 45.5% (43.4 to 48.0) |
| 1.618 | 31.4% | 27.9% (25.0 to 30.3) | 27.8% (23.9 to 30.7) | 24.0% | 24.4% (22.4 to 26.5) |
| 2.236 | 19.0% | 15.8% (13.0 to 18.4) | 17.5% (14.6 to 19.8) | 14.0% | 14.8% (13.0 to 17.1) |
| 2.618 | 14.9% | 11.4% (9.2 to 13.7) | 13.4% (10.6 to 15.7) | 11.2% | 11.4% (9.8 to 13.1) |
| 3.236 | 8.5% | 7.1% (5.0 to 8.2) | 9.1% (7.0 to 11.5) | 7.0% | 7.7% (6.2 to 9.0) |
| 4.236 | 5.6% | 3.0% (2.0 to 4.1) | 5.4% (3.7 to 7.3) | 3.5% | 4.3% (2.8 to 5.1) |

Random paths made of 20-day blocks of BTC's own days give almost the same curve. What sets BTC apart from a shuffled path is fat tails and volatility clustering, not Fibonacci. At 4H k4, 1.618 runs about 1 point above the block range; at the other scales it sits inside. **[verified]**

**Where moves stop.** Share of moves ending within +-0.05 of each level, per level:

| Level set | 4H k4 BTC | Block | 4H k3 BTC | Block | 1H k6 BTC | Block |
|---|---|---|---|---|---|---|
| 1, 1.618, 2.236, 2.618, 3.236, 4.236 | 1.58% | 1.74% (1.42 to 2.01) | 1.84% | 1.76% (1.46 to 2.01) | 1.85% | 1.64% (1.45 to 1.94) |
| Control: 1.3, 1.9, 2.4, 2.9, 3.6, 4.6 | 1.32% | 1.25% (0.96 to 1.55) | 1.21% | 1.25% (1.05 to 1.53) | 1.24% | 1.17% (0.98 to 1.42) |

No clustering beyond the null. The Fibonacci set is higher than the control on random paths too, because it includes 1.0, where more moves end. The empirical report tests this in more depth. **[verified]**

### The one lead: late in the weekly cycle, moves run out

The bucket tables flagged rows at about the rate chance would (9 to 14 of 50 per scale, about 10 expected), and most flagged rows flip between scales. One did not flip: `w_in_window`, the live weekly machine's timing window, 168 to 294 days after the last weekly low. I found it by looking, so I wrote a harder test before opening the 2013-2016 data: more paths, a holdout, other extensions, one plain alternative, one flag on its own, whole cycles resampled.

| | 4H k4 | 4H k3 | 1H k6 |
|---|---|---|---|
| 2017+: inside, n and hit | 100, 19.0% | 164, 14.0% | 191, 16.8% |
| 2017+: outside, n and hit | 280, 33.2% | 470, 28.7% | 544, 26.5% |
| Gap, points | -14.2 | -14.7 | -9.7 |
| Shuffled 5-95%; share of paths this low | -7.4 to +7.4; 0.7% | -6.4 to +6.0; 0.0% | -6.3 to +4.7; 0.0% |
| Block 5-95%; share of paths this low | -8.6 to +7.9; 0.7% | -7.0 to +6.1; 0.0% | -5.5 to +6.3; 0.0% |
| **Holdout 2013-2016**: inside, outside hit | 31 at 25.8%, 105 at 40.0% | 46 at 17.4%, 189 at 37.0% | 47 at 17.0%, 184 at 26.1% |
| Holdout gap, points | -14.2 | -19.6 | -9.1 |
| Holdout, share of null paths this low (shuffled; block) | 3.3%; 4.3% | 0.7%; 0.0% | 4.7%; 8.0% |
| Up setups, gap, 2017+ | -20.8 | -19.4 | -9.9 |
| Down setups, gap, 2017+ | -6.3 (inside null) | -9.7 (inside null) | -9.5 (at the null's edge) |
| Reach 1.0 / 2.236 / 2.618, gap | -9.4 / -13.1 / -9.4 | -11.6 / -10.3 / -7.4 | -11.6 / -3.3 / -2.7 |
| Flag alone on volatility + trend, walk-forward Brier gain x 1000 | +3.7 | +3.9 | +1.7 |
| Same on null paths, 5-95% (shuffled; block) | -2.1 to +0.9; -2.7 to +1.1 | -1.4 to +0.7; -1.7 to +0.6 | -1.3 to +0.5; -1.3 to +0.6 |
| Null paths reaching BTC's Brier gain | 0 of 600 | 0 of 600 | 1 of 300 |
| Resampling whole weekly cycles: gap 95% range | -25.5 to -4.1 (25 cycles) | -22.0 to -8.3 (25 cycles) | -17.4 to -3.0 (25 cycles) |
| Against a 60-day block null: share of paths this low | 2017+ 0.5%; holdout 7.0% | 2017+ 0.0%; holdout 1.0% | not run |

300 shuffled and 300 block paths per 4H scale, 150 and 150 at 1H, 200 with 60-day blocks. Null paths keep BTC's own bars and rerun the whole pipeline, cycle machine included. **[verified]**

The 60-day block null keeps volatility clustering up to two months and the gap still stands out, so it needs order longer than that. That fits a cycle of about 230 days, and it would also fit any other slow regime: this test cannot tell them apart. **[verified as measured]**

Added to the plain volatility model instead of volatility + trend, BTC only, the flag moves walk-forward Brier from 0.1942 to 0.1899 (4H k4), 0.1741 to 0.1698 (4H k3), 0.1811 to 0.1741 (4H k6) and 0.1634 to 0.1626 (1H k6). That is the best number at the two 4H scales where the plain model led, and about level with the raw barrier at 4H k3. At 1H the raw barrier (0.1611) stays ahead. **[verified, `ml_flag_on_volatility.py`]**

Hit rate by time since the live weekly low (2017+). Volatility says flat; price does not.

| Phase, days since the low / 231 | 4H k4: n, hit, raw barrier | 4H k3: n, hit, raw barrier | 1H k6: n, hit, raw barrier |
|---|---|---|---|
| 0.00-0.25 | 71, 38%, 19% | 125, 38%, 22% | 149, 31%, 24% |
| 0.25-0.50 | 98, 36%, 24% | 167, 28%, 23% | 191, 27%, 23% |
| 0.50-0.73 | 87, 30%, 22% | 141, 25%, 21% | 162, 22%, 23% |
| **0.73-1.00** | 61, **13%**, 22% | 100, **13%**, 23% | 118, **16%**, 23% |
| 1.00-1.27 | 36, 25%, 26% | 62, 16%, 22% | 70, 19%, 23% |
| 1.27-1.60 | 25, 24%, 26% | 35, 20%, 23% | 41, 24%, 24% |

By year at 4H k3, inside against outside: 2017 18/31, 2019 20/31, 2020 16/38, 2021 4/35, 2022 40/26, 2023 10/30, 2024 8/30, 2025 16/29, 2026 0/24 (4 setups inside). 8 of 9 years go the same way. **[verified]**

**What it is not.**

- **Not plain trend age.** "The lowest low of the last 294 days is at least 168 days old" points the other way (+6.6, +7.5 points). The two flags agree on only 55% of setups. **[verified]**
- **Not explained by the barrier.** It already sees volatility and distances, and it stays flat across phase. **[verified]**
- **Partly a volatility story.** Inside the window, realised volatility over the next H bars is about 15% below the trailing estimate (0.85-0.87 against 0.94-1.03 outside), and timeouts rise (42-54% against 32-37%). The market quiets down late in the weekly cycle. Origin-first does not fall, so it is not only lower volatility: drift in the setup's direction is also 0.3 to 0.5 sigma worse. **[verified]**
- **Not an edge.** In R, marked at the close on timeout, no costs, 2017+: inside the window -0.10 and -0.20 R per setup (4H k4, 4H k3), outside +0.16 and +0.12 R. The outside figures are inside the null range (-0.06 to +0.16 and -0.07 to +0.16); only -0.20 falls below its range (-0.11 to +0.18). Random paths carry BTC's drift too. It is a reason to expect less, not a trade. **[verified as measured, `ml_leads.py explain`; not a backtest]**

**How much weight it can bear.** It was found by looking at about 50 buckets at 5 variants. The holdout agrees in sign and size at all three scales, but it is small (31 to 47 setups inside the window). It is clear at 4H k3 (0-1% of null paths reach it) and weaker at the other two (3-8%). The weekly machine's settings were chosen while looking at BTC's whole chart, including 2013-2016, though never at a return or a null (`research/cycles-r1.md`), so the holdout is clean for this outcome and not for the machine. There are 25 weekly cycles in the test. It is strongest on up setups at 4H and even at 1H. And `research/cycles-r1.md` found the Camel cycle rules themselves no better than random paths, so this is a different and narrower claim. It agrees with what you said: structures tend to finish into the weekly cycle, so a move that starts late in the cycle does not get far. Your other half, the midpoint as a top, is not supported here: the aligned and opposed buckets of `s_w_cos` and `p0_w_align` stay inside the null at every scale (the empirical report tests it directly). **[verified as measured; real or not: unknown]**

**The test that settles it.** The live weekly low is 2026-07-01, so setups enter the window on 2026-12-16. From then on the flag can be logged forward with no way to fool ourselves. On current odds it would take a few weekly cycles, so a couple of years, to confirm. **[unknown]**

### The rulebook's own setup

Pullback 0.382-0.618, time rule met, legs parse as a 5 and a 3 one degree down (or are one leg): 26 setups at 4H k4 (hit 26.9%) and 39 at 4H k3 (17.9%), out of 380 and 634. Hit minus barrier against the rest: +7.7 and +2.5 points, inside the null. With W1 engulfing the prior swing: 20 setups (35%), +19.0 points, 3.7-7.0% of null paths as high; at 4H k3, 27 setups (18.5%), +7.0, inside the null. After a legal opposite five: 2 and 3 setups, too few. A setup this strict comes about three times a year on this scale, so history cannot judge it. **[verified]**

### Could this test have seen an edge?

Planted effect at the main scale: real features, synthetic labels from the structure-free model plus a known lift in the 0.5-0.618 zone (16% of setups). Share of 40 draws where the step to Fib and legs clears the 95th percentile of no-effect draws:

| True lift in the zone, points | Logistic, Brier | LightGBM, Brier | Logistic, AUC | LightGBM, AUC |
|---|---|---|---|---|
| 0 | 5% | 5% | 5% | 5% |
| +5 | 2% | 15% | 8% | 10% |
| +10 | 15% | 12% | 20% | 12% |
| +16 | 48% | 8% | 35% | 10% |
| +21 | 70% | 35% | 68% | 30% |

So the broad group test is weak: it would likely miss even a +10 point lift in one zone. "0 of 60" means no large effect, not no effect. The targeted bucket tables are sharper: their null range in that zone is about +-7 points at 4H k4 and about +-5 at 4H k3 and 1H, so a lift above about 8-10 points would have shown there, and did not. A smaller effect cannot be ruled out on BTC's history at these scales, and it would be hard to use after costs. **[verified]**

## What this means for choosing a model

| | Opus as the counter | Simple ML on outcomes | JEPA, foundation models (not tested here) |
|---|---|---|---|
| Follows the rulebook | Yes: 0 breaks in 114 | Not its job: rules are inputs | Not its job |
| Repeatable | No: 33-62% same state | Yes: same data, same number | Yes once trained |
| Can be tested on history | No: it remembers BTC, even masked | Yes: walk-forward, no leak | Yes, if trained only on the past |
| Tells BTC from noise | Barely, confidence 0.46 against 0.43 | Tested against the null at every step | **[unknown]** |
| Beats volatility alone | Not shown | No, except the weekly-window lead | **[unknown]**, see below |
| Cost for the whole 4H history | About $250, 9 hours, and the result cannot be trusted | About a minute of CPU | Rented GPU, **[unknown]** here |
| Good for | Explaining, reviewing, drafting rules as code, reading a chart image | Base rates, priors, filters, honest probabilities | Perhaps learning dynamics, if there are any beyond volatility |

**Decisions, from this evidence:**

1. **Do not use Opus to learn from BTC's history.** Not because it breaks rules: it doesn't. It already knows this history, it cannot be walk-forward tested, it counts noise the same way, and the same chart gives different counts. "Counting is deterministic code" in `CLAUDE.md` stands, and the reason given in the master plan should change from "it breaks rules" to "it is not repeatable, not testable, and not selective".
2. **The learner is simple statistics on the engine's output.** `rules.py` and `enumerator.py` show the deterministic part is small. What the statistics give is BTC's real behaviour: the extension table, base rates, how they drift by year, and the weekly-phase effect. That is the honest version of "teach the model how Bitcoin behaves".
3. **Start the probability layer from the volatility barrier.** It is a formula, needs no training, and at this question it wins or ties against everything tried, apart from the weekly flag. Any later model must beat it out of sample and beat the same step on null paths. If it can't, the barrier stays. Log the weekly flag next to it from now on, and do not trade on it yet.
4. **Use Opus at the edges.** It narrates engine JSON. It can review a draft rule file, and read a chart image with about 0.1% price error, which may be useful for checking a screenshot against the engine. The new finding is that it can be trusted to apply rules, so it can also explain which legal readings the enumerator kept and why. It should not supply a probability or pick the count.
5. **JEPA or a foundation model is worth trying only as a feature in this pipeline.** This is an inference from the results, not a test. BTC has about 250 to 1,000 setups per scale and 3 four-year cycles. Whatever a large model learns first will be volatility and its clustering, and the block null shows that this alone reproduces the extension curve. The bar is simple: its embedding goes in as another group, and it must beat volatility + trend by more than the same step does on null paths.
6. **Both of your positions can stand.** Your 23 October note says a tool should not count for people and should hold the trader's count to account. Today you ask for a model that learns from history. They fit: the engine and the statistics study history and claim nothing about which count is true. Live, your count goes through the checker (instant, free, names the rule it breaks), and your target and invalidation get the barrier probability and the base rate. That is what a tool can do honestly on today's evidence. Whether your own counts carry information the rule flags don't is the open question, and only your logged counts can answer it, as your September note says: no model here sees your eye.

## Decisions and why

| Decision | Value | Why |
|---|---|---|
| Mask every window | Price constant, dates moved | Otherwise the model recalls the future and random paths cannot pass as BTC. It leaked anyway on famous windows, which is the finding. |
| Mask factor | Never within a factor of 2 of the real level | The first draw for N1 was about 1.0, which left it at real prices. Changed before any call was made. |
| Fields `recognised_period`, `data_note` | Added | The only direct probe of memory and of noticing noise. They may prime it to look. |
| RSI(11) in tables | Added at pivots and bars | The rulebook leans on TDI; leaving it out would be unfair. Bands and signal are not given. |
| Budget split | 7 BTC windows (L1 pivot only), 3 random, 3 real-date, 2 image | 60 calls, smoke included. A third random window and the memory check were worth more than an eighth BTC window. |
| 1D k = 3, 4H k = 4 | Median leg 22-28% and 10-12% | Section 5's move sizes (1D 20-30%, 4H 12-15%). |
| Time minimum reported apart | Not counted as a hard break | Section 1 calls it a convention, section 4 a rule. |
| Lenient on log vs linear | A length rule breaks only if it breaks on both | The book allows either on wide ranges. Benefit of the doubt to the model. |
| Running wave | Minimum rules skipped for it, limits still apply | A wave not yet finished cannot fail a minimum. |
| Timeouts | Not reached | The brief's wording. Without them target against origin is 41-49%. |
| Same-bar ties | `hl_order`, else origin first | Conservative. Only 0-1 ties per scale on BTC. |
| H | About 2.236 x the 90th percentile leg | Section 1's time ratio for W3, on long legs. Structural, not chosen by result. |
| Linear target as main | Log target run as a variant | Section 4 says it is immaterial below 4H; on a 4H k4 leg it can matter, so both are shown. Same conclusions. |
| Model settings | Fixed in advance, no tuning | With 380 test setups, tuning would fool me. |
| First test year | 2017 | Before it, about 100 setups to train on. |
| 40 null paths per scale | 300 for the lead | Enough for a rough 5-95% range; a targeted claim needs a real tail. |
| Bucket rows relative to the feature's overall gap | Instead of raw excess | The barrier's level error, from the base rate falling after 2017, made every bucket look bad. |
| Series | Bitstamp, from 2013-03 | The longest verified series, same as the cycles work. Bybit (your chart) not run. |

## Claims by status

**Verified:** every table above comes from these scripts on this data; `check_causal.py` passes (6 cuts, garbage future, planted leak); the barrier formula agrees with Monte Carlo (0.313 against 0.304, 0.043 against 0.044, 0.620 against 0.588, 0.001 against 0.001); all Opus answers came from one model id, `claude-opus-5-5`, at `--effort high`; no repo file outside `research/model-options/` was changed and nothing was committed.

**Assumed:**
- A zigzag at these scales is a fair stand-in for the swings a trader would label. It is not a trader's count.
- Shuffled and 20-day block paths are fair nulls. They keep BTC's total return and destroy long-range order, so they cannot speak to anything that only shows over years.
- A single prompt is a fair test of Opus. A longer brief, worked examples, a lower timeframe in the same call, or a second pass might raise repeatability. Nothing I saw suggests they would fix noise or memory.
- TDI band width 1.6185 x stdev, the usual TDI default; the course setting was not checked for it.
- The list-price dollars stand for what an API user would pay. Your Max plan bills differently.

**Unknown:**
- Whether the weekly-window lead is real. The forward log starts 2026-12-16.
- Whether your own counts carry information the rule flags do not. Your trade log can answer it, nothing here can.
- Whether JEPA, Kronos or anything else beats volatility on this target. Not run.
- Whether any of this pays after costs. No trades were simulated beyond the R size-of-effect figures.
- How Opus behaves at other efforts or on cheaper models. Only Opus at high effort was run.

## Known weaknesses

- **Few LLM windows.** 7 BTC and 3 random paths. Rule breaks and validity are well measured because counts are many; forecast and noise numbers are hints because windows are few.
- **Famous windows are half the BTC set**, and they are the ones it recognised. Masking failed there. Only H3 and L1 stayed fully unrecognised, H2 almost.
- **The checker is one degree only.** It cannot say a leg is a 3 or a 5, and it cannot test order blocks or TDI rules. Opus may be more or less right about those.
- **The enumerator is a yardstick, not a rulebook engine.** Spans are capped at 19 legs, flats and zigzags use only the hard rules, and the loose grammar's hidden correction is my reading of section 0.
- **Setups are mechanical.** A 0-1-2 at every pivot is not a hand-picked W1-W2. The flags try to narrow it down, and setups strict enough to resemble a real one rarely occur, so that question stays open.
- **One target.** The 1.618 is one level of the book; W5, C and the strategy targets were not modelled. The extension table covers other levels without features.
- **Small samples.** 380 test setups at the main scale, overlapping in time. The null handles the overlap, not the small n. See the power table.
- **Many looks.** Every variant is reported, but the bucket tables are a fishing trip by design, which is why the one lead got a separate test.
- **One venue.** Results on Binance or Bybit were not run. They would not be independent evidence anyway, since it is the same market.

## Reproduce

From the repo root. Details and file list in [`spikes/bakeoff/README.md`](spikes/bakeoff/README.md).

```bash
export PATH=/opt/data/.local/bin:$PATH
PY="uv run --with numpy --with scipy --with scikit-learn --with lightgbm python research/model-options/spikes/bakeoff"
B=/opt/data/cache/scratch/elliott_research_r1/bake

# Part A
$PY/windows.py
$PY/llm_run.py --plan main null unmasked live --concurrency 3
node research/model-options/spikes/bakeoff/render_chart.mjs $B/windows/H2.json $B/llm/H2.png
node research/model-options/spikes/bakeoff/render_chart.mjs $B/windows/D1.json $B/llm/D1.png
$PY/llm_image.py H2 D1
$PY/llm_eval.py

# Part B
$PY/check_causal.py
$PY/ml_run.py btc
for sc in 4h_k4 4h_k3 1h_k6; do for k in shuffled block; do $PY/ml_run.py null --scale $sc --kind $k --paths 40; done; done
for k in shuffled block; do $PY/ml_run.py null --scale 4h_k6 --kind $k --paths 20; $PY/ml_run.py null --scale 4h_k4 --kind $k --paths 20 --log-target; done
$PY/ml_run.py power --paths 40
$PY/ml_report.py
$PY/ml_leads.py run --scale 4h_k4 --paths 300
$PY/ml_leads.py run --scale 4h_k3 --paths 300
$PY/ml_leads.py run --scale 1h_k6 --paths 150
$PY/ml_leads.py run --scale 4h_k3 --paths 200 --block-days 60
$PY/ml_leads.py run --scale 4h_k4 --paths 200 --block-days 60
$PY/ml_leads.py explain --scale 4h_k4
$PY/ml_leads.py explain --scale 4h_k3
$PY/ml_leads.py report
$PY/ml_flag_on_volatility.py
$PY/ambiguity_null.py --paths 20
```

Opus answers differ on every rerun, so part A reproduces the distribution, not the numbers. Part B is seeded and reproduces exactly on the same data; new bars move it a little. The rulebook path is `$BAKE_RULEBOOK` and is never copied into the repo.
