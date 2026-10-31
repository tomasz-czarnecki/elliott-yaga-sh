# 01. Literature: teach the model BTC through statistics, not bigger models

Research round `elliott_research_r1`, literature stream, 2026-10-30. Question: how can a model be taught how BTC behaves in Elliott Wave and Fibonacci terms, what does the literature say about each approach, and how do they compare?

## Summary

1. **"Jev":** most likely JEPA (Joint Embedding Predictive Architecture, LeCun's world-model line); the nearest alternatives are time-series foundation models such as Kronos, Chronos and TimesFM; no AI model called JEV was found, and only he can confirm what he meant. [verified as a search result]
2. **BTC itself:** direction is close to unpredictable up to a day (out-of-sample R2, share of variance explained, about 0; hit rates 51-56%), volatility is predictable (R2 about 0.50), and no source opened shows after-cost value on BTC direction that significantly beats buy and hold. [verified]
3. **JEPA:** no BTC or crypto JEPA was found; the largest walk-forward benchmark (US equities) gives LeJEPA a RankIC (rank correlation of forecast and outcome) of 0.0204 against 0.0170 for an untrained encoder and 0.0311 for supervised training; STOCK-JEPA is a real positive (RankIC 11-13%, net Sharpe, return per unit of risk, 1.24-1.50) on one test period. [verified]
4. **Opus direct:** a small pilot found Opus 5.5 remembers BTC: 40-day windows indexed to 100 with no dates (the prompt did name BTC) that it flagged as recognised were dated to the exact month 34 of 34 times and their next 30 days called right 34 of 34, then nothing on post-cutoff windows, so any replay before its June 2026 cutoff proves nothing, and the bake-off worker saw the same independently; rule compliance on text grids was a real positive (0 of 35 hard-rule breaks), repeatability and abstention were not. [verified, 3 runs]
5. **Fine-tuning:** Opus cannot be fine-tuned and no Claude model can be newly fine-tuned; on open models, nothing was found where a fine-tuned LLM on prices beats a naive forecast under walk-forward with costs. [verified as far as searched]
6. **Foundation models:** 2 of 43 beat persistence on raw error in the largest finance benchmark; in the largest study with costs every long-short strategy goes negative at 20 bps; Kronos's own 308 days of public BTC forecasts score a Brier (squared error of a probability, lower is better) of 0.3065 against 0.25 for a coin; the useful part is volatility, where a TTM plus log-HAR blend (a small foundation model plus a simple volatility regression) is the finding worth copying. [verified]
7. **Classical statistics and ML:** the best fit for what he asked, because ratio tables, hazard curves and a small logistic model answer "how does BTC behave" directly on a CPU; expect a filter, not an edge: AUC (chance a random win scores above a random loss) of 0.52-0.58 is the fair target [assumed], while slow moving averages cut drawdown (-85% to -64/-70%) with no significant Sharpe gain and one hourly filter reached Sharpe 1.09 against 0.82, also not significant. [verified]
8. **Elliott and Fibonacci literature:** it has mostly tested the wrong object: stock swings and levels show no Fibonacci excess, the famous 93.94% accuracy is 49.32% on raw prices, no study tests wave pairs with a frozen labeller and a sound null, and "every asset has its own Fibonacci" is unsupported, not refuted; the weekly-cycle lead in cycles-r1 (64%, n = 14) stays a lead. [verified among sources opened]
9. **Structured engine:** a rule-valid count exists on 90-95% of 41-pivot windows on BTC and on random paths alike, so passing the rules is no evidence; a deterministic chart parser is still cheap (1.6e18 parses summed in 154 ms) and is the right measuring tool, with Opus writing code, drafting rules and proposing logged variants, never counting. [verified on a small pilot grammar]
10. **Overall read:** build the honesty machinery and the parser first, then ratio tables and a small outcome model; run JEPA and Kronos only as capped side tests; the history can reject claims of about 5 points at 1H/4H and little smaller, so the likeliest answer is "not shown", which is not "no effect", and the tool still holds his own counts to account. [assumed ranking, reasoned from the above]

## How to read this

Tags: **[verified]** read in a source that was opened, or computed by a named script. **[assumed]** a choice or premise not tested. **[unknown]** could not be established. Own-run numbers name their script; all scripts sit in `/opt/data/cache/scratch/elliott_research_r1/lit/scripts/`. "Not found" means not found in this search, never "does not exist". All own runs are small first looks, not pre-registered tests (section 12). Rule references cite sections of his NewWave compact rulebook and paraphrase only. Costs are in bps (hundredths of a percent).

## 1. JEPA and world models: real and moving fast, but built to discard what a directional trader wants

**1. What it is.** An encoder turns a window of data into a vector; a predictor guesses the vector of a hidden or future window from the visible one. It never rebuilds the raw data, so it can ignore detail it cannot predict. Training needs an anti-collapse device, either a slowly updated copy of the encoder ([I-JEPA](https://arxiv.org/abs/2301.08243), [V-JEPA](https://arxiv.org/abs/2404.08471)) or a Gaussian penalty ([LeJEPA](https://arxiv.org/abs/2511.08544)). No labels. Value is measured by a small probe fitted on the frozen encoder. [verified]

**2. How it would apply to this repo.** All design choices [assumed]:
- Series: Binance spot from 2017-08 (about 322,000 15m windows), Bybit perp as a check. Bitstamp before 2017 is excluded: its thin-market bounce is an easy slow feature.
- Inputs: 15m tokens of scale-free features (return over trailing volatility, range over ATR, close position, log volume ratio, realised volatility from 1m bars, `hl_order`). Hour-of-week goes to the predictor only, copying [S2S-JEPA](https://arxiv.org/abs/2610.03106).
- Windows: context 96-192 tokens, target the next 16 (4 hours), causal encoder, SIGReg penalty, at most about 300k parameters first ([TFWM](https://arxiv.org/abs/2610.09048) found ViT-Tiny beat ViT-Base at 10x the compute).
- Causal: 10 yearly folds; normalisers, encoder, probe and calibrator fitted only before each test year, minus a purge; a test that changes bars after t and checks the embedding at t does not move.
- Probes: next 4h realised volatility; +k ATR before -k ATR within H; later the engine's "target before invalidation".
- Must beat: HAR (forecast volatility from recent daily, weekly, monthly volatility) plus hour-of-week, ridge on the raw window, a random untrained encoder, and the same pipeline on null paths (see section 7 for which nulls).
- Output: at most 3-8 numbers as one more field in the engine's JSON. The engine stays the only thing that counts.

**3. What it would learn and what it cannot.** Every claim here is **[assumed]**, because no JEPA was trained on BTC.
- Would learn, roughly in order: volatility level and clustering, time-of-week activity, volume state, era and venue micro-features. Reasoning: [Littwin et al.](https://arxiv.org/abs/2407.03475) show JEPA favours high regression-coefficient features in deep linear models, and on BTC those coefficients are +0.70 for log volatility, +0.45 for absolute return, -0.07 for return and about 0 since 2021 (`jepa_predictable_part.py`, 479,136 15m windows). [Mahns et al.](https://icml.cc/virtual/2026/poster/65643) (abstract only) saw the same on 500 stocks.
- Cannot learn: return direction if it is not there, wave labels, Fibonacci as a concept, anything needing more independent regimes than one path offers. It cannot count or explain itself. Action-conditioned planning has no use, since his size does not move BTC.

**4. The evidence.** Nothing was found on BTC, crypto or order books. [verified as a search result]

| Source | Data and design | Result | Rigour |
|---|---|---|---|
| [Merchant et al. 2026, TFWM](https://arxiv.org/abs/2610.09048) | US equities, 1 Hz, 2008-2025, 32 eval months, each on 6 prior months | RankIC of returns at 15m: supervised 0.0311, TimesFM 3.0 frozen 0.0232, Chronos-2 frozen 0.0230, TS2Vec 0.0205, LeJEPA best 0.0204, ridge 0.0196, Kronos frozen 0.0171, **random untrained 0.0170**, I-JEPA 0.0103. Volatility: LeJEPA 0.0721, ridge 0.0707, random 0.0694, HAR 0.0639 | Causal fit; hyperparameters from 5 months across the sample (mild look-ahead); frozen foundation models not restricted to prior data; month explains 97-99.9% of variance; 2,448 portfolio settings; friendly authors; no replication |
| [Luo et al. 2026, STOCK-JEPA](https://arxiv.org/abs/2610.07006) | 5,669 China + 10,152 US stocks, daily, test Jan 2024 to Jun 2026 | **RankIC 11.22% / 12.96%, net Sharpe 1.50 / 1.24.** Ordinary JEPA 9.17 / 9.05, Sharpe 1.01 / 0.50. Plain JEPA baselines -3.77% to 4.09% | Best positive; one split, 5 bps only, no impact or borrow; US book max drawdown -40%; baselines at most 12 epochs, may be under-trained |
| [Wang 2026, Fin-JEPA](https://github.com/cedricwyh/fin-jepa/blob/main/docs/jepa_paper.tex) | 6,230 equities, daily | AUC 0.484-0.496; loss 10.1% better than identity, no return signal; author says so plainly | Honest negative; single author, unreviewed |
| [Petersen et al. 2026, HEPA](https://arxiv.org/abs/2605.11130) | 14 benchmarks, includes VIX regime | Wins 10 of 14; VIX regime AUC 0.57, tied with a masked autoencoder, above PatchTST 0.48; ECE (calibration error) 0.310; C-MAPSS latent tracks time-to-failure at +0.97 | Authors' own; volatility target, not returns |
| [Feng et al. 2026](https://arxiv.org/abs/2609.31680) | 11 non-finance benchmarks, 9 backbones | JEPA pretraining improved mean absolute error in 24 of 49 cells, mean -0.12% (computed from its tables) | Best test of forecasting pretraining: a coin flip |
| [Dong, Mengaldo 2026, S2S-JEPA](https://arxiv.org/abs/2610.03106) | ERA5 weather, test 2023-2025 | Weeks 5-6 correlation 0.238, 0.230 vs ECMWF 0.202, 0.181; worse at week 3 | Fair positive in a low-predictability domain, but weather's slow modes carry the target itself |

- Supervised and reference points: [Jiang, Kelly, Xiu draft](https://www.kuntara.net/uploads/1/1/4/9/114945401/ssrn-id3756587-3.pdf): gross Sharpe 7.2 equal-weight, 1.7 value-weight weekly, turnover 690%+. [Gu, Kelly, Xiu](https://www.nber.org/papers/w25398): monthly stock R2 0.33-0.40%. [Nagel 2025](https://bpb-us-w2.wpmucdn.com/voices.uchicago.edu/dist/f/575/files/2025/07/Complexity_2.pdf) reduces "virtue of complexity" to volatility-timed momentum in its setting. [verified]
- LeCun's agenda: the 2022 position paper is a blueprint with no experiments or dataset. It could not be opened (blocked) and is described from a secondary summary. AMI Labs raised $1.03B in March 2026 to build world models ([TechCrunch](https://techcrunch.com/2026/03/09/yann-lecuns-ami-labs-raises-1-03-billion-to-build-world-models/)). That is money and intent, not evidence on markets. [verified as news]
- Time-series and signal JEPAs: mostly self-reported, mixed against simple baselines. [TS-JEPA](https://arxiv.org/abs/2509.25449) (workshop): FordA 91.5 vs supervised Transformer 91.8 and TS2Vec 86.4; short-term MSE (squared error) worse than an autoregressive model on 2 of 3 sets. [LaT-PFN](https://arxiv.org/abs/2405.10093): ECL MSE 0.32 vs ARIMA 0.44, but ETTh1 0.59 vs ARIMA 0.44, ETTh2 tied. [T-JEPA](https://arxiv.org/abs/2410.05016) (tabular): authors say most deep methods match or beat GBDT once augmented; among the worst on stocks in STOCK-JEPA's table. [Signal-JEPA](https://arxiv.org/abs/2403.11772) (EEG, "preliminary"): below literature on 2 of 3 paradigms, different subject sets. [ECG-JEPA](https://arxiv.org/abs/2410.08559): AUC 0.912 vs ST-MEM 0.882, self-reported; the [independent FOUND-AF benchmark](https://arxiv.org/abs/2608.03597) (abstract) names another model the consistent winner. [SC-JEPA, formerly MTS-JEPA](https://arxiv.org/abs/2602.04643): best on four anomaly-prediction sets, by about 1 point over TS2Vec on SWaT, numbers from v1. [Brain-JEPA](https://arxiv.org/abs/2409.19407): abstract only, numbers not read. In [Phys-JEPA](https://arxiv.org/abs/2606.16076)'s own table DLinear wins 7 of 8 rows. [verified]
- Known bias: [Sobal et al. 2022](https://arxiv.org/abs/2211.10831) (abstract only): JEPA holds up against distractor noise that changes every step and fails on noise that stays fixed, so slow, stable distractors are its weakness. On BTC those would be era and the current volatility level [assumed]. Test: probe the latent for calendar year; if that is easy, the encoder is an era detector.
- Generative world models and market simulators: [Quant GANs](https://arxiv.org/abs/1907.06673) (abstract), [FTS-Diffusion](https://proceedings.iclr.cc/paper_files/paper/2024/file/f90fc76b199fe6b0ec2a51aaf72c3277-Paper-Conference.pdf) and [MarS](https://arxiv.org/abs/2409.07486) (abstract) report stylised facts in self-reported comparisons. None is validated on BTC to this repo's standard, and MarS needs order data the repo lacks. As a null they carry a specific danger: a generator trained on one path can copy the wave structure under test, so keep simple nulls [assumed]. FTS-Diffusion's scale-invariant patterns are the nearest thing here to Elliott's idea, tested only as forecasting augmentation on three daily series.
- A rank IC of 0.03 does not travel to one asset: gross edge about 0.03 x 15 bps = 0.45 bps per 15m bar, against about 5 bps of cost at a flip every other bar. [computed, Gaussian assumed]

**5. Data needs vs BTC.** Vision JEPAs use millions of samples (V-JEPA 2: 22M videos), Fin-JEPA 2.07M windows, TFWM about 16M views per fold. BTC has 479,000 overlapping 15m windows since 2013-03, but the part that is predictable (volatility) behaves like 41 (raw) to 2,202 (less a trailing 30-day mean) independent samples (`jepa_predictable_part2.py`). Riley sample sizes for a probe, shrinkage 0.9 (`jepa_predictable_part2.py`): true AUC 0.55 needs 1,144 events for 1 feature, 3,432 for 3, 9,152 for 8, 73,210 for 64; AUC 0.60 needs 285, 854, 2,276, 18,203. With 2,320 1H legs an 8-number probe only works if true AUC is at least 0.60. Riley's criteria assume independent patients, so real needs are higher. [computed]

**6. Compute and money.** One 10-fold run: 295k parameters about 45 hours on this CPU, 1.57M parameters about 235 hours (9.8 days), a quarter of that at an hourly stride. Rented RTX 4090: 3.5-8.1 h, $1.18-$2.76 community, $3.10-$7.22 secure. A small honest grid (8 configs x 3 seeds): $28-$173. A cap of $100 is enough for a first answer (`jepa_cost_calc.py`; rates [assumed], prices [verified], see section 7).

**7. Effort with Claude Code.** 1-2 days to generate a harness, 1-3 days to run and check, plus renting a GPU. The hard part is reading warning signs (collapse, random-encoder floor, leak tests). An [independent LeWorldModel reproduction](https://arxiv.org/abs/2608.10145) needed four conventions found in no released config. Without engine labels only volatility and barrier probes can run. [assumed; reproduction verified]

**8. Main risks.** A latent that learns era or volatility level and looks healthy (Fin-JEPA's falling loss); leakage from an encoder fitted on all history; many view types and one lucky test period; miscalibration (HEPA's 0.310); decay (the published BTC candle-turn effect, 0.88 bps in 2021, is gone by 2024 on two venues, `jepa_toc_check.py`, a quick check, not a full replication); delay to Phases 1-5, which any outcome label needs anyway. [verified where cited, otherwise assumed]

**9. Verdict.** **Do not build on JEPA: it would most likely rediscover BTC's volatility state; keep it as a capped side test (under $100) after the engine exists, killed unless it beats HAR plus the engine on log loss out of sample; if ever built, anchor it on the engine as a prior, the one design with a positive result.**

## 2. LLMs used directly, with fine-tuning: excellent builders, contaminated forecasters

**1. What it is.** Direct use: prompt a frontier model with rules and prices and ask for a count, a probability or a trade. No training. Fine-tuning: a LoRA (a small trainable adapter on top of frozen weights) shifts a text model's token-to-token mapping toward your examples. [verified]

**Availability, read 2026-10-30.** No Claude model can be newly fine-tuned: the only one ever listed, Claude 3 Haiku, reached end of life on 2026-09-10 and legacy models accept no new jobs ([AWS lifecycle](https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle.html), [legacy page](https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle-legacy.html)). OpenAI is winding its platform down and is closed to new organisations ([OpenAI](https://developers.openai.com/api/docs/guides/model-optimization)); Mistral marks its service deprecated ([Mistral](https://docs.mistral.ai/capabilities/finetuning/finetuning_overview)); Gemini tuning is still open ([Google](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-supervised-tuning)). Open weights are the real route: Qwen3.8-27B (Apache 2.0), DeepSeek V4.1 Flash (MIT), LoRA from $0.34 per million training tokens at the 7-14B class ([Together](https://www.together.ai/pricing)). Adapters die with their base model. [verified]

**2. How it would apply to this repo.** [assumed design] Two modes, engine always the source of truth.
- Before the cutoff (2026-06-30 for Opus 5.5): grammar and consistency tests only, flagged `contaminated=true`, never a skill number. Use: which rules it breaks, windows where runs split, engine bugs, hindsight drafts for `gold/`.
- After the cutoff: a small frozen forward test next to the engine. Compact grid from `load_bars(..., complete_only=True)`, engine JSON for TDI and levels so nothing is computed by hand, validator in code, at least 3 repeats per as-of bar, a recognition probe, same task on matched null paths, volatility-only baseline, everything logged per call in one file per run.
- Fine-tune route: bars as text in, count or outcome as text out, one adapter per walk-forward fold, a 9B or 27B open model.

**3. What it would learn and what it cannot.**
- A replay learns nothing: each call is stateless and weights do not change. Memory notes between calls were a contamination channel in production (memory-write frequency vs P&L -0.200, p = 0.002, [DXRG](https://arxiv.org/pdf/2609.05663)). [verified]
- It already holds BTC's levels and shapes from training (pilot below). It cannot give unbiased BTC Fibonacci frequencies from its head or compute indicators reliably by hand. The ratio counts he actually asked for need no LLM: code over pivots, seconds, $0.
- What a fine-tune could learn, by label source (costs on Together 9B / 27B, `llm_cost_model.py`; reasoning [assumed]):

| Label source | Examples | Learns | Cannot learn | Train cost |
|---|---|---|---|---|
| His gold swings | 0 now, 30-60 planned | His labelling style | Market behaviour; burns the regression test | $4 / $7 |
| Engine counts | up to 119,803 1H | A noisy copy of a free deterministic engine | Anything new | $1,593 / $4,919 |
| Outcome labels | 119,803 overlapping, about 660-4,900 effective | Base rates, volatility clustering, weak reversal | Why; calibrated probabilities. Breaks "probabilities come from the engine" | $64 / $197 for 1,664 windows |
| Course text | 54,414 words | Vocabulary, recitation | Market information; rules stop being versioned config | $4 / $4 |
| Analyst counts | 1,972 multi-market pairs in [one corpus](https://arxiv.org/pdf/2412.04041) | How analysts phrase counts | Whether they were right; survivorship | $78 / $240 |

**4. The evidence.**

*Pilot on Opus 5.5 (small, not pre-registered; see section 12).* Fixed seed, random windows from `bitstamp_btcusd`, 3 fresh runs, no tools beyond file reads, results in `pilot_llm_direct_key/score.txt` (`llm_pilot_score.py` to `llm_pilot_score4.py`). [verified]
- Positive: 86 of 86 pivot prices within 2 ticks of a real high or low; 0 violations in 35 machine-checked hard-rule tests on the labelled degree (sub-wave claims not checked, so a lower bound on errors).
- Not repeatable on real windows: pivot overlap 0.12-1.0, one window got impulse up, diagonal down and zigzag down. The most repeatable count (identical three times) was on a path that never happened.
- No abstention: 0 of 12 main counts said "unclear"; other/unclear share 45.0 on real and 42.5 on null, so the share is a constant, not information.
- Hand-computed RSI off by 2 to 15 points; 9 of 62 legs not at the true extreme.
- Memory: of 42 pre-cutoff window tries, 34 flagged recognised, all 34 exact month, all 34 next-30-day directions right (Brier 0.030-0.048, against 0.204 for a constant base rate). Post-cutoff 0 of 9 within 12 months, Brier 0.21-0.24. Price recall from memory: median error 0.1-0.2% before the cutoff, 8.2-10.5% after.
- How to read the memory result: windows were 40 daily closes indexed to 100 with no dates, and the prompt named BTC/USD. Runs differed widely: within 3 months on 57%, 93% and 100% of pre-cutoff windows. A peek at the answer file would also have solved the post-cutoff windows, which scored 0 of 9, so this reads as memory [assumed inference].
- Independent check: the bake-off worker, with dates moved and prices rescaled, saw the period named in 17 of 18 calls on three famous windows, and 0 hard-rule breaks in 114 counts (`03-bakeoff.md`, summary items 1 and 4).
- Design defect disclosed: null series chain open to previous close and real ones do not, which leans toward spotting nulls.
- What it cannot show: 3 runs of one model are not a rate; only 40-bar daily windows were tested for dating; no images; no 1H or 4H recognition test; effort level unknown.

*Literature on trading and charts, most relevant first.*

| Source | Design | Result | Rigour |
|---|---|---|---|
| [FINSABER](https://arxiv.org/html/2505.07078v5) | 2004-2024, S&P 500 members including delisted, costs | Buy and hold Sharpe 0.315-0.384; FinMem -0.253 to 0.025; FinAgent 0.094-0.104; alpha (return beyond market exposure) p above 0.34; FinMem's +61.78% on TSLA reran at +5 to +20% | Strongest long test; mostly inside training data, which should flatter LLMs |
| [DXRG, Barton et al. 2026](https://arxiv.org/pdf/2609.05663) | Live crypto perps, 500-599 agents, 14,596 fills, 5.5 bps | Fleet -$217K; win rate 41% vs 50% matched retail; signal ledger sorts at 0.50; three frontier models within 263.27-264.37 bps of regret | Closest venue; commercial lab reporting its own null |
| [Wang 2026, Doppelganger](https://arxiv.org/html/2606.17423) | Charts with injected evidence and martingale nulls | Evidence AUC 0.469-0.517, trend coefficient 0.200-0.409, Claude Sonnet evidence -0.171 | Best design; single author; Claude version unnamed |
| [Hu et al. 2026](https://arxiv.org/html/2604.12659v1) | 193,524 charts, 30-day horizon | Direction 49.40-53.48% (Sonnet 4.5 highest), XGBoost 50.87% | No tests; inside training data [assumed] |
| [E2A-Bench](https://arxiv.org/pdf/2609.14302) | 969 queries vs OHLCV facts | Unsupported claims 61-72% for frontier models | Reliability, not returns |
| [Agent Market Arena](https://arxiv.org/html/2510.11695) | Live BTC, ETH 2 months | 2 of 20 beat BTC buy and hold (+0.66%) | Short; fees unstated |
| Alpha Arena Season 1 | 17 days, 6 models, real money | Qwen3 Max +22.3%; other figures conflict across [ForkLog](https://forklog.com/en/four-out-of-six-ai-models-suffer-losses-in-trading-tournament/) and [iWeaver](https://www.iweaver.ai/blog/alpha-arena-ai-trading-season-1-results/) | Secondary only; at 5% daily vol [assumed] the best of six zero-skill accounts is expected near +26% |
| [ElliottAgents](https://arxiv.org/html/2506.16813v1) | LLM agents on a coded wave tool, stocks | 58-89% per cell, N = 8 to 28 | No baselines, tool does the counting |
| [`noahnan-max`](https://github.com/noahnan-max/elliott-wave-trading-system) | Markdown skill, JSON schema, validator | No backtest; it says it claims no validated engine or performance | A design idea, not evidence |

- Positive LLM results: [R&D-Agent(Q)](https://arxiv.org/html/2505.15155), LLM writes factor code without seeing raw data: CSI 300 annual return 14.21%, information ratio (IR, Sharpe against a benchmark) 1.74 vs 5.70%, 0.85. [BlindTrade](https://arxiv.org/html/2603.17692v1): Sharpe 1.40 vs SPY 0.64 in one window, 0.69 vs 1.06 over a longer one. [AlphaForgeBench](https://arxiv.org/html/2602.18481): writing strategies as code removes run-to-run instability. [FinTradeBench](https://arxiv.org/html/2603.19225v6): judge scores out of 5: raw OHLCV 2.41, precomputed indicators 4.44. [verified]
- Lookahead: [Lopez-Lira et al.](https://arxiv.org/html/2504.14765v2) GPT-4o S&P direction 80.58% before cutoff, 45.70% after; agent backtests decay 51-62% in Sharpe ([Profit Mirage](https://arxiv.org/html/2510.07920)); [He et al.](https://arxiv.org/html/2502.21206) find the bias modest for news, likely because a named asset's path gives more to memorise (reasoned, not tested there). [verified]
- Fine-tuning on prices: [Gao et al. 2026](https://arxiv.org/abs/2604.02921), best design, numbers can be tuned, within R2 0.001. [Valeyre, Aboura](https://arxiv.org/html/2412.09394v2): Chronos T5-tiny retrained daily, gross Sharpe 2.12 / 3.90 / 2.29 vs a plain reversal rule 2.23 / 4.16 / 2.31, zero-shot 3.17 gross, -1.49 net. [PRICE](https://arxiv.org/html/2609.05235), BTC 1H, 64-day test: squared error (MSE) 0.0029, percentage error (MAPE) 1.53 vs PatchTST 0.0035; no naive baseline in the paper, and a no-change forecast on its window scores MSE 0.00320, MAPE 1.61, beating its other baselines (`label_counts.py`, comparison [assumed] on metric reading). Text tasks do benefit: [FinLoRA](https://arxiv.org/html/2505.19819v1) 37.05 to 74.74. [verified]
- **Forecasting, older models.** [LLMTime, Gruver et al.](https://arxiv.org/html/2310.07820) (GPT-3, Llama-2 70B, zero-shot) beats baselines on regular, seasonal series, with numbers only in figures and one finance-like series (246 TSMC closes). [Time-LLM, Jin et al.](https://arxiv.org/abs/2310.01728) claims to beat specialised forecasters (abstract only). **[Tan et al. 2024](https://arxiv.org/html/2406.16964): removing or replacing the LLM does not hurt: ablations beat Time-LLM in 26 of 26 cases, CALF in 22, OneFitsAll in 19, and Time-LLM takes 28.2 times longer at inference.** That tests the LLM as a neural backbone, not prompting. [Merrill et al. 2024](https://arxiv.org/html/2404.11757): GPT-4 33.5% on 4-way reasoning (humans 66.1%, random 25%); single-series questions scored 92% with the series removed, so they measured prior knowledge. These positive results rest on visible regularity, which BTC returns lack [assumed]. [verified]
- **Forecasting and reasoning, near-current models.** [TimeSeriesExamAgent](https://proceedings.iclr.cc/paper_files/paper/2026/file/8b6dd6597c2edeb9ee62468ccea6f512-Paper-Conference.pdf): finance exam GPT-5 0.617, GPT-4o 0.586, random 0.25. [TSRBench](https://arxiv.org/html/2601.18744): GPT-5 best at 55.6%; 4-way forecasting questions GPT-5 38.8, Qwen3-VL-8B 50.7, chance 25; scale helps perception and reasoning, not prediction; the only Claude tested is 4.5 Haiku. [TFRBench](https://arxiv.org/abs/2604.05364) (abstract): verified numeric traces lift accuracy from about 40.2% to 56.6%. [PriceSeer](https://arxiv.org/pdf/2601.06088): post-cutoff stocks, Sonnet 4.5 hit rates 0.70, 0.52, 0.46 at 3, 5, 10 days, no naive baseline, few market draws [assumed]. No study tested Opus 5.x, and none tested BTC against a no-change forecast. [verified]
- **Chart benchmarks, beyond the table.** [Chartography](https://arxiv.org/html/2608.10677) (100 tasks, 10 of them finance, candlesticks among the formats, no per-domain scores, no human baseline, vendor author): pass rate at max effort GPT-5.6 Sol 45.0, Claude Fable 5 34.8, Opus 4.7 16.5, Opus 4.8 15.9. [CRBench](https://arxiv.org/html/2509.04457v1), reading unlabelled values at 2% tolerance: human 78.64, Qwen2.5-VL-7B 66.25, GPT-4o 21.69. [FinChart-Bench](https://arxiv.org/html/2507.14823) (corporate charts, no candlesticks): Claude Sonnet 4 84.32, values read against axes the weak spot. [ChartMuseum](https://arxiv.org/abs/2505.13444) (abstract): human 93%, Gemini-2.5-Pro 63.0%. No candlestick benchmark on Opus 5.x was found. Exact levels should reach a model as text or JSON, not as an image [assumed reading]. [verified]
- **Patterns in noise, consistency, calibration.** On noise, older models only: [Bigelow et al.](https://arxiv.org/html/2310.17639): GPT-3.5 shows run aversion like the gambler's fallacy and jumps from "random" to highly confident "non-random" past a threshold. [Van Koevering, Kleinberg](https://arxiv.org/html/2406.00092): GPT-4 over-alternates when generating random sequences, 0.682 against humans about 0.60 and a fair coin 0.50. Current evidence is Wang's null market in the table, where every model followed past momentum, and the pilot above. Calibration, on events and not prices: [Prophet Arena](https://arxiv.org/html/2510.17638): GPT-5 Brier 0.184, Claude Sonnet 4 0.194, market 0.187, returns below break-even. [KalshiBench](https://www.alphaxiv.org/abs/2512.16030) (single author): Claude Opus 4.5 ECE 0.120, and calls above 90% confidence were wrong 15-32% of the time. [ForecastBench](https://arxiv.org/abs/2409.19839) (abstract, February 2025): experts beat the best LLM, p below 0.001. No LLM calibration on price-derived outcomes was found. [verified]
- Note: `arXiv 2607.15414` looks like the exact benchmark wanted but its tables are labelled simulated or illustrative, so it is not used.

**5. Data needs vs BTC.** Clean sample for Opus 5.5: 2026-07-01 to 2026-10-29, 121 days, 726 4H bars, 2,904 1H bars. Telling 55% from 50% takes about 782 independent outcomes; at 1-2 a week [assumed] that is 8-15 years, against a guaranteed model life to at least 2027-09-22 ([Anthropic](https://platform.claude.com/docs/en/about-claude/models/overview)). Fine-tune supply: 0 gold, 0 engine, about 660-4,900 effective outcome labels. Context fit: 1D and 4H history fit in 1M tokens, 1H and 15m do not, and 770K tokens of context produced no gain in DXRG's paired test. [verified, computed]

**6. Compute and money.** Runs on this box through an API; local inference of an 8-9B model at about 3-7 tokens/s means 21-112 minutes per rulebook-plus-700-bars call [assumed speeds]. List prices, `llm_cost_model.py`, 1,500 output tokens assumed (but see section 7):

| Job | Opus 5.5 | Sonnet 5.5 | Haiku 5.5 | DeepSeek V4.1 Flash |
|---|---|---|---|---|
| Live call each closed 1H bar, a year, no cache to best cache | $1,173 to $397 | $587 to $199 | $29 to $12 | $19 to $97 uncached, by endpoint |
| Replay every 1H bar from 2013-03 | $16,048 to $4,589 | $8,024 to $2,295 | $401 to $130 | $117 to $1,326 |
| Post-cutoff replay, 2,923 1H bars | $392 to $112 | $196 to $56 | $10 to $3 | not run |
| Rule-compliant narrator, 2,000 tokens JSON, a year | $175 | $88 | $4.38 | $3.42 |

The Max (5x) plan's $100 monthly API credit covers the live loop on Opus only just when uncached ($97.78) and not at 6,000 output tokens ($163.48); plan limits in tokens are unpublished [unknown]. Fine-tune: $4 to about $5,000 per adapter on Together, yearly walk-forward $422 to $32,462, serving $134 to $70,080 a year. [verified prices, computed]

**7. Effort with Claude Code.** Narrator: hours. Harness and validator: 1-2 days. Hosted LoRA pilot with a proper evaluation: about a week. Rented GPU training: 1-2 weeks and fragile. Walk-forward adapters: several weeks. [assumed]

**8. Main risks.** Memory mistaken for skill (a replay would show Brier near 0.03 with fluent reasons); trend extrapolation sold as chart reading; a fluent wrong count; non-repeatable output, with temperature no longer settable on Claude ([deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations)); a constant "unclear" share mistaken for calibration; hand-computed indicators logged as fact; model retirement breaking a forward test; idea-level contamination, since a proposer knows how BTC behaved [assumed].

**9. Verdict.** **Do not use an LLM to count, forecast or "learn BTC" from history, and skip fine-tuning; use it to write the engine, draft rules for review, narrate JSON and transcribe his counts, and let it count only in logged post-cutoff tests against the engine and null paths.**

## 3. Time-series foundation models: rank wins among models, rare wins over no-change, no wins after costs

**1. What it is.** Large neural forecasters pretrained on billions of points, so they can forecast a new series with no training ("zero-shot"), or be fine-tuned. Kronos is the finance-built one: it tokenises candles (12B+ K-line records, 45 exchanges, to June 2024) and samples future paths; 4.1M / 24.7M / 102.3M parameters public, the 499.2M large model unreleased, MIT licence ([paper](https://arxiv.org/abs/2508.02739), [repo](https://github.com/shiyu-coder/Kronos)). Others: Chronos family, TimesFM (3.0 weights non-commercial), Moirai (research only), TimeGPT (closed API), TTM (under 1M parameters), FinCast, EXAONE Finance and Chronos-2-Synth (both synthetic-only training). [verified]

Model facts, from the linked cards and papers in the bibliography; "vendor" marks the maker's own claim. [verified]

| Model | Parameters | Licence | CPU | Mode | Output |
|---|---|---|---|---|---|
| Kronos mini / small / base | 4.1M / 24.7M / 102.3M | MIT | Mini feasible as a kill test, see field 6 | Both; paper tests zero-shot only | OHLCV sample paths |
| Chronos T5 | 8-710M | Apache-2.0 | Slow: 1,764 ms P95 per forecast even on a T4 GPU | Both | Sample paths |
| Chronos-Bolt | 9-205M | Apache-2.0 | "Usable on CPU", up to 250x faster than T5, no timing (vendor) | Both | Quantiles |
| Chronos-2 | 28-120M | Apache-2.0 | Not stated; 300 series/s on one A10G GPU (vendor) | Zero-shot | Quantiles, covariates |
| TimesFM 2.5 / 3.0 | 200M plus head / about 0.3B | 2.5 Apache-2.0; 3.0 weights non-commercial | Not stated; 283 ms P95 on a T4 | Both | Mean plus 9 quantiles |
| Moirai 1.x / 2.0 | 2.0 small 11.4M | CC BY-NC, research only | Not stated | Zero-shot in tests found | Samples / quantiles |
| TimeGPT | Not disclosed | Closed API | API | Vendor-side fine-tune | Point plus intervals |
| Lag-Llama | 2.5M | Apache-2.0 | Weights 10 MB, no timing | Both | Student-t samples |
| TiRex | 35M | NXAI community, commercial terms not read | Not confirmed | Zero-shot | Quantiles and mean |
| TTM | Under 1M | Apache-2.0 | "Running efficiently on CPU" (Brini) | Both | Point |
| FinCast | 1B | Apache-2.0 | RTX 4060 tested (authors) | Zero-shot | Point |

**2. How it would apply to this repo.** Read bars with `load_bars(venue, tf, start, end, complete_only=True)`, Binance spot for 1H and 4H, context 80-512 bars, horizon 12-168 bars. Output paths or quantiles, scored on checkable events. To stay causal, score only after the checkpoint's cutoff: 2024-07 onward for Kronos small and base, 2025 is safer, Kronos-mini's cutoff is unknown. Only sample-path models (Kronos, Chronos T5, Moirai 1.x, Lag-Llama, Toto 1.0, Sundial) can price a target-against-invalidation race; per-step quantiles carry no joint path. Kronos's `predict()` averages paths away and needs a patch. Its CSV fine-tune leaks: mean and std cover the prediction target ([code](https://github.com/shiyu-coder/Kronos/blob/master/finetune_csv/finetune_base_model.py)). [verified]

**3. What it would learn and what it cannot.** Can learn volatility clustering and generic bar shapes; fine-tuning may adapt to BTC's scale and time of day. Cannot learn wave grammar or labels, cannot explain itself, has no shown return signal on BTC. It cannot see a weekly cycle in his sense: 512 bars is 21 days at 1H, 85 days at 4H, 1.4 years at 1D [computed]. Nothing published shows a tokenised model learning anything readable as Fibonacci behaviour; it could be probed by comparing ratio histograms of sampled paths with BTC and a null, after Phase 1 [assumed]. Kronos's BTC weights are probably not clean for 2021-2024, since Binance crypto is in its corpus [assumed; corpus verified].

**4. The evidence.**

| Source | Design | Result | Rigour |
|---|---|---|---|
| [Rahimikia et al. 2025](https://arxiv.org/abs/2511.18578) | US stocks, OOS 2001-2023, 18M+ returns, yearly refit, about 50,000 GPU hours | Against a zero forecast: best benchmark CatBoost R2 -0.03%, Chronos zero-shot -1.37%, TimesFM -2.80%. Gross Sharpe: CatBoost 6.46, Chronos large 2.92. Fine-tuning made portfolios worse (-3.34 to 0.07). From-scratch finance training helps: Chronos small 5.42, TimesFM with factors 7.69. **At 20 bps every long-short goes negative** (CatBoost 6.44 to -3.62) | Strongest; causal refits, DM tests (pairwise forecast comparison), costs; no crypto |
| [Fu et al. 2024](https://arxiv.org/abs/2412.09880) | TimesFM continued on 90M points, 50.7M hourly crypto; test from 2023 | Market-neutral Sharpe, tuned / original / AR1: crypto daily 0.26 / -0.03 / 0.17; S&P 1.68 / 0.42 / 1.58. Authors cannot show it consistently beats AR1 | Single split, cost-free; text and table disagree on crypto |
| [Kronos, Shi et al. 2025](https://arxiv.org/abs/2508.02739) | Fixed model, test from July 2024, 25 baselines, no naive | Headline 93% is price-path RankIC 0.0267 vs 0.0138. IC below is plain correlation of forecast and outcome. Return RankIC all assets 0.0675 vs DLinear 0.0423. **Crypto return IC: DLinear 0.0446 beats Kronos 0.0368-0.0376**; RankIC Kronos 0.0336 vs 0.0283. A-share simulation at 0.15% per trade: excess 21.93%, IR 1.42 (CSI300), large model, non-public | Authors' own, no confidence intervals; real positive inside its own table; no crypto backtest |
| [FinVerse, Lee et al. 2026](https://arxiv.org/abs/2608.03259) | 60,232 series, 43 models, from 2020 | **2 of 43 beat persistence on raw error**; 9 beat AR(1); Chronos-2 Synth ranks first on crypto | No costs; vendor authors; ranks only for crypto |
| [Alonso, Franklin 2026](https://arxiv.org/abs/2606.27100) | 5 stocks, 10 origins, against a zero-return walk | Models take 8 of 10 task wins; significant only twice, p = 0.0421, uncorrected | Independent; tiny |
| [Yu et al. 2026](https://arxiv.org/abs/2607.26792) | 12 stocks, test 2025-2026, past Kronos's cutoff | **Kronos zero-shot statistically level with a fully trained ANN**; generic models were not | Real if small point for Kronos; no naive |
| [Brini 2026](https://arxiv.org/abs/2607.05291) | Realised volatility, 50 assets, no crypto | Only TTM beats log-HAR on the typical asset: QLIKE ratio (volatility loss) 0.982, 0.986, 0.987. **Equal blend TTM + log-HAR 0.977, 0.984, 0.982**, in the confidence set for 98-100% of assets | Independent, rolling, DM and model-confidence-set tests; strong on volatility |
| [Goel et al. 2025](https://arxiv.org/abs/2505.11163), [2024](https://arxiv.org/abs/2410.11773) | Fine-tuned TimesFM on realised volatility and VaR | Beats HAR variants; best on Value at Risk (a loss threshold) coverage | Moderate; tasks with real persistence |

*Own run, Kronos's public BTC forecasts* (`tsfm_kronos_demo_eval.py`, small first look, causal because committed live, git timestamps not notarised). 8,562 hourly forecasts, horizon 24 bars, scored on `binance_btcusdt` 1h. Kronos-mini period, n = 7,387 over 308 days: [verified]
- P(up): Brier 0.3065 against 0.25, 95% block CI on the gap [0.0361, 0.0812]; log loss 0.8816 against 0.6931; hit rate 51.29%, about +/-5.6 points; correlation with outcome 0.015. Reliability is flat: stated 3% realised 52.4%, stated 94% realised 51.6%.
- Walk-forward Platt recalibration (a one-line logistic fix): median slope -0.026, Brier 0.2525. Nothing to rescue. The model leans against recent moves (correlation with past 24h return -0.40) and BTC did not reward it (-0.01).
- Volatility amplification: real signal, correlation 0.41, but Brier 0.2314 against 0.1999 for a two-feature rolling-volatility logistic; after recalibration 0.2062 against 0.1972, CI [-0.0090, 0.0254].
- What it cannot show: one size, one horizon, zero-shot, one regime, top_p truncation inflates path agreement; nothing on fine-tuned Kronos, Kronos-large or two-sided races.

Community tests agree but are unreviewed: Polybot on BTC 5-minute, Brier of a plain random-walk formula (GBM) 0.193 vs Kronos 0.213, out-of-sample half 0.188 vs 0.189 ([repost](https://1023jack.com/market/week-three-foundation-model-vs-brownian-motion-kronos-on-five-minute-btc-2/)); [issue #299](https://github.com/shiyu-coder/Kronos/issues/299) has a fine-tune near a coin flip and one unverified 60% claim. The lead author says fine-tuning is hard and often worse ([issue #177](https://github.com/shiyu-coder/Kronos/issues/177)). No BTC-only peer-reviewed test and no barrier-hit calibration paper was found. [verified as reports]

**5. Data needs vs BTC.** Zero-shot needs only context bars. Fine-tuning has 119,800 1H bars / 560 = 214 non-overlapping windows, 0.72M values against 4.1M to 102.3M parameters. Clean test window for Kronos: 851 days, 95% CI about +/-3.4 points on a hit rate, enough to reject a badly calibrated probability (308 days did), not to confirm a 1-2 point edge. [computed]

**6. Compute and money.** Demo cycle on the team's CPU about 21 s (commit-time median 26 s after the hour, `tsfm_kronos_demo_eval.py`), the only real CPU measure. This box, by operation counts (`tsfm_cpu_flop_probe.py`, load about 7, proxy only, Kronos not run): mini 31-108 s per demo origin. A kill test of about 670 daily origins costs 6-20 hours of low-priority CPU and $0. RTX 4090 at an assumed 12 TFLOP/s: 119,800 origins mini 4.8 h, $1.6-$4.3; base 131 h, $45-$117. Fine-tune predictor: mini $0.20-$0.53, base $4.9-$12.9. Quarterly walk-forward on the clean window: $2-$116. Rahimikia's programme at $2.29/h would be about $115,000. TimeGPT prices were not established from an opened page [unknown].

**7. Effort with Claude Code.** Pretrained inference: a day. Path exposure and barrier scoring: 2-3 days. Fine-tune on rented GPU with the leak patch and walk-forward: 1-2 weeks. [assumed]

**8. Main risks.** False confidence from sampled probabilities; overfit to one path; contamination in weights, which fine-tuning does not remove ([Zhu, Cai 2026](https://arxiv.org/abs/2609.04917)); silent environment bugs ([#415](https://github.com/shiyu-coder/Kronos/issues/415), reported, not re-run); licences; headline numbers out of context ("93%").

**9. Verdict.** **Do not use foundation models to teach BTC; keep them as a cheap sceptical baseline and a possible volatility input, and run one Kronos-mini kill test before spending anything on fine-tuning.**

## 4. Classical ML and statistics on engineered features: the right size of tool, with a thin and often misread literature

**1. What it is.** Four families. (A) Logistic or gradient boosting on engineered features with outcome labels: at the moment a rule proposes a setup, output the chance target comes before invalidation within H. (B) HMM or regime models: hidden states with their own volatility and drift. (C) Survival or hazard models: the chance a swing ends next, given its age or extension. (D) Empirical or hierarchical Bayes ratio tables: full distributions of ratios by wave pair and degree, shrunk toward a pool when thin. A volatility model and null paths are the structure-free reference for all four. [verified as methods]

**2. How it would apply to this repo.** [assumed design]
- (A) Events at `ts_confirmed` from a causal zigzag or the engine, 1H main, 4H structure. Features: geometry in volatility units, leg ratios, rule passes, 1H/4H agreement, TDI with rulebook settings (section 5), HAR forecast, slow trend, causal cycle position. Pre-register a short list. Feed geometry as an offset and report skill only against it: with mixed targets, AUC is high from geometry alone. Expanding train from 2013-03, 6-month test blocks, purge, embargo = H, at most 20 trials, L2 logistic first, LightGBM with 7-15 leaves second, weight by label uniqueness.
- (B) 4H or 1D returns and log realised variance, 2-4 states, forward-filtered probabilities only; smoothed states are look-ahead.
- (C) Swing-by-age rows, both clocks (bars and theta units), censor the live leg, compare with null paths.
- (D) Engine pivots with hard rules only, log and linear, recomputed per fold, same on nulls. Fibonacci-bearing rules and soft scores off during labelling, or the distribution is cut at a Fibonacci number by construction: C at least 0.618 of A, diagonal W5 at least 0.618 of W4, flat B below 1.618 of A, triangle E at least 0.382 of C-D (rulebook sections 2, 3).

**3. What it would learn and what it cannot.** Can learn volatility (next-day log realised variance OOS R2 0.498, by era 0.569, 0.480, 0.488, 0.375, `cml_predictability.py`), base rates, slow drift, which rule setups do better than their geometry. Cannot learn a true count (none exists), BTC against other assets from BTC alone, regimes never seen, or next-bar direction (daily OOS R2 -0.18% to +0.16%, hit 51-52%, `cml_predictability.py`). If labels come from rules it relearns the rules; if from him, it learns his bias, which fits his Oct 23 idea but is not market truth. Note on 15m: HAR plus hour-of-week reaches R2 0.48, rising to 0.63 in 2025, with a calendar share of 16-18% since 2024 (`jepa_predictable_part.py`), while daily R2 is falling. Different targets, not a conflict. [verified]

**4. The evidence.**

*A random walk already looks Fibonacci.* For a driftless Brownian zigzag, overshoot is exponential with mean equal to the threshold, the next/previous ratio has a closed form with its peak at 1 and no bump at any Fibonacci level, and P(target x R before 1 R) = 1/(1+x), so a 1.618 R target hits 38.2% by arithmetic. Among retracements that hold, 42.5% land in 0.5-0.786 by chance (`cml_bm_check.py`, checked by simulation on 11,823 swings). The directional-change literature's core law ([Glattfelder et al.](https://arxiv.org/pdf/0809.1040)) is what a coin flip gives. [computed]

*Direction and ML on BTC.*

| Source | Design | Result | Rigour |
|---|---|---|---|
| [Bysik, Slepaczuk 2026](https://arxiv.org/pdf/2606.00060) | BTC/USDT perp, 70,128 hours, 27 walk-forward folds, 10 bps | Sign trading +73.50% a year gross, -64.00% net. **Cost filter 65.40%, Sharpe 1.09 vs buy and hold 56.30%, 0.82**; gain +0.27, 95% CI -0.46 to +0.95; 16 of 27 folds profitable; Sharpe 1.35, 1.06, 0.47 at 0, 10, 20 bps (a close variant) | Best hourly benchmark; preprint; a positive that is not significant |
| [Jaquart et al. 2021](https://publikationen.bibliothek.kit.edu/1000150665/149388567) | 3-month test 2019 | 51.9-56.0% by horizon; up to +116% before costs, all negative after 30 bps; 53.9% accuracy earned -87% | One falling quarter |
| [Akyildirim et al. 2021](https://repository.bilkent.edu.tr/bitstream/11693/77044/1/Prediction_of_cryptocurrency_returns_using_machine_learning.pdf) | 12 coins to 2018 | BTC 15m 53-56%, 1 day 55-62%; random forest 0.99 in-sample, 0.49-0.55 OOS | Chronological, no costs |
| [Gradzki et al. 2025](https://link.springer.com/article/10.1186/s40854-025-00866-w) | Tick bars, 5 OOS quarters, 0.1% | 29 of 210 next-bar runs profitable; event sampling plus a target, stop and time-limit label "consistently positive"; ETH Sharpe up to 2.0 | Positive; no multiple-test correction; tables not visible |
| [Jaquart thesis](https://publikationen.bibliothek.kit.edu/1000153546/149798497) | 100 coins, cross-section, 15 bps | Long-short Sharpe 3.12-3.23 vs market 1.33 | Real, but cross-section; does not transfer to BTC alone |
| [Helformer 2025](https://ira.lib.polyu.edu.hk/bitstream/10397/112415/1/s40537-025-01135-4.pdf) | BTC, 80:20 split | R2 = 1, MAPE 0.0148% | Not credible: "tomorrow equals today" already gets price R2 0.9958 (`cml_naive_mape.py`); code not audited |

*Triple-barrier labels and meta-labelling.* A triple-barrier label scores a setup by which comes first: target, stop or time limit, which is his "target before invalidation within H". Meta-labelling is a model deciding how far to trust a rule's signal. Real as a filter, thin as an edge. No peer-reviewed study of either on BTC with both costs and multiple-testing correction was found. [Gatto, Daru Finance](https://daru.finance/research-review/lopez-de-prado/labeling-and-cross-validation): lifts profit factor in 38 of 42 instruments, 0 of 42 clear a deflated Sharpe (Sharpe corrected for the number of trials) of 0.95. [MBPE](https://github.com/maazkashif1/MBPE) and [EdgeProof](https://github.com/intikhab49/edgeproof-crypto-trading-backtest), personal projects: no tradable edge. Joubert and colleagues' series (abstract only) is framework plus controlled experiments, not market validation. Lopez de Prado's book was not opened. [as tagged]

*TA on BTC.* Early strong results are mostly tests against zero in a market that rose thousands of percent.
- [Hudson, Urquhart 2021](https://centaur.reading.ac.uk/85715/8/Hudson-Urquhart2019_Article_TechnicalTradingAndCryptocurre.pdf): 14,919 rules; on Bitstamp only 4.96% beat buy and hold on return, 32% on Sortino; one best rule OOS in 2018: Sharpe -0.06. Reported annual figures look mis-scaled (one stream's arithmetic).
- [Wei et al. 2024](https://eprints.gla.ac.uk/302711/1/302711.pdf): 7,846 rules with snooping controls: only a 1-week price/MA ratio and hashrate survive, BTC OOS R2 0.016%.
- **[Deprez, Frommel 2024](https://ideas.repec.org/a/eee/reveco/v93y2024ipbp858-874.html) (abstract only): 75,360 rules; selected portfolios can beat buy and hold out of sample, mainly on risk-return. The main positive counterweight; numbers not seen.**
- [Anghel 2021](https://ideas.repec.org/a/eee/finlet/v39y2021ics1544612320304414.html) (abstract only): rarely significant after snooping and frictions. [Molnar 2026](https://arxiv.org/pdf/2607.26188): across a 36-cell grid no cell survives false-discovery correction (BH); Newey-West rejects at 0.33 and 0.17 against nominal 0.05 on persistent signals. [Liu, Tsyvinski](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf): daily momentum t 2.96 regular, 1.22 bootstrapped.
- [Detzel et al. 2021](https://doi.org/10.1111/fima.12310) (abstract; numbers from a [CXO summary](https://www.cxoadvisory.com/currency-trading/timing-bitcoin-with-smas/) of the 2018 working paper, gross, July 2010 to December 2017): price/moving-average ratios forecast daily BTC returns in and out of sample. Buy and hold Sharpe 2.0, drawdown -89.5%; SMA rules Sharpe 2.6 to 2.2, drawdown -66% to -70%. No snooping correction seen. The drawdown shape matches the own check below; the sample ends before the decay. Published R2 not seen.
- [Grobys et al. 2020](https://doi.org/10.1016/j.frl.2019.101396) (abstract, [author's article](https://cointelegraph.com/news/is-technical-trading-in-cryptocurrency-markets-profitable)): the 8.76% a year excess is **excluding Bitcoin**, so it is not BTC evidence. [Corbet et al. 2019](https://doras.dcu.ie/25053/1/The_effectiveness_of_technical_trading_rules_in_cryptocurrency_markets%5B1%5D.pdf): 1-minute Bitfinex 2014-2018, variable moving averages significant, fixed not at 5%, range-break buys negative on average; no costs, no snooping control. [Gerritsen et al. 2020](https://ideas.repec.org/a/eee/finlet/v34y2020ics1544612319303770.html) (abstract): range breakout beats buy and hold, best in strong trends; no multi-rule correction stated.
- Efficiency over time: [Urquhart 2016](https://ideas.repec.org/a/eee/ecolet/v148y2016icp80-82.html) (abstract), [Bariviera 2017](https://arxiv.org/pdf/1709.08090) (first page) and [Tran, Leirvik 2020](https://doi.org/10.1016/j.frl.2019.101382) (abstract) find BTC moving toward efficiency, while volatility keeps long memory. This fits the decay of fast rules below.
- **Own check, slow rules (`cml_predictability.py`, rules fixed in advance, 10 bps, next-bar execution, Sharpe on log returns):**

| Rule, net Sharpe | 2013-2017 | 2018-2020 | 2021-2023 | 2024-2026 | Full |
|---|---|---|---|---|---|
| Buy and hold, 1D | 1.30 | 0.31 | 0.19 | 0.46 | 0.73 |
| SMA 5d | 1.99 | 0.45 | 0.07 | -0.19 | 0.97 |
| **SMA 50d** | 1.30 | 1.04 | 0.73 | 0.80 | 1.04 |
| **SMA 100d** | 1.44 | 0.80 | 0.69 | 0.61 | 1.02 |
| 4H, 30 bars | 1.76 | 0.57 | -0.10 | -0.60 | 0.82 |

Max drawdown fell from -85% to -70% (SMA 50d) and -64% (SMA 100d) with about the same annual log return (0.54 vs 0.57). That risk benefit is the most usable positive here; intervals on the Sharpe difference exclude zero in only 4 of 55 cells, about chance, and in no full-sample cell. Fast rules decayed. [verified]

*Regimes and hazard.* [Ardia et al. 2019](https://libra.unine.ch/bitstreams/68f79eef-f5b3-4954-987e-2ec953b2bf02/download): regime GARCH beats single-regime for one-day VaR over 1,355 rolling days. [Koki et al. 2022](https://arxiv.org/pdf/2011.03741): direction claim rests on only 30 OOS forecasts. [Lunde, Timmermann 2004](https://econweb.ucsd.edu/~atimmerm/dur-14-2.pdf): real duration dependence in stocks. No BTC hazard study found. LPPLS (a log-periodic bubble model, [Wheatley et al.](https://arxiv.org/pdf/1803.05663)) fits hindsight windows; no BTC out-of-sample record with false-alarm rates found, so keep it out of the core.

*ML on Elliott Wave.* No paper opened combines causal walk-forward, null, costs, multiple-test control and replication.

| Study | Claim | What it really is |
|---|---|---|
| [Akbarzadeh, Soleimani 2023](https://ijnaa.semnan.ac.ir/article_6725_cf4ef4731ce12549040d98f506ff302d.pdf) | 93.94% | **49.32% on raw prices (its Table 7, M = 0).** A no-waves rule on a pure random walk gets 92.87% at the same smoothing, BTC daily 94.24% (`ewfib_ma_persistence.py`). FX, not stocks |
| [Dos Santos et al. 2023](https://repositorio.unesp.br/entities/publication/a0d8bdbb-cb3f-4008-ae04-eb598d0f7508) | Error reduced "4 times" against guessing inside rule bounds | **Abstract only, not rated: a possible positive, with metric and data unseen.** The baseline is not a random path |
| [Kotyrba et al. 2013](https://www.scs-europe.net/dlib/2013/ecms13papers/is_ECMS2013_0050.pdf) | 67.8% on 1,189 patterns | Hand-built templates, no base rate |
| [Yang et al. 2023](https://doi.org/10.3390/math11061466) (Wayback) | 68.13% | Agreement with its own labels, not a forecast |
| [Naga Swetha, Arya 2026](https://doi.org/10.1109/access.2026.3693604) (reader) | "2.4 times" detection | A count of patterns found; states it is not a prediction tool |
| [Joseph 2025](https://monami.hs-mittweida.de/files/16331/Doniya_Joseph_Master_Thesis.pdf) | BTC 12 trades, 10 wins | Best of a grid; Sharpe 15.37 is not credible |
| [Atsalakis et al. 2011](https://doi.org/10.1016/j.eswa.2011.01.068) (reader, abstract and highlights) | "Always" beats buy and hold | Not rated; picks sub-models on out-of-sample hit rate |
| [Vantuch et al. 2018](https://doi.org/10.3233/IDT-170319) (abstract only) | Above 70%, "proves the relevancy" | Not rated; accuracy alone cannot prove that |
| [Volna et al. 2013](https://doi.org/10.1016/j.camwa.2013.01.012) (abstract, Wayback) | 62.4%, second-hand from Akbarzadeh's table | Not rated. Kotyrba et al. 2012 could not be opened |

*Fibonacci.* The two best tests find nothing on stocks, and neither uses wave labels.

| Study | Data | Numbers | Reading |
|---|---|---|---|
| [Batchelor, Ramyar 2006](https://openaccess.city.ac.uk/id/eprint/16276/) | DJIA, 22,194 days, 430 turning points, stationary block bootstrap | "15" of 144 cells above 0.90 vs 14.4 expected. **One stream's recount of the printed table gives 17, and at strict thresholds 15 cells at or above 0.95 vs 7.2 and 9 at 1.00 (`ewfib_br_table.py`; unconfirmed, cells are dependent, both tails heavy).** A cell needed a lift of 1.55-1.74 to register | Good design, low cell power; all swings |
| [Tsinaslanidis et al. 2022](http://hdl.handle.net/10251/195083) | Dow, DAX, NASDAQ stocks 1968-2019, random-level control | Fibonacci slope -0.016 [-0.092, 0.064] at zone 0; significantly negative at 6% | Best level test; stocks, no costs |
| [Kempen 2016](http://www.ftaa.org.hk/Files/2016.pdf) (mirror) | 58,530 retracements, fitted log-normal | Median 85%, mean 112%; no Fibonacci significance; **spikes at 100, 50, 33, 67%** | Useful base rates; survivorship; crude rule |
| [van Ginneken 2013](http://arno.uvt.nl/show.cgi?fid=131569) | FX 2005-2013, algorithmic waves, null, 3 bp | 14 of 240 tests significant; **real-time variant 20% significant, hourly, 0.1% per position**; exits lean on later-known peaks; null lacks volatility clustering | Most relevant design; a lead, not an edge |
| [Dehay 2026](https://github.com/baptiste-dehay/fractal-financial-markets-elliott-wave-validation) | SPY, GLD, USO, BTC daily, pre-registered, FDR | BTC 23 ratios, inconclusive. **Possible detector bug: 86% of bars stuck in a failing branch; fixing it gives 230-257 ratios on repo closes (`ewfib_dehay_check.py`; one stream's reading on retyped logic, the author has not confirmed it)** | Copy the governance |
| [Westland 2024](https://doi.org/10.1038/s41598-024-55011-x) | NFT trades | No wave counts, no Fibonacci test, no null | Not evidence on Elliott in BTC |

- [Prechter's reply](https://web.archive.org/web/2020/http://socionomics.org/pdf/EW_Fibo_Statistics.pdf) (Wayback): filtered trends are not waves, and adjacent-wave ratios are not what Elliott claimed. That shelters Elliott but not NewWave, whose W2 and W4 bands (section 1) are adjacent-wave claims. [verified, the inference is one stream's]
- Mechanism: [Osler 2000](https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf): published support and resistance levels bounce 60.8% vs 56.2% for arbitrary levels, a modest real effect lasting days. Order clusters are shown at round numbers ([Osler 2003](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf); [Urquhart 2017](https://ideas.repec.org/a/eee/ecolet/v159y2017icp145-148.html) on BTC, abstract via reader). Nothing was found on stop clusters at Fibonacci levels in crypto, either way. [verified as stated]
- "Every asset has its own Fibonacci": no study tests it after controlling for scale and volatility. Equity evidence points to similarity ([Kempen, Maier-Paape](https://arxiv.org/abs/1605.03559)). His rulebook's BTC values rest on instructor experience and chosen examples, no samples (rulebook sections 0, 7). The repo holds BTC only, so this is **unsupported, not refuted**. A random walk's scaled ratio distribution is the same for every asset, so real differences must come from tails or volatility dynamics. [computed]
- First look on BTC (`ewfib_swing_counts.py`, crude labeller, no grammar, not a test): against a per-bar sign-flip null, W2 in 0.5-0.618 is above range in 6 of 10 larger configurations (median lift 1.15, a fair lead); W4 in 0.236-0.382 is below in 8 of 10 (median lift 0.80), so W4s run deeper (median 0.44-0.47 vs 0.39-0.43). Outcome after a 0-1-2: BTC tracks the martingale baseline in all 16 configurations, -1.4 to +2.1 points, with a smooth gradient by depth and no step at 0.5 or 0.618. **The empirical worker's larger test does not confirm the two leads:** inside 1,106 rule-legal impulses, against random paths with BTC's own volatility, W2 at 0.5-0.618 is 17.6% against 17.5% and W4 at 0.236-0.382 is 41.9% against 41.3% (`02-empirical.md`, summary item 2). Labeller and null differ and the two were not reconciled here, so do not lean on these leads.

**5. Data needs vs BTC.** See section 7's table. AUC 0.55 needs 1,045 independent events (`cml_bm_check.py`), about 7 years live at 145 effective events a year. Frequency tests: 20% vs 25% needs 1,090 per group, 20% vs 30% needs 290. Detectable on the first-look counts: lift about 1.29 in a 22% band at n = 510, 1.54 at n = 148; outcome 2.6 points pooled at n = 3,540, dependence ignored, so optimistic. Weekly cycles (23) and daily cycles (86) are far too few for ratio tests.

**6. Compute and money.** All CPU, $0. LightGBM 5,000 rows x 29 features 0.88 s, 118,683 rows 112.5 s under load (`cml_predictability_timing.log`). Search of 17 folds x 20 trials about 6 minutes; 200 null paths about 1 hour once events exist [assumed]. The first look ran 16 configurations and 8,320 null paths in 454 s. Gaussian HMM seconds to minutes; Bayesian MS-GARCH likely hours [assumed].

**7. Effort with Claude Code.** [assumed] Generic swing events and harness 2-4 days; wave features and tests 1-2 more weeks after an engine exists. HMM 1-2 days. Hazard 1-2 days. Tables 1-3 days after an engine, about a week more with multi-asset ingest. A, C and D share one harness, which is most of the work.

**8. Main risks.** Geometry inflating AUC; overlap and leakage; hidden trial count; circular Fibonacci labels; thresholds as a hidden test; many cells; engine dependence, since the statistics describe this labeller; a broad shift of mass read as a Fibonacci spike; decay; reading calibration as profit. Personal track record: an edge of 0.10 R needs about 400 independent trades for t = 2.

**9. Verdict.** **Build these: ratio tables against a sound null first (they answer "own Fibonacci" directly), hazard curves next, then a small logistic outcome model before LightGBM; use HMM only as a causal volatility feature if it beats a plain percentile; expect a calibrated filter worth a few points, and let wave features fail if they add nothing.**

## 5. Structured and hybrid engines: the best fit with his rules, and rule validity alone carries no information

**1. What it is.** Code reads price as a stream of confirmed swings and, like a grammar checker on a sentence, lists every way those swings can be labelled under his rules. It keeps all live readings with their invalidation levels and reports the probability of a checkable outcome, always with an "other/unclear" share. An LLM may write the code, propose logged variants, transcribe his count and narrate. It never counts.

**2. How it would apply to this repo.** [assumed design] `load_bars` on 1H and 4H with `hl_order`, log prices, `bybit_btcusdt_perp` later for live. Directional-change zigzag on a pre-declared grid (for example 4H 5/10/20%, 1H 1/2/3%), each pivot entering the chart only at `t_confirm`. Windows of 41-81 pivots per level. Rules in `rules/newwave.yaml`, R rules only as hard. At each confirmed pivot, for each surviving hypothesis, store "target zone before invalidation within H". Filter and prefix values only, no re-labelling of history, a test that rewrites the future. Same pipeline on null paths. Version 1 keeps pivots, impulse, zigzag, flat, R rules, exact chart, invalidation tracking, null harness, barrier baseline, predictions log and his count as input. It cuts the particle filter, the LightGBM ranker, degree nesting, triangles, combinations, 15m drill-down, TDI and soft weights, each to return one at a time through the same gate.

**3. What it would learn and what it cannot.** Learns, per threshold, how often each pattern, ratio and duration occurs against random paths, which single rule moves an outcome beyond geometry, and a pooled map from score to outcome frequency. Cannot learn a "true" count, other regimes, a rule the grammar lacks, or his discretionary read except by outcome.

**4. The evidence.**

*Science of parsing.* Parsing plus tracking represents ambiguity soundly and every method is causal if only its filter is used. None gives calibrated probabilities by itself: HMMs run "very underconfident" ([Nguyen, O'Connor](https://aclanthology.org/D15-1182.pdf)), and structured models need an event-based recalibration step ([Kuleshov, Liang](https://papers.nips.cc/paper/5658-calibrated-structured-prediction.pdf)). Strongest evidence that a grammar helps prediction: [Qi et al. 2018](http://proceedings.mlr.press/v80/qi18a/qi18a.pdf), future-activity F1 59.9 vs 34.1, where activities really have grammars. Closest analogue on markets: [Tayal 2009](https://uwspace.uwaterloo.ca/handle/10012/4463), hierarchical HMM on 646,692 tick zig-zags: exceptional with look-ahead, falling without it through regime instability, no costs. A regime model can lose to a random walk on small misclassification ([Dacco, Satchell](https://doi.org/10.1002/(SICI)1099-131X(199901)18:1<1::AID-FOR685>3.0.CO;2-B), abstract). Bayesian online changepoint detection gives exact online run-length inference ([Adams, MacKay](https://arxiv.org/abs/0710.3742); [Fearnhead, Liu](https://eprints.lancs.ac.uk/id/eprint/745), abstract) but is poor under outliers: false discovery above 90% on well-log data by run-length maximum ([Knoblauch et al.](https://papers.neurips.cc/paper_files/paper/2018/file/a3f390d88e4c41f2747bfa2f1b5f87db-Paper.pdf)), a warning for BTC's wicks [assumed]. [verified]

*Elliott-specific.*
- No paper or open-source project doing grammar, parser, beam-search or particle-filter treatment of Elliott Wave was found (`sh_scholar_scan.py`, 24 OpenAlex queries, top 15 each; limited). Open ground, and a warning. [verified as a search result]
- No engine publishes a track record or calibration. EWAVES: $595 a month, crypto twice a day, recalculates from scratch, admits flip-flopping is "intractable" ([FAQ](https://ewaves.com/faq/)); its paper is still unpublished. ELWAVE and WaveBasis publish no numbers. MotiveWave documents a "proprietary pattern matching algorithm" with no rule detail, ranking method or accuracy claim in the parts read ([docs](https://docs.motivewave.com/video-tutorials/elliott-wave)). CXO's grade of Prechter himself: 20.8% on 24 forecasts, lowest of 68 gurus, with CXO's own "very low" confidence; it grades a person, not the method ([table](https://www.cxoadvisory.com/gurus/), [his page](https://www.cxoadvisory.com/gurus/robert-prechter/)). [verified]
- Best honest study found: [omaralasil W3 study](https://github.com/omaralasil/elliott-wave3-estudio), weekly stocks 2013-2026, N = 435: **fixing zigzag look-ahead cut Profit Factor 3.87 to 2.74; Carhart alpha about 5.6% a year, p = 0.063**; survivorship and no slippage. A modest positive with a real size for repainting risk. [PyBacktesting](https://github.com/philippe-ostiguy/PyBacktesting): training Sharpe above 3, test -13.99 on 10 trades. [verified]
- EWAVES raw data, the only published evidence near this ([elliottp6/rvr](https://github.com/elliottp6/rvr), `sh_rvr_analyse.py`): AUC of real above permuted 0.78-0.82 pooled at 1 year, 0.90-0.985 for BTC (n = 13), 0.71-0.73 at 3 months. Real, but random chunks still score (P38 at 1 year: 99.1% above 10, 21.0% above 30) and it measures conformity, not forecasting. A plain volatility statistic with no Elliott content gets 0.94-0.997 on the same test on BTC 1 year, collapsing to 0.53-0.68 once 20-day blocks keep the clustering (`sh_real_vs_perm.py`). So this test cannot credit Elliott. It does not prove elliotticity is only clustering, and the vendor's permutation period is undisclosed. [verified as measured; "0 is real" assumed from the file layout]

*Pilots, 4H, NewWave R rules only, no diagonals, triangles or combinations, so a lower bound on counts* (`sh_count_density.py`, `sh_subwave_test.py`). BTC / shuffled / block medians. [verified]

| Threshold | Windows with at least 1 strict impulse | Strict patterns per window | Squint patterns (unknown legs allowed) |
|---|---|---|---|
| N=25, 5% | 78% / 73% / 75% | 111 / 77 / 85 | 1,018 / 774 / 829 |
| N=25, 10% | 68% / 72% / 72% | 57 / 82 / 74 | 663 / 860 / 681 |
| N=41, 5% | 95% / 95% / 95% | 301 / 251 / 329 | 101,859 / 48,194 / 69,342 |
| N=41, 10% | 90% / 95% / 90% | 120 / 376 / 229 | 19,275 / 63,679 / 42,169 |

- **The direction flips with the threshold:** at 5% BTC runs above the nulls (N=25: 7 above, 1 below), at 10% below (0 above, 8 below). Trying one threshold would publish either story.
- BTC outside the null's 5-95% range: 19 of 352 at N=25, 11 of 176 at N=41, about chance or below.
- Fibonacci bands as a joint filter cut impulses hard but equally: 2 of 216 comparisons outside range, both with BTC below.
- **The 3-or-5 reading:** next leg fully retraces a leg read as 3 only 51.6%, as 5 only 30.4%, gap 21.3 points. Same gap on shuffled 21.8 (14.5 to 31.8), on block 21.5 (12.8 to 28.1). Strong-looking on BTC, mechanical on noise.
- Exact chart: 1.6e18 parses summed in 154 ms at N = 141 in pure Python; recount matched brute force on 39,200 cells (`sh_crosscheck.py`). Enumerating counts explodes; summing them does not.
- Geometry: P(up barrier first) = d/(u+d) is close on BTC 1H, mean gap 0.043, long side +0.058 (`sh_barrier_baseline.py`). See section 7.
- **What these pilots cannot show:** individual guidelines, TDI signatures, or his own eye, none of which were tested. Effects under about 8-10 points on the 3-or-5 gap would not show (only 112 and 35 five-only legs). Only 4H bars. A small grammar with a fixed theta/3. Scored forecasts were never tested. The block column has the limit in section 7, and the conclusions above rest on the shuffle column.

*Hybrids (LLM proposes, code disposes).*
- [R&D-Agent(Q)](https://arxiv.org/abs/2505.15155): real positive, on cross-sections, 33-44 loops, no correction seen. [AlphaAgent](https://arxiv.org/html/2502.16789): IR 1.488 and 1.05, selection period not stated. [SEADS](https://arxiv.org/html/2609.00731): best protocol, re-runs discovery at past dates: Sharpe 0.96 vs no-discovery 0.62, not distinguishable from rivals, gross.
- Risks: [survey of 19 studies](https://arxiv.org/html/2605.19337v1): 2 of 19 with extractable time-consistent splits, 1 of 19 with an explicit cost model. [Novy-Marx, Velikov](https://www.nber.org/papers/w33363): LLMs industrialise after-the-fact stories. [Gencay 2026](https://arxiv.org/pdf/2608.27734): every LLM strategy rejected at budgets up to 100; a planted look-ahead oracle with Sharpe 35 passes deflated Sharpe and PBO (probability of backtest overfitting), so statistics do not catch leakage. [ImpossibleBench](https://arxiv.org/pdf/2510.20270): Claude models cheat mainly (over 79%) by editing tests; read-only test access is a promising fix.
- Where Opus sits: writes engine and property tests; drafts rule YAML for line-by-line review ([Datla et al.](https://arxiv.org/pdf/2512.04408): span F1 0.97-0.98 but field similarity 0.36-0.39, so human review stays); proposes logged variants at the meta level; audits for look-ahead; transcribes his count so a validator names which rule it breaks; narrates JSON. It does not propose or rank counts at runtime, since the chart enumerates every parse in milliseconds. The loop needs an evaluator out of Opus's write reach, an append-only ledger, an end-date clamp, a promotion bar that rises with N (expected best z of N useless variants: 2.50 at 100, 3.24 at 1,000, `sh_misc_numbers.py`). [assumed design, nothing tested]

**5. Data needs vs BTC.** Rule counting needs no labels. Calibration needs at least 100-200 events per group ([Collins et al.](https://pubmed.ncbi.nlm.nih.gov/26553135/), clinical): BTC gives 63 legs a year at 4H 10%, 213 at 5%, 1,195 at 1H 2%, overlapping. So pool, keep parameters few, and say "not enough events" elsewhere. Weekly and 4-year levels cannot be calibrated. The 30-60 gold swings are a regression test only.

**6. Compute and money.** No GPU. Parse 6.2 ms at N = 41, 154 ms at N = 141. Re-parse per confirmed pivot over 400 null paths: about 11-50 hours, perhaps 10x for scoring, less 20-50x with Numba [assumed factors]. Overnight on the 4-core box, run sequentially. Outside tools for comparison: EWAVES $595 a month, ELWAVE Pro $150 a month plus feed. Open-source repos are ideas only; the most-starred has no licence ([drstevendev](https://github.com/drstevendev/ElliottWaveAnalyzer)). The pilot was about 600 lines including tests.

**7. Effort with Claude Code.** 8-14 calendar weeks part-time for a version 1 that decides go/no-go, plus forward logging [assumed]. See section 7 for how this sits against the plan's 17-25 weeks and the gates.

**8. Main risks.** Silent look-ahead; forking paths in soft scores; the agent editing the evaluator; "looks right on the chart", since marks look right on random paths too; rule encoding (16 course conflicts); no reviewer who can catch these, so reviews must be behavioural; and building a grand system on a rule layer that carries no signal.

**9. Verdict.** **Build the deterministic chart parser and null harness first, because they are cheap and fit his rules; expect rule validity alone to carry no edge; test single guidelines and TDI one at a time; let the null gate and barrier baseline decide whether anything more is ever built.**

## 6. Honesty machinery: the part most likely to tell him the truth

A method, not a model, so the fields are adapted. It finds no edge by itself. It says whether a claimed edge survives.

**1. What it is.** Count every variant tried, test on data not used to choose, score with rules that cannot be gamed, compare with a structure-free baseline and random paths, and know how many independent events exist.

**2. How it applies.** Inputs are the engine's logged "target before invalidation within H" events. It stays causal because the only scored number is a forecast stored before its outcome, and calibrators fit only on resolved events.

**3. What it can and cannot do.** Can reject claims and measure calibration. Cannot prove no edge exists, cannot see small effects at slow degrees, and cannot clean data already seen by a human, a rulebook author or an LLM.

**4. The evidence and tools, in one line each.**
- MinBTL ([Bailey et al. 2014](https://www.ams.org/notices/201405/rnoti-p458.pdf)): the more variants tried, the longer the history needed. Over 13.66 years the best of 100 pure-noise strategies is expected at Sharpe 0.68, of 1,000 at 0.88; BTC's own buy and hold shows 1.13 on arithmetic daily returns (`sample_size_derived.py`), the same period as the 0.73 in section 4's table, which uses log returns. So a raw Sharpe near 1 is no evidence here.
- PBO ([Bailey et al.](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)), probability of backtest overfitting: how often the in-sample winner lands below median out of sample. DSR ([Bailey, Lopez de Prado](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf)), deflated Sharpe: is the Sharpe above what the best of N noise trials would show. CPCV, combinatorial purged cross-validation: many train and test splits with overlapping labels removed. CPCV trains on the future, so it is a diagnostic only here. In [Gort et al.](https://arxiv.org/pdf/2209.05559) the lowest PBO (7.9%) lost -55.54% in a -50.78% market, one crash window, so PBO is not a ranking.
- Multiple testing: Reality Check ([White 2000](https://www.ssc.wisc.edu/~bhansen/718/White2000.pdf)) and SPA ask whether the best of many rules beats a benchmark; StepM ([Romano, Wolf](https://www.ssc.wisc.edu/~bhansen/718/RomanoWolf2005.pdf)) and BHY (false-discovery control) ask which; t above 3 ([Harvey et al.](https://www.nber.org/system/files/working_papers/w20592/w20592.pdf)) and haircuts ([Harvey, Liu](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF)) raise the bar. On 7,846 Dow rules the best was significant over 1897-1986, not in the next 10 years ([Sullivan et al.](https://www.fmg.ac.uk/sites/default/files/2020-11/dp303.pdf)), and performance "fully disappears" after costs ([Bajgrowicz, Scaillet](https://www.efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2008-Athens/papers/Bajgrowicz.pdf)).
- Scoring: Brier and log loss are proper; Brier skill (share of a baseline's Brier removed) is generally improper, so show it but rank by paired raw scores ([Gneiting, Raftery](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)). CORP reliability diagrams and the split of a score into miscalibration, discrimination and uncertainty (MCB, DSC, UNC) ([Dimitriadis et al.](https://arxiv.org/pdf/2008.03033)). DM and GW tests of forecast comparison ([Diebold 2015](https://www.sas.upenn.edu/~fdiebold/papers/paper113/Diebold_DM%20Test.pdf), [Giacomini, White](http://fmwww.bc.edu/EC-P/wp572.pdf)); GW's theorem rules out an expanding window. Anytime-valid tests for a log he will look at hourly ([Henzi, Ziegel](https://arxiv.org/abs/2103.08402), [Choe, Ramdas](https://arxiv.org/abs/2110.00115), abstracts).
- Calibration simulation (`sample_size_by_degree.py`, synthetic distortions only): below about 100 events recalibrating is worse than nothing; slope-only wins through about 1,000; isotonic (a free-form monotone fit) beat Platt only at 3,000 and only for a non-logistic distortion. Reliability diagrams: power to catch a 6-point overconfidence is 7.5% at n = 86, 17% at 300, 50% at 1,000, 94% at 3,000.
- Sign-flip nulls were not found tested in any source; the ones here are this round's own. No source opened tests the whole machinery on an Elliott engine.

**5. Data needs vs BTC: the per-degree numbers.** Bitstamp from 2013-03-01, 13.66 years, independent events assumed, so best cases (`sample_size_derived.py`, pattern division [assumed]). Detectable gap from 50% at 5% two-sided and 80% power; Brier skill in the same way. [verified as arithmetic]

| Pool | n | Gap from 50% | At t > 3 | Brier skill | Events a year | Years to 820 / 1,539 |
|---|---|---|---|---|---|---|
| 4-year lows | 3 | none (best two-sided p = 0.25) | none | none | 0.2 | 3,735 / 7,010 |
| Weekly-cycle lead | 14 | +34.4 | +45.0 | none | 1.0 | 800 / 1,502 |
| Weekly cycles | 23 | +27.7 | +37.1 | none | 1.7 | 487 / 914 |
| Daily cycles | 86 | +14.9 | +20.3 | 0.365 | 6.3 | 130 / 245 |
| 4H 20% swings; /8 | 268; 33 | +8.5; +23.5 | +11.7; +31.8 | 0.117; 0.951 | | |
| 4H 10% swings; /8 | 833; 104 | +4.8; +13.6 | +6.6; +18.5 | 0.038; 0.302 | | |
| 4H 5% swings; /8 | 2,899; 362 | +2.6; +7.3 | +3.6; +10.1 | 0.011; 0.087 | 11.0 (/8) | 74 / 139 |
| 4H 2% swings; /8 | 11,363; 1,420 | +1.3; +3.7 | +1.8; +5.1 | 0.003; 0.022 | 58.1 (/8) | 14 / 27 |
| Barrier events, H = 24h | 3,759 | +2.3 | +3.1 | 0.008 | 275.2 | 3.0 / 5.6 |
| Barrier events, H = 7d | 729 | +5.2 | +7.1 | 0.043 | 53.4 | 15 / 29 |
| Barrier events, H = 30d | 204 | +9.8 | +13.3 | 0.154 | 15.0 | 55 / 103 |

| Level | Can conclude | Cannot conclude |
|---|---|---|
| 4-year, n = 3 | It happened three times, with unusual spacing against cycles-r1's nulls | Clock or not, halving link, any win rate; the next low is the first out-of-sample point |
| Weekly (168-294 d), n = 23 | Can reject claims of about 80% or more; cycles-r1's 70-80% in-window claim is reproduced on random paths | Whether the 64% lead is real (n = 14, Wilson 38.8-83.7%; a 65% rule needs 97 events, 58 years) |
| Daily (54-66 d), n = 86 | Can reject claims of about 65% or more | Effects of 55-60%: 210 events take 33 years |
| 1H/4H swing | Calibration, 5-point claims, comparison with the baseline; the only level with enough events for a reliability diagram | Small edges within today's regime; many-way conditions; anything without a ledger |

- Conditioning eats sample: each balanced binary condition halves n, so 1,420 5-3 cycles become 89 after four conditions.
- Memory: signed 1h return autocorrelation time 0.81 h; abs(r) 661 h, 106 h with the yearly level removed; Politis-White block length 9-11 days for signed daily returns, 125 days for abs(r) (`sample_size_by_degree.py`, `sample_size_derived.py`). Most big swings come from thin high-volatility years: under 10% of 10-20% swings sit in the last three years.
- Pooling: venues are one path (1h return correlation with Bitstamp: Binance 0.964, Bybit 0.995), about 1.00-1.02 times the sample; timeframes are nested (99.4-100% of 4H and 1D pivots are also 1H pivots); other coins add at most about 1.67 times at correlation 0.6 ([Giller](https://arxiv.org/abs/2412.04263), abstract), and his own premise of asset-specific Fibonacci forbids pooling them.
- His Sep 2026 note is right: at 30 trades, 21 wins are needed for p below 0.05, power to see a true 55% is 7.4%, a true 55% trader shows 50% or less 35.5% of the time, and a 50% trader shows 60% or more 18.1%. At 40 trades: 27 wins, 7.8%, 31.6%, 13.4%. The rulebook's 3-month evaluation window (section 0) sits against this. [verified]

**6. Compute and money.** All CPU, no fees. The script took 64 s including 280 null paths on 4H bars. The real cost is engine speed times about 400 null paths. **7. Effort.** Ledger, single evaluation entry point, baseline, nulls and scoring: days, not weeks [assumed]; working baseline and null code exist in `sample_size_by_degree.py`. **8. Risks.** False comfort from undercounting N; a holdout that is not clean; resetting the live clock after every tweak; peeking without a test built for it; treating "beats a flat base rate" as skill.

**The checklist for this repo.** All thresholds are proposals to be fixed in the pre-registration, not results. [assumed] Item 8 and gate A are amended from the note, see section 7.
1. **Pre-register** before any engine tuning: at most 5 primary events, horizons, baseline, metrics, splits, N budget, thresholds, digests. A dated commit is a modern "model sequestration"; commit only when he asks.
2. **Variant ledger:** one evaluation entry point, each call one row (run id, actor, rules digest, data range, metric, seen or not), SQLite or one file per run. Report raw M and effective N. By-eye edits count; budget N of at most about 60 until the first gate (59 at Sharpe 0.75 in 9.72 years). Backfill cycles-r1 and this round's runs.
3. **Causal guards, separate from statistics:** state at t equals a fresh run on bars up to t; rewriting bars after t changes nothing; a planted same-bar bug fails a test.
4. **Locked holdout:** proposed 2022-11-22 to the freeze date, 3.94 years, 1,438 / 205 / 47 windows at 24h / 7d / 30d. Clean for engine parameters only, since he, the rulebook, LLMs and these notes have seen it. It can refute a big claim, not confirm a small one.
5. **Walk-forward as the headline:** replay the exact live loop on 2013-03 to 2022-11, calibrator on a rolling 4-year window, yearly refit, first test 2017-03, about 1,570 / 300 / 85 effective events. Purge: train only on s + H at or before t.
6. **CPCV and PBO as diagnostics only:** 12 groups, 2 test, 66 splits, 11 paths; S = 16 (12,870 splits; the paper's "12,780" is a misprint) if N is at least 20; never used to pick.
7. **Baselines, paired on the same events:** B0 past base rate; B1 finite-horizon barrier formula with zero drift and past-only volatility; **B3 = B1 through the same walk-forward recalibrator, the go/no-go comparator**. Fit on the venue traded.
8. **Nulls, amended:** for swing-scale claims use per-bar sign flip and a block shorter than a swing (scale it to the threshold). Keep 20-day and 125-day blocks and block sign flip for claims about scales longer than the block. At least 200 paths each. Report BTC's rank and the count of rows outside against the count expected. Add a HAR or GARCH residual simulation, which nobody ran here.
9. **Scores:** log loss and Brier, paired; MCB, DSC, UNC; CORP with block-resampled bands; no claim from a reliability diagram below about 300 independent events.
10. **Multiple-testing gate:** SPA across the primary family, top claim t above 3, DSR on the skill series, BHY for exploration.
11. **The live log is the real test:** append-only, keyed by bar, stored before the outcome, anytime-valid tests, his own calls as a second forecaster, Bybit prices for scoring.
12. **Go/no-go gates** (below).
13. **Versions:** text-only changes do not reset; scheduled refits do not; any forecast-changing fix or rule change is a new version, ledger +1, live clock to zero. Each reset costs real years, so bundle changes.
14. **Profit is a separate gate**, after A, with costs and funding.
15. **Blind chart test:** unlabeled real against swing-breaking null segments, ask him for counts and confidence.
16. **Reporting rule:** every percentage carries n effective, N tried, baseline and period. Words allowed: "beat B3", "not shown", "failed". Never "no edge exists" from low power, never "edge" from one path.

| Gate | Data, effective n | Pass needs | Otherwise |
|---|---|---|---|
| A. Replay | 2017-03 to 2022-11; 24h about 1,570, 7d about 300, 30d about 85 | SPA p below 0.05; top event paired t at least 3 against B3; Brier skill against B3 at least 0.038 (24h), 0.19 (7d); BTC above the 95th percentile on swing-breaking nulls; PBO at most 0.10 if N is 20 or more; DSR at least 0.95 | Skill near zero with enough n: fail. Below detectable: "not shown" |
| B. Holdout, one look | 24h about 1,080, 7d 205 | One frozen variant: same sign, t at least 2, calibration inside band | Fail is final |
| C. Live, 300 events | About 1.1 years at 24h | Mean calibration within about +/-5.8 points; "no harm" only | If skill is below zero here and at 820, stop showing percentages as edge |
| C. Live, 820 events | About 3.0 years at 24h | May claim a 55% hit rate if an anytime-valid test rejects | Still "not shown" |
| C. Live, 1,539 events | About 5.6 years at 24h | May claim Brier skill of 0.02 or more | Still "not shown" |

**9. Verdict.** **Mandatory, nearly free, and to be built first: its most likely output is "not shown", and if the engine turns out to be a discipline tool rather than an edge, items 2, 7, 9 and 11 alone already deliver the accounting tool he described in October.**

## 7. Where the streams measure different things, reconciled

### Event counts: nested answers to different questions, not rival estimates

| What is counted | Definition, threshold | Count | Script | Question it answers |
|---|---|---|---|---|
| Bars | 1H, Bitstamp from 2013-03 | 119,784 to 119,803 (end time differs) | `ewfib_swing_counts.py`, `llm_cost_model.py` | How much raw data. Not a sample size |
| Finished legs, ATR | Causal zigzag, 1H and 4H at ATR14 x 5 | **about 2,320 and 570**; 2,771 and 681 on another ATR | `jepa_predictable_part.py`; `ewfib_swing_counts.py` | How many swings a probe could be scored on, upper bound. Same label differs by up to 27% (922 vs 1,175 at 1H x 8) |
| Finished legs, percent | 1H 5% | 1,488 (closes only), 3,447, 3,480, 4,017, 4,222 (highs and lows, details differ) | `label_counts.py`; `sample_size_by_degree.py`; `sh_pivot_scale.py`; `cml_swing_null.py`; `jepa_predictable_part.py` | Same. A factor of 2.8 comes from definition alone; wicks are the likely main cause [assumed] |
| Rule-legal impulses | 4 hard rules, one scale, 1H k=3; 4H k=3; 1D k=2 | **510** (421 non-overlapping; sign-flip median 463); 148; 68 | `ewfib_swing_counts.py` | How many wave-labelled ratios a frequency test can use |
| Rule-legal windows, sibling census | 1H ATR x 4; 1H x 8; 4H x 4; 4H x 8 | **165; 47; 47; 15** | sibling `a_census.py`, read by the classical stream | Same question, other code. Legal rate 4.4-5.4% of windows vs 6.3-10% above; the reason is [unknown]. A real grammar cuts both further [assumed]. `02-empirical.md`'s final summary gives about 17 / 59 / 188 / 219 independent rule-legal 5-wave structures at 1D / 4H / 1H / 15m |
| Patterns by division | Swings / 5 or / 8, 4H 5%; 4H 2% | 579 or 362; 2,272 or 1,420 | `sample_size_derived.py` | How many full patterns, as units. Upper bound, division [assumed] |
| Causal 0-1-2 events | Pullback confirmed, does price reach pivot 1 before pivot 0, 1H k=3 | **about 3,540** (of 8,148 triples) | `ewfib_swing_counts.py` | How many first-touch outcomes to score against the martingale baseline. No horizon, not independent |
| Swing-start barrier labels | Target 1.618 x threshold, 10-day limit; 1H x 4; 1H x 8; 4H x 4 | 4,502; 1,176; 1,128 raw, **effective 1,975; 712; 688** | `cml_label_overlap.py` | How many labels a classifier on generic swings has. Effective = summed uniqueness, an upper bound. This is the "700-2,000" |
| Hourly barrier, symmetric | Each hour, +/-1 sigma sqrt(H), H = 24h; 7d; 30d | 119,040; 118,896; 118,344 raw, **3,760; 729; 205** by autocorrelation (uniqueness 7,512; 1,166; 281; non-overlap 4,991; 713; 166) | `sample_size_derived.py` | How many independent outcomes a time-sampled forecast has: the live-loop rate |
| Hourly barrier, asymmetric | Each hour, +2 / -1 sigma sqrt(H), H = 24h; 72h; 168h | **119,803** bars give 119,448-119,592 labels, shrinking to about **4,914; 1,526; 661** (non-overlap 4,983; 1,660; 711) | `label_counts.py` | Same question, for a fine-tune's labels. Agrees in scale with the row above: both about span / H |
| Cycles | 4-year, weekly, daily, hindsight | 3; 23; 86 | `research/cycles-r1.md` | Slow-degree claims |
| Volatility state | Effective samples of log volatility | 41 to 2,202 (15m); 181 to 1,135 (1h abs r) | `jepa_predictable_part2.py`; `sample_size_by_degree.py` | How much a representation learner really sees |

Plain rule: pick the row that matches the question. Rows are nested and cannot be added. Engine events will be fewer than any of these [assumed]. All sit on one path.

### Power numbers: one hit-rate test at two hurdles, a rank test and a Brier test

| Number | Test | Script |
|---|---|---|
| 782 | Hit rate 55% vs 50%, two-sided 5%, 80% power, normal formula with z = 0.84 | `llm_pilot_score2.py`, `cml_bm_check.py` |
| 783 | Same, z = 0.8416, rounded up | `sample_size_by_degree.py` |
| 820 | Same, exact binomial | `sample_size_by_degree.py` |
| 1,473 | Same hit rate, hurdle t above 3 instead of 1.96 | `sample_size_by_degree.py` |
| 1,045 | AUC 0.55 vs 0.5 on a continuous score, rank test, balanced | `cml_bm_check.py`; `jepa_predictable_part2.py`'s formula agrees |
| 1,144 | Not power: Riley's events to fit 1 feature at AUC 0.55 without overfitting | `jepa_predictable_part2.py` |
| 31 / BSS | Paired Brier difference, calibrated forecaster vs flat baseline; 59 / BSS at t above 3. Brier skill 0.01: 3,109; 0.02: 1,539 | `sample_size_by_degree.py` |

Same forecaster, different tests [computed here from those formulas, binormal assumed]: AUC 0.55 equals a best hit rate of 53.5% and Brier skill 0.0078, which takes 1,045 events by rank test, about 1,560 by hit rate and about 4,000 by Brier. A 55/45 forecaster takes 783 by hit rate and 3,109 by Brier. Beating a baseline on Brier costs about 4 times the sample of showing association, because half the signal is spent paying for the forecast's own spread. All assume independent events.

### Null models: the "no difference" claim is much weaker than it reads

Block lengths actually used [verified in the code]:

| Script | Null | Block | Paths | Applied to |
|---|---|---|---|---|
| `cml_swing_null.py` | Shuffle; fixed block with replacement | 20 days: 480 1h, 120 4h, 20 1d bars | 200 each | All-swing next/previous ratios, 13 swing sets |
| `ewfib_swing_counts.py` | Shuffle; 20-day block; **per-bar sign flip**; short block = mean leg / 3 (2-33 bars) | 480, 120, 20, 1,920 (15m) | 200 each at 1d, 4h; 100 at 1h; 20 at 15m | Impulse cells, all-swing ratios, 0-1-2 outcomes |
| `sample_size_by_degree.py` | Shuffle; 20-day and 125-day blocks; per-bar sign flip; **sign flip of whole 20-day blocks** | 120 and 750 4h bars | 40 each | Swing counts, durations, up-first |
| `sh_count_density.py`, `sh_subwave_test.py` | Shuffle; block | 120 4h bars | 100, 30, 60 | Count density, 3-or-5 reading |
| `src/ewave/cycles/evaluate.py` | Shuffle; block with replacement | 20 1d bars | 200 each | cycles-r1 marks |

The principle: a block null with block length L copies everything shorter than L, so it can only reveal structure longer than L. Tallies from the saved JSON [computed here]:

| Saved output | Cells | 20-day block outside | Others outside (10% is chance) |
|---|---|---|---|
| `cml_swing_null.json`, windows, block holds 3.9-42 swings (7 sets, n 981-10,487) | 133 | **0** | Shuffle 39 |
| Same, block holds 0.3-1.2 swings (6 sets, n 64-297) | 114 | **9** | Shuffle 17 |
| `cml_swing_null.json`, bands, same two groups | 70; 60 | 2; 9 | Shuffle 45; 17 |
| `ewfib_swing_counts.json`, all-swing cells, 3 or more legs per block (11 configs) | 77 | **0** | Sign flip 39, short block 39, shuffle 42 |
| Same, under 3 legs per block (5 configs) | 35 | 7 | Sign flip 9, short block 11, shuffle 13 |
| Same file, impulse cells, all configs | 128 | 3 | Sign flip 30, short block 40, shuffle 34 |
| `sh_subwave_test.py`, block holds 3.4-11.6 swings | 56 | 0 | Shuffle 13 |
| `research/cycles-r1.md`, rate rows, block is 0.34 of a daily, 0.10 of a weekly cycle | 86 | 6 | Shuffle 11 |

So all 9 of the classical stream's 247 outside windows come from the sets where the block holds about one swing or fewer, and none from the 133 where it holds several. Taken together:
- **"BTC matches block paths at 1H and 4H" carries almost no information.** It would come out that way whatever BTC's swings looked like. The EW stream is right on this, and the classical stream's own output shows it. The claim cannot be judged from those columns.
- **What survives needs no null:** Fibonacci against neighbouring control windows on BTC itself: 17.1 / 17.1 (1H ATR x 4), 17.6 / 17.6 (1H ATR x 8), 17.9 / 17.9 (4H ATR x 4), 17.1 / 17.9 (1H 5%), theory 17.2 / 17.9 (`cml_swing_null.py`). No Fibonacci spike in all-swing ratios at those scales. Moderately strong for that object, silent on wave pairs (the Prechter objection), and totals can hide per-level shifts.
- **Against nulls that break swings BTC does differ,** in 39 of 77 all-swing cells. Sizes are small: at 1H k=3 near 1.0 5.45% vs 6.53%, near 0.5 4.13% vs 3.36%, near 0.618 5.34% vs 4.95%. Per-bar sign flip also shows BTC with 2-8% fewer swings: 2,899 vs 3,017 (2,965-3,069) at 4H 5%, 833 vs 902 (878-942) at 10% (`sample_size_by_degree.py`, 40 paths). This fits the EW stream's smooth depth gradient and reads as mild trend persistence, not a Fibonacci step. It is a first look: one venue, correlated cells, no correction, and the sign flip also removes drift and wick asymmetry. **Whether any of it is wave structure cannot be judged from these outputs.** I do not choose.
- **Where block is about one swing, the test is fair but thin:** n 64-297. Swing-size memory exceeds the block there (lag-1 log size 0.48 vs 0.28 at 4H ATR x 8, 0.48 vs 0.27 at 1D ATR x 4), which agrees with Politis-White's 125 days. The Fibonacci leads at high degree (29.0 / 10.1 at 4H 40%, n = 70; 23.8 / 12.7 at 1D 40%, n = 64) stay inside block ranges and stay leads.
- **"Sign flip" is two different nulls.** Per bar destroys swings. Per 20-day block keeps every swing inside a block, mirrored half the time, so swing ratios are copied exactly. The honesty note's "swing counts are nearly fixed by the vol path" (2,899 vs 2,899-2,928) comes from the block version, and the per-bar column in the same output does not support it. Its recommended null for "Fib ratios cluster" (sign flip 20d and block 20d) has the EW objection at 1H and 4H, and so does the gate "beat the null on both ends of the bracket": a real effect at swing scale would be copied into those nulls and fail. Section 6, items 8 and 12, carry the fix. The sibling census already sets block = median leg.
- **Other readings to adjust.** The structured note's "keeping 20-day clustering removes every difference" is not shown, since the block keeps swings too. Its main results stand on the shuffle column instead: 72-95% of windows hold an impulse on shuffled paths, gap 21.8 against 21.3. The plain shuffle is still too weak on its own, since it doubles swing length (1.67 d vs 3.83 d at 10%), but a surplus on BTC is what it can flag, and these rows show none.

**For the block-null columns in `research/cycles-r1.md`.** At cycle scale they are fair: the block is shorter than the cycles tested, and the column still flags 6 of 86 rate rows, near the 8.6 chance gives, unlike the zeros above. So "the cycle rules did not beat random paths" is not a block artefact. Four limits apply. Rows that live under 20 days (median confirmation lag, local candle behaviour) are copied, so equality there says little. Rows about bears and long memory ("weekly failure 39% vs 21% and 25%", "live lows hold worse") face a null that cannot hold such regimes. Block paths do not keep total return as the docstring says (3.78-12.55 log units on a 4H version vs BTC 7.74, `sample_size_by_degree.py`), which widens the ranges and may be part of why the weekly lead clears shuffled (12-56%) and not block (14-67%) [assumed]. And power: 23 and 86 cycles only see gaps of about 28 and 15 points. "Did not beat" means no large effect.

### Baselines: +7.3% and +12-15% are different mixes, both are geometry

| | Structured, `sh_barrier_baseline.py` | Honesty, `sample_size_by_degree.py` |
|---|---|---|
| Formula | d / (u + d), no volatility, no horizon | Finite-horizon barrier formula, past-only EWMA volatility (7-day half-life) |
| Barriers | Fixed stops 2, 5, 10, 20%, R:R 0.5-5 | +/-k sigma sqrt(H), k 0.5 and 1, ratios 0.618-2.618 |
| Horizon | None; unresolved dropped | 24h, 7d, 30d; timeout counts as not hit |
| Starts | Every 24 bars, 48 setups | Every 24 or 72 bars, 16 setups, 62,304 / 62,208 / 20,608 events |
| Flat comparator | One in-sample base rate over all setups | Walk-forward base rate |
| Brier | 0.2235 vs 0.2410 | 0.1736 vs 0.2004; 0.1798 vs 0.2107; 0.1925 vs 0.2191 |
| Skill | **+7.3%** | **+13.4%, +14.6%, +12.2%** (Platt 14.8, 14.7, 12.1) |

Neither is a property of BTC. Skill over a flat rate measures how spread out the setups' true odds are: adding a horizon spreads them much further (the same 1 sigma setup goes from 50% to 31.5%). Both agree on what matters: an engine probability that only encodes distances looks skilled, so never compare against a flat rate, and judge on the same events against B3. The EW stream's martingale baseline for 0-1-2 events is the same idea with no horizon: BTC minus baseline -1.4 to +2.1 points.

### GPU costs: same prices, different speed assumptions

Prices are compatible, from the same pages: RunPod (page dated 2026-10-08), community / secure per hour: RTX 4090 $0.34 / $0.89, A100 $1.19 / $1.79, H100 PCIe $1.99 / $2.89; Lambda: A10 $1.29, GH200 $2.29, H100 PCIe $3.29. [verified] The assumed throughput is not: JEPA's 3,000-7,000 windows/s at 724 MFLOPs per window is 2.2-5.1 TFLOP/s on a 4090, against the foundation stream's 12 TFLOP/s, a factor of 2.4-5.5 [computed]. At 12 TFLOP/s the JEPA 10-fold run takes 1.5 h, not 3.5-8.1 h; at JEPA's rate the Kronos figures rise by the same factor. CPU assumptions differ too: JEPA 75 GFLOP/s sustained [assumed], foundation stream 16-56 measured under load. No figure was measured on a real training run. No verdict changes: money is not the blocker in either.

### Effort: different scope, and logging is longer than either says

The plan's 17-25 weeks (16-24 in its TL;DR) is an experienced engineer at about 30 hours a week on the full system. The structured stream's 8-14 calendar weeks is a part-time cut-down version 1 with Claude Code, and the plan's own MVP is 6-8 weeks, so that is the fairer comparison. Both are judgment, not measurement; [METR's 2025 trial](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/) found experienced developers 19% slower with AI while feeling faster, and it is dated. The "6-12 months of forward logging" [assumed] gives about 140-275 independent events at the 24h rate, below the honesty gate's 300 for "no harm" (1.1 years), let alone 820 (3.0 years) for a 55% claim. Code time is the small part: calendar time decides.

### Other mismatches found while reconciling

- **Output tokens:** the cost model's base case is 1,500 output tokens per call; the pilot used 10.6-13.5k per count. At 12,000, Opus goes from $0.134 to about $0.34 a call, about $3,000 a year live and about $41,000 for a full 1H replay [computed from $20 per million]. Treat the Opus rows in section 2 as a floor.
- **Holdouts:** four proposed: 2022-11-22 on (honesty), 2023-01 on (EW), the last 2 years (structured), 2025-07-01 on (classical). Only the first is argued against power numbers. The choice belongs in the pre-registration.
- **Calibrators:** classical says Platt below about 1,000 events; honesty says slope-only or Platt until about 3,000 independent events, from its simulation. The stricter rule is the safer default until events are counted.
- **Volatility predictability:** see section 4, field 3: daily and 15m targets differ.

## 8. Marked part: his weekly-cycle observation

**Camel's "weekly cycle" means a cycle of 168-294 days, not the days of the week.** His observation: Elliott structures often finish at weekly-cycle lows, and the middle of the cycle is often a top.

**Where it fits.** As a logged feature in the outcome model and one row in the null harness. It cannot be a study of its own at this sample size.

**What was found.**
- Weekly-level marks, hindsight (`research/cycles-r1.md`): top left of the middle in 35% of cycles, right in 61%, at the middle (+/-5%) in the remaining 4% or so, under that narrow band. So "the middle is a top" is not the typical shape in those marks. [verified]
- One causal lead: top left of midpoint, then a lower low, 64% (n = 14) against 36-38% on nulls. It clears the shuffled range, not the block range. Wilson 38.8-83.7%; times 172 comparisons, nothing is left. Not refuted, not evidence. [verified]
- BTC-specific volatility seasonality exists at weekly scale ([Petrov et al.](https://smallake.kr/wp-content/uploads/2019/02/SSRN-id3243797.pdf)); hour-of-week explains 16-18% of 15m volatility anomaly since 2024 and has no return signal, R2 -0.20% (`jepa_predictable_part.py`). Day-of-week return effects are mixed ([Caporale, Plastun](https://bura.brunel.ac.uk/bitstream/2438/17208/3/FullText.pdf), [Kinateder, Papavassiliou](https://researchrepository.ucd.ie/server/api/core/bitstreams/3fe12e0f-f1c4-4226-937e-b7fc034dfcd9/content)). None of that is Camel's cycle.
- 4-year level: [Molnar 2026](https://arxiv.org/pdf/2607.26188) finds top timing rare on block paths, 0 of 10,000, but bottom timing reproduced by 31-43% of paths. cycles-r1 finds spacing this even in 1 of 400. Different tests (top to bottom vs bottom to bottom), so no conflict. Both are post hoc, n = 3. Live window 2026-10-05 to 11-16 (Molnar), box 2026-10-04 to 11-20 (cycles-r1). [verified]

**What was not found.** No backtest, out-of-sample test or peer-reviewed study linking Elliott structures to cycle lows or mid-cycle tops, on one targeted search that returned only opinion pieces. No peer-reviewed spectral test of a 4-year cycle with proper significance. This is "not found", not "no link".

**How to read it.** Cycle lows and wave ends mark the same kind of point, the lowest low of a stretch, so they will coincide on any path, and the observation can be true on the chart and carry no information [assumed reasoning]. The test: distance from each engine wave end to the nearest causally marked cycle low, on BTC against null paths. Power: only gaps of about +28 points can be seen at 23 cycles.

## 9. The tension: history study against live calls

His Oct 23 note holds that wave counts are so individual that a tool should not count for people; it should hold the trader's own count to account, by logging main and alternate counts, marking invalidation, and showing later where the bias lies. Today he asks for a model that learns Elliott Wave from history. These pull in different directions, and the evidence supports keeping both, split by use.

- **History study:** the engine counts in bulk, as a research instrument, to measure ratios, outcomes and rule value against nulls. Nobody reads its labels as what the market is doing. Opus's memory is harmless when it only drafts hindsight labels.
- **Live:** the tool scores his logged count and invalidation against B3, as one forecaster, and shows where the bias lives. No live "AI count". A fine-tune on his labels would be the opposite of his note.
- **What this costs him:** a model that "knows" BTC, in the sense he asked for, is not on offer from any approach here. What is on offer is measured statistics, and an accounting of his own calls: calibration in the large in about 1.4 years at 140 trades a year, edge in about 6, by the same arithmetic as his Sep note. [inference, arithmetic verified]
- **What would change this:** a single guideline, a TDI signature or a learned state that beats B3 on swing-breaking nulls, out of sample, at every threshold. Then a live engine probability has earned a place next to his count, as a logged second opinion.

## 10. How the approaches compare

Evidence column: out-of-sample value on markets, as opened. "CPU" means this 4-core box without a GPU.

| Approach | Learns BTC-specific behaviour? | Needs labels? | Evidence of out-of-sample value on markets | CPU-feasible? | Cost | Interpretability | Fit with "deterministic counting, calibrated outcomes" |
|---|---|---|---|---|---|---|---|
| Plain JEPA | Volatility state most likely [assumed]; nothing on BTC found | No for encoder; yes for probe | Weak: at or barely above a random encoder in TFWM; STOCK-JEPA positive only with a prior, cross-section | One small run, 45-235 h; no grid | $1-$173 rented | Low: an unlabelled vector | Compatible only as an extra engine field after calibration |
| Opus direct | No: holds memory, learns nothing per call | No | None on BTC; FINSABER, DXRG null; pilot's skill is memory | Yes, API | $112 (post-cutoff) to $16,048 (full) for a 1H replay, more with thinking; narrator $175 a year | Fluent reasons, unverifiable | Breaks it if it counts; fits as narrator or logged test |
| Fine-tuned open LLM | Weakly: base rates, reversal | Yes | None beating naive with walk-forward and costs; text tasks yes | No training on CPU; short prompts only | $4-$5,000 per adapter; serving $134-$70,080 a year | Low | Breaks it: not deterministic, not fitted probabilities |
| Foundation model, zero-shot | No: generic bars and volatility | No | Rare over no-change; negative at 20 bps; Kronos BTC P(up) no signal; volatility near log-HAR | Mini kill test yes, 6-20 h; full replay no | $0-$117 | Low | Fine as an outside baseline, not inside the engine |
| Foundation model, fine-tuned | Maybe scale and time of day; unproven | No, self-supervised on prices | Fine-tuning usually hurt portfolios; helps volatility and VaR; no BTC protocol found | No | $0.2-$13 per run, walk-forward $2-$116 | Low | Same; leak patch needed; contamination stays |
| Logistic or LightGBM on outcome labels | Yes: volatility, geometry, drift, setup odds | Yes, automatic outcomes | Modest: Bysik filter Sharpe 1.09 vs 0.82, not significant; meta-labelling helps, rarely clears deflated Sharpe; no wave-feature test | Yes, seconds | $0 | High for logistic, medium for trees | Best final layer: calibrated outcomes by construction |
| Ratio tables or hierarchical Bayes | Yes: that is the direct answer | Engine labels, Fibonacci-free | Method only; no published use on swing ratios | Yes, seconds to minutes | $0 | High | Direct fit: code over pivots, null-controlled |
| HMM | Volatility regimes | No | Real for VaR and volatility; thin for direction (30 forecasts in one study) | Yes | $0 | Medium; states shift across refits | Causal feature only, forward filter only |
| Deterministic parser with null gate | Measures it; adds nothing by itself | No for counting | None for Elliott parsing; pilots show rule validity alone carries none; W3 study p = 0.063 | Yes, milliseconds per parse; overnight for nulls | $0 | Highest: rule trail per hypothesis | Exact fit, and the thing the rules describe |
| Opus as logged variant proposer | Indirectly, through tests | No | Positive on cross-sections (R&D-Agent, SEADS); no single-asset test with a stated variant count | Yes, API | Modest; under $10 per run claimed elsewhere | High, since the output is code | Fits if the evaluator is out of reach and every variant is counted |

Reading it: the table has one group of tools that measure (parser, null gate, ratio tables, outcome model) and one group that would have to discover something (JEPA, foundation models, fine-tunes). Evidence and cost favour measuring first, because the second group needs the first group's labels and gates to be judged at all. What this does not say: that JEPA or a foundation model cannot work on BTC. Nobody has tested one properly on BTC with costs and a sound null. A capped test is cheap, and the verdicts above say when to run it.

## 11. Corrections to the master plan

Listed only. The plan was not edited.

1. TL;DR on Batchelor and Ramyar, Kempen and Westland: wrong as worded. None tests Elliott structure. Suggested line: no rigorous study has tested Elliott wave pairs; tests on stock swings and levels find no Fibonacci effect; on BTC nothing adequate exists.
2. Westland 2024: quotes are real but partial; no wave counts, no Fibonacci test, no null. Remove as evidence on Elliott or Fibonacci in BTC.
3. "Multiple-testing is exactly what sank the Fibonacci studies": loose; no study was sunk that way.
4. Prechter: incomplete. His first objection is form (filtered trends are not waves); he also says adjacent-wave ratios are not claimed, which leaves NewWave's W2 and W4 bands exposed.
5. Phase 2 null, line 144 and repo rule: "shuffled" alone is too weak (doubles swing length), and "block-bootstrapped" needs a block shorter than the swing tested. Add per-bar sign flip.
6. Phase 1-2 order: move the null harness and a threshold grid into Phase 1 as a gate, before any soft-score tuning. Require a Fibonacci-free labeller for ratio statistics.
7. Phase 3 "thousands of labeled examples": true for raw labels only. Effective n is about 200-3,800 by horizon, and 15-510 for rule-legal windows.
8. Phase 3 calibration: "isotonic or Platt" should be slope-only or Platt until about 3,000 independent events, isotonic for diagnosis.
9. Phase 5 "expanding window": rules out GW as stated; use a rolling window if GW is used.
10. Baselines: (a) base rate is too easy, since geometry alone earns +7% to +15%; make recalibrated B3 the go/no-go comparator.
11. Posterior: "solves EWAVES's flip-flop problem honestly" is unsupported, and a likelihood from Phase 2 statistics is circular. Make the null a hypothesis, with clutter density from null paths as the denominator ([Reid 1979](https://doi.org/10.1109/tac.1979.1102177), abstract) [assumed, not built].
12. Beam and particles: "explodes" is true for enumeration, not for chart counting. Consider a sum-over-parses chart [assumed, not built with scoring].
13. LLM guardrail: "violate hard rules or invent levels" has no citation and was not reproduced on Opus 5.5 with text grids (0 of 35, 86 of 86, small pilot). Keep the rule, change the reasons: memory, non-repeatable counts, no abstention, unverifiable indicators. The string-match guard misses context mismatch, the largest error class in [Cao et al.](https://arxiv.org/html/2404.06162v3).
14. Prior art: add ElliottAgents as weak evidence. `drstevendev` has no licence, so ideas only. `python-taew` is not a straight port. The BTC CSV example and "ELWAVE scores alternatives" are unconfirmed. "11 pattern types" is unverified; later papers say 12. IJNAA used FX pairs, not stocks.
15. Dos Santos: abstract only; "closest published analogue" cannot be supported from it. Baptiste-dehay: copy the governance, not the detector (possible bug, author has not confirmed).
16. EWAVES: still unpublished, but the plan misses the abstract now in the FAQ and the public raw data, which changes the assessment.
17. TL;DR 16-24 weeks against the table's 17-25.

Also outside the plan: `research/cycles-r1.md` and the `evaluate.py` docstring say both nulls keep BTC's total return; that is exact only for the shuffled null.

## 12. Own runs in this research

All of these are **small demonstrations and first looks, not pre-registered tests.** Settings were chosen while looking at BTC. No correction for multiple testing. Read-only on the repo, one process, Bitstamp unless stated. Add them to the ledger as trials.

| Script | What it measured |
|---|---|
| `llm_pilot_make.py`, `llm_pilot_score.py`, `llm_pilot_score2.py`, `llm_pilot_score3.py`, `llm_pilot_score4.py`, `llm_pilot_yearvol.py` | **LLM pilot:** blind test of Opus 5.5 on 4 count windows, 21 dating windows, 20 recall dates, 3 runs. **It cost about 557,000 sub-agent tokens and was not requested in the brief;** the stream ran it because the literature has no answer for this model and task |
| `llm_bar_sizes.py`, `llm_cost_model.py` | Tokens per bar row; cost tables for live, replay, narrator, fine-tune, serving |
| `label_counts.py` | Hindsight legs, hourly outcome labels with effective N, naive check on PRICE's window, course text sizes (no text copied) |
| `jepa_predictable_part.py`, `jepa_predictable_part2.py` | Autocorrelation and walk-forward direction and volatility at 15m, effective N, zigzag counts, Riley sample sizes, AUC power |
| `jepa_toc_check.py`, `jepa_cost_calc.py`, `jepa_cpu_flops.py`, `jepa_schema_check.py` | Candle-turn decay on two venues; JEPA cost arithmetic; CPU ceiling; venue columns. No model trained |
| `tsfm_kronos_demo_eval.py`, `tsfm_cpu_flop_probe.py` | Grading of Kronos's 8,562 committed BTC forecasts; CPU proxy. Kronos itself not run |
| `cml_swing_null.py`, `cml_bm_check.py` | Swing statistics on 13 sets against theory, shuffle, 20-day block; random-walk theory check and sample sizes |
| `cml_predictability.py`, `cml_label_overlap.py`, `cml_naive_mape.py` | Walk-forward price/MA and HAR, SMA rules by era, LightGBM timing; label overlap and effective N; no-skill price metrics |
| `ewfib_br_table.py`, `ewfib_ma_persistence.py`, `ewfib_dehay_check.py` | Re-tally of Batchelor and Ramyar's table; moving-average persistence baseline; check of a swing-detector bug |
| `ewfib_swing_counts.py`, `ewfib_swing_report2.py` | 16 configurations, 8,320 null paths: legs, rule-legal impulses, template cells, all-swing ratios, 0-1-2 outcomes |
| `sh_rvr_analyse.py`, `sh_real_vs_perm.py` | EWAVES vendor CSV statistics; AUC of plain statistics on the vendor's design |
| `sh_count_density.py`, `sh_crosscheck.py`, `sh_pivot_scale.py`, `sh_subwave_test.py` | Parse counts on BTC and nulls; brute-force check; pivot counts and timing; 3-or-5 reading |
| `sh_barrier_baseline.py`, `sh_misc_numbers.py`, `sh_scholar_scan.py` | Geometry against BTC; expected maxima; OpenAlex and arXiv scan |
| `sample_size_by_degree.py`, `sample_size_derived.py` | Swings, memory, overlap, power, nulls, barrier baseline, calibration simulation, per-degree tables |
| Writer's tallies, no new data loaded, not saved | Outside counts by swings per block from the saved JSON; flags in cycles-r1; AUC to Brier conversion |

What the runs cannot show, across the board: individual NewWave guidelines, TDI, his own eye, a real grammar with nesting, 1H count density, venues other than Bitstamp for most ratios, linear-price ratios (log only in the swing sets), scored forecasts from any engine, fine-tuned models, and anything needing trained JEPA or Kronos weights on this box. Absence of an effect in a run of this size means it was not seen, not that it is not there.

## 13. What stayed open

- **Web search:** the shared web-search budget ran out during the round. Last planned searches that did not run: Merrill 1977; independent records of Elliott forecasters, Hulbert primary data; newer calibration studies; more BTC hazard, LPPLS and wavelet work; one more query on anonymised price recognition. So recent items may be missing.
- **Unread items that may matter:** Shanaev and Gibson 2022, Mahadzva 2026 and Lu 2026 (SSRN, metadata only); Prechter and Goel 2003 ("Idealized Elliott Waves and Random Walk Tests", SSRN 403); the Applied Sciences ElliottAgents paper (MDPI 403), the only LLM-plus-Elliott paper on BTC; Lopez de Prado's 2018 book; Hansen 2005; Deprez and Frommel's numbers; Dos Santos full text; TFWM's net Sharpe per encoder (figure only); Mahns et al. full text.
- **Pages read through a reader service (`r.jina.ai`, because the publisher refused a direct fetch):** Naga Swetha and Arya 2026; Atsalakis et al. 2011; Dos Santos et al. 2023 and 2024; Gurrib et al. 2022; Khattak et al. 2024; Kavajecz and Odders-White 2004; Urquhart 2017; Tsinaslanidis 2024.
- **Pages read through a Wayback copy:** Yang et al. 2023; Volna et al. 2013 (abstract page); Prechter's "Elliott Waves, Fibonacci and Statistics". Goel's page could not be recovered.
- **Pages read through the fetch tool's summariser, not raw:** model cards and vendor pages in the foundation-model stream; Anthropic help pages and vendor pricing in the cost stream; vendor pages, CXO and repos in the structured stream. Long HTML papers in the LLM stream were read to the first 100k characters where stated. Marked in the bibliography.
- **Empirical gaps:** no BTC JEPA; no fine-tuned Kronos on BTC with a public protocol; no barrier-hit calibration for any foundation model; no LLM calibration on price-derived outcomes; whether 1H or 4H windows are recognised by Opus; whether mirroring defeats recognition; real engine event counts; ETH or other-asset ratios; stop clusters at Fibonacci levels (needs L2 and liquidation data); a HAR or GARCH null; a drift-preserving swing-breaking null.
- **Sibling work:** an empirical stream (`02-empirical.md`) and a bake-off (`03-bakeoff.md`) ran larger tests the same day. They are not merged here, so this report stands on the literature and its own small runs. Only four pointers were added: the census counts, the empirical worker's W2 and W4 result (section 4), its structure counts (section 7), and the bake-off's recognition and rule-compliance results (section 2). Only the summaries of those files were read; they were not reconciled in full with this one.
- **Spot check after writing:** these were re-opened against the source and matched: the TFWM Rank IC table; STOCK-JEPA's numbers; FinVerse (60,232 of 116,897 series evaluated, 2 of 43 beat persistence); Rahimikia's R2 and the 20 bps statement (saved text); Kronos's crypto row and the 93%; Brini's abstract; Bysik and Slepaczuk's Sharpe and interval; the AWS lifecycle page for Claude 3 Haiku; Anthropic's API credits page; CXO's table and Prechter page. The arithmetic behind 782, 1,473, 1,045, the MinBTL figures and the Wilson interval was redone by hand. All other numbers rest on the research streams' reading of their sources.

## 14. Annotated bibliography

Only sources actually opened. Each line: source, year, URL, what it shows and how strong, access. "Via summariser" means read through a fetch tool that condenses pages; "via reader" means `r.jina.ai`; "read in part" means targeted reading of a long text. Citation problems the streams flagged are noted where they matter.

### JEPA and world models

- Assran et al. 2023, I-JEPA. https://arxiv.org/abs/2301.08243. Defines image JEPA, 79.3% ImageNet linear; strong for vision. Full text.
- Bardes et al. 2024, V-JEPA. https://arxiv.org/abs/2404.08471. Video JEPA with attentive probes; strong for vision. Full text.
- Assran et al. 2025, V-JEPA 2. https://arxiv.org/abs/2506.09985. 22M videos, up to 1B parameters; strong for vision. Full text.
- Mur-Labadia et al. 2026, V-JEPA 2.1. https://arxiv.org/abs/2603.14482. Successor, probes and robot tasks. Abstract only.
- Balestriero, LeCun 2025, LeJEPA. https://arxiv.org/abs/2511.08544. SIGReg anti-collapse; strong on vision, authors' own. Full text.
- Kuhn et al. 2026, LeVJEPA. https://levjepa.github.io/. Cheaper video JEPA, authors' figures; preprint. Project page.
- Maes et al. 2026, LeWorldModel. https://arxiv.org/abs/2603.19312. One-GPU world model from pixels. Abstract only.
- Singh 2026, reproduction of LeWorldModel. https://arxiv.org/abs/2608.10145. Four conventions missing from configs; single author. Read in part.
- Terver et al. 2026, EB-JEPA. https://arxiv.org/abs/2602.03604. Teaching library. Abstract only.
- Cui et al. 2026, JEPA generalisation theory. https://arxiv.org/abs/2606.27014. Finite-sample bound; theory. Abstract only.
- TechCrunch 2026, AMI Labs raises $1.03B. https://techcrunch.com/2026/03/09/yann-lecuns-ami-labs-raises-1-03-billion-to-build-world-models/. Funding and agenda; reliable news, no finance statement. Full page.
- Anonymous wiki on LeCun 2022. https://mishig-jepawiki.hf.space/wiki/papers/lecun-position-paper. Summary of the position paper; secondary, weak. Full page.
- Sobal et al. 2022. https://arxiv.org/abs/2211.10831. JEPA weak on slow stable distractors; workshop. Abstract only.
- Littwin et al. 2024. https://arxiv.org/abs/2407.03475. JEPA favours high regression-coefficient features; deep linear only. Full text.
- Ruiz-Morales et al. 2025. https://arxiv.org/abs/2511.09783. Near-identity predictor learns regime indicators; synthetic only. Read in part.
- Feng et al. 2026. https://arxiv.org/abs/2609.31680. Forecasting pretraining: 24 of 49 cells improve, coin flip; best test of its kind. Full text.
- Ennadir et al. 2025, TS-JEPA. https://arxiv.org/abs/2509.25449. Mixed against autoregressive and MAE; workshop. Full text.
- Verdenius et al. 2024, LaT-PFN. https://arxiv.org/abs/2405.10093. Mixed against ARIMA. Read in part.
- Thimonier et al. 2024, T-JEPA. https://arxiv.org/abs/2410.05016. Tabular, authors' own; among the worst on stocks in STOCK-JEPA. Read in part.
- Guetschel et al. 2024, Signal-JEPA. https://arxiv.org/abs/2403.11772. EEG; preliminary. Read in part.
- Kim 2024, ECG-JEPA. https://arxiv.org/abs/2410.08559. AUC 0.912 vs 0.882, self-reported. Read in part.
- Taleshinosrati et al. 2026, FOUND-AF. https://arxiv.org/abs/2608.03597. ECG benchmark names another winner. Abstract only.
- Dong et al. 2024, Brain-JEPA. https://arxiv.org/abs/2409.19407. fMRI claim, numbers not read. Abstract only.
- He et al. 2026, MTS-JEPA, now SC-JEPA. https://arxiv.org/abs/2602.04643. Anomaly prediction, authors' own; numbers from v1. Full text of v1.
- Petersen et al. 2026, HEPA. https://arxiv.org/abs/2605.11130. Label efficiency, VIX row; authors' own. Read in part.
- Lee, Sim 2026, CF-JEPA. https://arxiv.org/abs/2606.07031. 27% lower multivariate MSE, authors' own. Abstract only.
- Nie et al. 2026, Phys-JEPA. https://arxiv.org/abs/2606.16076. DLinear wins its own table. Read in part.
- Toderean et al. 2026, Distributed JEPA. https://arxiv.org/abs/2609.17029. Energy forecasting under bad data. Abstract only.
- Melino Muhammad et al. 2026, CGM-JEPA. https://arxiv.org/abs/2605.00933. Small cohorts. Abstract only.
- Dong, Mengaldo 2026, S2S-JEPA. https://arxiv.org/abs/2610.03106. Fair positive in subseasonal weather. Read in part.
- Kuo et al. 2026, ACTS-WM. https://arxiv.org/abs/2610.37963. Improves pretrained encoders, numbers not read. Abstract only.
- Merchant et al. 2026, TFWM. https://arxiv.org/abs/2610.09048, code https://github.com/fin-ai-lab/tfwm, models https://huggingface.co/fin-ai-lab. Strongest financial JEPA evidence; multi-regime, unreplicated. Full text, README, page.
- Luo et al. 2026, STOCK-JEPA. https://arxiv.org/abs/2610.07006. Best positive; one test window, partial costs. Main text and appendices E-G.
- Wang 2026, Fin-JEPA. https://github.com/cedricwyh/fin-jepa/blob/main/docs/jepa_paper.tex, repo https://github.com/cedricwyh/fin-jepa. Honest negative; unreviewed. Full paper source, README.
- Mahns, Balestriero, Assran 2026. https://icml.cc/virtual/2026/poster/65643. Embeddings track second moments far more than direction; peer reviewed per listing, numbers unseen. Abstract only.
- ArgusJEPA, CassaFormer, jepa-transformer-model 2026. https://huggingface.co/dams2005/ArgusJEPA, https://huggingface.co/dams2005/CassaFormer, https://github.com/daMS2005/jepa-transformer-model. No results. Pages.
- ashesh8500 2026, FinJEPA. https://huggingface.co/ashesh8500/finjepa. Agent-generated, no evaluation. Page.
- Dolphin et al. 2024. https://arxiv.org/abs/2407.18645. SSL for hedging, 19.1% vs 23.8% volatility; no costs. Read in part.
- Hwang et al. 2024, SimStock. https://arxiv.org/abs/2407.13751. Stock similarity. Abstract and partial text.
- Lee et al. 2026, FASCL. https://arxiv.org/abs/2602.10711. Spread trade net Sharpe 2.49-3.98 at 5 bps, break-even 8-12 bps; one test year. Read in part.
- Ye, Schuller 2024, CET. https://arxiv.org/abs/2409.17392. CPC on earnings; no cost test found. Abstract and partial tables.
- Ma et al. 2021. https://arxiv.org/abs/2112.10139. Denoised labels with self-supervision, includes BTC. Abstract only.
- Liu, Shu, Zhu 2024. https://doi.org/10.3390/stats7020025. Contrastive crash classification, no trading test visible. Abstract only.
- Li et al. 2024, SimLOB. https://arxiv.org/abs/2406.19396. Order-book SSL for simulator calibration. Abstract only.
- Prata et al. 2023, LOBCAST. https://arxiv.org/abs/2308.01915. All 15 deep LOB models drop on new data. Abstract only.
- Jiang, Kelly, Xiu draft of 2023 JF paper. https://www.kuntara.net/uploads/1/1/4/9/114945401/ssrn-id3756587-3.pdf. Chart CNN, gross Sharpe 7.2 weekly; check the JF version before quoting. Read in part.
- ArjunDivecha 2026, Pattern. https://github.com/ArjunDivecha/Pattern. Informal replication, edge mostly 1999-2004. README.
- Gu, Kelly, Xiu 2020. https://www.nber.org/papers/w25398. ML on stock returns, R2 0.33-0.40%, gross; strong. Read in part.
- Kelly, Malamud, Zhou 2024. https://economics.yale.edu/sites/default/files/2024-01/The%20Journal%20of%20Finance%20-%202023%20-%20KELLY%20-%20The%20Virtue%20of%20Complexity%20in%20Return%20Prediction%20%281%29.pdf. Virtue of complexity. Read in part.
- Nagel 2025. https://bpb-us-w2.wpmucdn.com/voices.uchicago.edu/dist/f/575/files/2025/07/Complexity_2.pdf. Reduces it to volatility-timed momentum; strong critique, working paper. Abstract, intro, conclusion.
- vishwesh-V 2025, virtue-of-complexity. https://github.com/vishwesh-V/virtue-of-complexity. Informal replication. README.
- Shanaev et al. 2023. https://pmc.ncbi.nlm.nih.gov/articles/PMC10015199/. Candle-turn effect in BTC; repo data shows it gone by 2024. Abstract only, via Europe PMC.
- Catania, Sandholdt 2019. https://www.mdpi.com/1911-8074/12/1/36. BTC intraday seasonality, predictability up to 6 hours varying over time. Abstract only.
- Tang et al. 2024. https://arxiv.org/abs/2402.11930. Abs-return power law; Hurst 0.42-0.49. Abstract only.
- pmsampsize code and manual, undated. https://github.com/cran/pmsampsize/blob/master/R/pmsampsize_bin.R, https://cran.r-universe.dev/pmsampsize/doc/manual.html. Riley's formula, since the BMJ paper was closed. Opened.
- Wiese et al. 2019, Quant GANs. https://arxiv.org/abs/1907.06673. Generative paths, claimed fidelity. Abstract only.
- Huang et al. 2024, FTS-Diffusion. https://proceedings.iclr.cc/paper_files/paper/2024/file/f90fc76b199fe6b0ec2a51aaf72c3277-Paper-Conference.pdf. Scale-invariant patterns, authors' comparison. Read in part.
- Cetingoz, Lehalle 2025. https://arxiv.org/abs/2501.03993. Synthetic finance data limits. Abstract only.
- RunPod 2026. https://www.runpod.io/pricing. GPU prices, page dated 2026-10-08. Page.
- Lambda 2026. https://lambda.ai/pricing. GPU prices, undated beyond 2026. Page.
- Vast.ai 2026. https://vast.ai/pricing. Price grid empty when fetched. Page.
- Tech Insider 2026. https://tech-insider.org/runpod-vs-lambda-vs-vast-ai-2026/. Secondary, date mismatches, weak. Page.

### LLMs used directly

- Hu et al. 2026. https://arxiv.org/html/2604.12659v1. 193,524 candlestick charts, 49.4-53.5%; no tests; medium. Full text.
- Wang Z. 2026, Martingale Doppelganger-Eval. https://arxiv.org/html/2606.17423. Trend followed, evidence ignored; strong design, single author. First 100k of 133k characters.
- Wang X. et al. 2026, E2A-Bench. https://arxiv.org/pdf/2609.14302. Claims against OHLCV facts; not returns. Text extracted.
- Shu et al. 2025, FinChart-Bench. https://arxiv.org/html/2507.14823. Corporate charts, no candlesticks. Full text.
- Qiu, Chersoni 2024, StockGenChaR. https://arxiv.org/pdf/2412.04041. 1,972 Elliott-vendor chart captions, about 40% sentiment match. Text extracted.
- Garre et al. 2026, Chartography. https://arxiv.org/html/2608.10677. Current models 9-45% on professional chart tasks, Opus 4.8 at 15.9%; vendor author, no human baseline. Full text.
- Tang et al. 2025, ChartMuseum. https://arxiv.org/abs/2505.13444. Human 93, best model 63. Abstract only.
- Zhang X. et al. 2025, CRBench. https://arxiv.org/html/2509.04457v1. Reading values off charts; own benchmark. Full text.
- Gruver et al. 2023, LLMTime. https://arxiv.org/html/2310.07820. Zero-shot on regular series, older models. First 100k of 126k characters.
- Jin et al. 2024, Time-LLM. https://arxiv.org/abs/2310.01728. Claims against specialised forecasters. Abstract only.
- Tan et al. 2024. https://arxiv.org/html/2406.16964. Removing the LLM does not hurt; strong ablation. First 100k of 116k characters.
- Merrill et al. 2024. https://arxiv.org/html/2404.11757. Weak zero-shot reasoning; older models. First 100k of 111k characters.
- Gwiazda et al. 2026, TimeSeriesExamAgent. https://proceedings.iclr.cc/paper_files/paper/2026/file/8b6dd6597c2edeb9ee62468ccea6f512-Paper-Conference.pdf. Finance exam about 0.6; current models. Text extracted.
- Yu et al. 2026, TSRBench. https://arxiv.org/html/2601.18744. Scale does not help prediction; no naive baseline. Full text.
- Ahamed et al. 2026, TFRBench. https://arxiv.org/abs/2604.05364. Reasoning traces lift 40.2% to 56.6%. Abstract only.
- Agrawal et al. 2026, FinTradeBench. https://arxiv.org/html/2603.19225v6. Indicators far above raw bars; LLM judge. First 100k of 201k characters.
- Liang et al. 2025, PriceSeer. https://arxiv.org/pdf/2601.06088. Post-cutoff hit rates, no naive; weak. Text extracted.
- Wawer, Chudziak 2025. https://arxiv.org/html/2506.16813v1, ICAART version https://www.scitepress.org/Papers/2025/131912/131912.pdf. Cells of 8-28, no baselines; weak. Full text.
- Chudziak, Wawer 2024/2025, ElliottAgents. https://arxiv.org/html/2507.03435v1. Same system; case-study arithmetic does not reconcile; weak. Full text.
- Wawer et al. 2024, Applied Sciences 14(24) 11897. https://doi.org/10.3390/app142411897, record https://www.citedrive.com/en/discovery/large-language-models-and-the-elliott-wave-principle-a-multi-agent-deep-learning-approach-to-big-data-analysis-in-financial-markets. Tested on stock and crypto per abstract; not rated. Abstract only, third-party record.
- noahnan-max 2026. https://github.com/noahnan-max/elliott-wave-trading-system. Markdown skill, no evaluation. Repo page.
- Li W.W. et al. 2025/2026, FINSABER. https://arxiv.org/html/2505.07078v5. Strongest long-run test; LLMs trail on Sharpe. First 100k of 124k characters.
- Barton et al. 2026, DXRG. https://arxiv.org/pdf/2609.05663. Largest live record, no directional edge; commercial lab, discloses retractions. Text extracted.
- Chen et al. 2025/2026, StockBench. https://arxiv.org/html/2510.02209. 82 days, small differences, no test; inconsistent dates. Full text.
- Yu et al. 2025, LiveTradeBench. https://arxiv.org/html/2511.03628. 50 days, no baseline or costs. First 100k of 136k characters.
- Qian et al. 2025, Agent Market Arena. https://arxiv.org/html/2510.11695. BTC 2 of 20 beat buy and hold; possible artifact. Full text.
- Fan et al. 2025, AI-Trader. https://arxiv.org/html/2512.10971. Very short windows. Full text.
- Li et al. 2024, CryptoTrade. https://arxiv.org/html/2407.09546. "Comparable" to buy and hold; short windows. Full text.
- Xiao et al. 2024, TradingAgents. https://arxiv.org/html/2412.20138. Three months, Sharpe implausible by its own account. First 100k of 117k characters.
- Zhang W. et al. 2024, FinAgent. https://arxiv.org/abs/2402.18485. 84.39% claim, does not survive FINSABER. Abstract only.
- Jeon, Lee 2026, BlindTrade. https://arxiv.org/html/2603.17692v1. Positive in one short window, holdout screening flagged. Full text.
- ForkLog 2025. https://forklog.com/en/four-out-of-six-ai-models-suffer-losses-in-trading-tournament/, https://forklog.com/en/ai-model-grok-4-2-triumphs-in-trading-tournament/amp. Alpha Arena; secondary. Full pages.
- iWeaver 2026. https://www.iweaver.ai/blog/alpha-arena-ai-trading-season-1-results/. Alpha Arena, conflicts with ForkLog; secondary. Full page.
- TradeRank 2026. https://www.traderank.ai/blog/alpha-arena-alternatives-2026. Secondary, a competitor. Full page.
- sipi.bot 2025. https://sipi.bot/incidents/alpha-arena-six-models-lose-2025-11. Secondary, promotional. Full page.
- PapersWithBacktest 2026. https://paperswithbacktest.com/course/vision-language-models-candlestick-charts. "Illustrative ranges"; used only as a lead. Full page.
- Lopez-Lira et al. 2025. https://arxiv.org/html/2504.14765v2. Strongest recall measures, GPT-4o. First 100k of 185k characters.
- Sarkar, Vafa 2024. https://icml.cc/virtual/2025/48685. Lookahead bias in pretrained models. Abstract only.
- Glasserman, Lin 2023. https://arxiv.org/abs/2309.17322. Anonymised headlines beat raw in-sample. Abstract only.
- Drinkall et al. 2024, Time Machine GPT. https://arxiv.org/abs/2404.18543. Point-in-time models. Abstract only.
- He et al. 2025. https://arxiv.org/html/2502.21206. Bias modest for news. Full text.
- Yan et al. 2026, DatedGPT. https://arxiv.org/abs/2603.11838. Yearly cutoffs, lookahead adds 26.4 bps per SD. Abstract only.
- Gao et al. 2025/2026, Lookahead Propensity. https://arxiv.org/abs/2512.23847. Date-only recall probe. Abstract only.
- Li X. et al. 2025, Profit Mirage. https://arxiv.org/html/2510.07920. Decay numbers solid, FactFin claims single-run. Full text.
- Benhenda 2026, Look-Ahead-Bench. https://arxiv.org/pdf/2601.13770. Small universe; random control also fell. Text extracted.
- Li W.W. et al. 2026, FinCAD. https://arxiv.org/html/2605.24564. Inference-time mitigation, small models only. First 100k of 149k characters.
- Wongchamcharoen, Glasserman 2025. https://arxiv.org/abs/2511.14214. Chronology in LLMs. Abstract only.
- Van Koevering, Kleinberg 2024. https://arxiv.org/html/2406.00092. Over-alternation when generating random sequences. Full text.
- Bigelow et al. 2023/2024. https://arxiv.org/html/2310.17639. Run aversion, older models. First 100k of 132k characters.
- Hasanhodzic, Lo, Viola 2010. https://arxiv.org/pdf/1002.4592. Humans tell real returns from permuted, 78 subjects; small but clean. Read in part.
- Atil et al. 2024/2025. https://arxiv.org/html/2408.04667v5. Non-determinism at temperature 0; older models. Full text.
- Zhang W. et al. 2026, AlphaForgeBench. https://arxiv.org/html/2602.18481. Strategy as code removes instability; some internal conflicts. First 200k of 216k characters.
- Yang et al. 2025, Prophet Arena. https://arxiv.org/html/2510.17638. Event calibration, GPT-5 Brier 0.184. First 100k of 217k characters.
- Nel 2025, KalshiBench. https://www.alphaxiv.org/abs/2512.16030. Claude Opus 4.5 ECE 0.120; single author. Via alphaXiv.
- ffrench-Constant et al. 2026, ConfidenceBench. https://arxiv.org/abs/2607.20526. Claude Opus 4.6 Brier 0.103. Abstract only.
- Halawi et al. 2024. https://arxiv.org/html/2402.18563v1. GPT-4 retrieval 0.179 vs crowd 0.149. First 100k of 162k characters.
- Karger et al. 2024/2025, ForecastBench. https://arxiv.org/abs/2409.19839. Experts beat the best LLM. Abstract only.
- Sun et al. 2026, SepSeq. https://arxiv.org/pdf/2604.07737. Accuracy falls on long lists; authors' own method. Text extracted.
- Li H. et al. 2025, NumericBench. https://arxiv.org/pdf/2502.11075. Stock-table numeric tasks. Text extracted.
- Ni 2026. https://arxiv.org/html/2608.13129. Numeracy; single author, weak. Full text.
- Chen et al. 2022/2023, Program of Thoughts. https://arxiv.org/abs/2211.12588. Code beats chain of thought by about 12%; older models. Abstract only.
- Gao et al. 2022/2023, PAL. https://arxiv.org/abs/2211.10435. Same, older models. Abstract only.
- Li Y. et al. 2025, R&D-Agent(Q). https://arxiv.org/html/2505.15155. Positive, cross-sections, cutoff "nearly" before test. First 100k of 174k characters.
- Datla et al. 2025. https://arxiv.org/pdf/2512.04408. Rules from policy text, human gold set; field similarity 0.36-0.39. Text extracted.
- Guliani et al. 2026, De Jure. https://arxiv.org/abs/2604.02276. LLM-judged, weak. Abstract only.
- Cao et al. 2024. https://arxiv.org/html/2404.06162v3. Number hallucination 4-6.5%, context mismatch largest; older models. Full text.
- Zhang M. et al. 2025, FAITH. https://arxiv.org/html/2508.05201. 10-K masked numbers, 89-96%. Full text.
- Anthropic 2026, Models overview. https://platform.claude.com/docs/en/about-claude/models/overview. Cutoffs, context window, retirement dates; primary. Full page.
- Not used: Ntale 2026, arXiv 2607.15414, https://arxiv.org/pdf/2607.15414. Opened, but its tables are labelled simulated or illustrative, so it is not evidence.

### Fine-tuning and cost

- Anthropic 2026, pricing and API docs. https://platform.claude.com/docs/en/about-claude/pricing, https://platform.claude.com/docs/en/models/overview, https://platform.claude.com/docs/en/about-claude/model-deprecations, https://platform.claude.com/docs/en/api/rate-limits, https://platform.claude.com/docs/en/build-with-claude/batch-processing, https://platform.claude.com/docs/en/build-with-claude/token-counting, https://platform.claude.com/docs/en/build-with-claude/thinking, https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers, https://platform.claude.com/llms.txt. Prices, limits, no fine-tune page in index; primary. Full pages.
- Anthropic 2026, prompt caching. https://platform.claude.com/docs/en/build-with-claude/prompt-caching. TTL and prefix rules; primary. Via summariser, first 140k characters.
- Anthropic 2026, plan and terms pages. https://claude.com/pricing, https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-and-team-plans, https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan, https://support.claude.com/en/articles/11145838-using-claude-code-with-your-max-plan, https://support.claude.com/en/articles/11049741-what-is-the-max-plan, https://www.anthropic.com/legal/consumer-terms. Plan limits not published in tokens; primary. Via summariser.
- Anthropic 2026, Claude Code docs. https://code.claude.com/docs/en/costs, https://code.claude.com/docs/en/cli-reference. Cost reference, flags; primary. Full pages.
- AWS 2026, Bedrock. https://docs.aws.amazon.com/bedrock/latest/userguide/custom-model-fine-tuning.html, https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle.html, https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle-legacy.html, https://docs.aws.amazon.com/bedrock/latest/userguide/fine-tuning-openai-apis.md. Claude 3 Haiku past end of life; table is stale. Full pages.
- AWS blogs, undated. https://aws.amazon.com/blogs/machine-learning/fine-tune-anthropics-claude-3-haiku-in-amazon-bedrock-to-boost-model-accuracy-and-quality/, https://aws.amazon.com/blogs/machine-learning/best-practices-and-lessons-for-fine-tuning-anthropics-claude-3-haiku-on-amazon-bedrock/. Limits; "new knowledge" rated low likelihood. Via summariser, second in part.
- OpenAI 2026. https://developers.openai.com/api/docs/guides/model-optimization, https://developers.openai.com/api/docs/pricing, https://developers.openai.com/api/docs/deprecations. Platform winding down. Via summariser.
- Google 2026. https://cloud.google.com/vertex-ai/generative-ai/pricing, https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-supervised-tuning. Tuning open, prices. Full page; via summariser.
- Mistral 2026. https://docs.mistral.ai/capabilities/finetuning/finetuning_overview. Deprecated. Via summariser.
- Together 2026. https://www.together.ai/pricing, https://docs.together.ai/docs/fine-tuning-models, https://docs.together.ai/docs/fine-tuning-quickstart. LoRA prices; LoRA column reading [assumed]. Via summariser.
- Fireworks 2026. https://fireworks.ai/pricing, https://docs.fireworks.ai/fine-tuning/fine-tuning-models. Prices; pricing page and docs conflict on serving. Via summariser.
- Tinker 2026. https://thinkingmachines.ai/tinker/, https://thinkingmachines.ai/tinker/pricing/. Per-token sampling of adapters. Via summariser.
- OpenRouter 2026. https://openrouter.ai/api/v1/models, https://openrouter.ai/pricing, https://openrouter.ai/docs/api/reference/limits, https://openrouter.ai/docs/faq, https://openrouter.ai/docs/guides/best-practices/prompt-caching, https://openrouter.ai/docs/guides/features/batch-api.md. Live prices vary by endpoint. Full JSON; docs via summariser.
- DeepSeek 2026. https://api-docs.deepseek.com/quick_start/pricing, https://api-docs.deepseek.com/guides/kv_cache. Prices, cache. Via summariser.
- Hugging Face API 2026. https://huggingface.co/api/models/Qwen/Qwen3.8-27B, https://huggingface.co/api/models/deepseek-ai/DeepSeek-V4.1-Flash and siblings. Licences and parameters; tokenizers measured. Full JSON.
- Unsloth 2026. https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements. VRAM by model size. Via summariser.
- startdebugging.net 2026. https://startdebugging.net/2026/06/claude-agent-sdk-separate-credit-pool-june-15/. Third-party claim that Anthropic's own article contradicts. Opened, not used as fact.
- Wang et al. 2025, FinLoRA. https://arxiv.org/html/2505.19819v1. LoRA helps text tasks, no market test; abstract's "36%" does not reconcile. Full text.
- Yang et al. 2023, FinGPT. https://arxiv.org/abs/2306.06031. Framework. Abstract only.
- Guo, Hauptmann 2024. https://arxiv.org/html/2407.18103v2. Newsflow to returns, Sharpe 1.49 vs 0.92; gross, news not prices. Full text.
- Gao, Jiang, Yan 2026. https://arxiv.org/abs/2604.02921, PDF https://arxiv.org/pdf/2604.02921. Best fine-tune design; tiny signal. Extracted text.
- Valeyre, Aboura 2024/25. https://arxiv.org/html/2412.09394v2. Walk-forward; reversal rule matches; costs kill it. Full text.
- Fakhari, Safayani 2026, PRICE. https://arxiv.org/html/2609.05235. Closest BTC fine-tune; one short window, no naive. Full text.
- Makri et al. 2025. https://arxiv.org/html/2503.23190v1. ETH daily, no naive, weak. Full text.
- Simonyan 2024, BreakGPT. https://arxiv.org/html/2411.06076v1. Loses to its baseline. Full text.
- Tsaryk et al. 2025, CryptexLLM. https://datasys.cs.iit.edu/publications/2025_eScience-cryptexllm-poster.pdf. Poster, numbers only in figures. Full text.
- agarkovv 2024/2025, CryptoTrader-LM. https://huggingface.co/agarkovv/CryptoTrader-LM/blob/main/README.md. Sharpe 0.94 on validation, fees excluded; self-reported. Full page.
- Mai 2024, StockGPT. https://arxiv.org/html/2404.05101v3. Tokenised returns from scratch, Sharpe 6.5 gross, value-weight 1.0. Full text.
- Nguyen et al. 2024. https://arxiv.org/html/2404.11792v2. FinanceBench 41 questions: iteration beats fine-tuning. Full text.
- Zhang et al. 2024. https://arxiv.org/pdf/2402.01722. Fine-tune plus RAG, plots only; weak. Extracted text.
- DEV post 2026. https://dev.to/manoir_yantai_f22f01340f0/-running-llms-on-cpu-in-2026-real-benchmarks-from-a-4-core-xeon-server-a-4-1438. 4-core Xeon speeds; single author, no logs. Full page.
- It's FOSS 2026. https://itsfoss.com/testing-local-llms-without-gpu. Laptop speeds. Full page.
- OpenBenchmarking 2025. https://mail.openbenchmarking.org/result/2508016-MAKS-EPYC91345&grs&export=html. EPYC, 32 cores, not 4. Full page.
- Radxa forum 2025/2026. https://forum.radxa.com/t/llama-cpp-benchmarks/27813/17. ARM board. Full page.
- Computing for Geeks 2026. https://computingforgeeks.com/fine-tune-llm-unsloth-qlora/. One small LoRA run. Full page.
- simplified.guide. https://www.simplified.guide/_export/xhtml/llama-cpp/benchmark-run. Opened, not used. Undated.

### Time-series foundation models

- Rahimikia, Ni, Wang 2025. https://arxiv.org/abs/2511.18578. Largest finance test, costs, causal refits; strong, stocks only. Full text.
- Shi et al. 2025, Kronos. https://arxiv.org/abs/2508.02739. Authors' own, no naive baseline. Full text of v1.
- Fu, Hirano, Imajo 2024. https://arxiv.org/abs/2412.09880, code https://github.com/pfnet-research/timesfm_fin. Cost-free mock trading, crypto row; moderate. Full text.
- Noguer i Alonso, Pereira Franklin 2026. https://arxiv.org/abs/2606.27100. Honest about the random walk, tiny sample. Results sections.
- Lee et al. 2026, FinVerse. https://arxiv.org/abs/2608.03259. Broad, no costs, LG authors. Selected sections and tables.
- LG AI Research 2026, EXAONE Finance. https://arxiv.org/abs/2609.04239. Vendor on own benchmark; synthetic-only training. Selected sections.
- Zhu et al. 2025, FinCast. https://arxiv.org/abs/2508.19609, code https://github.com/vincent05r/FinCast-fts. No naive baseline found. Selected sections; repo metadata.
- Yu et al. 2026. https://arxiv.org/abs/2607.26792. Independent Kronos comparison, 12 stocks, quantile loss. Selected sections.
- Marconi 2025. https://arxiv.org/abs/2507.07296. TTM and Chronos on non-return tasks; report-style. Selected sections.
- Brini 2026. https://arxiv.org/abs/2607.05291, code https://github.com/Alessiobrini/tsfm-rv. Strong on realised volatility, no crypto. Main text.
- Goel et al. 2025. https://arxiv.org/abs/2505.11163. Fine-tuned TimesFM on realised volatility; moderate. Selected sections.
- Goel et al. 2024. https://arxiv.org/abs/2410.11773. VaR on stocks; moderate. Selected sections.
- Zhu, Cai 2026. https://arxiv.org/abs/2609.04917. Survey; no persistent net alpha established. TSFM sections.
- Zeng et al. 2023. https://arxiv.org/abs/2205.13504. Repeat beats Transformers on Exchange-Rate by 31-45% (the "45%" is the shortest horizon); classic. Table 2 checked.
- Soni et al. 2026. https://arxiv.org/abs/2605.24381. Latency and MASE; Google authors, so vendor-adjacent. Selected sections.
- Wang, Zhang 2026. https://arxiv.org/abs/2601.06371. Monthly commodities only. Abstract and intro.
- Ansari et al. 2025, Chronos-2. https://arxiv.org/abs/2510.15821. Vendor benchmarks. Selected sections.
- Shchur et al. 2025, fev-bench. https://arxiv.org/abs/2509.26468. No finance by text search. Grep and intro.
- Liu et al. 2025, Moirai 2.0. https://arxiv.org/abs/2511.11698. Abstract and intro.
- Auer et al. 2025, TiRex. https://arxiv.org/abs/2505.23719. Selected.
- Graf et al. 2025, FlowState. https://arxiv.org/abs/2508.05287. Abstract and selected.
- Fu et al. 2026, Reverso. https://arxiv.org/abs/2602.17634. Small models. Abstract and intro.
- Kawawa-Beaudan et al. 2026, TradeFM. https://arxiv.org/abs/2602.23784. Needs order flow, so does not apply. Abstract and selected.
- Li et al. 2024, MarS. https://arxiv.org/abs/2409.07486. Order-level simulator, does not apply. Abstract and selected.
- Wheeler, Varner 2024, MarketGPT. https://arxiv.org/abs/2411.16585. Order messages, does not apply. Abstract and selected.
- Garza et al. 2023, TimeGPT-1. https://arxiv.org/abs/2310.03589. Vendor. Selected.
- Baron, Karpinski 2025. https://arxiv.org/abs/2501.10216. Secondary account of the Nixtla and Chronos dispute. Abstract and passage.
- Kronos repo and issues 2025-2026. https://github.com/shiyu-coder/Kronos, https://github.com/shiyu-coder/Kronos/issues. Code, leak, unreviewed community tests. Listed files; issue bodies, some truncated.
- Kronos-demo 2025-2026. https://github.com/shiyu-coder/Kronos-demo. Primary data for the own grading. Code and history.
- moscowmule2240 2026. https://gist.github.com/moscowmule2240/1bb5bf350ad58e42199ac350f8768672. Community, useful, wrong that the demo runs Kronos-base. Full text.
- Meyer 2026, repost. https://1023jack.com/market/week-three-foundation-model-vs-brownian-motion-kronos-on-five-minute-btc-2/. 497 paired BTC 5m trades; secondary, code private. Via summariser.
- Kinlay 2026. https://jonathankinlay.com/2026/02/time-series-foundation-models-for-financial-markets-kronos-and-the-rise-of-pre-trained-market-models/. Commentary with errors, not evidence. Via summariser.
- Nixtla experiment. https://github.com/Nixtla/nixtla/tree/main/experiments/amazon-chronos. Vendor against vendor; table unreadable. Via summariser, undated.
- Model pages 2024-2026. https://github.com/google-research/timesfm, https://huggingface.co/google/timesfm-3.0-pytorch, https://github.com/amazon-science/chronos-forecasting, https://aws.amazon.com/blogs/machine-learning/fast-and-accurate-zero-shot-forecasting-with-chronos-bolt-and-autogluon/, https://huggingface.co/Salesforce/moirai-2.0-R-small, https://github.com/time-series-foundation-models/lag-llama, https://github.com/NX-AI/tirex, https://github.com/DataDog/toto, https://huggingface.co/ibm-granite/granite-timeseries-flowstate-r1, https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2, https://huggingface.co/NeoQuasar/Kronos-mini. Vendor facts. Via summariser or API metadata.
- Nixtla plans 2026. https://www.nixtla.io/docs/introduction/timegpt_subscription_plans. Enterprise plans, no usable price. Via summariser.

### Classical ML, statistics and TA on BTC

- Hudson, Urquhart 2021. https://centaur.reading.ac.uk/85715/8/Hudson-Urquhart2019_Article_TechnicalTradingAndCryptocurre.pdf. Strong against zero, weak against buy and hold; annual figures look mis-scaled. Full text.
- Corbet et al. 2019. https://doras.dcu.ie/25053/1/The_effectiveness_of_technical_trading_rules_in_cryptocurrency_markets%5B1%5D.pdf. Minute data, no costs, no snooping control; weak. Full preprint.
- Wei et al. 2024. https://eprints.gla.ac.uk/302711/1/302711.pdf. Strong design, little survives. Full text.
- Liu, Tsyvinski 2018/2021. https://www.nber.org/system/files/working_papers/w24877/w24877.pdf. In-sample momentum to 2018. NBER version.
- Liu, Tsyvinski, Wu 2019/2022. https://www.nber.org/system/files/working_papers/w25882/w25882.pdf. Cross-section factors, not BTC alone. NBER version, in part.
- Jaquart et al. 2021. https://publikationen.bibliothek.kit.edu/1000150665/149388567. Good benchmark, one test. Full text.
- Jaquart dissertation 2022. https://publikationen.bibliothek.kit.edu/1000153546/149798497. Cross-section, net of 15 bps. Relevant chapter.
- Akyildirim et al. 2021. https://repository.bilkent.edu.tr/bitstream/11693/77044/1/Prediction_of_cryptocurrency_returns_using_machine_learning.pdf. Chronological, no costs. Full text.
- Bysik, Slepaczuk 2026. https://arxiv.org/abs/2606.00060, PDF https://arxiv.org/pdf/2606.00060. Best hourly BTC benchmark; preprint. Full text.
- Baquero 2026. https://arxiv.org/html/2606.00071. Narrative survey of 23 studies. Full text.
- Gradzki et al. 2025. https://link.springer.com/article/10.1186/s40854-025-00866-w. Positive, 5 quarters, no correction. Web text, tables missing.
- Islas Anguiano, Garcia-Medina 2025. https://arxiv.org/pdf/2511.00665. One test year; weak. Full preprint.
- Baumann et al. 2024. https://arxiv.org/pdf/2407.17930. No robust accuracy above 50%. In part.
- Kehinde et al. 2025, Helformer. https://ira.lib.polyu.edu.hk/bitstream/10397/112415/1/s40537-025-01135-4.pdf. Non-credible price metrics; code not audited. In part.
- Kapoor, Narayanan 2023. https://pmc.ncbi.nlm.nih.gov/articles/PMC10499856/, https://arxiv.org/pdf/2207.07048. Leakage across 17 fields; strong. In part.
- Hewamalage et al. 2023. https://arxiv.org/pdf/2203.10716. Forecast evaluation; strong tutorial. In part.
- Nikolopoulos 2026. https://arxiv.org/pdf/2604.15531. Falsify a workflow on null paths; preprint. First pages.
- Molnar 2026. https://arxiv.org/pdf/2607.26188. Careful nulls, post hoc, live window; unreviewed. In part.
- Koki et al. 2022. https://arxiv.org/pdf/2011.03741. 30-day OOS; weak for direction. arXiv v2.
- Ardia et al. 2019. https://libra.unine.ch/bitstreams/68f79eef-f5b3-4954-987e-2ec953b2bf02/download. Regime GARCH for VaR; solid. Full text.
- Lunde, Timmermann 2004. https://econweb.ucsd.edu/~atimmerm/dur-14-2.pdf. Duration dependence; strong, stocks only. Working version, in part.
- Glattfelder et al. 2011. https://arxiv.org/pdf/0809.1040, https://ar5iv.labs.arxiv.org/html/0809.1040. Directional-change laws; foundational, FX. In part.
- Petrov, Golub, Olsen 2018/2019. https://smallake.kr/wp-content/uploads/2019/02/SSRN-id3243797.pdf. BTC weekly volatility seasonality; descriptive. Third-party mirror, in part.
- Petrov, Golub, Olsen 2019, JRFM. https://doi.org/10.3390/jrfm12020054. Same topic. Abstract only.
- Houweling 2025. https://arxiv.org/pdf/2511.14408. DC share 0.62 at 1 s; single author. In part.
- Wheatley et al. 2019. https://arxiv.org/pdf/1803.05663. LPPLS on hindsight windows. arXiv v1, in part.
- Gerlach et al. 2019. https://arxiv.org/pdf/1804.06261. Mock forecasts at known peaks. In part.
- Shu, Zhu 2020. https://arxiv.org/pdf/1905.09647. One window, no false-alarm rate. In part.
- Filimonov et al. 2017. https://arxiv.org/pdf/1602.08258. tc unstable by the authors' account. Abstract section.
- Marc 2020. https://www.imperial.ac.uk/media/imperial-college/faculty-of-natural-sciences/department-of-mathematics/math-finance/marc_jeremy_01795865.pdf. In-sample tuning; weak. In part.
- Caporale, Plastun 2019. https://bura.brunel.ac.uk/bitstream/2438/17208/3/FullText.pdf. Monday effect, not exploitable beyond random. In part.
- Kinateder, Papavassiliou 2021. https://researchrepository.ucd.ie/server/api/core/bitstreams/3fe12e0f-f1c4-4226-937e-b7fc034dfcd9/content. Volatility pattern yes, classic return effect no. In part.
- Pessa et al. 2023. https://arxiv.org/pdf/2302.12319. Hierarchical per-coin tails. In part.
- Jensen, Kelly, Pedersen 2021/2023. https://www.nber.org/system/files/working_papers/w28432/w28432.pdf. Shrinkage formula. In part.
- Fu, Zhu, Liu 2025. https://arxiv.org/pdf/2507.22409. HAR R2 0.75-0.78 on another yardstick; preprint. In part.
- Bariviera 2017. https://arxiv.org/pdf/1709.08090. More efficient since 2014, volatility long memory. First page.
- Nadarajah, Chu 2017. https://pure.manchester.ac.uk/ws/files/84322516/bittest.pdf. Inefficiency depends on the test. Abstract section.
- Garnier, Solna 2019. https://arxiv.org/pdf/1809.08403. Time-varying Hurst, not a cycle test. First page.
- Li et al. 2023. https://articlegateway.com/index.php/JAF/article/view/6453. No profitable strategy in 18 months; lower-tier venue. Skimmed.
- Chen, Wang, Yang 2023. https://pubs.sciepub.com/jfe/11/4/2/index.html. Pre-2021 edges fail OOS; lower-tier venue. About 75% of text.
- Jin, Jung, Song 2024. https://www.emerald.com/jdqs/article-pdf/32/1/23/9465019/jdqs-08-2023-0021.pdf. 99 coins, no outperformance. First pages.
- Gatto 2025/2026. https://daru.finance/research-review/lopez-de-prado/labeling-and-cross-validation. Meta-labelling, 0 of 42 clear deflated Sharpe; unreviewed. Page.
- Hudson and Thames. https://hudsonthames.org/does-meta-labeling-add-to-signal-efficacy-triple-barrier-method/. E-mini, two rules; vendor. Page, undated.
- MBPE 2026. https://github.com/maazkashif1/MBPE. Hourly BTC triple barrier, no tradable edge; personal project. README.
- EdgeProof 2026. https://github.com/intikhab49/edgeproof-crypto-trading-backtest. No direction edge, volatility forecast works; small, personal. README.
- QuantConnect thread, undated. https://www.quantconnect.com/forum/discussion/14706/why-meta-labeling-is-not-a-silver-bullet/. Logic argument; forum. Page.
- CXO on Detzel. https://www.cxoadvisory.com/currency-trading/timing-bitcoin-with-smas/. Numbers of the 2018 working paper; secondary. Page.
- Grobys article, about 2019-2020, date not read. https://cointelegraph.com/news/is-technical-trading-in-cryptocurrency-markets-profitable. Author summary; excludes BTC. Page.
- Detzel et al. 2021. https://doi.org/10.1111/fima.12310. Price/MA ratios forecast daily returns; numbers unverified. Abstract only.
- Gerritsen et al. 2020. https://ideas.repec.org/a/eee/finlet/v34y2020ics1544612319303770.html. Range breakout beats buy and hold; costs unclear. Abstract only.
- Anghel 2021. https://ideas.repec.org/a/eee/finlet/v39y2021ics1544612320304414.html. Rarely significant after snooping; details unverified. Abstract only.
- Deprez, Frommel 2024. https://ideas.repec.org/a/eee/reveco/v93y2024ipbp858-874.html. 75,360 rules, OOS portfolios can beat buy and hold on risk-return; main positive counterweight, numbers unverified. Abstract only.
- Grobys et al. 2020. https://doi.org/10.1016/j.frl.2019.101396. 8.76% a year excluding Bitcoin; not BTC evidence. Abstract only.
- Gradojevic et al. 2023. https://ideas.repec.org/a/eee/intfor/v39y2023i1p1-17.html. Hourly weakly efficient; good journal. Abstract only.
- Urquhart 2016. https://ideas.repec.org/a/eee/ecolet/v148y2016icp80-82.html. Moving toward efficiency; dated. Abstract only.
- Tran, Leirvik 2020. https://doi.org/10.1016/j.frl.2019.101382. Time-varying efficiency. Abstract only.
- Arain, Snudden 2025. https://doi.org/10.1002/for.70077. Directional gains rarely become profit. Abstract only.
- Bergsli et al. 2022. https://doi.org/10.1016/j.ribaf.2021.101540. HAR beats GARCH; solid. Abstract only.
- Joubert 2022; Meyer et al. 2023; Thumm et al. 2022. https://doi.org/10.3905/jfds.2022.1.098, https://doi.org/10.3905/jfds.2023.1.119, https://doi.org/10.3905/jfds.2022.1.114. Meta-labelling framework, one group, controlled experiments. Abstracts only.
- Giudici, Abu-Hashish 2019. https://ideas.repec.org/a/eee/finlet/v28y2019icp309-318.html. Network VAR, not an HMM as sometimes cited. Abstract only.
- Giudici, Abu-Hashish 2020. https://doi.org/10.1002/qre.2673. Bull, stable, bear HMM; descriptive. Abstract only.
- Ma et al. 2020. https://doi.org/10.1002/for.2691. Markov-switching MIDAS improves RV. Abstract only.
- Catania et al. 2019. https://doi.org/10.1016/j.ijforecast.2018.09.005. Model averaging, some direction gains. Abstract only.
- Regime-aware framework 2026. https://doi.org/10.1007/s10614-026-11338-3. Price metrics only. Abstract only.
- Zakamulin 2023. https://doi.org/10.1080/00036846.2022.2089344. Duration dependence, US stocks. Abstract only.
- Maheu, McCurdy 2000. https://doi.org/10.1080/07350015.2000.10524851. Duration-dependent switching. Abstract only.
- Tsang et al. 2017. https://doi.org/10.1080/14697688.2016.1164887. DC on UK equities. Abstract only.
- Shu et al. 2021. https://doi.org/10.3390/stats4040056. After-the-fact classification. Abstract only.
- Camacho, da Silva. https://doi.org/10.13133/2037-3643/18744. Wavelets 2011-2021, no dominant period in abstract; date varies by source. Abstract only.
- Kristoufek 2015. https://doi.org/10.1371/journal.pone.0123923. Wavelet coherence, not a cycle test. Abstract only.
- Halving MS-GARCH 2023. https://doi.org/10.3390/math11030698. Takes the cycle as given. Abstract only.
- JRFM 2025. https://doi.org/10.3390/jrfm18050242. Returns and volatility around halvings falling. Abstract only.

### Elliott Wave and Fibonacci

- Akbarzadeh, Soleimani 2023. https://ijnaa.semnan.ac.ir/article_6725_cf4ef4731ce12549040d98f506ff302d.pdf. 93.94% is a smoothing artefact; teaching example. Full text, table images.
- Manjunath, Sekhar 2022. http://www.jatit.org/volumes/Vol100No18/10Vol100No18.pdf. 98.67%, no described split; very weak. Full text.
- Yang et al. 2023. https://doi.org/10.3390/math11061466. Class agreement, not a forecast. Full text, Wayback.
- Naga Swetha, Arya 2026. https://doi.org/10.1109/access.2026.3693604. Identification only. Full text, reader.
- Kotyrba et al. 2013. https://www.scs-europe.net/dlib/2013/ecms13papers/is_ECMS2013_0050.pdf. Hand templates, no baseline. Full text.
- Volna et al. 2013. https://doi.org/10.1016/j.camwa.2013.01.012. Not rated. Abstract only, Wayback.
- Jarusek et al. 2022. https://doi.org/10.1016/j.neunet.2021.10.024. Not rated. Abstract only.
- Atsalakis et al. 2011. https://doi.org/10.1016/j.eswa.2011.01.068. Not rated; red flags. Abstract, highlights, reader.
- D'Angelo, Grimaldi 2017. https://doi.org/10.5539/ibr.v10n6p1. Hindsight chart reading, no ML, no test. Full text.
- Vantuch et al. 2018. https://doi.org/10.3233/IDT-170319. Above 70%, not rated. Abstract only.
- Dos Santos et al. 2023. https://doi.org/10.1109/CSCI62032.2023.00060, https://repositorio.unesp.br/entities/publication/a0d8bdbb-cb3f-4008-ae04-eb598d0f7508. Error reduced 4 times against rule-bound guessing; possible positive, unseen metric. Abstract only, reader.
- Dos Santos et al. 2024. https://doi.org/10.1007/978-3-031-56599-1_1. No number. Preview, reader.
- Mahmoudi et al. 2026. https://doi.org/10.61838/jafci.441. Near-tautology. Results read.
- Joseph 2025. https://monami.hs-mittweida.de/files/16331/Doniya_Joseph_Master_Thesis.pdf. 12 BTC trades, best of a grid. EW section.
- Zhao, Xu 2024; Ben Miloud, Kim 2024; Zhou et al. 2022; Tabar et al. 2020. https://doi.org/10.1145/3672919.3673003, https://doi.org/10.1109/idsta62194.2024.10747018, https://doi.org/10.1109/acait56212.2022.10137970, https://doi.org/10.4018/ijban.2021010101. Not rated. Abstracts only.
- Attariq, Briantama 2025; Ardiansyah et al. 2025. https://openalex.org/works?search=PENERAPAN%20ELLIOTT%20WAVE%20DAN%20FIBONACCI%20RETRACEMENT%20BITCOIN, https://doi.org/10.37641/jimkes.v13i1.3044. Descriptive. Abstracts only.
- Batchelor, Ramyar 2006. https://openaccess.city.ac.uk/id/eprint/16276/. Best early test, low cell power; printed table does not match its count on one stream's recount. Full text.
- Prechter about 2006. https://web.archive.org/web/2020/http://socionomics.org/pdf/EW_Fibo_Statistics.pdf. Key objection, no test of its own. Full text, Wayback.
- Kempen 2016. http://www.ftaa.org.hk/Files/2016.pdf. Base rates, survivorship. Full text, mirror.
- Kempen (Brenner), Maier-Paape 2016. https://arxiv.org/abs/1605.03559. Log-normal, scale and market invariance on stocks. Full text.
- Tsinaslanidis et al. 2022. http://hdl.handle.net/10251/195083, https://doi.org/10.1016/j.eswa.2021.115893. Strongest level test; negative. Accepted manuscript.
- Westland 2024. https://doi.org/10.1038/s41598-024-55011-x, https://www.nature.com/articles/s41598-024-55011-x.pdf. No wave counts, no Fibonacci test, no null. Full text.
- van Ginneken 2013. http://arno.uvt.nl/show.cgi?fid=131569. Algorithmic waves, null, costs; not significant overall, hourly lead. Full text.
- Dehay 2026. https://github.com/baptiste-dehay/fractal-financial-markets-elliott-wave-validation. Best governance; apparent detector bug, unconfirmed by the author. README, protocol, code, manuscript sections.
- Sang 2021. https://doi.org/10.18686/fm.v6i1.3266. Hand-picked, no null. Full text.
- Bhattacharya, Kumar 2006. http://www.aeconf.com/Articles/May2006/aef070109.pdf. Cherry-picked. Full text.
- Gurrib et al. 2022. https://doi.org/10.1186/s40854-021-00311-8. No BTC, no costs. Full text, reader.
- Gurrib 2022. https://doi.org/10.32479/ijeep.11015. Abstract only.
- Khattak et al. 2024. https://doi.org/10.1186/s40537-024-00908-7. Leaky split, almost no effect. Full text, reader.
- Khattak et al. 2026. https://doi.org/10.1186/s40537-026-01372-1. Abstract only.
- Presto Labs. https://www.prestolabs.io/research/technical-analysis-in-statistical-arbitrage-i-fibonacci-retracement. Momentum on a range, no costs; industry note. Full text, undated.
- Thosen 2026. https://publiscologne.th-koeln.de/files/2896/BA_Thoesen_Tim.pdf. Descriptive BA thesis. Conclusions.
- Ishizaka 2023; Daffa et al. 2026; Hamdi, Younis 2026; Tarassov, Houlie 2022. http://hdl.handle.net/11449/242582, https://doi.org/10.59535/efe.v4i1.685, https://doi.org/10.5281/zenodo.23728788, https://doi.org/10.1371/journal.pone.0274165. Weak. Abstracts only.
- Osler 2000. https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf. Ex-ante published levels; modest real effect. Full text.
- Osler 2003. https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf. Order clustering at round numbers. Full text.
- Kavajecz, Odders-White 2004. https://ideas.repec.org/a/oup/rfinst/v17y2004i4p1043-1071.html. S/R at depth peaks. Abstract only, reader.
- Garzarelli et al. 2014. https://arxiv.org/abs/1110.5197. Bounce memory at S/R. Full text.
- Chung, Bellotti 2021. https://arxiv.org/abs/2101.07410. S/R reversal decays. Full text.
- Urquhart 2017. https://ideas.repec.org/a/eee/ecolet/v159y2017icp145-148.html. BTC round numbers, no return pattern. Abstract only, reader.
- Mbanga 2019; Baig et al. 2020; Financial Innovation 2022; FRL 2022; Griffin, Shams 2020; Schnaubelt et al. 2019. https://doi.org/10.1080/13504851.2018.1497844, https://doi.org/10.24135/afl.v9i0.200, https://doi.org/10.1186/s40854-021-00307-4, https://doi.org/10.1016/j.frl.2022.102811, https://doi.org/10.1111/jofi.12903, https://doi.org/10.3390/jrfm12010025. Crypto round-number and order-book work. Abstracts only.
- Tsinaslanidis 2024. https://doi.org/10.1007/978-3-031-49105-4_62. BTC, ETH, BNB support bounces; not Fibonacci. Preview, reader.
- Zhumalieva et al. 2026. https://doi.org/10.1109/icecco67619.2026.11488775. Results do not validate wave counting, by the authors' words. Abstract only.
- CXO Advisory, last updated 2012. https://www.cxoadvisory.com/gurus/, https://www.cxoadvisory.com/gurus/robert-prechter/, https://www.cxoadvisory.com/individual-gurus/robert-prechter/. Prechter 20.8% on 24 forecasts, low confidence; grades a person. Page, via summariser.
- Wikipedia, read 2026. https://en.wikipedia.org/wiki/Robert_Prechter, https://en.wikipedia.org/wiki/Elliott_wave_principle, https://en.wikipedia.org/wiki/The_Elliott_Wave_Theorist, https://en.wikipedia.org/wiki/Fibonacci_retracement. Secondary. Pages.
- Finnish pop study 2018. https://doi.org/10.1017/s0261143018000065. Socionomics, not wave structure. Abstract only.

### Structured and hybrid engines

- Stolcke 1995. https://aclanthology.org/J95-2002.pdf. Prefix probabilities; foundational. Full text.
- Qi, Jia, Zhu 2018. https://proceedings.mlr.press/v80/qi18a.html. Grammar helps future prediction, activities not markets. Full text.
- Wang, Portnoy, Pollak 2007. https://doi.org/10.1109/icassp.2007.367069. SCFG on S&P volatility; weak, unreplicated. Abstract only.
- Tayal 2009. https://uwspace.uwaterloo.ca/handle/10012/4463. HHMM on zig-zags, filter far below smoother; one month. Full text.
- Adams, MacKay 2007. https://arxiv.org/abs/0710.3742. Online changepoints; foundational. Full text.
- Fearnhead, Liu 2007. https://eprints.lancs.ac.uk/id/eprint/745. Complexity. Abstract only.
- Knoblauch et al. 2018. https://papers.neurips.cc/paper_files/paper/2018/file/a3f390d88e4c41f2747bfa2f1b5f87db-Paper.pdf. False discovery under outliers; strong. Full text.
- Altamirano et al. 2023. https://arxiv.org/abs/2302.04759. Robust changepoints. Abstract only.
- Doucet et al. 2000. https://arxiv.org/abs/1301.3853. Rao-Blackwellised filters. Abstract only.
- Snyder et al. 2008. https://www.stat.berkeley.edu/~bickel/Snyder%20et%20al%202008.pdf. Weight collapse; strong. Full text.
- Reid 1979. https://doi.org/10.1109/tac.1979.1102177. MHT with false targets; foundational. Abstract only.
- Kim et al. 2015. https://www.cv-foundation.org/openaccess/content_iccv_2015/papers/Kim_Multiple_Hypothesis_Tracking_ICCV_2015_paper.pdf. MHT depends on detector quality. Full text.
- Nguyen, O'Connor 2015. https://aclanthology.org/D15-1182.pdf. HMM underconfident; strong in NLP. Full text.
- Kuleshov, Liang 2015. https://papers.nips.cc/paper/5658-calibrated-structured-prediction.pdf. Event recalibration. In part.
- Dacco, Satchell 1999. https://doi.org/10.1002/(SICI)1099-131X(199901)18:1<1::AID-FOR685>3.0.CO;2-B. True regime model can lose to a random walk. Abstract only.
- Gelman, Loken 2013. https://sites.stat.columbia.edu/gelman/research/unpublished/p_hacking.pdf. Forking paths. In part.
- Lo, Mamaysky, Wang 2000. https://www.nber.org/system/files/working_papers/w7613/w7613.pdf. Pattern testing template; patterns on GBM; strong. NBER version.
- Zapranis, Tsinaslanidis 2009. https://repository.canterbury.ac.uk/item/871wx/an-examination-of-the-head-and-shoulders-technical-pattern-a-support-of-the-technical-analysis-s-subjective-nature. Pattern found on Brownian paths. Abstract only.
- Prechter, Sardo-Infirri, Prechter Jr., raw data 2024. https://github.com/elliottp6/rvr. 437 one-year chunks, 8 markets; paper unpublished. Full data.
- EWAVES pages 2026. https://ewaves.com/faq/, https://ewaves.com/ewaves-live/, https://www.ewaves.com/, https://ewaves.com/news/, https://ewaves.com/elliott-waves/, https://ewaves.com/2026/06/26/elliott-prechter-on-markus-koch-wall-street-elliott-waves-ai-and-the-psychology-of-markets/. Vendor claims. Raw HTML or summariser.
- von Thienen 2026. https://research.marketzeitgeist.com/p/elliott-prechter-elliott-waves-interview-cycles-lars-von-thienen. Interview, no methods. Via summariser.
- Vendor and script pages 2026. https://www.elwave.com/, https://www.elwave.com/ELWAVEPro/, https://wavebasis.com/, https://wavebasis.com/docs/reference-guide/automatic-wave-counts/, http://app.wavebasis.com/pricing, https://docs.motivewave.com/video-tutorials/elliott-wave, https://docs.motivewave.com/llms-full.txt, https://www.esignal.com/products/elite, https://trendspider.com/trading-tools-store/indicators/6a29c8-elliott-wave-auto-counter/, https://tr.tradingview.com/script/U76W8mpk-Self-Validating-Elliott-Wave-Engine/. Claims, no numbers. Mostly via summariser.
- WaveLogic 2026. https://note.com/wavelogic_app/n/n81a8e9a26e37?hl=en. Names the parser idea, nothing built. Via summariser.
- Bailey 2014. https://mathinvestor.org/2014/03/a-sobering-analysis-of-financial-gurus-market-forecasts/. CXO data resembles chance. Via summariser.
- Open-source repos, read 2026. https://github.com/topics/elliott-wave, https://github.com/drstevendev/ElliottWaveAnalyzer, https://github.com/Raj1984/ElliottWaveAnalyzer, https://github.com/DrEdwardPCB/python-taew, https://github.com/tradecharts/tradecharts-nemotron, https://github.com/SmarterSystems/ElliottWavesEngine, https://github.com/nkieu-config/elliott-wave-engine, https://github.com/philippe-ostiguy/PyBacktesting. None a usable engine; nemotron is a good validator-gate reference. Via summariser or API.
- omaralasil 2026. https://github.com/omaralasil/elliott-wave3-estudio. W3 walk-forward, look-ahead cost measured; best honest example. Via summariser.
- Tang et al. 2025, AlphaAgent. https://arxiv.org/html/2502.16789. Uncorrected tests. Full text.
- Wang et al. 2023/2025, Alpha-GPT. https://arxiv.org/abs/2308.00016. Cannot judge. Abstract only.
- Agentic Empirical Asset Pricing 2026, SEADS. https://arxiv.org/html/2609.00731. Best evaluation protocol seen. First 100k of 160k characters.
- Agentic Trading survey 2026. https://arxiv.org/html/2605.19337v1. 2 of 19 with time-consistent splits. First 100k of 337k characters.
- Novy-Marx, Velikov 2025. https://www.nber.org/papers/w33363. Industrialised story-telling. Abstract page.
- Chen, Lopez-Lira, Zimmermann, revised 2025. https://arxiv.org/abs/2212.10317. Mined about equals peer reviewed, half persists. Abstract only.
- Zhong et al. 2025, ImpossibleBench. https://arxiv.org/pdf/2510.20270. Agents edit tests. In part.
- Niculescu-Mizil, Caruana 2005. https://www.cs.cornell.edu/~alexn/papers/calibration.icml05.crc.rev3.pdf. Platt beats isotonic below 200-1,000 cases. In part.
- Collins et al. 2016. https://pubmed.ncbi.nlm.nih.gov/26553135/. 100 events minimum, clinical. Abstract only.
- Gupta, Ramdas 2023. https://arxiv.org/abs/2305.00070. Online Platt. Abstract only.
- Gibbs, Candes 2021. https://arxiv.org/pdf/2106.00170. Adaptive conformal, demonstrated on stock volatility. In part.
- METR 2025. https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/. 19% slower with AI; dated by METR itself. Via summariser.
- METR 2026, transcripts note. https://metr.org/notes/2026-02-17-exploratory-transcript-analysis-for-estimating-time-savings-from-coding-agents/. Soft upper bound on time savings. Via summariser.

### Honesty machinery

- Bailey et al. 2014. https://www.ams.org/notices/201405/rnoti-p458.pdf. MinBTL; strong on the math, assumes independent trials. Full text.
- Bailey et al. 2017. https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf. CSCV, PBO and limits; prints 12,780 for 12,870. Full text of the 2015 version.
- Bailey, Lopez de Prado 2014. https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf. DSR; worked example reproduced. Full text.
- Lopez de Prado, Lewis 2019. https://smallake.kr/wp-content/uploads/2020/04/SSRN-id3167017.pdf. Effective trials by clustering. SSRN copy, in part.
- Li 2026. https://arxiv.org/pdf/2609.29530. Walk-forward as the causal frontier; single author. In part.
- Gort et al. 2022. https://arxiv.org/pdf/2209.05559. PBO on crypto RL; one 8-week test, weak. Full text.
- Wiecki et al. 2016. https://c.mql5.com/forextsd/forum/208/All%20that%20Glitters%20Is%20Not%20Gold%20-%20Comparing%20Backtest%20and%20Out-of-Sample%20Performance%20on%20a%20Large%20Cohort%20o.pdf. 888 algorithms, weak link. Third-party copy.
- Gencay 2026. https://arxiv.org/pdf/2608.27734. Trial ledger, LLM strategies all rejected; single author, equities. In part.
- purgedcv docs 2025/2026. https://eslazarev.github.io/purged-cross-validation/methodology/, https://eslazarev.github.io/purged-cross-validation/api/paths/, https://raw.githubusercontent.com/eslazarev/purged-cross-validation/main/paper/paper.md. Secondary for purge, embargo, CPCV. Opened.
- White 2000. https://www.ssc.wisc.edu/~bhansen/718/White2000.pdf. Reality Check; foundational. Full text.
- Hsu, Kuan. https://c.mql5.com/forextsd/forum/211/Re-Examining%20the%20Profitability%20of%20Technical%20Analysis%20with%20Whitets%20Reality%20Check%20and%20Hansen9s%20SPA%20Tes.pdf. Secondary statement of SPA. Working paper copy, in part, undated.
- Romano, Wolf 2005. https://www.ssc.wisc.edu/~bhansen/718/RomanoWolf2005.pdf. StepM. Abstract and introduction.
- Sullivan, Timmermann, White 1999. https://www.fmg.ac.uk/sites/default/files/2020-11/dp303.pdf. Best rule fails out of sample; strong, Dow only. 1998 working paper.
- Bajgrowicz, Scaillet 2012. https://www.efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2008-Athens/papers/Bajgrowicz.pdf. Disappears after costs. January 2008 version.
- Harvey, Liu, Zhu 2016. https://www.nber.org/system/files/working_papers/w20592/w20592.pdf. t above 3. NBER version.
- Harvey, Liu 2015. https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF. Haircuts, BHY. Full text.
- Gneiting, Raftery 2007. https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf. Proper scores; foundational. Full text.
- Dimitriadis et al. 2021. https://arxiv.org/pdf/2008.03033. CORP. arXiv version.
- Diebold 2015. https://www.sas.upenn.edu/~fdiebold/papers/paper113/Diebold_DM%20Test.pdf. DM and its limits. Full text.
- Giacomini, White 2006. http://fmwww.bc.edu/EC-P/wp572.pdf. Conditional ability test, finite window. Working paper.
- Niculescu-Mizil, Caruana 2005, UAI. https://arxiv.org/abs/1207.1403. Boosting calibration. Abstract only.
- Van Calster et al. 2016. https://lirias.kuleuven.be/retrieve/577522. 100+100 and 200+200 rule, clinical. Author copy.
- Henzi, Ziegel. https://arxiv.org/abs/2103.08402. E-values for score differences. Abstract only, undated.
- Choe, Ramdas. https://arxiv.org/abs/2110.00115. Confidence sequences for forecasters. Abstract only, undated.
- arch docs. https://arch.readthedocs.io/en/latest/bootstrap/generated/arch.bootstrap.optimal_block_length.html. Politis-White length; secondary. Opened, undated.
- Brock, Lakonishok, LeBaron 1992. https://ideas.repec.org/a/bla/jfinan/v47y1992i5p1731-64.html. GARCH nulls; rules later failed out of sample. Abstract only.
- Theiler et al. 1992. https://digital.library.unt.edu/ark:/67531/metadc1094730/m2/1/high_res_d/6026813.pdf. Surrogate data. Scanned preprint, OCR, in part.
- Broadie, Glasserman, Kou 1997. https://www.columbia.edu/~sk75/mfBGK.pdf. Discrete barrier correction. First section.
- Sigman 2006. http://www.columbia.edu/~ks20/FE-Notes/4700-07-Notes-BM.pdf. Exit probabilities; teaching notes. Full text.
- Giller 2024. https://arxiv.org/abs/2412.04263. Crypto pair correlation of order 60%. Abstract only.
- Design effect, Wikipedia, read 2026. https://en.wikipedia.org/wiki/Design_effect. Secondary, cites Kish. Page.

## 15. Not opened, not relied on

Seen only as a search snippet, title or metadata, or blocked. Nothing above rests on them as if read.

- **JEPA:** LeCun 2022 (https://openreview.net/forum?id=BZ5a1r-kVsf, blocked); Mahns et al. full text (https://openreview.net/forum?id=BZfkxSasd3); Fin-JEPA SSRN (https://ssrn.com/abstract=6855118); https://huggingface.co/fin-ai-lab/lejepa-demo-ecoder; Ait-Sahalia et al. 2022 (https://www.nber.org/papers/w30366); CoFinDiff (https://arxiv.org/pdf/2503.04164); MarketGANs (https://arxiv.org/html/2601.17773v1); Takahashi, Mizuno 2024 (https://arxiv.org/html/2410.18897v1); Sousa et al. 2026 (https://arxiv.org/pdf/2604.16182); https://neurips.cc/virtual/2025/132506; Cheng et al. 2021 on GEV (https://arxiv.org/pdf/2102.04591); Riley et al. 2020 (https://www.bmj.com/content/368/bmj.m441).
- **LLM:** CharXiv, ChartQAPro originals; TemporalBench (https://arxiv.org/html/2602.13272v1); ForecastBench October 2025 update; Good Judgment page; AIA Forecaster; PROLEG; TabFaith; Lopez-Lira, Tang (https://arxiv.org/abs/2304.07619); Chen et al. (https://www.aeaweb.org/conference/2026/program/paper/zNrQ4Yn6); https://gigagpu.com/rtx-4090-24gb-fine-tune-throughput/; https://aiwiki.ai/wiki/mistral_forge; https://costbench.com/software/fine-tuning-apis/mistral-ai-fine-tuning/; https://the-agent-report.com/2026/06/meta-muse-spark-llama-abandoned/; https://www.tkmxai.it.com/claude-api-in-2026-6; https://www.phoronix.com/review/amd-epyc-turin-avx512/5; https://www.anthropic.com/news/fine-tune-claude-3-haiku-ga (404); AMD ZenDNN article (timed out).
- **Foundation models:** TempoPFN (https://arxiv.org/abs/2510.25502); X post on "93%" (https://x.com/quantscience_/status/2052418989561618815); https://www.researchsquare.com/article/rs-10306663/v1; Nixtla price page (404, snippet).
- **Classical:** Lopez de Prado 2018 book; Arian et al. 2024 (https://doi.org/10.1016/j.knosys.2024.112477); Guillaume et al. 1997; Demos, Sornette 2017 (truncated abstract, https://doi.org/10.1080/14697688.2016.1231417); Aharon, Qadan 2019; Yaya, Ogbonna 2019; Pacific-Basin 2025 on halvings; Lim 2026; IRFA 2026 on realised volatility; Physica A 2026; IRFA on BITO; JIFMIM 2022; Helformer community post; DS-LPPLS; practitioner posts (FXEmpire, FXStreet, TradingView, Weiss sheet); seen only through Baquero 2026: Yae, Tian 2022, Cakici et al. 2024, Puoti et al. 2024, McNally et al. 2018, Gurgul et al. 2025.
- **Elliott and Fibonacci:** Kotyrba et al. 2012; Volna et al. 2018; Wawer, Chudziak 2026; Jain et al. 2025; Subedi 2026; Natadikarta, Saepudin 2023; Vantuch conference paper; Merrill 1977; Goel 2006; Shanaev, Gibson 2022 (https://doi.org/10.2139/ssrn.4212430); Mahadzva 2026 (https://doi.org/10.2139/ssrn.7430898); Lu 2026 (https://doi.org/10.2139/ssrn.6829821); Bhusal 2025; Han 2024; Prechter et al. 2012; Macalester thesis; blog figures from stoic.ai and theledgermind.com.
- **Structured:** Fine et al. 1998; Murphy, Paskin 2001; Wisebourt 2011; Wan, Si 2018; Cagatay 2009; Prechter, Goel 2003 (https://doi.org/10.2139/ssrn.381560); Zhu 2026 MLC; FactorBench mirror; QuantaAlpha, AlphaSchema, Hubble, FaVOR, AlphaDiverse; METR 2026 update; ResearchGate retrospective; IJCRT study.
- **Honesty:** Hansen 2005; Politis, Romano 1994; Politis, White 2004; Patton et al. 2009; Witzany 2021; Arnott et al. 2019; Wilks 2010; Bradley et al. 2008; Shao 2010; St. Louis Fed paper on GW; `arch` multiple-comparison page.
