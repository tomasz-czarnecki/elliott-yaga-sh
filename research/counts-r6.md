# Top-down count board, round 6: predictions

What this is: your request for a predictive mechanism, built as you decided, deterministic code with no LLM at run time. Every kept count now says where it should go next, wave by wave, in price and time. Package `src/ewave/counts/`, config `rules/counts.yaml` (version `counts-r6.0`), private chart panel `site/counts.js`. Nothing here is committed or public.

**Read this first.**

- **It does not beat the volatility null.** I ran the engine causally at 67 dates and scored 883 predictions (839 resolved). On 1H the running wave's target was reached 28.6% of the time against 28.2% by a random walk at that day's volatility. On 4H it was 35.0% against 30.5%, and that gap's 95% interval runs from -7.1 to +16.6 points. Forecasts that use what the count knew so far score no better than the null on Brier. So treat the paths as a planning tool, not as a measured edge.
- **There is one lead, and it is not proven.** Among 4H and 1H targets, higher-fit counts beat the null and lower-fit ones did not: +12.9 points against -7.6 on the same dates as the random paths. That gap of 20.6 is above all 12 random paths (their range is -18.7 to +7.5). I tried four such splits, the dates overlap, and the fit's time bands were chosen while looking at BTC, so BTC has a home advantage. The forward log will test it on bars no one has looked at.
- **The chart now shows what you drew.** 1d.1: Y down from 87,384 through A 50,970 and B 71,121 to C 41,484 by 2027-01-22, inside a box of 34,796 to 55,141. "After Y" is a faint dashed line to 82,486 and never a filled box. A count falling into its zone now leads with its own target, not with the move after it.
- **Your X point holds up, and part of it was a gap in r4.** X of 1d.1 passed as a flat, but its B (82,811 to 57,756) reads better as a 5 by 0.18. It is a legal 3 at 12 of 20 swing sizes, the first of them at 4H k5. As a Z that same fall already dies in r4 (impulse 0.62 against flat 0.40). As a B one level down it passed, because r4 does not look inside a 3's legs. Now X says: "X 3, fair as a combination; the flat on the chart is weak". The other legal reading, W=76,054 X=64,936 Y=87,384, grades 0.46.
- **The nearest output.** 1H: up to 83,124, invalid below 76,232, R:R 4.2, null 20%, on a magnet of 7 counts at 83,041. 15m: up to 78,386, invalid below 77,026, R:R 1.5, null 40%, on a magnet of one count. Those figures are as of 2026-10-31 16:15 UTC, close 77,563.

## How to use it

```bash
uv run ewave-counts report --root 1d --brief   # each node with path, clarity and cycles; magnets at the top
uv run ewave-counts export                     # counts.json, plus the forward log and events
uv run ewave-counts events --new               # unseen events, one line each, and marks them seen
uv run ewave-counts score                      # the forward log against what happened and against the null
uv run ewave-counts backtest [--no-minutes] [--paths 12 --workers 2] [--out DIR]   # this report's replay
```

On the chart, choosing a count still moves nothing. A new button, **Fit path**, fits the time and price of the chosen count's whole path, once. In the popover, hover or tap a Clarity line to draw that wave's inside: the labelling on the chart in full, a weak leg in red, a clearer labelling dashed.

New files, all gitignored: `data/counts/forward.jsonl`, `events.jsonl`, `events.seen`, `state.json`.

## Projected path

For every kept node, in `project.py`:

1. **The running wave.** A box in price (its zone) and time (its window), and a most likely point inside the box.
2. **What is left of its structure,** each leg from `describe` run on the count with the wave before it closed at that point. So a projected W4 is pulled from the projected W3, and a level a hard rule forbids is not used.
3. **One step after it,** faint, labelled "after Y", outline only. Nothing past that (sec 0: project 1 structure ahead).
4. **The running wave's own inside,** from the pattern its grammar allows, landing on the running wave's point. A printed first leg, or one that has gone further than the template, stays as printed. The rest of the window is shared out from now.

Below the root, a child that closes the parent's wave projects the parent's next wave.

### Ratio tables

IDs are sections of the NewWave complete reference; the numbers are in `rules/counts.yaml`.

| Wave | Levels, as in r4 | Most likely | Source | Time levels | Most likely | Source |
|---|---|---|---|---|---|---|
| W2 | 0.382, 0.5, 0.618 of W1 | 0.618 | IMP-F1, EMP B2 | 0.25, 0.33, 0.618, 1 x W1 | 0.618 | IMP-T3, FIB-T3 |
| W3 | 1.618, 2.618, pull 0-1-2 | 1.618 | IMP-F4 | 1, 1.618, 2.236 x W1 | 1.618 | IMP-T1 |
| W4 | 0.236, 0.382, 0.5 of W3 | 0.382 | IMP-F2 | 0.25, 0.33, 0.618, 1 x W3 | 0.33 | IMP-T4, FIB-T4, EMP B3 |
| W5 | add-one row; 0.618, 1, pull 0-1-4 | 1.0 | IMP-F5, F6, F7 | 0.618, 1 x W1 | 1.0 | IMP-T2, T5 |
| Zigzag B | 0.382 to 0.786 of A | 0.618 | ZZ-G3 | 0.25 to 4 x A | 1.0 | FIB-T5 |
| Zigzag C | 0.618, 1, 1.236, 1.618 of A | 1.0 | ZZ-G1, G2 | 0.618, 1 x A | 1.0 | COR-4 |
| Flat B | 0.786, 1, 1.236, 1.382 of A | 0.786 | FLAT-G1, G5 | 0.25 to 4 x A | 1.0 | FIB-T5 |
| Flat C | 0.618, 1, 1.618, 2.236 of A | 1.0 | FLAT-G1, G3 | 0.618, 1 x A | 1.0 | COR-4 |
| X | 0.5, 0.618, 0.786 of W | 0.618 | CPX-G5 | 0.25 to 4 x W | 1.0 | CPX-G6 |
| Y | 0.618, 1, 1.236 of W | 1.0 | CPX-G1, G3 | 0.618, 1 x W | 1.0 | CPX-G3 |
| Z | 1, 1.236, 1.382 of W | 1.236 | CPX-G4 | as Y | 1.0 | CPX-G3 |
| Triangle B, C, D; E | 0.786; 0.618 of B-C-D | those | TRI-G2, R10 | none in the book | ours | |
| After a five | 0.5, 0.618 of 0-5 | 0.5 | IMP-F3, sec 4 | 0.25 to 1 x the five | 0.618 | ours |
| After a correction | 0.618, 1 of 0-end | 0.618 | ours | 0.25 to 1 x the whole | 0.618 | ours |

**Why these points.** The book names no frequencies, so a "most likely" is the book's typical number. The research says none of these levels is special (EMP B2: every window hits at random-path rates), and on 4H and 1H a leg reaches 1.0 of itself about half the time (RECOMMENDATION). So 1.0 is near a median for a pull of that form, and that is all it is.

Inside a running wave, sizes against its first leg, time against its first leg:

| Pattern | Sizes | Time | Source |
|---|---|---|---|
| Zigzag | 1, -0.618, 1 | 1, 1, 1 | ZZ-G1, G3, COR-4, FIB-T5 |
| Flat | 1, -0.618, 1 | 1, 1, 1 | FLAT-G1, G5, COR-4, FIB-T5 |
| Combination | 1, -0.618, 1 | 1, 1, 1 | CPX-G1, G3, G5, G6 |
| Triangle | 1, -0.786, 0.618, -0.486, 0.3 | all 1 | TRI-G2; the time is ours |
| Impulse | 1, -0.618, 1.618, -0.618, 1 | 1, 0.618, 1.618, 0.53, 1 | IMP-F1, F2, F4, F6, IMP-T1, T3, T4, T5 |
| Diagonal | 1, -0.786, 0.786, -0.618, 0.618 | 1, 0.618, 1, 0.5, 1 | sec 2 G K, DIAG-G3; the split is ours |

A flat's inner B uses the shallow BTC value (FLAT-G5). My first version used 0.786, which sent A almost all the way to the target and B nearly back to X.

Which pattern: the child's, when the child ends inside this box. Otherwise the first the grammar allows, and a W4 is a flat (sec 1 G). So Y of 1d.1 draws as a flat, because the 4H child ends far short.

## Nested targets and magnets

A child's level is judged against its parent's box, from the parent's start to the box's far edge:

| Status | Meaning | Weight |
|---|---|---|
| Inside | In the box | 1 |
| On the way | Short of the box, and the child has more legs after it | 1 |
| Short | Short of the box, and this level would end the child's whole structure | falls with distance, floor 0.25 |
| Beyond | Past the far edge or behind the start | same |
| Late | Lands after the parent's window | same |

Nothing is deleted. It ranks lower, draws dimmer, and weighs less in a magnet. The move after a structure has no "short": no rule says how far it must go.

Today this says something real: **the 4H Y of 1d.1.1 (75,812) cannot be the whole 1D Y**, which needs at least 55,141 (CPX-R6). It gets status short, weight 0.65. So if 1d.1 is right, 4H's combination is at most a first part of it.

**Magnets** (`confluence.py`). Levels from all frames and all three roots merge when within 2 x 0.25 x 1D ATR of the cluster's first level, a fixed width so that a run of near levels cannot chain across a range. Today that is 1.3%. Weight is the sum of the fits of the distinct readings, each times its parent's weight. The same 15m count under three roots counts once. Levels of a move-after weigh half.

Today's top: 83,041 (+7.1%, 7 counts, all frames), 87,384 (+12.7%, 6), 75,823 (-2.2%, 4), 126,150 (+62.6%, 3).

**Being on a magnet is not shown to help.** On 4H and 1H, a target on a magnet of 3 or more counts has lift +0.8 against +3.9 without, on all dates. On the 38 dates of the random paths it is +6.5 against -2.3. The sign changes with the sample, and on the paths the gap averages -2.5, range -21.8 to +7.6.

## Inside clarity

`clarity.py`, on r4's ladder, for each finished wave:

- **Rungs:** thresholds and frames where the wave itself is a swing, down to where it is too fine to label.
- **Share:** rungs holding a legal labelling of the required form.
- **Margin:** that share minus the opposite form's, and the gap in fit between the two.

A 3 must show its break, so a rung reading one straight leg counts against it (sec 0, velocity test). A 5 may hide its corrections (sec 0), so a straight leg says nothing about it. A legal 3 exists on nearly every rung that holds a 5, so a 5's grade does not use the rung margin. Both take the fit gap: a tie costs nothing (sec 0, hold both), and the other form better by 0.1 halves the grade.

The wave's clarity is the lower of its own grade and its weakest leg, one level down, on the clearest labelling its grammar allows (FND-8: for a 5, only its largest motive wave). It gets the benefit of the doubt, and the panel says when the labelling on the chart is not that one. Words: clear 0.6, fair 0.3, weak 0.15.

Below 0.3 a count loses rank (item `clarity`, structure axis, weight 1.5, penalty only) and its boxes widen, up to 2 x at zero. **It never kills.**

### X of 1d.1, before and after

| | Before (r4) | Now |
|---|---|---|
| Panel | "X 3 ok (4H)" | "X 3, fair as a combination; the flat on the chart is weak: B at 12 of 20 swing sizes, and reads better as a 5 by 0.18" |
| Grade | none: pass | 0.47 |
| Flat A, 82,811 | passed unasked | 0.50: a 3 at 14 of 14 sizes, and a 5 at all 14 too |
| Flat B, 57,756 | passed unasked | **0.15**: 1 leg at k16 to k12, 3 legs at k10 to k6 (59,081, 67,276, 57,756) that are no legal 3 because C is 0.40 of A, under the 0.618 rule; first legal at k5 with 7 legs; a 5 fits better by 0.18 |
| Flat C, 87,384, your five | passed unasked | 0.87 |
| Combination W=76,054 X=64,936 Y=87,384 | not shown | 0.46: W 0.50, X 0.46, Y 1.00 |

**One correction to the brief's note.** "B found only at k=5, the finest step" holds for `best`'s score on the old list of thresholds. On r4's wider ladder B is legal at 12 of 20 rungs. So the panel says "12 of 20", not "only at the finest". What makes it weak is that nothing coarser shows a legal 3, and that it fits better as a 5.

Root 1's fit does not move: its weakest wave is 0.47 after the rescue. With no rescue it would be 0.15.

### Your gold entries

| 4H five, W | Clarity | Why |
|---|---|---|
| W1 | 0.39, fair | 5 at 11 of 22 sizes, first at 4H k2.5 |
| W2, to 62,240 | 0.32, fair | its C holds a 5 at 8 of 25 |
| W3, to 82,277 / 81,500 | 0.80 / 0.62, clear | |
| W4, from 82,277 | 0.31, fair | the X of its combination |
| W4, from 81,500 | 0.38, fair as a combination | the flat on the chart is very weak: its C holds no 5 at any size |
| W5 | 0.52, fair | |

With 2 at 62,505: W2 0.79 as a combination, W3 0.48. Your 4H five costs nothing and ranks first of 51, as before.

| 1D macro, across your pivot pairs | Clarity | Why |
|---|---|---|
| W1, to 31,844 / 31,062 | 0.93 / 0.53 | |
| W2 | 0.00 to 0.49, by pivot pair | to 24,201 from 31,062 has a B with no legal form; from 31,844 it is 0.49 |
| W3 | 0.31 to 0.32 | reads better as a 3 by about 0.1 |
| W4 | 0.30 | |
| W5 | **0.11, very weak** | a 5 at 4 of 19 sizes, reads better as a 3 by 0.15 |

Your macro W5 is the weakest wave on the board. It is your premise, so nothing changes, and it still ranks 27 of 557 as before. I am telling you because it is the same kind of doubt you raised about X.

**Set with your counts in view.** The word thresholds and `ok` (0.3) came after I saw X and your five. At my first 0.35, your W2 and W4 would have cost a little rank.

## Events

`events.py`, compared at each export with the state the last one left. Kinds: top count changed, invalidation crossed, box or top-3 magnet entered, window opened or closed. The first run and any rules change start a baseline, because an engine change is not a market event. A second export on the same bar does nothing. Default root only, since 12H is the same picture.

**How N was chosen: top counts at every 15 minutes for the last 4.01 days, causal, 385 exports, 1m bars off.** Each cell is confirmed changes, then how many went straight back to the top count before:

| Frame | N=1 | N=2 | N=3 | N=4 | N=6 | N=8 | N=12 | N=16 | **Chosen** |
|---|---|---|---|---|---|---|---|---|---|
| 15m | 32, 5 | 29, 4 | 23, 3 | **20, 1** | 19, 1 | 16, 0 | 10, 0 | 5, 0 | **4**, one hour: the knee, about 5 a day |
| 1H | 6, 1 | 6, 1 | 6, 1 | **6, 1** | 6, 1 | 6, 1 | 6, 1 | 4, 1 | **4**, one 1H bar: no cost |
| 4H | 1, 0 | 1, 0 | 1, 0 | 1, 0 | 1, 0 | **1, 0** | 1, 0 | 1, 0 | **8**, two hours |
| 1D, 12H | 1, 0 | 1, 0 | 1, 0 | 1, 0 | 1, 0 | **1, 0** | 1, 0 | 1, 0 | **8**, two hours |

The 4H and 1D values rest on one change in four days, so they are judgement, not measurement. Over those days the board wrote, at N=2 on 15m, 59 messages: 37 top changes, 13 invalidations, 8 windows, 1 box entered. At N=4 that is about 12 a day. **A message volume for Lily: mostly 15m.**

## Forward log and score

`forward.py`. Each export appends what is new, keyed by a hash of engine version, reading, wave, kind, direction, target, stop and window. So a prediction counts once however long it stands. Each line has the as-of time, count, target, invalidation, window and the null odds at that moment. Kinds: `leg` (the running wave to its nearest level ahead), `likely` (to the path's point), `next` (the wave after it).

Resolving reads only 15m bars opening at or after the as-of time. A bar holding both levels goes to the invalidation. A row stays open until its horizon has passed, and open rows are left out, so short horizons resolve first.

**The engine has no probability of its own.** So its forecast is the null's log odds, moved walk-forward by how far that group has beaten the null, on rows already resolved when the forecast was made. With no edge it stays near the null.

## Replay against the null

`ewave-counts backtest`: weekly from 2025-10-13 on the premise root, plus the r2 and r3 dates (before the top the premise does not apply and the root is searched). 67 dates, 883 predictions, 839 resolved, 44 open. Data cut at each date. It took about 7 minutes on one core. A check on this replay: the premise itself is hindsight, you drew it in October 2026, so this measures what a reader with your assumption sees.

**All dates, 1m on, as the live engine runs.** Lift is hit rate minus the null, in points; the interval resamples whole dates.

| Frame, kind | n | Hit | Null | Lift | 95% | Brier null / engine | Log loss null / engine | In window / null |
|---|---|---|---|---|---|---|---|---|
| 4H leg | 80 | 35.0% | 30.5% | +4.5 | -7.1, +16.6 | 0.2343 / 0.2367 | 0.7411 / 0.7451 | 27% / 22% |
| 1H leg | 112 | 28.6% | 28.2% | +0.3 | -7.8, +9.2 | 0.1823 / 0.1836 | 0.5474 / 0.5516 | 20% / 15% |
| 15m leg | 103 | 21.4% | 22.5% | -1.2 | -8.7, +7.1 | 0.1488 / 0.1498 | 0.4599 / 0.4628 | 14% / 14% |
| 1D leg | 33 | 33.3% | 26.9% | +6.5 | -11.7, +24.8 | 0.1918 / 0.1947 | 0.5726 / 0.5775 | 22% / 19% |
| All leg | 328 | 28.4% | 26.8% | +1.5 | -4.3, +7.2 | 0.1854 / 0.1879 | 0.5697 / 0.5729 | 20% / 17% |
| 4H likely | 34 | 44.1% | 33.0% | +11.1 | -5.3, +28.8 | 0.2966 / 0.2978 | 0.9734 / 0.9734 | 31% / 22% |
| 1H likely | 49 | 28.6% | 18.9% | +9.6 | -1.1, +21.0 | 0.1678 / 0.1667 | 0.5486 / 0.5437 | 16% / 12% |
| All likely | 129 | 31.8% | 24.7% | +7.1 | -0.0, +14.4 | 0.1961 / 0.1960 | 0.6527 / 0.6462 | 18% / 14% |
| 4H next | 93 | 12.9% | 15.5% | -2.6 | -8.4, +3.9 | 0.0960 / 0.0981 | 0.2926 / 0.2977 | |
| 1H next | 133 | 18.8% | 20.5% | -1.7 | -8.2, +5.0 | 0.1210 / 0.1208 | 0.3816 / 0.3818 | |
| All next | 382 | 18.1% | 19.6% | -1.6 | -5.7, +2.7 | 0.1177 / 0.1181 | 0.3654 / 0.3667 | |

**Weekly since the top only:** 4H leg +3.5 (n 62, -9.1 to +16.2), 1H leg +2.3 (n 88, -7.0 to +11.6), all leg +0.6 (n 255, -6.1 to +6.9), all likely +7.4 (n 109, -1.0 to +15.9).

**Plainly: no interval on the main rows excludes 0, and the engine's forecast scores worse than or level with the null on Brier in most rows.** The widest improvement is 1H likely, 0.1678 to 0.1667, on 49 rows.

**The null itself is off where targets are far.** On all leg rows it says 7.7% in its lowest band and 15.4% happened (n 143). BTC's bursts of volatility reach far targets more than a steady walk does. This may explain part of the "likely" lift, because that kind has many far targets. On the random paths the same band says 7.0% and 8.6% happened, which is closer.

| All leg rows, null band | n | Null says | Happened |
|---|---|---|---|
| 0 to 0.2 | 143 | 7.7% | 15.4% |
| 0.2 to 0.4 | 94 | 30.5% | 28.7% |
| 0.4 to 0.6 | 68 | 48.6% | 45.6% |
| 0.6 to 0.8 | 22 | 65.9% | 54.5% |

### Against random paths

12 paths: BTC to the 2026-02-06 low, then each 15m bar's direction flipped at random, premise on (r3's check B). None left the premise. 38 weekly dates, 2026-02-09 to 2026-10-26. 1m bars off on both sides, so BTC is rerun without them. About 12 minutes per path, 2 workers, niced.

| Frame, kind | BTC n | BTC lift | Paths, mean lift | Paths, range | Paths below BTC |
|---|---|---|---|---|---|
| 4H leg | 35 | **+7.5** | -0.5 | -8.9 to +16.8 | 11 of 12 |
| 1H leg | 58 | -0.1 | -0.2 | -8.8 to +12.1 | 7 of 12 |
| 15m leg | 63 | -6.4 | +2.1 | -6.2 to +8.0 | 0 of 12 |
| All leg | 167 | -1.2 | +0.8 | -3.5 to +8.5 | 3 of 12 |
| 4H likely | 18 | +8.3 | -2.0 | -18.1 to +14.8 | 11 of 12 |
| 1H likely | 27 | +9.7 | +4.1 | -3.4 to +21.0 | 10 of 12 |
| All likely | 72 | +3.4 | +1.2 | -7.6 to +12.9 | 8 of 12 |
| 1H next | 82 | +4.7 | -0.6 | -7.5 to +3.9 | 12 of 12 |
| 15m next | 70 | +8.4 | +1.1 | -4.6 to +8.0 | 12 of 12 |
| 4H next | 46 | -5.1 | +1.5 | -8.1 to +7.8 | 2 of 12 |
| All next | 213 | +3.0 | +0.5 | -3.5 to +4.8 | 10 of 12 |

**What I read in it, and nothing stronger.** The pipeline itself is sound: pooled over the paths, 4H and 1H leg rows hit at the null (26.6% against 26.9%, 22.0% against 22.2%). On BTC the 4H rows lean up, the all-frames row leans down, and 15m is below every path on `leg` while above every path on `next`. Rows that disagree like this, one path of BTC, 15 rows and 12 paths, are what noise looks like. It removes BTC's slow trend too, so it is rough.

### Do the board's own marks separate outcomes?

4H and 1H `leg` rows, lift in points:

| Split | BTC, all dates, 1m on: yes / no (gap) | BTC, 38 flip dates, 1m off: yes / no (gap) | Paths: mean gap, range |
|---|---|---|---|
| Fit at or above the median | +7.1 / -3.0 (+10.1) | +12.9 / -7.6 (**+20.6**) | -4.5, -18.7 to +7.5 |
| Clarity 0.3 or more | +2.0 / +2.1 (-0.1) | +4.2 / +2.1 (+2.1) | +1.7, -13.7 to +11.8 |
| Target inside or on the way to the parent's box | +1.1 / +5.0 (-3.9) | +4.3 / -3.7 (+8.0) | 0.0, -23.7 to +17.8 |
| On a magnet of 3 or more | +0.8 / +3.9 (-3.0) | +6.5 / -2.3 (+8.8) | -2.5, -21.8 to +7.6 |

- **Fit is the one lead.** It separates on BTC and not on the paths. Against it: four splits tried, n near 47 a side, overlapping dates, and the fit's time bands were tuned on these months. It is the first thing to check in the forward log.
- **Clarity separates nothing yet.** It orders counts the way you read them; there is no evidence it predicts.
- **The penalty for leaving the parent's box has no support.** Targets outside it did better on all dates and worse on the flip dates. It is the book's logic, not a measured rule.

## Cycles as a second clock

`clock.py`, info only: it never reaches the fit. A wave down agrees when its window overlaps a cycle low window, and conflicts when it does not. A wave up conflicts when it is due to end inside one.

**Your example, 1d.1:** Y window 2026-12-06 to 2027-01-22.

- **4-year: conflicts.** The low was due 2026-10-22 to 10-28 by spacing, 39 days before Y's window opens. With the wider ATH-to-low span, 2026-10-04 to 11-20, it is 16 days.
- **Weekly: agrees.** The low is due 2026-12-16 to 2027-04-21, and the windows overlap.

So if the 4-year low is on time, Y ends too late for it; if Y is right, the cycle low runs a month or more late, or the low is not this cycle's. Tags on 1H and 15m nodes are shown because you asked for each node, but a wave that small is not what makes a cycle low.

## The tree, as of 2026-10-31 16:15 UTC, close 77,563

1. **1d.1 1D, 0.60:** combination in Y. Y down via A 50,970, B 71,121 to C 41,484 (34,796 to 55,141) by 2027-01-22, then after Y up to 82,486. Dies above 87,384.
2. **1d.1.1 4H, 0.59:** combination in Y. Down to 75,812 (75,787 to 80,244) by 11-14, then up to 82,768. Short of the parent's box. Dies above 84,880.
3. **1d.1.1.1 1H, 0.63:** combination finished at 76,232, so 4H Y is over: up to 83,124 (to 87,384) by 11-23. Dies below 76,232.
4. **1d.1.1.1.1 15m, 0.48:** zigzag in C, up to 78,386, then down to 77,055. Window passed. Dies below 77,026.
5. **1d.2 1D, 0.58:** combination finished at 57,756. Up to 93,600 (91,924 to 128,450) by 12-13. Dies below 57,756. Its Y is weak, 0.26.
6. **1d.2.1 4H, 0.59:** your five finished. Next-degree pullback down to 72,570 (69,074 to 72,570) by 11-12.
7. **1d.2.1.1 1H, 0.57:** combination in Y, past every level, so far 76,232, then up to 83,124. Dies above 84,880.
8. **1d.2.1.1.1 15m, 0.64:** combination finished at 76,232: up to 83,124.
9. **1d.3 1D, 0.55:** zigzag in B. B up to 93,600 by 2027-03, C down to 42,853 (26,443 to 57,756) by 2027-12, then up to 83,515. Dies above 126,150.
10. **1d.3.1 4H, 0.54:** zigzag in B. B down to 69,074 by 12-13, C up to 98,701 by 2027-03. Dies below 57,756.
11. **1d.3.1.1 1H, 0.59:** combination in Y, down to 75,445 by 11-14, then up to 82,823.
12. **1d.3.1.1.1 15m, 0.62:** combination finished at 76,232: up to 83,124.

**The crossroads:** 1H and 15m all expect up next, first 83,124 and 77,867, while above 76,232 and 77,026. Below 76,232 kills the 1H "finished" readings and leaves 1H Y running. Above 87,384 kills root 1; below 57,756 kills roots 2 and 3.

## Export timing

| Run | Time |
|---|---|
| r4, cold / warm | 4.3 s / 1.3 s |
| r6, cold | **24.2 s** |
| r6, warm | **1.7 s** |

Well under 60 s, and under the cron's 5 minute timeout. Cold is one run after any change to the rules or to the code that reads waves. Clarity's ladder walk is most of that cost. It covers the top 12 candidates per window. `counts.json` grew from 300 KB to 496 KB.

**A fix you did not ask for:** a locked cache file now makes an export carry on in memory instead of failing. A manual run beside the cron could otherwise have stopped the 15-minute export, and I hit that lock myself while working.

## Decisions, and why

| Decision | Why |
|---|---|
| The running wave's plan leads whenever a level is ahead | Your objection. Rank is unaffected: `tf_move` keeps its old logic |
| New module `forward.py`, not `score.py` | `score.py` already means rulebook fit |
| Inner legs drawn only when due 8 or more bars ahead, 3 sigma away | Smaller is noise on any chart |
| Clarity takes the clearest labelling | A wave is a 3 if any legal 3 reads clearly. The chart's labelling is still shown as what it is |
| Magnets exclude inner legs | They are templates split by ours, not book levels |
| Forward log and events on the 1D root only | 12H repeats it. It would count the same call twice |
| Logs under `data/counts/`, not `.cache/` | The forward log is evidence, not rebuildable. `EWAVE_DATA` moves it with the rest |
| `--as-of` runs log nothing and read no cycles file | A run on cut data is not a moment that happened, and the cycles file is today's |
| Fit path holds its price range until the next Fit or timeframe change | Choosing a count must not move it |
| `tools/shots_counts.mjs` updated | Its checks still expected a click to switch timeframe, which Lily removed today at your request |

## Verified, and assumed

**Verified:** each case below by test; the no-zoom check prints SAME for every click after my UI work (I did not run it before starting); every screenshot looked at; the replay's resolver reads no bar before the as-of time and is unchanged by bars after a row resolves; a clarity grade does not change when the future does; the tree under `export` is the same cold and warm.

**Assumed:** that a most likely point is the book's typical number; every number marked ours in the yaml; the wave grades and word thresholds; that 12 flipped paths are a fair rough control; that the volatility null is a fair yardstick, though it undershoots far targets on BTC; N for 4H and 1D.

## Honest limits

- **Small sample, one path.** 67 overlapping dates over one correction. BTC's own 12-month fall is in every row.
- **Forward log is empty of results.** 18 predictions, 0 resolved as of this report.
- **Fib levels are hit at random-path rates.** Nothing here changes that; magnets count where the board's levels pile up, and that is all.
- **Boxes are wide on purpose.** Y's box is 34,796 to 55,141 and a window of 47 days. A hit there is not a precise forecast. The null is what makes it fair.
- **Inner legs are templates.** "A 50,970, B 71,121" is arithmetic on Y's point, not a level anyone should expect price to respect. Printed swings will change them at the next pivot.
- **A parent's Y can have no live inner reading.** The 4H child is not used as Y's inside when it lands short, so the 1D path and the 4H path disagree on the chart, by design.
- **A first wave has no price.** It takes the parent's level or is drawn as if it ended at its extreme so far, and it says so.
- **Events are only as stable as the top count below 4H:** about 5 a day on 15m, one in twenty going straight back.
- **Flips were read with 1m bars off,** which only touches 15m waves. Reading them per export was too slow.
- **The 12H root gets paths and magnets, but no events or log.**
- **Cold run is 5 times r4's.** Fine for the cron, and it is why the control took about 90 minutes.

## Checks

- `uv run pytest -q`: 364 pass, 6 network tests deselected. New: `tests/test_predictions.py`, 67 tests: a planted zigzag projects C at the stated ratios; what is left of an impulse; Y runs as a 3 and lands on its point; the move after is never the main plan; a child's target outside its parent's box ranks lower and stays; magnets merge, weigh, and do not chain; one reading counts once across roots; a clean 3 grades higher than one found only at the finest step; a straight leg against a 3 and not a 5; clarity cached and causal; a new top needs N exports, a flicker resets it, one bar counts once, new rules are a baseline; invalidation and box fire once; the log dedupes and survives a cut line; nothing before the as-of time counts, a bar with both goes to the invalidation, later bars change nothing, horizons; walk-forward uses only what had resolved; flipped paths keep the past and the sizes; the cycle tags; and the no-zoom rule read off the code.
- `uv run ewave-counts gold`: both entries pass, exit 0. Your 4H five ranks 1 of 51.
- `uv run ewave-data status --check`: exit 0. `export`, `events --new`, `score` run.
- `git check-ignore data/counts/{state.json,events.jsonl,events.seen,forward.jsonl} .cache/counts/...`: all ignored. Nothing new tracked under `site/data/`.
- `node tools/shots_counts_r6.mjs`: all checks pass. `node tools/shots_counts.mjs`: all OK. `node /opt/data/cache/scratch/elliott_nozoom_check.mjs`: SAME for every click, no errors. Screenshots in `/opt/data/cache/scratch/elliott_counts_r6/shots/`.
