# Top-down count board, round 2: Fibonacci time

What this is: round 1 with time as its own axis. You looked at count 1d.3 (zigzag down from 126,150) and said a correction this short, with a B this short and such a shape, is very unlikely to be an ABC, and that Fibonacci time is the missing link. Package `src/ewave/counts/`, config `rules/counts.yaml` (version `counts-r2.0`), command `ewave-counts`, private chart panel `site/counts.js`. Nothing here is committed or public.

**Read this first.** You were right about both, and the board now says so:

- **1d.3 (C took 3.65 x A) fell from 3rd to 29th of 97 states.**
- **1d.1 (W2 took 3.98 x W1 once dated on the hour; r1's daily bars said 4.25) fell from 1st to 18th.**
- **The new top 3 at 1D:** the 2022-2025 rally is a finished zigzag; the decline is W-X with Y down running; the decline is an X with Y up running.

Three cautions, none of them small:

1. **Time here is the rulebook's plausibility filter and the way a NewWave trader reads a chart. It is not a proven edge.** On mechanical pivots the Fib time templates hit at random-path rates (`research/model-options/02-empirical.md`, B3), and my own check below does not change that.
2. **The tree turned mostly bearish, and that is not a forecast.** It follows from the time checks removing the two "57,756 was the end" readings from the top. Both stay legal, and only their invalidation levels can kill them.
3. **The ranking is still rulebook fit, not a win chance.** Fits cannot be compared with r1's: the formula changed, and r2's numbers run lower.

## How to use it

```bash
uv run ewave-counts report --root 1d --brief      # each node with its legs and time window
uv run ewave-counts report --root 1d              # the whole tree: labels, legs, window, crosshairs, odds, fits and misses
uv run ewave-counts rank --root 1d --top 30       # states below the kept ones too, with their three axes
uv run ewave-counts export                        # site/data/local/counts.json for the chart panel (gitignored)
uv run ewave-counts replay --dates 2025-01-01,2026-01-01 --days 30
```

On the chart, turning on **Counts** draws the best count of the current timeframe. Choosing a count now also draws:

- **the time window:** a shaded vertical band, its dates at the top. It turns red once the window has passed;
- **the target as a box:** the price zone across the width of the window;
- **crosshairs:** small white crosses where a price level still ahead meets a time level still ahead. A ring marks an extreme that already sits on one;
- **a tag on each finished leg:** its duration and its ratio (`46d · 1.17x`), red when time fails on that leg. On a phone, only the duration, and only where there is room.

Each row in the panel shows `price x.xx · time x.xx · structure x.xx`, with an axis at 0.25 or below in red, and "due <date> to <date>". The long reasons now sit behind **Why this score**, grouped by axis, and the full levels behind **All levels**.

## Time inventory

Every time statement I found in the complete reference and the compact rulebook. Status: R rule (break kills), G guideline, C course convention, B BTC-calibrated, K course conflict. Weights are on the same scale as price items, whose main templates weigh 1.0.

| ID / section | Status | What it means | How it is implemented | Weight or kill |
|---|---|---|---|---|
| FIB-T3, sec 4 minimum | R | Any correction takes at least 25% of the wave it corrects | Hard rules on W2, W4, B, X and a triangle's B, on exact times | **Kill**, tolerance one measuring candle |
| FIB-T4, BTC-3, sec 7 | B | Crypto uses 1.25, traditional markets 1.33 | Minimum is 0.25; 0.33 is only a level in the windows | With the rule above |
| FND-4 | C | A broken guideline never kills; guidelines include time | Everything else on this list ranks and never kills | n/a |
| IMP-T1 | C | W3 duration vs W1, Trend-Based 0-1-2: 1.618, 2.236, 1.0 in a fast market | `w3_time`; window for a running W3 | 1.0 |
| IMP-T2 | C | W5 duration vs W1, Trend-Based 0-1-4: 1.0, else 0.618 | `w5_time`; window for a running W5 | 1.0 |
| IMP-T3 | C | W2 should not outlast W1 (Fib Time Zone 0-1) | `w2_time`, credit 0 at 1.618 x W1; window for a running W2 | 1.0, veto |
| IMP-T4 | C | W4 should not outlast W3 (Fib Time Zone 2-3) | `w4_time`, same | 1.0, veto |
| IMP-T3/T4, degree check | C | A correction under the minimum is unfinished or of a lower degree | The hard rule above, plus `degree_mix` (below) | See both |
| IMP-T3/T4, pattern check | C | A correction outlasting its wave is typically corrective, not a W2 | The veto, and the note says so | Veto |
| IMP-T3/T4, emotional control | C | Knowing a correction is too early | Not modelled, except "due" dates | n/a |
| IMP-T5 | C | W1 and W5 tend to equal time, except truncation and ending diagonal | `w5_time` skipped on a truncated W5 and on diagonals | With IMP-T2 |
| IMP-T5, fast W1 | C | A very fast W1 leaves W3 behind in time; keeping up means parabolic | `w3_steepest` stays soft. Parabolic is not detected | 0.5 |
| IMP-T6, STR-C8 | C | A finished fifth or C is retraced in about its own time or less; holding past that says it may not have ended | `retrace_time`. "Retraced" here means back to that wave's start: **my reading** | 1.0 |
| L114 in IMP-T6 | C | A retraces W5, W1 down retraces C, in equal time or less | Same measurement on the finished count | With IMP-T6 |
| STR-C8 time test, CONFLICT-21 | C, K | A sub-wave 2 outlasting the primary W2 kills the impulse reading; a tie is a warning | `sub_w2_time`: a tie scores 0.5. A veto, not a kill: the book's kill sits in a strategy | 1.0, veto |
| IMP-N8, compact sec 1 K | K | W4 about W2 in time, or alternation: both held | `alternation` accepts equal time or a clear difference in depth | 0.4 (structure) |
| FIB-T10 | C | Paired legs drastically out of symmetry is a novice error | `w4_w2_time`: fine from 0.382 to 2.618 x W2, fading after. The numbers are ours | 0.5 |
| IMP-G15 | G | W4 often divides the impulse in Fib proportion in time | `w4_split`: credit if W4 ends about 0.382 or 0.618 through | 0.3, bonus |
| DIAG-G3, sec 3.4 | G | Contracting: W4 less time than W2. Expanding: more | `diag_time`; window for a diagonal's W4 | 0.7 |
| Sec 3.5 look-alike 6 | G | W4 longer than W2 is not contracting, maybe expanding | Reclassifies rather than kills: same item | With DIAG-G3 |
| Trend-Based template, correction | C | C vs A: 0.618 or 1 | `ac_time`: credit 0 at 2 x A or more, or at 0.31 x A or less | 1.0, veto |
| COR-4 | G | A and C compared on speed and time | `ac_speed`, fine from 0.5 to 2 x | 0.5 |
| FIB-T5 | G | B can take up to 4 x the wave before it | `b_time`: fine to 4, credit 0 at 6.854 | 1.0, veto |
| FIB-T5, B template 2.618 and 4 | C, K | The book reads these at face value, unlike other Fib Time Zone levels | Levels in the B and X window, as the book says | Window only |
| CPX-G6 | G | X goes like a B, up to 4 x | `x_time`, same | 1.0, veto |
| CPX-G3 | G | W and Y tend to equal time, as A and C do | `wy_time`: template 0.618, 1, tightened like `ac_time` | 1.0, veto |
| FIB-T1 | C | A violent move is paid for in sideways time | The idea behind the axis; no item of its own | n/a |
| FIB-T2 | C | Fib Time Zone numbering is cumulative: read level minus one | Every Fib Time Zone level is stored as the time it means | n/a |
| FIB-T6 | C | A candle bounds time resolution; drop a timeframe to measure | Pivots dated on 1H (1D, 12H) and 15m (4H, 1H). Tolerance from that candle | See below |
| FIB-T7 | C | Drawing rules; Fib Time Zone on adjacent moves only | Fib Time Zone used only on adjacent moves | n/a |
| FIB-T8 | C | Partner legs: Trend-Based time plus price, better in both wins | `partner_filter` removes the loser before ranking | Removes readings |
| FIB-T9 | C | Where a price level and a time level meet is a likely pivot | Target box, crosshairs ahead, ring on the extreme, `crosshair` on finished pivots | 0.7, bonus |
| Sec 8.2 Programmer, sec 16 | C | A conclusion needs price and time pointing the same way | The geometric mean of the axes | n/a |
| TDI-D3 | C | The Fib Time Zone helps tell two hidden-bullish cases apart | **Not modelled:** no hidden divergence detector | n/a |
| TO table, TO-9 | C | Take Off: primary W2 vs W1; failure sequence | Only `sub_w2_time` | n/a |
| E5-5 | C | An extended fifth squeezes up fast, no longer than earlier corrections | **Not modelled** | n/a |
| SCR-3 | C | Under about 40 candles is no trend (a Three Frame screen) | Not a wave rule, so not used. `min_span_bars` stays ours | n/a |
| Triangles (TRI-G), flats (FLAT-G) | n/a | **The book gives no time numbers** beyond the minimum; flats use the correction template | Triangles have no window; flats are judged like zigzags | n/a |

Ours, and marked so in the config:

- **`degree_mix`:** the longest partner leg of a structure against its shortest. Fine to 2.618 x, credit 0 at 6.854 x, a veto. The basis is IMP-T1, T2 and T5 and the degree check, but no line in the book states it. This is the check for "a 4-day W1 under a 102-day W3".
- **`whole_time`:** a finished correction at the root against the wave it corrects. The numbers are the book's (FIB-T3, FIB-T5, the W2 template). **Finding that wave is ours:** the move from the opposite extreme of the 1,500 days before it.
- **`past_end`:** how far a correction's inside goes past the end of the wave it corrects. The book allows it in an expanded flat, so a little is free. At 0.146 of that wave in log it is a veto. It is a structure item, not a time item, and I added it because of what I saw on the chart: an A at 64,936 with 57,756 printed inside its B.
- **`nest_time`:** see Nesting below.

## Decisions, and why

**Scoring**

| Decision | Value | Why |
|---|---|---|
| Three axes | price, time, structure | Your request. Each item's axis is in the config |
| Axis score | (sum of w x f + 3.0 x 0.35) / (sum of w + 3.0) | Keeps r1's lesson: with little judged, an axis stays near 0.35, so a bare "B running" cannot outrank a fully labelled count. A test checks this. Both numbers are ours |
| Combining | Geometric mean of the three | A 1% loss on any axis costs the same whatever the others are, so no axis can pay for another. A min() would do that too, but would ignore everything except the worst axis. A test checks a fail on time against a middling count |
| Veto | A named pattern or degree check at 0.05 or less caps its axis at 0.2 | Without it, the passing items of the same axis average a failure away. With price and structure perfect, fit stays under 0.59. It is still a guideline: the count stays legal |
| Credit types | both, penalty, bonus | "Has not failed yet" is no evidence, so a pass on `running_time` or `running_depth` counts for nothing and a miss costs. A crosshair is rare by construction, so a hit counts and a miss costs nothing |
| Time template shape | Full on a level, 0.6 inside the range, fading to 0 over a factor of 2.618 in log (2 for A-C and W-Y) | Ratios of durations are multiplicative. r1 used a narrow match, which gave 0 to almost everything. The numbers are ours |

**Measuring**

| Decision | Why |
|---|---|
| Each pivot gets an exact time from the bar that holds its extreme: 1H for 1D and 12H, 15m for 4H and 1H, its own bar for 15m | FIB-T6. Those bars closed with the pivot's own bar, so this reads no later data. A test cuts the data and compares |
| The hard minimum's tolerance is one measuring candle, not one bar of the frame | FIB-T6. A whole daily bar of tolerance would pass a W2 that is 2.4 hours short (a test has this case). **The hard minimum stays:** the book marks it R. B3 says about a third of mechanical W2s break it, also on random paths, so it filters, it does not discover |
| A template is met within the larger of 6% or 2 measuring candles against the base | Two pivots, each dated to one candle |

**Windows**

| Running wave | Tool | Window | Credit gone at |
|---|---|---|---|
| W2, W4 | Fib Time Zone 0-1, 2-3 | 0.25 to 1 x W1, W3 | 1.618 x |
| W3 | Trend-Based 0-1-2 | 1 to 2.236 x W1 | 5.854 x |
| W5 | Trend-Based 0-1-4 | 0.618 to 1 x W1 | 2.618 x |
| B, X | Fib Time Zone 0-A, 0-W | 0.25 to 4 x A, W | 6.854 x |
| C, Y | Trend-Based 0-A-B, 0-W-X | 0.618 to 1 x A, W | 2.618 x |
| Diagonal W4 | Fib Time Zone | 0.618 to 1 x W2 | 2.618 x |
| After a finished structure | Fib Time Zone over the whole of it | 0.25 to 1 x | 2.618 x |
| W1, A, W; diagonal W3 and W5; triangles | None: **the book gives no base** | Says so in the panel | n/a |

The "credit gone" numbers are ours. After a finished 5 the tool mirrors the next-degree W2 pull in time; after a finished correction the book has no tool, so using the same one is ours.

- **`running_time_ceiling` is gone.** r1 used 4.236 for every wave. Each wave now has its own limit, and a wave past its window loses credit from the first day over.
- **Odds horizon.** The leg runs until its window closes. The next wave runs until then plus its own largest template. Past the window, under 5 bars left, or with no base, it falls back to the fixed horizon. Every row says which it used. **This makes r2's "what came first" column not comparable with r1's:** horizons are much longer, so more rows end in invalidation.

**Partnering (FIB-T8).** Same family, direction, running wave and end pivot, with the legs paired differently: a pairing beaten by 0.1 or more on **both** time and price is removed before ranking. Better on one and worse on the other both stay. Readings with no pair yet are not compared. It works, and a test shows it can remove a higher-fit reading. On real data it mostly thins the list:

| Measured | Result |
|---|---|
| Root readings removed today | 33 of 444 |
| Root readings removed at the 8 replay dates | 6 to 46 |
| Kept nodes changed today | None |
| Kept nodes changed at the replay dates | One 1H node swapped, on 2023-07-01. None on the other 7 dates |

**Nesting.** A child that finishes the parent's wave must end inside the parent's window. One that does not must be able to end before that window closes. Credit fades over one base wave of the parent. This test is ours. The book's own nesting statement is STR-C8, which is `sub_w2_time`.

**Other small decisions**

- At the root, the seat kept for the other direction now prefers a count already running that way. Otherwise, today's bullish seat went to a "down, then up after its zone" count, while all its children ran down.
- Below the root a crossroads can appear on time grounds. Today 1H has one (see below).

## The current tree

As of 2026-10-30 22:30 UTC, Bybit perp, rules `counts-r2.0`.

```
Root: 411 legal readings in 97 states. Kept: top 3; other/unclear 90% of fit.
1D [1d.1] Zigzag up finished at 126,150, next move down running. Fit 0.66 (price 0.66 · time 0.65 · structure 0.66).
   A 478d; B 144d, 0.30 x A; C 428d, 0.89 x A. Running: due 2026-06-26 to 2028-08-21, 0.37 x the whole so far.
1D [1d.2] Combination down, in Y. Fit 0.58 (price 0.51 · time 0.58 · structure 0.66).
   W 267d; X 83d, 0.31 x W. Running: due 2027-03-06 to 2027-06-16, 0.15 x W so far.
1D [1d.3] Combination up, in Y. Fit 0.54 (price 0.51 · time 0.58 · structure 0.53).
   W 1050d; X 267d, 0.25 x W. Running: due 2028-04-09 to 2029-05-15, 0.12 x W so far.
```

**The three in plain words.**

1. **The 2022-2025 rally was a three, finished at 126,150.** A and C are partners: C took 0.89 x A and 1.32 x A in price, and B took 0.30 x A. The decline since then is the next move. Its low, 57,756, sits on a crosshair: 25 dollars from the 0.618 of the rally, at 0.255 x the rally's time, the 1.25 line. Invalidation 126,150. Its time window is 26 months wide, so at this degree time says little about *when*.
2. **The decline to 57,756 is W, the rally to 87,384 is X, Y down is running.** X took 0.31 x W and 0.433 of it in price. Y's zone is 33,271 to 53,920, due March to June 2027. Above 87,384 it dies.
3. **The decline is an X of a much larger three, and Y up is running.** W took 1,050 days and X only 0.25 x that, right at the minimum, and 0.618 in price. So X sits on a crosshair, but with the least time the book allows. Y's zone is 126,175 to 194,593, due April 2028 to May 2029. Below 57,756 it dies. This is the bullish seat, kept by the rule that both directions get one; it ranks 7th.

**By frame, r1 against r2** (r1 and r2 at the same moment; kept nodes, the same reading under several parents counted once):

| Frame | r1 | r2 |
|---|---|---|
| 1D | Impulse down finished at 57,756 (0.82); zigzag up finished at 126,150 (0.81); zigzag down finished at 57,756 (0.77) | Zigzag up finished at 126,150 (0.66); combination down, in Y (0.58); combination up, in Y (0.54) |
| 12H | Impulse down finished at 57,756 (0.82); zigzag up finished (0.80); impulse up finished at 126,150 (0.79) | Zigzag up finished (0.66); combination down, in Y (0.58); combination up, in Y (0.53) |
| 4H | Impulse up in W5 (0.81); impulse up finished at 87,384 (0.81); impulse down finished at 57,756 (0.81); zigzag down finished at 57,756 (0.77) | Zigzag down, in C (0.55); combination down, in Y (0.55); flat down, in C (0.51); combination up finished at 87,384 (0.47); combination up, in X (0.45) |
| 1H | Impulse up finished at 87,384 (0.82); impulse up in W5 (0.81); impulse down in W5 (0.74); impulse up in W2 (0.64) | Combination down, in Y (0.56); flat down, in C (0.51); ending diagonal down, in W5 (0.48) |
| 15m | Leading diagonal down in W5 (0.77); combination down in Y (0.76); impulse down in W3 (0.67); impulse up in W2 (0.62) | Combination down, in Y (0.56); ending diagonal down, in W5 (0.51); zigzag down, in C (0.50); flat down, in C (0.43); impulse down, in W3 (0.37) |

Notice that **impulses have nearly gone from the top of every frame.** The time checks hit a five harder than a three, because a five has more legs to fail on. That also fits the book's "unsure means corrective".

**Crossroads and Y's, r2:**

| Frame | Kept counts: next move | Nearest Y above | Nearest Y below |
|---|---|---|---|
| 1D | 1 up (first 126,175), 2 down (first 57,731) | 87,384 | 57,756 |
| 4H | 2 up (first 82,943), 4 down (first 72,371) | 84,880 | 39,691 |
| 1H | **All 8 expect up next, first 80,556** | 81,967 | n/a |
| 15m | 5 up (first 80,556), 3 down (first 74,665) | 78,072 | n/a |

The 1H crossroads is real by the book's definition, but read it for what it is. All 8 are down-moves whose zone has already been touched, so each expects a move up *next*. Every one of them also sits inside a larger move down, so it is a bounce on that frame, not a call to buy.

## Worked example: the three daily counts of r1

Dated on 1H bars. Lily's numbers came from daily bars, so 4.25 x became 3.98 x; none of her conclusions changes.

| | **r1 1d.1**, impulse down | **r1 1d.3**, zigzag down | **r1 1d.2**, zigzag up |
|---|---|---|---|
| Legs | W1 4.12 d; W2 16.42 d; W3 101.71 d; W4 89.46 d; W5 55.58 d | A 45.75 d; B 54.33 d; C 167.21 d | A 478.42 d; B 143.96 d; C 427.50 d |
| Time numbers | W2 **3.98 x** W1 (limit 1); W3 **24.66 x** W1 (template 1, 1.618, 2.236); W5 **13.47 x** W1 (template 0.618, 1); longest partner leg **24.7 x** shortest; W4 0.88 x W3 (fine); W4 5.45 x W2 | C **3.65 x** A (template 0.618, 1); C speed 0.32 x A; whole correction 0.25 x the 1,051-day rally, only just at the minimum; B 1.19 x A (fine) | C 0.89 x A; B 0.30 x A; C speed 0.68 x A; whole 2.79 x the 377-day fall before it (fine for a B or X, not for a W2) |
| Retraced in time? | W5 back to its start in 1.47 x its own time: 82 d against 56 d. Late | Not reached: C still not retraced, but within its own time | Not reached, within its own time |
| Failed checks | `w2_time`, `degree_mix` | `ac_time` | none |
| r1 fit, rank | 0.823, 1st | 0.771, 3rd | 0.81, 2nd |
| r2 price / time / structure | 0.71 / **0.20** / 0.59 | 0.66 / **0.20** / 0.55 | 0.66 / 0.65 / 0.66 |
| r2 fit, rank of 97 states | 0.438, **18th** | 0.416, **29th** | 0.657, **1st** |

So on price alone the two you doubted still hold up: 1d.1 leads the three at 0.71, and 1d.3 ties 1d.2 at 0.66. Only time separates them, which is your point.

**What your words map to, and where the book stops.**

- "The correction is so short": 0.25 x the rally it corrects. That **passes** the book's minimum by the width of a line, so it costs credit but is no rule break.
- "Later the B correction is so short": B took 1.19 x A, which the book accepts, and 0.32 x C. **The book has no rule for B against C.** That ratio only shows up through C against A, so I did not invent one.
- "Such a weird shape": mostly C's own inside. C has a W4-like rally of 89 days in it. The board sees that as "A-" one frame down and a low C speed, not as a shape test. It is only partly captured.

## Replay: r1 and r2 side by side

The same eight dates as r1, data cut at each date. **No win rate can come from this:** 8 dates, overlapping rows, one root. The two "what came first" columns use different horizons, as said above, so do not count them against each other. Dates in the r2 column are the running wave's window; a window in the past means the wave was already past it at that date.

| as of, close | # | r1: count, running | r1: plan, vol odds, what came first | r2: count (price / time / structure), running, due | r2: plan, vol odds, what came first |
|---|---|---|---|---|---|
| 2023-01-01, 16,550 | 1 | impulse down, fit 0.83: 0=69,138 1=32,906 2=48,185 3=17,600 4=25,199 5=15,440; after | down 1,625 before 69,138, 0%, neither 2023-05-01 | impulse down, fit 0.61: 0=69,138 1=32,906 2=48,185 3=17,600 4=25,199 5=15,440 (0.61 / 0.68 / 0.56); after; 2023-02-23 to 2023-12-03 | down 1,625 before 69,138, 0%, invalidation 2024-03-05 |
|  | 2 | impulse down, fit 0.81: 0=69,138 1=32,906 2=48,185 3=17,600 4=25,199; 5 | up 32,673 before 15,440, 0%, neither 2023-05-01 | impulse down, fit 0.59: 0=69,138 1=32,906 2=48,185 3=17,600 4=25,199 (0.54 / 0.68 / 0.55); 5; 2022-09-30 to 2022-10-29 | up 32,673 before 15,440, 0%, neither 2023-05-01 |
|  | 3 | impulse down, fit 0.76: 0=69,138 1=32,906 2=48,185 3=17,600; 4 | down 11,993 before 32,906, 4%, neither 2023-05-01 | impulse down, fit 0.50: 0=69,138 1=32,906 2=48,185 (0.51 / 0.50 / 0.48); 3; 2022-06-11 to 2022-09-12 | down 14,494 before 48,185, 40%, neither 2023-05-01 |
| 2023-07-01, 30,466 | 1 | impulse down, fit 0.83: 0=69,138 1=32,906 2=48,185 3=17,600 4=25,199 5=16,203; after | down 3,006 before 69,138, 0%, neither 2023-10-29 | impulse down, fit 0.63: 0=69,138 1=32,906 2=48,185 3=17,600 4=25,199 5=16,203 (0.62 / 0.69 / 0.59); after; 2023-03-31 to 2024-01-28 | down 3,006 before 69,138, 1%, invalidation 2024-03-05 |
|  | 2 | impulse up, fit 0.78: 0=15,440 1=18,379 2=16,353 3=31,062 4=24,780; 5 | down 23,442 before 31,444, 10%, invalidation 2023-07-06 | flat up, fit 0.55: 0=9,834 A=64,944 B=15,440 (0.52 / 0.66 / 0.49); C; 2023-04-07 to 2023-06-30 | up 49,498 before 15,440, 8%, neither 2023-10-29 |
|  | 3 | combination down, fit 0.78: 0=69,138 W=32,906 X=48,185 Y=19,535; after | up 42,662 before 19,535, 22%, neither 2023-10-29 | impulse down, fit 0.39: 0=69,138 (0.35 / 0.35 / 0.48); 1; none | up 38,995 before 15,440, 37%, neither 2023-10-29 |
| 2024-01-01, 42,325 | 1 | impulse down, fit 0.83: 0=69,138 1=32,906 2=48,185 3=17,600 4=25,199 5=16,353; after | down 4,345 before 69,138, 0%, invalidation 2024-03-05 | impulse down, fit 0.64: 0=69,138 1=32,906 2=48,185 3=17,600 4=25,199 5=16,353 (0.64 / 0.69 / 0.59); after; 2023-04-13 to 2024-02-18 | down 4,345 before 69,138, 0%, invalidation 2024-03-05 |
|  | 2 | combination down, fit 0.78: 0=69,138 W=32,906 X=48,185 Y=19,535; after | up 69,138 before 19,535, 5%, target 2024-03-05 | combination up, fit 0.55: 0=16,203 W=31,062 X=24,201 (0.55 / 0.61 / 0.49); Y; 2023-10-28 to 2023-12-11 | down 27,118 before 44,777, 5%, invalidation 2024-01-02 |
|  | 3 | flat down, fit 0.74: 0=69,138 A=19,535; B | down 20,504 before 150,989, 0%, neither 2024-04-30 | flat up, fit 0.53: 0=6,466 A=64,944 B=15,440 (0.51 / 0.59 / 0.49); C; 2023-07-04 to 2023-11-20 | up 51,579 before 15,440, 44%, target 2024-02-14 |
| 2024-07-01, 62,750 | 1 | combination up, fit 0.79: 0=6,466 W=69,138 X=17,600 Y=73,949; after | down 32,244 before 73,949, 0%, neither 2024-10-29 | combination up, fit 0.62: 0=6,466 W=69,138 X=17,600 Y=73,949 (0.64 / 0.57 / 0.66); after; 2025-03-06 to 2028-02-10 | down 32,244 before 73,949, 17%, invalidation 2024-11-06 |
|  | 2 | impulse up, fit 0.78: 0=15,440 1=18,379 2=16,353 3=31,062 4=24,201 5=73,949; after | up 151,173 before 15,440, 0%, neither 2024-10-29 | combination up, fit 0.61: 0=6,466 W=69,138 X=15,440 (0.56 / 0.61 / 0.66); Y; 2023-11-11 to 2024-06-17 | down 32,244 before 73,949, 0%, neither 2024-10-29 |
|  | 3 | impulse up, fit 0.77: 0=19,535 1=31,844 2=24,201 3=73,949; 4 | up 68,814 before 31,844, 62%, target 2024-07-27 | zigzag up, fit 0.52: 0=24,853 A=73,949 B=56,505 (0.50 / 0.58 / 0.49); C; 2024-08-23 to 2024-11-01 | up 86,846 before 56,505, 8%, invalidation 2024-07-05 |
| 2025-01-01, 93,530 | 1 | impulse up, fit 0.83: 0=15,440 1=31,062 2=24,201 3=73,949 4=48,914; 5 | down 61,931 before 108,422, 10%, invalidation 2025-01-20 | impulse up, fit 0.65: 0=15,440 1=31,062 2=24,201 3=73,949 4=48,914 (0.63 / 0.76 / 0.58); 5; 2024-11-01 to 2024-12-26 | down 61,931 before 108,422, 10%, invalidation 2025-01-20 |
|  | 2 | zigzag up, fit 0.78: 0=24,853 A=73,949 B=52,500 C=108,422; after | down 56,776 before 108,422, 5%, invalidation 2025-01-20 | zigzag up, fit 0.60: 0=24,853 A=73,949 B=52,500 C=108,422 (0.64 / 0.68 / 0.49); after; 2025-04-12 to 2026-03-25 | down 56,776 before 108,422, 20%, invalidation 2025-01-20 |
|  | 3 | impulse up, fit 0.76: 0=15,440 1=73,949 2=48,914; 3 | up 143,582 before 48,914, 9%, neither 2025-05-01 | impulse up, fit 0.39: 0=15,440 (0.35 / 0.35 / 0.48); 1; none | down 72,903 before 108,422, 29%, invalidation 2025-01-20 |
| 2025-07-01, 107,081 | 1 | impulse up, fit 0.83: 0=15,440 1=31,062 2=24,201 3=73,949 4=48,914; 5 | down 63,704 before 111,968, 0%, invalidation 2025-07-09 | impulse up, fit 0.62: 0=15,440 1=31,062 2=24,201 3=73,949 4=48,914 (0.62 / 0.67 / 0.58); 5; 2024-11-01 to 2024-12-26 | down 63,704 before 111,968, 0%, invalidation 2025-07-09 |
|  | 2 | impulse up, fit 0.79: 0=15,440 1=25,296 2=19,535 3=108,422; 4 | down 63,978 before 120,362, 0%, invalidation 2025-07-14 | zigzag up, fit 0.59: 0=15,440 A=73,949 B=48,914 (0.55 / 0.56 / 0.66); C; 2025-05-27 to 2025-11-26 | down 52,314 before 111,968, 0%, invalidation 2025-07-09 |
|  | 3 | impulse up, fit 0.78: 0=38,532 1=73,949 2=52,500 3=108,422 4=74,456 5=111,968; after | up 216,945 before 38,532, 0%, neither 2025-10-29 | impulse up, fit 0.50: 0=15,440 1=73,949 2=48,914 (0.40 / 0.52 / 0.61); 3; 2025-11-26 to 2027-07-10 | up 143,582 before 48,914, 51%, open |
| 2026-01-01, 87,595 | 1 | zigzag up, fit 0.81: 0=15,440 A=73,949 B=48,914 C=126,150; after | down 57,731 before 126,150, 3%, neither 2026-05-01 | zigzag up, fit 0.66: 0=15,440 A=73,949 B=48,914 C=126,150 (0.66 / 0.65 / 0.66); after; 2026-06-26 to 2028-08-21 | down 57,731 before 126,150, 41%, open |
|  | 2 | impulse up, fit 0.80: 0=16,353 1=31,062 2=24,201 3=73,949 4=48,914; 5 | down 71,252 before 126,150, 29%, target 2026-02-05 | zigzag up, fit 0.60: 0=15,440 A=73,949 B=48,914 (0.51 / 0.63 / 0.66); C; 2025-05-27 to 2025-11-26 | down 57,731 before 126,150, 3%, neither 2026-05-01 |
|  | 3 | impulse up, fit 0.78: 0=24,201 1=73,949 2=48,914 3=126,150; 4 | up 111,352 before 73,949, 21%, invalidation 2026-02-03 | impulse up, fit 0.58: 0=24,201 1=73,949 2=48,914 3=126,150 (0.63 / 0.65 / 0.49); 4; 2026-01-21 to 2026-12-08 | up 111,352 before 73,949, 41%, invalidation 2026-02-03 |
| 2026-07-01, 58,604 | 1 | zigzag up, fit 0.81: 0=15,440 A=73,949 B=48,914 C=126,150; after | down 15,440 before 126,150, 0%, neither 2026-10-29 | zigzag up, fit 0.66: 0=15,440 A=73,949 B=48,914 C=126,150 (0.66 / 0.65 / 0.66); after; 2026-06-26 to 2028-08-21 | down 15,440 before 126,150, 5%, open |
|  | 2 | impulse down, fit 0.78: 0=126,150 1=101,046 2=116,373 3=59,888 4=82,811; 5 | up 85,569 before 58,043, 2%, invalidation 2026-07-01 | zigzag up, fit 0.58: 0=15,440 A=73,949 B=48,914 (0.51 / 0.57 / 0.66); C; 2025-05-27 to 2025-11-26 | down 15,440 before 126,150, 0%, neither 2026-10-29 |
|  | 3 | zigzag up, fit 0.77: 0=15,440 A=73,949 B=48,914; C | down 15,440 before 126,150, 0%, neither 2026-10-29 | combination up, fit 0.56: 0=48,914 W=109,952 X=74,456 Y=126,150 (0.61 / 0.60 / 0.49); after; 2026-01-21 to 2026-12-08 | down 48,914 before 126,150, 55%, open |

What I read in it, and nothing stronger:

- **The top count is the same on all 8 dates.** Time does not rewrite history at the top, because those counts mostly pass time. It changes what sits below them: ranks 2 and 3 are mostly different.
- **The bad readings do leave.** On 2026-07-01, r1's second count was "impulse down, in W5", with the same 4-day W1 and W2 of nearly 4 x it that you doubted. r2 drops it, and "zigzag up, in C" takes that seat.
- **Today's top is the bigger change.** r1 led today with the impulse down, which arose after the last replay date. r2 leads with the zigzag up, which r1 also led with on 2026-01-01 and 2026-07-01.
- **It still does not know the big turns in advance.** On 2025-07-01 r2's top is W5 up, already well past its window (2.30 x W1 against a limit of 1). Price made new highs, so the book's "extended fifth" exception happened. A running wave past its window loses credit but stays on the board, which turned out right here, and that is one case.
- **A past window is common.** Several rows have a running wave whose window has already closed, including the top rows of 2025-01-01 and 2025-07-01. Either waves run long on BTC or these labels are wrong; a replay of 8 dates cannot say which.

## Against random paths

The same check as r1, repeated: 20 sign-flipped paths (Bybit's own 15m bars with random directions, keeping volatility and removing direction), now at two dates. It is a rough check: two dates, 20 paths, and it removes BTC's slow trend, which the research found matters. I also chose the time bands while looking at BTC, so BTC has a home advantage here.

| 2026-10-30 | BTC | Random, median | Random, range | BTC's percentile |
|---|---|---|---|---|
| Top root fit | 0.657 | 0.584 | 0.494 to 0.669 | 95% |
| Top root's time axis | 0.648 | 0.626 | 0.506 to 0.759 | 75% |
| Best time axis of any state | 0.689 | 0.685 | 0.585 to 0.763 | 50% |
| Median time axis of states | 0.462 | 0.200 | 0.200 to 0.533 | 80% |
| Labelled states failing a time check | 15.7% | 21.2% | 5.6% to 38.9% | 30% |
| Legal readings | 411 | 385 | 117 to 832 | 60% |
| Other/unclear share | 90% | 92% | 89% to 95% | 10% |
| Mean time axis, 4H / 1H / 15m | 0.47 / 0.49 / 0.50 | 0.44 / 0.52 / 0.49 | | 60% / 40% / 70% |

| 2025-01-01 | BTC | Random, median | Random, range | BTC's percentile |
|---|---|---|---|---|
| Top root fit | 0.652 | 0.588 | 0.496 to 0.631 | 100% |
| Top root's time axis | 0.755 | 0.585 | 0.502 to 0.759 | 95% |
| Best time axis of any state | 0.755 | 0.674 | 0.542 to 0.759 | 95% |
| Median time axis of states | 0.519 | 0.200 | 0.200 to 0.585 | 90% |
| Labelled states failing a time check | 2.7% | 20.1% | 6.1% to 47.5% | 0%, below all 20 |
| Legal readings | 212 | 355 | 46 to 1,011 | 15% |
| Other/unclear share | 85% | 92% | 80% to 95% | 15% |
| Mean time axis, 4H / 1H / 15m | 0.55 / 0.48 / 0.50 | 0.47 / 0.48 / 0.43 | | 90% / 50% / 75% |

**Does time separate BTC from random readings any better? Not clearly.**

- Random paths get counts that fit about as well on time. Today BTC's best time axis is exactly at the random median.
- BTC's top fit sits at the top of the random range on both dates, as it did in r1 (0.823 against a range of 0.771 to 0.829). So time did not add the separation.
- The one striking number is 2.7% at 2025-01-01, below all 20 paths. But on today's date BTC is at the 30th percentile on the same measure. With one good date out of two, and a measure I invented, I read nothing into it. To make it mean something it would need many dates and a null that keeps the trend.
- **Time here changes which counts a NewWave trader would accept. Nothing shows it improves a forecast.**

## Honest limits

- **Fit is not validated as anything.** r1's limit stands, and r2 adds more hand-set numbers (bands, veto cap, evidence). The items added nothing over volatility in the research.
- **Tuned on what I was looking at.** The A-C tightening (`ac_fade`) came after I saw a 4H C of 2.29 x A pass, and `past_end` after I saw the A at 64,936. Both look right to me and both are in-sample. The 1d.1 and 1d.3 outcomes were also the stated goal, so they prove nothing about the method.
- **Only the mechanical pivots can be labelled.** A pivot you would draw can still be missing at every threshold.
- **Time windows can be very wide.** 1d.1's is 26 months. At root degree the box says little about when.
- **Crosshairs are a grid.** They are every remaining price level against every remaining time level. A point on a grid is not a prediction, and with this many levels some will always sit near something.
- **The "wave it corrects" at the root is my guess:** the opposite extreme of the prior 1,500 days. A different guess changes `whole_time`. Bybit's history starts in March 2020.
- **Partnering is weak on real data.** It thins the list and rarely changes what you see. It also does not do the book's second step, joining the connector into a larger wave.
- **"Retraced" means all the way back to the wave's start,** which is my reading of the book.
- **Shape is only partly captured.** "Weird" as a person's eye sees it (C's big inner rally, for one) is judged only through sub-waves and speed.
- **Exact time stops at 15m.** The 15m frame's own resolution is one bar.
- **The tree is mostly corrective now.** Partly that is what time says, and partly the scoring: a five has more legs to fail. A real impulse with one odd leg can now fall below a three that had less to prove.
- **No forward log.** As in r1, nothing stores these trees, so none of this can be scored later.

## Checks

- `uv run pytest -q`: 204 pass (166 before this round), no network, no real data. New tests cover: the three axes and the geometric mean, a failure not being bought back, the veto, little evidence not outranking much, exact time and its tolerance, every time item on its pass and fail side, both r1 cases by number, every wave's window, crosshairs, horizons, partnering (including that it can remove a higher-fit reading), nesting and STR-C8, and that cutting the data gives the same tree with its windows.
- `node tools/shots_counts.mjs` from `tools/`: 17 views, with console errors and failed requests checked; I looked at each image. It covers 1D root and 1d.2, 1d.3, 4H, 1H, 15m nested, 12H, cycles together, phone, reasons collapsed and expanded, turning Counts on (the best count draws without a click), switching timeframe (follows the chosen branch), no private file (no toggle), and the public host (the private file is never requested).
- **Bugs this found in r1's page, fixed:** the level tags could bounce forever on a short phone pane and hang the page; a zoom could run before the panel narrowed the chart, cutting off the count's start; the address bar did not follow an automatic pick.
