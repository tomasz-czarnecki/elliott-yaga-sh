# Which approach is best for you

Research round `elliott_research_r1`, synthesis, 2026-10-30. All three worker reports arrived complete, and nothing here is committed.

**How to read this.** BAKE = [`03-bakeoff.md`](03-bakeoff.md), EMP = [`02-empirical.md`](02-empirical.md), LIT = [`01-literature.md`](01-literature.md), CYC = [`../cycles-r1.md`](../cycles-r1.md), PLAN = [`../probabilistic-elliott-wave-engine-plan.md`](../probabilistic-elliott-wave-engine-plan.md). SYNTH = five small scripts I ran for this file, in `/opt/data/cache/scratch/elliott_research_r1/synth/`. Literature numbers are as LIT read them; I did not reopen those sources. Tags: **[verified]** measured or read in a named report, **[assumed]** a choice or judgement, **[unknown]** cannot be told yet.

**How I read "jev".** Most likely JEPA (Joint Embedding Predictive Architecture, LeCun's world-model line). No AI model called JEV was found (LIT). The nearest alternatives, foundation models such as Kronos, Chronos and TimesFM, are covered too. **[assumed]**

**Three terms used throughout.**
- *Barrier formula*: the chance a random walk with today's volatility and no drift hits the target before the stop within H bars. No training. *Geometry* is the same thing with no time limit: stop distance / (stop distance + target distance).
- *Setup*: a mechanical 0-1-2 at a confirmed zigzag pivot. Target 1.618 of the 0-1 leg, stop at 0. It is not a trader's hand-picked count.
- *Null* or *random path*: BTC's own bars with their order or direction scrambled, run through the same code. If a number also shows up there, it is not evidence.

## 1. The answer in 10 lines

1. **Neither Opus nor JEPA should be the thing that learns Bitcoin.** The best setup for you is small math on top of rule code, with your own counts as the thing being measured and Opus as the interface. I call it the audit stack. **[assumed: a judgement from the evidence below]**
2. **Opus** follows your rulebook almost perfectly (0 hard breaks in 114 counts). But the same chart gives the same state only 33-62% of the time, it counts shuffled paths with the same confidence (0.43 against 0.46), and it remembers BTC even when masked (17 of 18 famous-window calls named the period). It cannot be backtested, and it never refuses. **[verified, BAKE]**
3. **JEPA** has not been run on BTC by anyone we could find. It would most likely rediscover volatility, and in the largest benchmark it barely beats an untrained network (0.0204 against 0.0170, supervised 0.0311). Keep it as a side test under $100, later. **[verified, LIT; the prediction is assumed]**
4. **Simple math already did what you asked,** on this server, in about a minute of CPU. Walk-forward logistic on volatility scores Brier 0.1942 against 0.2105 for the base rate. Unlike Opus, it can be tested honestly, on this box, any time. **[verified, BAKE]**
5. **What it learned about BTC:** volatility (out-of-sample R2 0.35-0.56), a weak slow trend, falls 1.2-1.3 times faster than rises, and a step at the previous swing extreme. **[verified, EMP]**
6. **It did not find a BTC Fibonacci.** Rulebook windows are hit as often as on random paths (W2 at 0.5-0.618: 17.6% against 17.5%; W4 at 0.236-0.382: 41.9% against 41.3%). Fib, TDI and rule flags cleared the null in 0 of 60 comparisons. **[verified, EMP and BAKE]**
7. **Weekly cycles:** "structures finish at weekly lows" is true and also true on random paths (75% against 57-70%). "The middle is a top" is not shown, and the causal test points the other way. One lead stands: late in the weekly cycle, 4H-size moves run out (1.618 reached 14-19% against 27-33% outside). It is a caution, not a trade, and its live test starts 2026-12-16. **[verified as measured; real or not is unknown]**
8. **All of that is mechanical counting. Nobody has tested your eye.** It is the main place left where an Elliott edge could live, and the one sample that grows every week. So the first thing to build is a log of your calls, scored against the barrier formula. **[unknown whether the edge exists]**
9. **First two weeks:** call log, rule checker, barrier formula, a frozen forward log, and a blind test of your eye on 40 charts. About 165 independent calls, 6 to 13 months at 3-6 a week, can show a 10-point edge over volatility. **[computed, SYNTH `power.py`]**
10. **Expect "not shown" as the likeliest verdict.** Even then you end up with a rule checker, honest odds on your own levels and a record of where your bias lives, which is your 23 October idea. No Elliott engine we found publishes its own calibration. **[assumed; the last sentence verified, LIT]**

## 2. Your questions, answered

### "Opus or Jev (JEPA): which?"

For the job you described, learning how BTC behaves, **neither**. For helping you work every day, **Opus, by far**. They are different kinds of tool. JEPA is the right kind in principle, because it trains on BTC's data. Opus is the wrong kind, because it does not train at all. In practice, nothing shows JEPA learning more than volatility, and Opus tells a fluent story on any path, including noise. **[assumed: the verdict; the evidence is below]**

All rows **[verified]** from the named report unless marked.

| | Opus (LLM) | JEPA (world model) |
|---|---|---|
| What it does with BTC's history | Nothing new. Each call is stateless. It recalls what it saw in training (BAKE, LIT) | Trains an encoder on BTC bars to predict the summary of the next window. Real learning, on your data (LIT) |
| What it would pick up | Levels and shapes it already remembers. It cannot give unbiased frequencies from memory (LIT) | Volatility first. Coefficients on BTC 15m: +0.70 log volatility, +0.45 absolute return, -0.07 return, about 0 since 2021 (LIT, `jepa_predictable_part.py`). **[assumed that JEPA follows them; none was trained]** |
| Knows NewWave | Yes. 0 hard breaks in 114 counts and 824 labels, where a random labelling breaks a rule 75% of the time (BAKE) | No. It cannot count or explain itself (LIT) |
| Same answer twice | No. Same state 62% on a pivot table, 33% on raw bars, 30% across formats (BAKE) | Yes, once trained |
| Can history test it | No. It named the period in 17 of 18 famous-window calls despite masking. Clean data: about 4 months since its June 2026 cutoff (BAKE) | Yes, if fitted only on the past (LIT) |
| Tells BTC from noise | Barely. Confidence 0.46 against 0.43, primary count on 15 of 15 random paths, never refused (BAKE) | **[unknown]** |
| Forecast, our runs | Brier 0.181 against 0.171 for volatility on its own levels. 6 windows, a hint only (BAKE) | None. No BTC or crypto JEPA was found (LIT) |
| Forecast, outside | FINSABER: buy and hold Sharpe 0.315-0.384, FinMem -0.253 to 0.025. DXRG, live crypto perps: win rate 41% against 50% for matched retail (LIT) | TFWM, US equities walk-forward: LeJEPA 0.0204, untrained network 0.0170, ridge 0.0196, supervised 0.0311. STOCK-JEPA: RankIC 11-13%, net Sharpe 1.24-1.50, one test period, about 15,800 stocks, a cross-section that does not transfer to one asset (LIT) |
| Data | Clean sample 121 days (LIT) | 1,871 non-overlapping 256-bar 15m windows on one path (EMP). Volatility behaves like 41 to 2,202 independent samples (LIT) |
| Cost | $0.22 a call at list price, 83 s. No per-call charge on Max. One call per 4H pivot over history: about $250, 9 hours. One per 1H bar: about $29,000 (BAKE) | 45-235 hours per run on this CPU, or $1-$7 on a rented RTX 4090. A small grid: $28-$173 (LIT) |
| What you get | A fluent count with reasons | 3 to 8 numbers, one more column in a table |
| Verdict | Interface and builder. Never counter or probability source | Capped side test, after the harness exists |

**New in this synthesis: Opus's probability is largely the geometry of its own levels.** On its 57 usable primaries, stated P correlates 0.74 with stop / (stop + target), mean gap 8 points; on 30 random-window counts, 0.79. **[verified, SYNTH `opus_vs_geometry.py`]** On today's 4H chart (close $77,793), run 1 says down to $76,109 before $84,843 at P 0.70; the barrier formula over 150 bars says 0.79. Run 3 says up to $87,374 before $74,913 at P 0.25; the formula says 0.17. **[verified, SYNTH `today_card.py`; a test artefact, not a call]** The two runs disagree on direction and both land near the formula. The number comes from where the levels sit, not from the wave count.

**One point in Opus's favour that BAKE left out of its report.** In `llm_tables.md`, its next move was right on 63% of 35 masked BTC calls against 20% of 15 random-path calls, and on 77% of the 13 calls where it did not recognise the chart. That is 6, 3 and 3 windows, so whole windows move these numbers. It is a hint, and the only clean way to firm it up is a forward log. **[verified as measured; too few windows]**

### "Is there a better way?"

Yes. The better way is not a bigger model. It is changing what the model is asked to do: stop asking it to learn wave truth from one price path, and instead score checkable outcomes for every forecaster on the same levels. Four reasons:

- **One path, few examples.** 13.7 years hold about 17, 59, 188 and 219 independent legal 5-waves at daily, 4H, 1H and 15m, plus 23 weekly cycles and 3 four-year lows. On 59 events you can only see an edge of 18 points or more. **[verified, EMP A1]**
- **No true count to learn.** A pivot that can end a legal 5-wave has about a dozen legal ways to draw it, from about 5 origins, the same as on random paths (EMP A4). A BTC window has about 200 to 1,100 rule-legal readings and about 20 distinct states, with up and down structures in every window (BAKE). "The wave count" is not a usable label. **[verified]**
- **Outcomes are checkable, and they are already your rule.** Target before invalidation within H resolves by itself, needs no one's opinion, and can be scored on random paths too. **[verified as method, LIT section 6]**
- **Your eye is the untested variable.** Every test here used a zigzag and a rule checker. The reports say so plainly, so the gap is measurable and open. **[unknown]**

### "Should a simple mathematical model or ML do it?"

Yes, and it already has. Walk-forward by year from 2017, BTC out-of-sample, lower is better. All from BAKE **[verified]**.

| Scale | Setups | Hit rate | Base rate | Barrier formula, no training | Logistic, volatility | Volatility + weekly flag |
|---|---|---|---|---|---|---|
| 4H k4 (main) | 380 | 29.5% | 0.2105 | 0.2019 | **0.1942** | 0.1899 |
| 4H k3 | 634 | 24.9% | 0.1894 | **0.1695** | 0.1741 | 0.1698 |
| 4H k6 | 159 | 25.8% | 0.1936 | 0.1926 | **0.1811** | 0.1741 |
| 1H k6 | 735 | 23.9% | 0.1824 | **0.1611** | 0.1634 | 0.1626 |

Bold marks the best number without the flag. It is always a volatility model, and at two of four scales it is a formula with no training.

Adding features at the main scale makes it worse: + Fib and legs 0.2034, + TDI 0.2045, + rule flags 0.2059, everything 0.2300. Logistic on everything says 0.75 when price delivers 0.46 (slope 0.33). LightGBM holds up better but still adds nothing (0.2057). **[verified, BAKE]**

Three things keep this honest:

- **AUC 0.7 is arithmetic.** Random paths score the same or better (barrier AUC 0.661 on BTC, 0.746 and 0.697 on nulls), because a near target and a far stop win on any path. Any "AUC 0.7" claim on this kind of target has shown nothing yet. **[verified, BAKE]**
- **"0 of 60" means no large effect, not no effect.** A planted +10 point lift in one zone was caught only 12-20% of the time by the broad test. The targeted tables are sharper and would have shown about 8-10 points. **[verified, BAKE]**
- **Expect a filter, not an edge.** The best hourly BTC study found Sharpe 1.09 against 0.82, gain 95% CI -0.46 to +0.95. In our own check, slow moving averages cut drawdown from -85% to -70% and -64% with no significant Sharpe gain. **[verified, LIT section 4]**

**Usable today, no code.** Your free baseline win rate on any trade is stop / (stop + target). That is 33% at 2:1 and 25% at 3:1. On BTC 1H this formula was off by 0.043 on average, longs about +0.058 (LIT, `sh_barrier_baseline.py`). A count earns credit only for what it adds above that number. **[verified, LIT]**

### "Does every asset have its own Fibonacci, and can a model learn BTC's?"

**BTC's swing ratios differ from random paths in shape, but not at Fibonacci levels.** Inside 1,106 rule-legal impulses, against random paths that keep BTC's volatility and slow trend (EMP B2) **[verified]**:

| Rulebook window | BTC | Random | p |
|---|---|---|---|
| W2 ends at 0.5-0.618 | 17.6% | 17.5% | 0.90 |
| W4 ends at 0.236-0.382 | 41.9% | 41.3% | 0.70 |
| W3 near 1.618 | 9.2% | 9.4% | 0.87 |
| W3 near 2.618 | 5.6% | 5.4% | 0.76 |
| W5 near 2.236 | 9.3% | 8.6% | 0.43 |
| W5 near 1.0 of 0-1-4 | 6.0% | 6.6% | 0.43 |

Over all swings, 264 of 3,696 tests read high against 235 (202-270) on random paths. **[verified, EMP B1]** Your rulebook itself says it holds no samples (section 7), and the course numbers come from instructor experience. **[verified]**

**What is really BTC's**, and small:

- W2 runs deeper than chance: over 0.618 is 58.1% against 54.6%, under 0.382 is 10.1% against 13.0%.
- W3 extends more at 15m and 1H: beyond 2.618 is 18.8% and 19.4% against about 15.9%.
- W1 is the longest least often, and W5 is the longest more often than chance.
- Alternation is real and tiny: Spearman about -0.1 against -0.03.
- The step at 1.0: a leg stops short of the last pivot about +3 points more than chance and rarely stops just past it.

**[verified, EMP B1-B3]**

**Can a model learn it? Yes, and it is a lookup table, not a neural net.** Here is the honest form of "BTC's own extensions": how often a generic setup reaches each multiple of its last leg before the origin breaks or time runs out. **[verified, BAKE]**

| Multiple of the leg | 0.618 | 1.0 | 1.618 | 2.236 | 2.618 | 3.236 | 4.236 |
|---|---|---|---|---|---|---|---|
| 4H k4 | 72.7% | 49.4% | 31.4% | 19.0% | 14.9% | 8.5% | 5.6% |
| 1H k6 | 71.6% | 46.0% | 24.0% | 14.0% | 11.2% | 7.0% | 3.5% |

That is useful for a scale-out plan. It is not a Fibonacci property: nothing special happens at these multiples. And a target at 1.618 times your risk hits 38.2% on a pure random walk (1 / 2.618), by arithmetic. **[verified, LIT section 4]** That may be part of why Fibonacci feels right on a chart. **[assumed]**

**Limits.**

- A fit of the 12-band ratio shape up to 2021 beats the null on 2022-2026 at only 7 of 48 histograms, worth well under 1% of what is unknown about the next ratio. **[verified, EMP]**
- A bump of +20% at a level would have been visible on 1H, and +40% on 4H. Smaller and high-degree bumps cannot be excluded. **[verified, EMP]**
- One faint lead: linear extensions at 1.618 run 14% above neighbours on Bitstamp and on Bybit (your chart), none on Binance, family-wise p 0.18-0.34, about 3 legs in 1,000. It gets no weight until forward data says otherwise. **[verified as measured, unconfirmed]**
- Whether assets differ from each other is **[unknown]**: the repo holds BTC only, and no study controls for scale and volatility (LIT). "Unsupported, not refuted." A random walk's scaled ratio law is the same for every asset, so any real difference must come from tails or volatility dynamics. Running ETH through the same code is cheap, so it is in the plan.

### "Is your weekly-cycle and Elliott Wave correlation real?"

**Partly, and not the way it feels on the chart.** "Weekly cycle" here means Camel's 24-42 week cycle. **[assumed; the day-of-week reading was tested too and shows nothing, EMP C7]**

| Claim | Result | Verdict |
|---|---|---|
| Structures finish at weekly lows | 18 of 24 lows have a legal 5-wave down ending within 14 days at one of six degrees: 75%, against 57-70% on random paths. With zigzags: 100% against 100%. 34% of all days have such a 5-wave within 14 days, 85% with zigzags (EMP C3) | True, and not evidence |
| The midpoint is the cycle's top | Within 0.1 of the middle: hindsight 3 of 23 (13%), live 6 of 22 (27%), random 14-19% (EMP C1) | Not shown |
| The midpoint is a top of something | Pivot highs and lows have the same profile there: live 28.9% and 28.4%, hindsight 10.6% and 10.9%. Live up-structures do end there more (53% against 22-26%), which fails correction and reverses in hindsight (EMP C2, C3) | Not shown |
| A mid-cycle up-structure makes a good top | Top holds 3 of 12 (25%) against 11 of 22 (50%), same sign at all 8 settings, p 0.05 at best (EMP C5) | Points the other way: the move more often keeps going |
| Structures confirmed with the window open do better | -1.5 and -15.1 points, null medians about -1 and -3 (EMP C5) | No |
| Late in the cycle, moves run out | Setups inside day 168-294 reach 1.618 in 14-19% against 27-33% outside. The barrier formula expects no difference. 2013-2016 holdout: gaps -9 to -20 points. 0 of 600 null paths reach the Brier gain at both 4H scales (BAKE) | Best lead, unconfirmed |
| Top left of midpoint means a lower next low | 64% against 36-38%, n = 14, clears the shuffled null but not the block null (CYC) | Lead, small |
| A 24-42 week rhythm exists | Spectral power 1.90 against 0.97, p 0.02; by era 2.28, 1.77, 0.69 (EMP C6) | Weak, absent in 2022-2026 |
| 4-year lows | Gaps 1,431 and 1,437 days; 1 of 400 random paths that even (CYC) | A pattern, n = 3 |

All rows **[verified as measured]**.

Two separately written pipelines, on the same data and the same cycle machine, tell one story. EMP finds mid-cycle up-moves keep going. BAKE finds follow-through by phase of 38%, 36%, 30%, then 13% at phase 0.73-1.00 on the main scale. So **early and middle of the cycle, moves run; from about day 168, they tire.** That is the opposite of "the middle is a top", and it fits the first half of what you said: structures tend to finish into the cycle's end. **[verified as measured; the reading is assumed]**

**A check of my own on the late-cycle lead,** on settings and venues outside BAKE's lead test, fixed before running, all reported. Same flag, same outcome. **[verified, SYNTH `flag_replication.py`]**

| Setting | Inside: n, hit | Outside: n, hit | Gap, 2017+ | Gap over barrier | 2013-2016 gap | 2023+ gap |
|---|---|---|---|---|---|---|
| Bitstamp 4H k5 | 66, 19.7% | 171, 31.0% | -11.3 | -13.1 | -16.1 | -15.0 |
| Bitstamp 4H k6 | 55, 12.7% | 116, 31.0% | -18.3 | -23.1 | -19.9 | -23.5 |
| Bitstamp 4H 8% reversal | 106, 15.1% | 318, 28.6% | -13.5 | -10.9 | **+0.6** | -13.4 |
| Bitstamp 1H k12 | 66, 21.2% | 143, 28.7% | -7.5 | -11.5 | -20.8 | -4.3 |
| Bitstamp 1H k8 | 119, 14.3% | 315, 27.9% | -13.7 | -13.1 | -9.1 | -14.1 |
| Bitstamp 1H k4 | 395, 23.5% | 1101, 25.5% | **-2.0** | -1.9 | -8.3 | -2.4 |
| Bitstamp 1H 4% reversal | 377, 24.9% | 1219, 27.4% | **-2.5** | -1.9 | -1.6 | -1.9 |
| Bybit 4H k3 | 120, 10.8% | 305, 27.2% | -16.4 | -15.3 | | -18.7 |
| Bybit 4H k4 | 73, 12.3% | 169, 30.8% | -18.4 | -18.8 | | -16.9 |
| Bybit 1H k6 | 151, 15.9% | 339, 24.5% | -8.6 | -9.1 | | -6.0 |
| Binance 4H k3 | 145, 12.4% | 430, 27.7% | -15.3 | -14.9 | | -14.2 |
| Binance 4H k4 | 90, 15.6% | 249, 31.3% | -15.8 | -16.7 | | -13.4 |
| Binance 1H k6 | 175, 16.6% | 478, 25.5% | -9.0 | -9.5 | | -6.3 |

Reading:

- All 13 gaps are negative, and it shows on your own Bybit chart. It is still one market and the same 25 cycles, so this tests robustness, not fresh evidence. **[verified]**
- **It lives at 4H-size swings.** It holds on larger 1H swings and fades to about -2 points on small ones, where 2017+ sits inside the null (23% of paths this low, no Brier gain, 100 paths each). So it is about big moves, not your typical 1H signal. BAKE's scales did not include small 1H swings. **[verified as measured]**
- At the 8% fixed reversal, the 2017+ gap stands out (0% of shuffled and 3% of 60-day block paths this low), but the 2013-2016 holdout shows nothing (+0.6, n = 52). So the holdout support is not universal. **[verified, 100 paths each]**
- At 4H scales it holds from 2023 on, while the spectral bump is absent from 2022 on. So this is probably not a steady clock. **[verified as measured; the reading is assumed]** What it is: **[unknown]**.
- **Size:** about 2-4% of the Brier score at the 4H scales. On R, inside the window -0.10 and -0.20 per setup, outside +0.16 and +0.12, marked at the close on timeout, no costs, and the outside figures sit inside the null range. It is a reason to expect less, not a trade. **[verified, BAKE; not a backtest]**

**How to use it.** At most, lower your expectations on 4H-degree setups inside the window: earlier profit-taking, more timeouts (42-54% against 32-37%, BAKE). Do not trade it as a signal. **[assumed]** Two dated forward points:

- **2026-11-04:** day 126 of the current live weekly cycle, the first day it can end. If no new high above $87,373.64 by then, the state logged is "top left of the midpoint", the 64% (n = 14) lead for a next low below $57,734.63.
- **2026-12-16:** day 168, the late-cycle window opens, running to 2027-04-21 unless a new live low confirms.

These are test entries, not calls. **[verified from CYC and the machine's settings, computed dates]**

## 3. The options compared

Costs are at list price unless marked, your Claude Max plan has no per-call charge, and its usage limits are **[unknown]**. Effort estimates and every "In practice" and "Main risk" line are my judgement **[assumed]**.

### A. Opus or another LLM, counting in context

- **Pros:** 0 hard breaks in 114 counts, all 380 cited prices exact, correct Fib arithmetic, nothing to build. It spotted the real January 2015 Bitstamp halt. **[verified, BAKE]**
- **Cons:**
  - Same chart, different count: 2 of 13 BTC cells fully agree across 3 runs, 3 of 5 random cells do.
  - It never abstains.
  - With real dates, all 3 runs switched to the count that fits what came next, breaking its own time minimum.
  - Hand-computed RSI was off by 2-15 points.
  - **[verified, BAKE and LIT pilot]**
- **Our runs:** 59 Opus calls, $12.92. LIT's pilot: 34 of 34 recognised windows dated to the exact month with next-30-day direction right, then 0 of 9 dated within 12 months after the cutoff. **[verified]**
- **Cost:** $0.22 a call, 83 s, over the API with no local load and none of your time. Live hourly for a year about $1,900. LIT's lower table assumed 1,500 output tokens; the measured mean is 7,711, so use BAKE's number. **[verified]**
- **In practice:** a sharp second reader who writes a good story on any chart, noise included.
- **Main risk:** a fluent wrong count feels like confirmation.

### B. Fine-tuned open LLM (Qwen, DeepSeek, via Together or OpenRouter)

- **Pros:** open weights, cheap at the small end, would learn your vocabulary. Tuning can reshape how a model handles numbers, though in the best design the signal is tiny, within R2 0.001 (Gao, LIT). **[verified, LIT]**
- **Cons:**
  - No Claude model can be newly fine-tuned.
  - Labels are the problem: 0 gold swings, engine labels only copy a free engine, outcome labels are about 660-4,900 effective.
  - Nothing found beats a naive forecast with walk-forward and costs. Chronos T5-tiny retrained daily earned gross Sharpe 2.12, 3.90, 2.29 against a plain reversal rule's 2.23, 4.16, 2.31.
  - Rules stop being versioned config.
  - **[verified, LIT]**
- **Our runs:** none trained. Costs modelled only.
- **Cost:** $4 to about $5,000 per adapter, yearly walk-forward $422-$32,462, serving $134-$70,080 a year, a week or more of your time. Training cannot run on this CPU, so it means rented GPU or a hosted service. Cheap models are fine for narration (DeepSeek V4.1 Flash $3.42, Haiku 5.5 $4.38 a year). **[verified, LIT]** Whether cheap open models count or forecast any better: **[unknown]**, nothing suggests it.
- **In practice:** a noisy copy of a free formula, or your own style echoed back.
- **Main risk:** money and weeks spent on something that cannot beat "tomorrow equals today".

### C. Vision LLM on chart images

- **Pros:** reads your marked-up screenshots. 25 labels, mean price error 0.1%, worst 0.22%, on 2 calls. Good as an input device. **[verified, BAKE]**
- **Cons:** a third format gave a third reading, and it recognised the period from the picture alone. There is no candlestick benchmark on Opus 5.x, and reading values against axes is the known weak spot of chart models. **[verified, BAKE and LIT]**
- **Our runs:** 2 calls, one each on H2 and D1. A capability check, not a statistic. **[verified, BAKE]**
- **Cost:** $0.26 a call, 69 s, none of your time. Needs `--input-format stream-json` to pass the image. **[verified, BAKE]**
- **In practice:** turn your screenshot into JSON, snap every level to the real bar's high or low, and have you confirm. As a counter it has all the problems of option A.
- **Main risk:** trusting a level read from a picture. Snapping to the data removes it.

### D. JEPA or another self-supervised world model

- **Pros:** real learning on your data, no labels needed, causal if fitted fold by fold, fast-moving research with money behind it. One real positive on stock cross-sections, STOCK-JEPA. **[verified, LIT]**
- **Cons:** built to discard what it cannot predict, which is exactly direction. No BTC evidence. In TFWM, LeJEPA sits close to a random encoder on returns (0.0204 against 0.0170) and on volatility (0.0721 against 0.0694). Forecasting pretraining helped 24 of 49 cells, a coin flip. Fin-JEPA's loss fell with no return signal. It cannot count or explain. **[verified, LIT]**
- **Our runs:** none, as there is no GPU. Our data shows direction memory near zero and volatility memory high (EMP A0), which is why I expect it to learn volatility. **[assumed]**
- **Cost:** $100 cap, because a run takes 45-235 hours on this CPU, so it means a rented GPU. 1-2 days to generate a harness, 1-3 days to run and check. Warning signs (collapse, random-encoder floor, leaks) are hard for you to read alone. **[verified prices, assumed effort, LIT]**
- **In practice:** a few extra numbers that probably say "volatility is high". If they beat the same step on random paths, that would be a real surprise worth having.
- **Main risk:** a latent that looks healthy and has learned the era or the volatility level, delaying everything else.

### E. Time-series foundation models (Kronos, Chronos, TimesFM, TTM)

- **Pros:** no training needed, finance-built options exist, public weights. Kronos-mini is a $0 test, and TTM plus log-HAR is a real, if small, volatility gain (QLIKE ratios 0.977-0.984). **[verified, LIT]**
- **Cons:** 2 of 43 models beat persistence on raw error in the largest finance benchmark. At 20 bps every long-short went negative in the largest cost study. Kronos's crypto return IC loses to DLinear (0.0368-0.0376 against 0.0446). A 512-bar context is 85 days on 4H, too short to see a weekly cycle. **[verified, LIT]**
- **Our runs:** LIT graded Kronos-mini's 7,387 public hourly BTC forecasts over 308 days: Brier 0.3065 against 0.25 for a coin on P(up), hit rate 51.3%, recalibrating only reaches 0.2525. That is one small demo at one horizon, not the whole family. **[verified, LIT]**
- **Cost:** $0 and 6-20 hours of low-priority CPU for a kill test. $2-$116 for a quarterly walk-forward. A day or a few days of work. **[verified as estimates, LIT]**
- **In practice:** a sceptical baseline and maybe a small volatility input.
- **Main risk:** false confidence from sampled paths, and weights that already saw BTC up to 2024.

### F. Classical ML on Fib, structure and cycle features, with outcome labels

- **Pros:** the right size. CPU in seconds, causal by construction, can be calibrated, explainable, and it answers "how does BTC behave" directly. **[verified, BAKE and LIT]**
- **Cons:** it finds what is there, which so far is volatility. It overfits fast if fed everything (0.2300, slope 0.33). It sees mechanical setups, not your picks. At the 4H scale it has only 380 test setups. **[verified, BAKE]**
- **Our runs:** BAKE's full ladder, 40 null paths per step test and 600 per 4H scale for the lead; `check_causal.py` passes. **[verified]**
- **Cost:** $0, about a minute for BTC, a few seconds per random path, days to promote from spike. **[verified, BAKE]**
- **In practice:** honest odds on any target and stop, and a table of what BTC does.
- **Main risk:** reading calibration as profit; a hidden trial count.

### G. Deterministic NewWave engine + statistics + Bayesian or particle-filter tracking (the master plan)

- **Pros:** exact fit with your rules, a rule trail for every reading, deterministic and cheap to run (a parse takes 6.2 ms at 41 pivots). It is the only option that can express your method of drawing every legal count. **[verified, LIT]**
- **Cons:**
  - A rule-valid count exists on 90-95% of 41-pivot windows on BTC and random paths alike.
  - A growing count predicts little: W5 makes a new extreme 58-66% against 64-68%, and the leg after a legal five behaves as on random paths. Rule flags: 0 of 60.
  - A likelihood built from statistics that sit at null rates is circular (LIT section 11), and "probability the count is true" cannot be checked.
  - Neither parsing nor tracking gives calibrated probabilities on its own.
  - No Elliott engine or paper doing this was found, which is open ground and also a warning.
  - **[verified, EMP, BAKE, LIT]**
- **Our runs:** BAKE's `rules.py` and `enumerator.py` show the deterministic core is small and works. **[verified]**
- **Cost:** $0 and overnight null runs, but 8-14 calendar weeks for a cut-down version and 17-25 for the full plan. Look-ahead bugs are hard for you to catch by reading code, so reviews must be behavioural tests. **[assumed effort, LIT]**
- **In practice:** an annotation and invalidation tracker. It draws your legal counts and cannot say which is right.
- **Main risk:** months of building on a layer that, in every test so far, carries no signal.

### H1. The audit stack (recommended)

Rule checker + barrier formula and small model + a ledger of your calls + Opus at the edges.

- **Pros:** it starts the one sample that cannot be recreated later. It works whichever way the evidence falls, and it needs no signal in the rules to be useful. It is your 23 October idea and your September note made into software, and it uses Opus where its rule record is safe: checking, not choosing. **[assumed]**
- **Cons:** it needs you to log before the outcome, every time, which is a habit and not code. It does not hand you a count. The likely verdict is "not shown". **[assumed]**
- **Our runs:** every part exists as a spike, except the ledger, the Discord link and the weekly report. **[verified]**
- **Cost:** $0 extra compute. Opus through your Max plan. At list price 6 calls a week is about $70 a year. Claude Code days, not months. Your time: 1-2 minutes per call and about 2 hours for the blind test. **[computed; the times are assumed]**
- **In practice:** say your count on Discord and get back, in seconds, the rule it breaks, the odds of your target on volatility alone and the cycle state. Every week you see where your calls beat that number and where they do not.
- **Main risk:** you stop logging. Then this is just a calculator, which is a kill criterion below.

### H2. Engine + ML + narrator, no ledger

The master plan's MVP. **Pros:** a live probability page. **Cons:** it scores mechanical counts, which we already know sit at the volatility floor, and never touches your eye. **In practice:** a nice page that mostly restates the barrier formula. **Cost:** 6-14 weeks, overnight null runs. **Main risk:** percentages that look like edge. **[assumed, from EMP and BAKE]**

### H3. Opus proposes variants, code disposes

R&D-Agent(Q) is a real positive on cross-sections. SEADS: Sharpe 0.96 against 0.62, not distinguishable from rivals. **Cons:** it industrialises after-the-fact stories, every LLM strategy was rejected at budgets up to 100 in one test, and Claude models cheat mostly by editing tests, so the evaluator must be out of reach. **In practice:** useful later, with a counted budget, as a cheap way to generate single-feature tests. **Cost:** modest. **Main risk:** spending your few honest trials. **[verified, LIT]**

### H4. Audit stack plus a JEPA or Kronos column

H1, plus the side tests as one more feature column on the same events and nulls. This is how you get an answer on JEPA without betting on it. **Cost:** H1 + up to $100 and a week. **[assumed]**

### Scores

1 to 5, higher is better, equal weights. Judgement, not measurement. **[assumed; sums and sensitivity from SYNTH `score_sensitivity.py`]**

| Option | Learns BTC-specific | Honest, measurable | Buildable by you | Cost | Useful for trading and product | Fits your rules | Total |
|---|---|---|---|---|---|---|---|
| **H1 audit stack** | 4 | 5 | 4 | 5 | 5 | 5 | **28** |
| F classical ML alone | 4 | 5 | 5 | 5 | 3 | 4 | 26 |
| H4 audit + JEPA/Kronos | 4 | 5 | 3 | 4 | 5 | 5 | 26 |
| H2 engine + ML + narrator | 4 | 4 | 2 | 4 | 3 | 4 | 21 |
| G full engine + particle filter | 3 | 3 | 2 | 4 | 3 | 4 | 19 |
| H3 Opus proposes | 3 | 3 | 3 | 4 | 2 | 4 | 19 |
| E foundation model | 2 | 3 | 3 | 4 | 2 | 3 | 17 |
| D JEPA | 2 | 3 | 2 | 4 | 1 | 3 | 15 |
| A Opus counts | 1 | 1 | 5 | 2 | 3 | 1 | 13 |
| C vision LLM counts | 1 | 1 | 5 | 2 | 3 | 1 | 13 |
| B fine-tuned LLM | 2 | 2 | 2 | 1 | 1 | 1 | 9 |

**How far to trust this table.** H1 ranks first under 83% of random weightings and F under the other 17%. Doubling any one column leaves H1 first. Dropping "useful" ties them. But H1 wins partly by construction, since it combines the parts that scored best. The real choice is F alone against H1, and the difference is the ledger of your calls plus the checker. That is where your own time goes, so it should be judged on whether you will log. **[verified as arithmetic; the scores are mine]**

The product angle, in one line: none of EWAVES ($595 a month), ELWAVE, WaveBasis or MotiveWave publishes calibration (LIT). A tool that scores itself in public and audits a trader's count is open ground, and it stays honest even if the verdict is "no edge". **[verified as to the competitors; the opportunity is assumed]**

## 4. The recommended architecture

```
  bars, 1m to 1D, 3 venues  (done: ewave.data, Hermes cron every 15 min)
        |
        v
  MEASURE, deterministic code
    causal pivots > rule checker > legal readings and their invalidations
    cycle state, live machine only (ewave.cycles)
        |
        v
  LEARN, small math
    barrier formula > recalibrated walk-forward (B3)
    BTC tables: reach rates, depths, speeds, each with its null
    small logistic: only features that passed the gate
        |
        v
  SCORE, append-only ledger, one file per day, keyed by bar
    every forecast stored before its outcome, resolved by code
    side by side on the same levels:
      you | B3 | frozen leads | Opus shadow | later: engine, JEPA, Kronos
        ^                                            |
        |                                            v
  TALK, Opus at the edges                     weekly report to Discord
    your voice note or screenshot > JSON > validator > you confirm
    engine JSON > plain English, every number string-matched
    Claude Code builds and tests all of the above
```

Design, so all rows **[assumed]**.

| Component | Does | Must not |
|---|---|---|
| **You** | The count, your odds, the decision. Your eye is the thing under test | Log after the fact |
| **Rule code** | Name the rule a count breaks, list legal readings, show where they agree and split, track invalidation. R rules only; guidelines stay off until a single one earns it | Choose the count. Claim which reading is true |
| **Barrier formula** | Volatility-only odds on any target and stop. The bar everything must beat | Be called an edge. It is a floor |
| **Small ML** | Recalibrate the barrier, fit tables by walk-forward, test one feature at a time, later fit your own call log | Take a feature without passing the gate |
| **Ledger** | Store every forecast before its outcome, count every variant tried | Rewrite anything |
| **Opus, interface** | Transcribe your count, read your screenshot (levels snapped to bars), narrate JSON (only numbers from the JSON), review your count for rule breaks | Supply a count or a probability that enters a score as truth |
| **Opus, builder** | Write the code and tests through Claude Code, draft rule YAML for your line-by-line review | Edit the evaluator or the frozen definitions |
| **Opus, shadow forecaster** | One logged call a day on post-cutoff bars, scored like anyone else. Low priority, about $80 a year at list, no per-call charge on Max | Be read as skill. At 1-2 independent events a week this catches only big differences |
| **JEPA, Kronos** | Nothing now. Later a capped side test as one more feature column | Delay anything above |
| **Cheap models (Haiku, DeepSeek)** | Narration, if you want it automated hourly: $3-$4 a year | Forecast |

Why volatility and not an engine probability sits in the middle: volatility-only models won or tied at every scale among BAKE's main columns, and the formula needs no training and cannot overfit. An example of what you would see, on Opus run 3's levels (numbers real, layout a sketch, not a call):

```
long 77,793, stop 74,913, target 87,374, within 150 4H bars
  rule check:     names the first rule your labels break, or "legal"
  volatility:     17%   (no time limit: 25%)
  reach table:    1.0 49% | 1.618 31% | 2.618 15%  generic 4H setups, 2013-on
  weekly state:   day 120, phase 0.52, normal zone
                  late-cycle flag opens 2026-12-16, status: under test
```
**[verified: 0.171, 0.245 from SYNTH `today_card.py`, Bitstamp 4H, sigma 0.755% per bar; reach rates from BAKE; day and phase from CYC]**

**How "both can be true" works.** You asked today for a model that learns from history; your 23 October note says a tool should never count for people. They split by use:

- **History study:** the code counts in bulk as a research instrument, and nobody reads its labels as what the market is doing.
- **Live:** your count goes in, and the tool holds it to account. No live "AI count".

What this costs you: a model that "knows" BTC, in the sense you asked for, is not on offer from any option here. What is on offer is measured statistics and an accounting of your own calls. **[assumed; follows LIT section 9 and BAKE decision 6]**

## 5. The plan

**Why this order.** Code can be written any time. A forecast not logged today can never be logged. So calendar time is the scarce resource, and logging starts first. LIT's parser-first and EMP's logistic-first both make sense as engineering. I put them second and third for this reason. **[assumed]**

### First two weeks

| Day | Deliverable | Reuses | Who |
|---|---|---|---|
| 1 | **Frozen leads file:** the seven leads below, exact definitions, a digest, dated. Forward scorer on bars from 2026-10-31 | `ml_leads.py`, `c2_followups.py` | Claude Code |
| 1-2 | **`barrier` module and CLI:** odds for any target, stop and H, on Bybit by default, with tests against Monte Carlo | `ml_features.barrier_prob`, `barrier_check.py` (bake scratch) | Claude Code |
| 2-4 | **Rule checker, R rules only**, as YAML plus code, with numbers and section IDs and no course text, since the repo is public. Half a day for you to review it line by line | `rules.py`, `enumerator.py` | Claude Code, you review |
| 3-5 | **Call ledger:** append-only, one file per day, schema validated, resolves itself on each sync | | Claude Code |
| 4-6 | **Discord link:** voice or screenshot > Opus > JSON > snap to bars > you confirm > ledger, reply in seconds | Lily | Lily, Claude Code |
| 6-8 | **Blind chart test:** 40 masked windows, 20 real BTC (no famous stretches) and 20 trend-flip paths. For each: count or "unclear", real or random, confidence. 10 of them repeat a week later | `nulls.py`, `windows.py` | Claude Code builds, you take it, about 2 hours |
| 8-10 | **Variant ledger:** backfill this round's trials. One evaluation entry point, every call a row | | Claude Code |
| 10-14 | **Weekly report v0** to Discord: calls, rule breaks, hit against barrier, plan followed or broken | | Claude Code |
| 14 | **Gates G0 and G1** read; you decide on the open questions | | You |

The seven frozen leads: late-cycle flag (`w_in_window`, 4H k3 and k4); top left of midpoint then a lower low; live mid-cycle up-structures; linear 1.618 extension; the step at 1.0; W4 at 0.236-0.382 on up-impulses at 4H and up; alternation. No new tuning on any of them, ever. Freeze the file with a dated commit on a branch when you say so, because a push to `main` deploys the site. **[assumed choice, from EMP and BAKE]**

The blind test is the cheapest direct measure of your eye there is. Opus never refused a random path in 15 tries, and its confidence differed by 0.03. If you tell them apart, or say "unclear" more often on random paths, that is something no mechanical test here could see. Real windows must get the same re-chaining as null paths, so the candles give nothing away; LIT disclosed that defect in its own pilot. **[assumed; the Opus numbers verified, BAKE]**

### What you log, so the system learns your edge

Your sample grows every week and belongs only to you. Log calls as well as trades: every count with a target and an invalidation is a forecast, traded or not, which is how you get past the 30-40 trades problem. **[assumed]**

**You say it** (a minute by voice, before the outcome):

1. Main count: pattern, degree, last printed wave, next move.
2. Alternate count, the same. Keep it even if you barely believe it.
3. For each: invalidation, target zone, time limit in bars.
4. Your odds: chance of target before invalidation in that time, plus an other/unclear share.
5. Sub-waves of 1, 3, 5 checked one timeframe down: yes, partly, no.
6. Your evidence, in tags: TDI read (3-5 divergence, shark, zone), Fib confluence, and your own cycle read, including where you mark the weekly and daily low.
7. Call only or trade. If a trade: strategy name, entry, stop, size in R, take-profit plan.

**After a trade:**

8. Plan followed or broken, which rule, stop moved or not, exit reason, one word on your state.

**Whenever it happens:**

9. A count flip, and why. A flip closes the old call.

**The system fills in by itself:** timestamp and bar, venue, the rule check and the first rule broken, the time-minimum check, how many legal readings exist and whether yours is one, barrier and geometry odds on your levels, weekly and daily state, volatility regime, then later the outcome, time to outcome, max favourable and adverse move, and R result, plus the engine version.

**Counting rule, so the sample is honest:** at most one open call per degree and direction. Standard errors come from whole weeks resampled, not single calls. **[assumed]**

**What comes back each week:**

- Your hit rate minus the barrier's odds on the same levels.
- Your stated odds against what happened.
- The same split by strategy, degree, direction and weekly zone.
- Plan followed against plan broken, in R.
- Your flip rate and your rule-break rate.

That is "where the bias lives". Plan-followed against plan-broken needs no market edge at all to pay off.

### Phases

Plan, so all rows **[assumed]**.

| Phase | When | Deliverables | Your time |
|---|---|---|---|
| **A. Audit v0** | Weeks 1-2 | The table above | About 5 hours, plus 3+ calls a week |
| **B. Measure** | Weeks 3-8 | One evaluation harness with the null set below. B3. BTC behaviour tables with nulls on all three venues, including ETH as the first test of "own Fibonacci". Volatility forecast (HAR) for stops and sizing. Opus shadow arm. Private chart overlay for the card | Reading, a few hours |
| **C. Checker v1** | Months 3-6, only as needed | Hard-rule parser for impulse, zigzag, flat on 1H and 4H. Legal readings with invalidation and "where they all agree" as one test feature. Then guidelines and TDI one at a time through G3 | Reviewing behaviour, not code |
| **D. Your model** | From 165 resolved calls | Your excess over the barrier by condition. A logistic on your calls with at most 3 features until 300 calls. This is the real "teach the model": what separates your good calls from your bad | None beyond logging |
| **E. Side tests** | After B, each capped | Kronos-mini kill test ($0, 6-20 hours at low priority, alone on the box). TTM + log-HAR on volatility. JEPA under $100. Each is one more column in the harness | A few hours to read |

**Null set from here on.** At swing scale: per-bar sign flip (volatility only), trend flip +-60 days (volatility and slow trend), block as long as one median leg. At cycle scale: 20-day and 60-day blocks. At least 200 paths. A block longer than the swing under test copies the swing, so it cannot test it. **[verified as reasoning, LIT section 7]**

### Go/no-go gates

Thresholds are proposals to freeze at day 1. Every n assumes independent events, so it is a best case, and G4 assumes base odds near 0.30 (165 calls; 147 at 0.25, 188 at 0.40). LIT section 6 holds a stricter version (SPA, paired t at least 3, deflated Sharpe) to apply before any public claim of edge. **[assumed thresholds; arithmetic from SYNTH `power.py`]**

| Gate | When | Test | Pass | Otherwise |
|---|---|---|---|---|
| **G0 Habit** | Day 14, week 6 | Calls logged before outcome | 10 by day 14, then 3+ a week | Stop the "your edge" track. Keep the checker and barrier as on-demand tools |
| **G1 Your eye, blind** | Day 14 | Real or random on 40 windows | 27+ correct (p 0.038; 70% power if your true rate is 70%) | "Not shown". Then a confident count is not evidence by itself. Repeat in 12 months on fresh windows |
| **G2 Causality** | Every build | Truncate, rewrite the future, planted leak | All pass | Every result since the last pass is void |
| **G3 Structure against volatility** | End of B, then yearly | One feature alone on B3 + volatility, walk-forward 2017+, at 4H k3, 4H k4, 1H k6 | **Edge:** Brier gain at least 0.007 at 2 of 3 scales (about what 635-735 setups can detect, 31/n), above the 95th percentile of sign-flip and trend-flip nulls, same direction on log loss, calibration slope 0.7-1.3. **Context only:** at least 0.003 at 2 of 3, above the nulls, shown labelled "under test" | Below 0.003 or inside the nulls: the feature stays out. **If nothing passes, stop treating the probabilities as edge, and the engine stays an annotation and invalidation tracker** |
| **G4 Your calls against volatility** | 50, 165, 400 resolved calls | Mean of (hit - barrier odds), plus paired Brier against B3 | At 165: lower 95% bound above 0, about +7 points or more. At 400: about +4.5 or more. Then Phase D and a profit test | At 165: upper bound below +5, about -2 or less: your counts add nothing beyond geometry. Keep logging for discipline, and stop letting the count set size. In between: go on to 400, and at 400 about +0.5 or less is final |
| **G5 Late-cycle flag** | From 2026-12-16 | Frozen flag, 4H k3 setups, forward | After 32 inside setups (about 2 years): gap -7 or lower keeps it as a caution (a true -14 is 1.7 se). A claim needs 69-87 inside setups, 4-5 years | Gap at 0 or above after 32: drop it (a true -14 would do that only 4.5% of the time) |
| **G6 Live calibration** | 300 events, about 1.1 years at the 24h rate | B3 mean calibration | Within +-5.8 points (LIT) | Fix or stop showing percentages. Below zero skill at 820 events (about 3 years): stop for good |
| **G7 Side tests** | Each | Same events, same nulls, plus an untrained encoder, plus HAR for volatility | Brier gain at least 0.007 as in G3, or beats log-HAR on QLIKE by at least 2% | Killed. One test each, cap $100 for JEPA. An embedding that easily predicts the calendar year is an era detector: kill it |
| **G8 Full engine** | After G3 and G4 | Triangles, combinations, nesting, particle filter | Only if a structure feature passed G3 Edge, or G4 passed and your report shows you need it | Stay with the checker |
| **G9 Money** | Only after a pass above | Walk-forward with costs and funding, separate from all of the above | Survives costs | No real size on it |

Two checks of this table against today's evidence. Fib, TDI and rule flags already fail G3: raw gains run from -18.1 to +5.3 x 1000, 21 of 30 negative, the top one on the thinnest scale. **[verified, read from BAKE's table]** The late-cycle flag gets "Context only" and not "Edge": +3.7 and +3.9 x 1000 at 4H, +1.7 at 1H. **[verified, BAKE]**

A note on expectations for G4. The only public grade of a famous Elliott forecaster we found is poor: Prechter 20.8% on 24 forecasts, lowest of 68 gurus, with CXO's own "very low" confidence. It grades a person, not the method, and says nothing about you. **[verified, LIT section 5]**

**Kill criteria, all at once:**

- You stop logging for 4 weeks.
- 12 months pass with no gate above G2 passed: freeze building, keep sync, ledger and checker.
- JEPA goes over $100, or any side test delays Phase A or B.
- Phase C runs past 14 weeks with no feature through G3.
- Anyone, human or agent, edits a frozen definition or the evaluator without a new version and a ledger row.

**What this implies for the repo rules** (not changed; your call):

- `CLAUDE.md` goal 2: the "1-2 most probable counts" stay as readings, and probabilities attach only to level outcomes.
- The build order puts the ledger first.
- The null rule becomes the set above.
- The reason for "never the LLM" changes from "it breaks rules" to "not repeatable, not testable, not selective".

LIT section 11 lists 17 corrections to the master plan.

## 6. What to stop believing or doing

Said plainly, because you asked for that in your own rules. None of this says you cannot trade. It says what the chart has not earned. All of it is tested on mechanical counts, not on your eye. **[verified as measured]**

1. **"BTC has its own Fibonacci that a model can learn."** Keep Fibonacci as your planning language for targets and invalidations, since consistency has value. Stop reading a pullback landing on 0.618 as evidence for the count. It lands there as often on random paths, and 58% of legal W2s go deeper. (EMP B2)
2. **"The structure finished at the weekly low, so the low is in."** You will always find one: 34% of all days have a legal 5-wave within two weeks at some degree, 85% with zigzags. (EMP C3)
3. **"The middle of the weekly cycle is a top."** Not shown, and tops there hold worse. (EMP C1, C5)
4. **"A legal count is evidence."** Rules eliminate; they do not point. Every window has legal readings both ways, and a legal five says nothing about the next leg. (BAKE, EMP A3) Keep the rules for what they do well: killing a count and telling you when you are wrong.
5. **"Shark in the water and 3-5 divergence confirm the top."** The pattern and the divergence appear as often on random paths (54-70% against 55-68%), and the apparent edge is the arithmetic of a short W5. "Almost always" is not what the mechanical test shows. (EMP D) Your reading of it may be better. Log it and see.
6. **"Let me ask Claude what the count is."** It will give a good-sounding answer on any chart. Ask it instead what your count breaks, and what the strongest legal alternative is. Do not take its confidence or its probability as information. (BAKE)
7. **"An AI should run through the whole history."** On Opus that cannot produce evidence, because it remembers. On anything bigger, one path is too few, and the part that is learnable is small. Stop waiting for a bigger model to find what one path may not hold. And be wary of the headlines: "93.94%" is 49.32% on raw prices, and Kronos's "93%" is RankIC 0.0267 against 0.0138. (LIT)
8. **"Three months of trading tells me if the method works."** At 30 trades you need 21 wins for p below 0.05, and a true 55% trader shows 50% or less 35.5% of the time. An edge of 0.10 R needs about 400 independent trades. Your September note was right, and the rulebook's 3-month window sits against it. (LIT)
9. **The cycle boxes as forecasts.** Daily boxes catch the next low 7% of the time against 7-8% on random paths, weekly 5% against 12-16%. The 4-year box ($16,547 to $28,327) is the rule's output on n = 3. Keep the overlay as a map. Do not size from it. (CYC)
10. **The full master plan as the next step.** The particle filter, nesting and learned weights have no measured signal to work on yet. They can come back through G8.
11. **Any "AUC 0.7" or "win rate above 60%" from anyone, including this repo, without a null and a barrier baseline beside it.** A near target and a far stop win on any path. Compare your win rate to 1 / (1 + reward:risk) first: 33% at 2:1, 25% at 3:1.

What you can keep believing: invalidation discipline, holding two counts, and treating unsure as corrective all cost nothing and are not refuted here. Volatility really is forecastable, so sizing and stops in volatility units are on firm ground (R2 0.35-0.56, EMP). Falls are faster than rises (EMP A0). The previous swing extreme matters (EMP B1). Alternation is real, if tiny. And your eye is still an open question. **[verified where cited; the rest assumed]**

## 7. Open questions only you can answer

1. **Is the reading right?** "Jev" = JEPA, and "weekly cycle" = Camel's 24-42 week cycle. If either is wrong, tell Lily, because the weekly section changes.
2. **Will you log before the outcome, 3 or more calls a week, including calls you do not trade?** Everything in the audit stack rests on this, and no code can fix a no. If 3 a week is unrealistic, say the real number: 2 a week means about 19 months to G4.
3. **Private or public?** Should the forward log and your scored calls stay private, or do you want a public track record on elliott.yaga.sh as the product? My default until you say otherwise: private, in gitignored `data/`, because this repo is public and a push to `main` deploys.

## Where I disagree with the workers, and why

1. **BAKE, "BTC's extension curve comes out almost the same on 20-day block paths".** The table is good; that inference is weak. A 4H k4 leg lasts about 4 days (EMP A1), so a 20-day block holds several legs and copies them. LIT section 7 shows the block column flags nothing whenever the block holds several swings. So "same as block paths" would come out whatever BTC did. I keep the table as description and rest "no Fibonacci" on EMP's nulls, which use a block of one leg, sign flip and trend flip. The 60-day block is fair for the weekly lead, since it is shorter than the cycle.
2. **BAKE, "0 of 60" against both nulls.** The same objection applies, but the conclusion survives without the block null, because the raw gains themselves are at or below zero on most rows (21 of 30 negative, 2 zero).
3. **BAKE, "a couple of years" to confirm the weekly flag.** Two years gives about 32 inside setups at 4H k3, 1.7 standard errors on a true -14 point gap: a hint. A claim needs 69-87 inside setups, 4-5 years, and they overlap in time, so it is likely longer (`power.py`).
4. **BAKE's scope for the lead.** Its three lead-test scales all use larger swings. On small 1H swings the lead nearly vanishes (-2.0, -2.5), and the 2013-2016 holdout fails at the 8% reversal (+0.6). It is narrower than the summary reads (`flag_replication.py`).
5. **LIT, JEPA "after the engine exists".** It does not need the engine. The generic setups and barrier labels in BAKE's pipeline are enough for a probe. It needs the harness, so it can run after Phase B if you want the answer sooner.
6. **LIT, the locked holdout from 2022-11-22.** EMP's era tables and BAKE's by-year tables have now looked at those years, and this round ran thousands of tests. It is no longer clean for today's leads, though it may still serve for the parameters of a future engine. For anything found today, only forward data counts. EMP says the same.
7. **LIT's two first-look Fibonacci leads** (W2 lift 1.15, W4 lift 0.80). I side with EMP's result: a real rule checker, 1,106 impulses, better nulls, 1,000 paths. LIT itself says not to lean on them.
8. **Ordering.** LIT says parser first, EMP says logistic first, BAKE says barrier first. I start with the ledger of your calls because that is the only thing that cannot be done later.
9. **PLAN's particle filter and "1-2 most probable counts".** Deferred. LIT's points 11-12 and EMP's stage table are the reason. This is the largest change to the master plan, and it is your decision.

## Numbers checked

Each was read in the worker's report and matched against its raw output, using read-only lookups on 2026-10-30. Scratch paths are under `/opt/data/cache/scratch/elliott_research_r1/`.

| Number | Report | Raw source |
|---|---|---|
| 0 hard breaks, 114 counts (42+36+18+12+6), 824 labels | BAKE | `bake/llm_tables.md` |
| Same state 62% / 33% / 30% | BAKE | `llm_tables.md` |
| Confidence 0.46 / 0.43, other 0.27 / 0.30, 15 calls | BAKE | `llm_tables.md` |
| Brier 0.181 / 0.171; next move 63% of 35, 20% of 15 | BAKE | `llm_tables.md` |
| $0.22 a call, 7,711 mean output tokens; $250, $7,300, $29,000, $1,900 | BAKE | `llm_tables.md`; recomputed in `power.py`: $246, $7,329, $29,316, $1,927 |
| Inside / outside 19.0 / 33.2, 14.0 / 28.7, 16.8 / 26.5 | BAKE | `bake/ml/leads_*.json`: 0.190 / 0.332, 0.140 / 0.287, 0.168 / 0.265 |
| Holdout 25.8 / 40.0, 17.4 / 37.0, 17.0 / 26.1 | BAKE | Same files |
| Flag gain +3.7, +3.9, +1.7 x 1000 | BAKE | Same files: 0.00375, 0.00394, 0.00175 |
| Brier 0.2105, 0.2019, 0.1942, 0.2034, 0.2045, 0.2059, 0.2300, 0.2057 at 4H k4 | BAKE | `bake/ml/report.md` |
| W2 17.6 / 17.5; W4 41.9 / 41.3; n 1,106 | EMP | `emp/b2_windows.csv`: 0.1763 / 0.1752, 0.4186 / 0.4126 |
| Independent legal 17 / 59 / 188 / 219 | EMP | `emp/tables.md`, from `census_btc.csv` |
| 75% against 57-70%; 100% against 100% | EMP | `emp/c_metrics.csv`: BTC 0.75; shuffle 0.571, block 0.696, signflip 0.619, trend 0.652 |
| Spectral 1.90 / 0.97; 2.28, 1.77, 0.69 | EMP | `emp/c2_spectrum.csv`: 1.901, signflip 0.968; 2.279, 1.773, 0.693 |
| Kronos-mini Brier 0.3065 / 0.25 | LIT | `lit/research_notes/.../ts_foundation_models.md` |
| 30 trades: 21 wins, 7.4%, 35.5% | LIT | `lit/scripts/sample_size_derived.out.txt` |
| 17 of 172; 64%, n = 14, against 36-38% | CYC | Report tables, and the shared brief |

All matched. Findings from the check: "57" in EMP's 57-70% is the shuffle null only, and the nulls that keep volatility give 62-70%. BAKE's 1,117 and 133,254 call counts multiply out to its dollar figures.

## Status of this round

- **Verified:** every number above is from a named report or from SYNTH. No worker report was missing or partial.
- **Assumed:** the scores, gate thresholds, effort and time estimates, "jev" = JEPA, and a zigzag as a stand-in for a trader's swings.
- **Unknown:** whether your eye adds information. Whether the late-cycle lead is real. Whether JEPA or Kronos beats volatility on this target. Whether anything pays after costs. Whether assets differ in their ratios.
- **Not done:** no trades were simulated beyond BAKE's size-of-effect figures. No JEPA or foundation model was trained or run. LIT's web search budget ran out, with gaps listed in its section 13.
- **Not changed:** nothing outside `research/model-options/RECOMMENDATION.md` and `README.md` in this repo. SYNTH scripts stay in scratch.
