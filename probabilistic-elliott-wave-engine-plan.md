# Building a Probabilistic Elliott Wave Engine for BTC: Architecture and Phased Plan

**Bottom line: build it, but as a deterministic hypothesis-tracking engine that applies your NewWave rulebook in code and turns its output into calibrated probabilities. The probabilities should describe observable outcomes (did this count's target get hit before its invalidation level), not a "true" wave count, because no ground-truth count exists. An LLM should explain the counts, not produce them.** The data is cheap and good, and enough prior art exists to borrow from. The hard parts are degree and nesting, causal pivot detection, and proving the probabilities are honest. The published evidence that Elliott/Fibonacci structure predicts anything beyond chance is weak, so treat Phase 5 as the go/no-go gate rather than a formality.

## TL;DR
- **What to build:** a Python pipeline. It stitches Bitstamp (2012→), Binance spot (2017→) and Bybit perp (2020→) data. It detects only pivots that would have been confirmed at the time. It enumerates candidate counts with beam search, discards any that break hard rules, scores the rest against NewWave guidelines and historical statistics, and runs a Bayesian update every hour after the 1H close. The output is the top 1–2 counts plus an explicit "other/unclear" probability, each with invalidation and target levels.
- **How to get honest probabilities:** label every historical hypothesis by outcome (target hit before invalidation, yes/no). Fit a calibrator to those labels (isotonic or Platt). Judge it on walk-forward Brier score, log loss and reliability diagrams, and compare against a dumb baseline. Commercial engines such as EWAVES still "flip-flop" between near-equal counts. That is a feature to model, not hide.
- **Effort and realism:** about 16–24 weeks of focused solo work to a first evaluated system, with Phase 1 (labeling engine) taking the most time. Rigorous studies (Batchelor & Ramyar on the Dow, Kempen 2016, Westland 2024 on crypto) find Fibonacci ratios and Elliott structure no more frequent or predictive than chance. Your system must beat a baseline to justify itself.

## Key Findings

### 1. Data sources: free data covers everything you need
| Source | Instrument | History | Resolutions | Cost / notes |
|---|---|---|---|---|
| Bitstamp via Kaggle (mczielinski) and the ff137 GitHub mirror | BTC/USD spot | 1 Jan 2012 → present | 1-minute (resample to 15m/1H/4H/1D) | Free. The ff137 cleaned bulk file holds 6,846,600 records to 7 Jan 2025, about 90 MB zipped, with "no missing minutes, no duplicates", plus daily updates. Liquidity is thin in 2012 and becomes reasonable during 2013. CC BY-SA 4.0. |
| Binance public data (data.binance.vision) | BTCUSDT spot, USDT-M perp | Spot from Aug 2017 | All intervals (1s, 1m, 15m, 1h, 4h, 1d, …) as daily or monthly zips | Free, with checksums. New daily files appear the next day; monthly files on the first Monday. Easiest bulk source. |
| Bybit API v5 `/v5/market/kline` | BTCUSDT linear perp (your trading venue) | USDT perps announced 24 March 2020 and live 25 March 2020 (CoinDesk: "The contracts, going live Wednesday…") | 1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M | Free and paginated. The WebSocket `kline.{interval}.BTCUSDT` topic carries `confirm=true` when a candle closes, which is the natural trigger for the hourly loop. |
| TradingView export | Any | Daily: all history. Intraday: 5K bars (Basic), 10K (Essential/Plus), 20K (Premium), 25K (Expert), 40K (Ultimate) | Chart export, paid plans only | Not usable as a data backbone, and there is no public data API. Use it only for visual cross-checks. |
| CryptoDataDownload | Binance and others | Binance since late 2017 | Daily, hourly, minute CSV | Free tier; handy as a sanity cross-source. |
| Kaiko, CryptoStruct (paid) | Ticks / L2 | CryptoStruct's Bybit coverage starts July 2023 at €1 per instrument-day | Tick | Not needed. Candles are enough for wave work. |

**Stitching, my recommendation:** don't splice prices into one fake continuous series. Build a canonical *analysis series*: Bitstamp BTCUSD until Binance spot starts (Aug 2017), then Binance BTCUSDT spot. Keep Bybit perp as a parallel *live/execution series*. During the overlap (2020→), measure how often confirmed pivots differ between spot and perp (perp wicks from liquidation cascades can set different extremes). If the disagreement is small, run live analysis on Bybit perp. Otherwise analyse spot and execute on perp. Store everything in log price as well as linear price: at higher degrees on BTC, ratios measured in log space differ materially from linear ones, and you should record both and let the statistics decide. One more lesson from EWAVES: it converts each bar into ordered points (high/low in the sequence they occurred) because "bars are inherently ambiguous for wave counting." Use your 1-minute data to decide whether the high or the low came first in every 15m/1H bar. This removes a large source of wrong pivots.

### 2. Prior art: plenty of rule-checkers, almost nothing calibrated
- **Commercial engines.**
  - **EWAVES** (Elliott Wave International; the Individual Investor plan of EWAVES Live is $595/month per the ewaves.com pricing page, about $7,140/year if billed monthly) is the best-documented reference design. Its FAQ says it encodes historical pattern behaviour "as probabilistic tendencies", "recalculate[s] the wave count from scratch" on every new data point, and lets segments have "unknown" internal structure ("squint") so that real data can be counted at all. It analyses recent waves in more detail than old ones and treats targets as the centre of a zone (the final endpoint should land below the projection "about half the time"). It openly admits "flip-flopping" between near-equal counts, calling the core issue "intractable".
  - **ELWAVE** scores alternatives, shows which rules and guidelines drove each score, and emphasises consensus across alternatives.
  - **WaveBasis** and **MotiveWave** provide auto-counts, editable counts and scanners.
  - On TradingView, scripts such as EWCore show ranked alternatives with a score table and a multi-timeframe coherence table.
  - None of these publishes calibration evidence. Their "scores" are rankings, not probabilities.
- **Open source** (worth reading, none production-ready):
  - `drstevendev/ElliottWaveAnalyzer` brute-forces combinations of "MonoWaves" and validates them against rule classes; its example even runs on a BTC daily CSV. It is a good template for the rule-validation layer.
  - `Raj1984/ElliottWaveAnalyzer` handles impulses and diagonals, with Plotly output.
  - `DrEdwardPCB/python-taew` ports the method from the Tilburg FX thesis.
  - `philippe-ostiguy/PyBacktesting` uses a genetic algorithm to tune Elliott/Fibonacci parameters with walk-forward testing.
  - `noahnan-max/elliott-wave-trading-system` is an LLM "skill" with multiple counts, hard-rule filtering and explicit invalidation, and is closest to your agentic framing.
  - `baptiste-dehay/fractal-financial-markets-elliott-wave-validation` tests Elliott and Fibonacci claims against stochastic benchmarks, a pattern to copy for Phase 5.
- **Academic work:**
  - Vantuch, Zelinka & Vasant (2018), "An algorithm for Elliott Waves pattern detection," *Intelligent Decision Technologies* 12:15–24 (DOI 10.3233/IDT-170319): rule-based detection, then prediction from incomplete patterns.
  - Martin Kotyrba and Eva Volná, "Elliott Waves Recognition via Neural Networks" (ECMS 2012), and the follow-up methodology paper (ECMS 2013): a backpropagation network that recognises 11 pattern types (P1–P11).
  - Rafael Ribeiro Dos Santos, Vanderlei Bonato and Geraldo Nunes Silva (São Paulo State University; IEEE conference paper published 13 Dec 2023), "Predicting Elliott Flat and Zigzag Internal Shapes by Statistical Learning on Fibonacci Ratios": statistical learning on ratios "reduce[d] the error 4 times" versus guessing lengths from rules alone. This is the closest published analogue to your Phase 2 statistics database.
  - Treat high-accuracy claims sceptically, such as the IJNAA paper (Vol. 14, Issue 1, pp. 2587–2600) that uses a self-organising map to detect twelve Elliott patterns and reports "an average accuracy of 93.94% in predicting stock trends." Most are not causal walk-forward tests.

### 3. Empirical evidence on Fibonacci ratios and Elliott Wave predictiveness (read before investing months)
- **Batchelor & Ramyar (2006), "Magic numbers in the Dow"** (Cass Business School), DJIA 1914–2002, block-bootstrap tests: "A few significant ratios appear, but no more than would be expected by chance given the large number of tests we conduct." Prechter's rebuttal is that Elliott claims Fibonacci relationships only between specific wave pairs, so testing all swings dilutes the effect. That is a fair point, and your engine should test exactly those wave-pair conditions.
- **René Kempen (2016), "Fibonaccis Are Human (made)"** (*IFTA Journal* 2016, pp. 4–9), using "all 17.931 retracement values" from the current constituents of the Dow30, Nasdaq100 and DAX30, 4 Jan 1974 to 30 Jan 2015: retracements follow a log-normal distribution, and "there are no overall statistically significant retracement levels. While in a local environment the 100% retracement do show significance, the Fibonacci retracements are not seen empirically." The average reversal comes at about 112% of the prior move and the median at 85%. There is about an 86.6% chance price has not reversed by the 38.2% level, and about a 33.0% chance it has reversed by the 61.8% level.
- **Merrill (1977), *Filtered Waves*:** reported (second-hand, via Wikipedia) as finding "no reliably standard retracement".
- **Westland (2024), "Periodicity, Elliott waves, and fractals in the NFT market"** (*Scientific Reports* 14:4480): "The investigation of autocycles in cryptocurrency and NFT markets did not support the existence of Elliott Wave behavior in any of these blockchain enabled assets." Fractal models "are not consistent or stable over time."
- **van Ginneken (2013), Tilburg MSc thesis** (FX, 2005–2013): "did not result in finding significant profitability." However, the simulated real-time variant did produce some significant returns after costs. The result is mixed and the null was not rejected.
- **BTC-specific ratio frequencies:** I found no rigorous published study. Figures like "73% of wave 2s retrace 50–61.8%" come from TradingView posts and blogs with no chance baseline.

**What this means:** your Phase 2 database will itself be the evidence. Build it to answer "is the 0.618 bucket overrepresented versus a matched random-walk or shuffled-returns baseline, conditional on wave label?" If it isn't, the soft-rule priors should come from the data, not from textbook Fibonacci ratios.

## Details: the plan

### Recommended stack
- **Language and data:** Python 3.12, Polars (or pandas), Parquet files queried with DuckDB, and Numba for the enumeration hot loops.
- **Storage:** Postgres or SQLite with JSON columns for the hypothesis store, plus an append-only predictions log in Parquet.
- **Ingestion and scheduling:** `pybit` (Bybit REST/WebSocket); Binance bulk zips for backfill; APScheduler or a systemd timer, triggered by the Bybit `confirm=true` kline event with a REST fallback at :00:30.
- **Charts:** TradingView's open-source Lightweight Charts or Plotly for your own annotated charts. TradingView has no API to push drawings, so the practical bridge is generating a small Pine script with hard-coded levels and labels for the current top counts, or simply webhook/Telegram the levels.
- **Testing:** pytest plus property-based tests (Hypothesis) for the rules engine.
- **Agent tooling:** Claude Code as the build agent, plus a thin LLM layer at the edges (see below).

### Core data structures
```python
@dataclass(frozen=True)
class Pivot:
    ts_extreme: datetime      # when the high/low occurred
    ts_confirmed: datetime    # when it became knowable (causal!)
    price: float; kind: Literal["H","L"]
    tf: str; threshold: float # e.g. ATR multiple or % used
    level: int                # fractal level in the pivot pyramid

@dataclass
class WaveNode:               # a node in the count tree
    label: str                # "1","2","3","4","5","A","B","C","W","X","Y","a".."e"
    pattern: str              # impulse|leading_diag|ending_diag|zigzag|flat_reg|flat_exp|running|triangle|wxy|unknown
    degree: int               # e.g. Minuette=0 … Primary=4
    start: Pivot; end: Pivot | None   # None = in progress
    children: list["WaveNode"]
    ratios: dict[str, float]  # e.g. {"w2_retr_w1": 0.61, "w3_ext_w1": 1.72} in lin and log
    tdi: dict[str, float]     # NewWave TDI signature at end pivot (RSI/TDI band position, divergence flags)

@dataclass
class Hypothesis:             # one live count
    id: str; root: WaveNode; current_path: list[str]  # e.g. ["Primary 3","Interm (5)","Minor 3"]
    invalidation: float; invalidation_rule: str
    targets: list[tuple[float, float, str]]  # zone low/high + rule ("w3=1.618*w1")
    raw_score: float; prior: float; posterior: float; calibrated_p: float
    history: list[dict]       # per-hour snapshots: ts, posterior, reason, event
    status: Literal["live","invalidated","target_hit","merged","expired"]
    parent_id: str | None     # lineage, for when a count morphs (e.g. impulse→diagonal)
```
Every hourly run writes an immutable snapshot of each hypothesis (who existed, their probabilities, the forecasted event) to the predictions log. That log is your calibration dataset.

### Phase 0: Data foundation (1–2 weeks)
- Backfill Bitstamp 1-minute data (2012→2017-08) and Binance spot 1-minute data (2017-08→), plus Bybit perp 1-minute/15-minute data (2020-03→). Resample to 15m, 1H, 4H and 1D, always in UTC.
- Build gap and outlier reports (flash wicks, exchange outages). Derive intrabar high/low ordering from the 1-minute data.
- Compute indicators once and version them: ATR, RSI and the NewWave TDI as you use it. Write down your exact TDI parameters; the NewWave course teaches price action, pattern identification, TDI and Fibonacci together, so encode your settings, not generic ones.
- Deliverable: `bars/{venue}/{tf}/year=YYYY.parquet` plus a data-quality notebook.

### Phase 1: Pivot detection and labeling engine (6–9 weeks; the core)
1. **Causal multi-scale pivots.** Use a zigzag with ATR-multiple thresholds (for example k = 1, 2, 4, 8 × ATR) at each timeframe to build a pivot pyramid of nested levels. Every pivot stores `ts_confirmed`. A zigzag repaints by design, and backtests that use pivots "where they are drawn rather than where they were confirmed" contain lookahead bias. The live, in-progress leg is always provisional and must be represented as such.
2. **Candidate enumeration as a grammar.** Treat Elliott as a context-free-like grammar: Impulse → 5 motive/corrective legs, Zigzag → 5-3-5, Flat → 3-3-5, Triangle → 3-3-3-3-3, and so on, with an `unknown` leaf allowed (EWAVES's "squint"). Parse bottom-up (CYK/chart-parser style) over the pivot sequence with **beam search**, keeping the top N = 100–500 partial parses per position. Brute-forcing every combination (the ElliottWaveAnalyzer approach) is fine for a single window but explodes across a 14-year multi-degree history.
3. **Hard rules** (rejection): wave 2 never goes beyond the start of wave 1; wave 3 is never the shortest of 1/3/5; wave 4 does not overlap wave 1 except in diagonals; diagonal convergence and overlap rules; triangle leg contraction; C-wave and flat B-wave constraints. Add your NewWave-specific hard rules as data (YAML), not code branches, so you can version and A/B them.
4. **Soft scores** (ranking): Fibonacci fit, alternation (2 vs 4), channeling, wave-of-largest-extension, time ratios, internal subdivision quality, and NewWave TDI signatures (for example, the expected TDI behaviour at a wave 3 versus a wave 5 end, or divergence on 5). Initially the weights are hand-set; Phase 3 learns them.
5. **Degree nesting across timeframes.** A 1D wave node must decompose into 4H children, and those into 1H children. Enforce this with a consistency penalty rather than a hard constraint, because, as EWAVES notes, bar quantisation means "a beautiful five-wave structure on an hourly chart may appear as a three-wave structure" on daily bars. Use the 15m data only for drill-down when deciding the internal structure of the most recent leg.
6. **Gold set.** Hand-label 30–60 major BTC swings with your own NewWave counts (2015–2018, 2018–2021, 2022 bottom, 2024–2025, and so on). These are not ground truth. They are a regression test that the engine can at least reproduce *your* reading.

### Phase 2: Historical statistics database (2–3 weeks, overlaps Phase 1)
Run the engine causally across all history (as-of each confirmed pivot) and record, per completed pattern:
- retracement and extension ratios (linear and log) for W2/W1, W3/W1, W4/W3, W5 vs W1 and vs 0→3, B/A, C/A, and triangle legs;
- which wave extended; pattern-type frequencies by degree and timeframe; durations; TDI state at the end of each wave;
- **conditional distributions**, such as P(W3/W1 | W2 retraced > 0.786), and survival functions such as P(W3 extends beyond 2.618 | it has already reached 1.618).

Store full empirical distributions (kernel density estimates or histograms), not single "typical" ratios. Always store a **null-model** version computed on the same engine run over synthetic paths (block-bootstrapped returns or GARCH-simulated BTC). Only the *difference* from the null is evidence of Elliott structure. This mirrors the Batchelor & Ramyar and baptiste-dehay methodology and is the single most valuable research output of the project.

Caveat: these statistics are conditional on your engine's choices (thresholds, beam, rules). They describe the engine's counts, not "the market's true waves." Report them that way.

### Phase 3: Probabilistic scoring and calibration (4–6 weeks)
- **Define the probability target.** "P(count is true)" is unobservable. Define instead, for each hypothesis at time t, a forecast event E: "price reaches target zone T before invalidation level I within horizon H." Store E at prediction time, and later resolve the label automatically. This is outcome-based labeling, and it gives you thousands of labeled examples from history.
- **Posterior update** (each closed 1H bar): posterior ∝ prior × likelihood(new bar | hypothesis). The likelihood comes from Phase 2 distributions; for example, if H says "wave 3 in progress, at 1.4× W1," the probability that the next hour's path is consistent uses the survival function of W3/W1. A breached invalidation level sets the posterior to 0. New hypotheses enter with a prior from the grammar score. This is effectively a **particle filter / multiple-hypothesis tracker** where each particle is a full count. It solves EWAVES's flip-flop problem honestly, because the posterior carries memory without "sticking to its guns."
- **Ranking model.** Once the log exists, train a gradient-boosted ranker or classifier (LightGBM) on features (rule-fit scores, ratios versus Phase 2 percentiles, TDI state, degree agreement, volatility regime) to predict E. Then **calibrate** with isotonic regression or Platt scaling on a later, separate time fold.
- **The "other" bucket.** Always reserve mass for "none of the top-K / unclear." Output, for example, "Primary 34%, Alternate 21%, Other/unclear 45%." Forcing the top two counts to sum to 100% is the most common way these systems lie.
- **Metrics:** Brier score and log loss versus two baselines: (a) a base rate, and (b) a structure-free model (for example, the probability of hitting the same price levels estimated from volatility alone with a barrier-hit approximation). Plot reliability diagrams per probability bucket, plus sharpness. Report results separately by timeframe and volatility regime.

### Phase 4: Live hourly loop (2–3 weeks)
```
on Bybit kline.60 confirm=true (fallback: cron hh:00:30 REST poll):
  1. ingest closed 1H (+ 15m, and 4H/1D if their bar also closed); verify no gap
  2. update pivot pyramid; mark new confirmed pivots; update provisional leg
  3. for each live hypothesis: check invalidation/target → resolve & log outcome
  4. extend hypotheses with new pivots (beam expand); spawn new ones from parser
  5. Bayesian update → raw posteriors → calibrator → calibrated_p (+ "other")
  6. diff vs previous hour: what changed and why (rule hit, ratio crossed, TDI event)
  7. persist snapshot (append-only); render chart; emit report (Telegram/Slack/email)
  8. LLM step (optional): narrate the diff using ONLY the structured JSON
```
Make every step idempotent and keyed by bar timestamp, so a rerun or late bar never double-counts. Keep the engine version in each snapshot, so calibration is only computed within one engine version.

### Phase 5: Evaluation (2 weeks to set up, then ongoing)
- **Walk-forward replay:** run the *exact live loop* over history bar by bar (2014→), using only `ts_confirmed` information, and refit the Phase 2 statistics and the Phase 3 calibrator only on past folds (for example, expanding window with yearly refits).
- **Lookahead traps to test for:** pivots used before confirmation; statistics fitted on the full sample; the gold set leaking into weights; intrabar ordering using future minutes; and resampling misalignment (4H/1D bars that hadn't closed).
- **Honesty tests:** reliability diagrams; Brier/log-loss skill versus the volatility-only baseline; the same pipeline on shuffled or synthetic BTC paths (if it scores equally well there, it has found nothing); stability (how often the primary count flips per day).
- **Go/no-go:** if calibrated count probabilities don't beat the structure-free baseline out of sample, keep the system as a disciplined *annotation and invalidation tracker* (still useful for your discretionary trading) and stop treating its percentages as edge.

### Where LLMs help, and where they must not
- **Use an LLM (Claude) for:**
  - turning your NewWave course notes into a draft machine-readable rulebook (YAML), which you then review line by line;
  - writing and refactoring the engine with Claude Code;
  - narrating the hourly diff from structured JSON;
  - summarising external analysts' published counts as *features* (for example, "consensus says wave 4"), to test later whether they add information.
- **Never let the LLM** propose pivots, labels, ratios or probabilities from a chart image or raw prices. LLMs produce fluent, confident counts that can violate hard rules or invent levels. The `noahnan-max` repo's design (hard-rule filter plus explicit invalidation) is the right instinct, but the counting must be deterministic code. Guardrail: the narrator receives only engine JSON, and any number in its output must string-match a number in that JSON.

### Effort estimate (solo, experienced engineer, ~30 h/week)
| Phase | Weeks | Main risk |
|---|---|---|
| 0 Data | 1–2 | intrabar ordering, venue stitching |
| 1 Pivot + labeling engine | 6–9 | grammar/beam explosion, degree nesting |
| 2 Statistics DB + null model | 2–3 | statistics are engine-dependent |
| 3 Scoring + calibration | 4–6 | defining forecast events; class imbalance |
| 4 Live loop | 2–3 | idempotency, partial bars |
| 5 Evaluation | 2 + ongoing | discovering there's no edge |
| **Total** | **~17–25** | |

An MVP shortcut gives a useful tool in about 6–8 weeks: run 1H/4H only, cover impulses, zigzags and flats only (no triangles or combinations), set weights by hand, and log predictions from day 1. Calibration then grows from live data.

## Hardest problems and how to tackle them
1. **Degree assignment.** The same swing can be a wave 3 or a wave C at different degrees. Model degree explicitly in the grammar; tie degree loosely to pivot-pyramid level; penalise inconsistent nesting rather than forbidding it.
2. **Combinatorial explosion.** Use beam search, memoise sub-parses (a dynamic-programming chart), cap the number of `unknown` leaves, and give recent legs more detail than old ones (the EWAVES design choice).
3. **The repainting live leg.** Represent the provisional extreme as a distribution, and never confirm a count on an unconfirmed pivot.
4. **No ground truth.** Outcome-based labels plus a null model, with your gold set used only as a regression test.
5. **Count instability.** Use Bayesian memory instead of recomputing from scratch, and report an explicit "unclear" mass when the top counts are close.
6. **Overfitting the rulebook.** Freeze rule versions, tune only on past folds, and count every variant you try (multiple-testing is exactly what sank the Fibonacci studies).

## Recommendations
- Start with Phase 0 and the Phase 1 MVP on 1H/4H, and log predictions from the first week. Live, out-of-sample logs are worth more than any backtest.
- Make "probability" mean the probability of an outcome you can resolve, and always show the "other" bucket.
- Build the null-model comparison into Phase 2 from the start. It is cheap, and it tells you whether the BTC Fibonacci statistics are real.
- Encode NewWave rules and TDI signatures as versioned config so you can measure which of *your* rules carry information.
- Use EWAVES's FAQ and ELWAVE's scoring UI as design references, `drstevendev/ElliottWaveAnalyzer` as a starting rules-layer template, and Dos Santos et al. (2023) as the closest academic analogue for learning ratio statistics.

## Caveats
- I could not verify the internals of NewWave's proprietary TDI or its strategy rules. The plan assumes you transcribe them.
- Vendor claims are marketing until published. ewaves.com describes "a decade-long R&D process led by engineers from Lockheed and MIT… trained on a massive database of real-world historical market patterns." The EWAVES Live page cites an "upcoming paper, 'Using the Elliott Wave Model to Distinguish Real from Random Financial Returns'" and claims "Real market data have higher elliotticity, to a statistically significant degree." That paper is still unpublished.
- The Merrill (1977) finding is second-hand. There is no rigorous BTC-specific Fibonacci-frequency study, so your own Phase 2 output will be the first credible number you have.
- Effort estimates assume part-time-plus focus and exclude UI polish.
- Nothing here is evidence that the system will be profitable. The evidence leans the other way, which is precisely why the calibration and baseline machinery is the core of the plan rather than an add-on.
