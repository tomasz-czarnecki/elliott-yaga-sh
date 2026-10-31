# Top-down count board, round 3: rules kill, time ranks, his premise and his gold count

What this is: round 2 with a new root and a new principle. You gave the macro count as an assumption ("everything before was 5 waves up and now we are in a correction going down") and rejected a 4H node ("it is clearly 5 waves"). Package `src/ewave/counts/`, config `rules/counts.yaml` (version `counts-r3.0`), your premise `rules/premise.yaml`, your counts `gold/counts.yaml`, command `ewave-counts`, private chart panel `site/counts.js`. Nothing here is committed or public.

**Read this first.**

- **Your 4H five is back, and it ranks first.** Unconstrained, your impulse from 57,756 to 87,384 is first of 53 readings that cover that move, with all four of your variants of 2 and 3 found. In the premise tree it shows under all three root readings.
- **The veto was not what lost it.** Lily's guess was reasonable and wrong; the cause is below. The vetoes are gone anyway, because the book says rules eliminate and guidelines rank.
- **The root is now the correction since 126,150.** Nothing before the red line is re-counted. Three readings are kept, one child each down to 15m.
- **Your macro count breaks a rule the book marks R, on your pivots and on Lily's.** W4 took 77 days against a W3 of about 500. The minimum is 25%, about 125 days. W2 on Lily's pivots breaks it too. The brief said the hard rules pass; on price they do, on the time minimum they do not. It is your premise, so it kills nothing and the tree uses it, but the panel says so, and the engine run without the premise cannot keep your exact pivots. Details under Gold.
- **Reading 2 is the one you doubted in r2, under another name.** W=80,608, X=97,963, Y=57,756 is your r2 "C took 3.65 x A" on the same pivots. Without the veto it is back at rank 2, with the lowest time axis of the three (0.47). It is there because it is the only reading that says the correction is over. The brief asked for no caps, so it stays, marked.
- **The ranking is tuned on your count.** Your count ranks first partly because I looked at it while choosing the items. That is what a gold test is for, and it proves nothing about forecasts. On random paths the top root fit is not separated from BTC's (below).

## How to use it

```bash
uv run ewave-counts report --root 1d --brief      # premise, then each node with its legs, window and the 5s inside it
uv run ewave-counts gold                          # your counts against the engine: pass or fail, rank, axis scores
uv run ewave-counts gold --latest                 # the same on today's bars
uv run ewave-counts --no-premise rank --root 1d   # every root searched again, as r2 did
uv run ewave-counts export                        # site/data/local/counts.json for the chart panel (gitignored)
```

To change the premise, edit `rules/premise.yaml`; `active: false` switches it off. To add a count, Lily adds one entry to `gold/counts.yaml`.

On the chart, turning on **Counts** on 1D opens at the top. A red vertical line marks the end of the five, its labels are drawn faintly, and a pinned line at the top of the panel reads "Premise (Tomasz): 5 up ended 126,150 on 2025-10-06; counting the correction since". Below it, the premise's own levels. Choosing a count also draws what its finished waves look like inside, one degree down: a 5 in plain lines, the way to it dotted. The time windows, crosshairs, leg tags, collapsed reasons and Lily's autopick are unchanged.

## The exact cause of r2 losing your count

I measured it on r2's code, snapshot taken before any change.

| Hypothesis | Test | Result |
|---|---|---|
| The veto caps sank it | Vetoes on all four variants of your count | **None.** No axis was capped |
| | r2 with the cap switched off | The same three 1D roots |
| It ranked too low | r2's 4H readings from 57,756, any pattern | r2's first was "impulse in W5", the same pivots with 5 still open (0.602). Finished at 87,384 it was 4th (0.533). Low, not lost |
| **No parent could hold it** | What r2's kept 1D parents let run from 57,756 | **This is it** |

The three kept parents in r2:

- 1d.1, zigzag up finished at 126,150: its child starts at 126,150 and goes down.
- 1d.2, combination in Y: its child starts at 87,384 and goes down.
- 1d.3, combination up in Y from 57,756: the only one going up from the right place. Y may be a flat, triangle or combination (sec 3: Y is always a 3). So an impulse was excluded by grammar, and the best 3 it allowed was your "Combination up finished at 87,384".

The first root that could host an impulse there was rank 8. r2's rule that gives the last seat to the other direction took rank 7 instead, because rank 7 was already running up. So: **a correct grammar rule, applied under a parent that should not have been kept.** No time check was involved.

The finished reading was also low for four reasons of its own, all fixed:

| Reason | Cost in r2 | r3 |
|---|---|---|
| The same pivots with W5 "still running" have fewer items to fail, so they outrank the finished one | Rank 1 went to it | Dropped while the finished twin is alive; it comes back by itself if price passes 87,384 |
| W5 fast: 0.30 x W1 scored 0.14 | Time | 0.6, E5-5 (below) |
| `degree_mix` charged the same fast W5 again: 0.24 | Time | Item removed |
| `tf_move` measured a finished 5 by the wave after next: "60.6% away, wrong frame", scored 0 | Price | A bug. It now measures the wave running now: 6.1% away, passes |

Plus one data fix. A zigzag threshold that shrinks while price waits can confirm a swing long after the next leg's real extreme, and the pivot code then took the confirming bar's low as that leg's start. So at threshold 8 your Aug 14 low, 62,505, was missing: it showed 62,676, two days later. `pivots.py` now takes the extreme since the swing. It reads no later bars, and a test checks this on every leg.

## The premise

`rules/premise.yaml`, version `premise-1.0`, stored with every output. It is your input: `Builder` reads it and the enumerator never sees anything before the top.

| Label | Date | Price | Alternative kept in the file |
|---|---|---|---|
| 0 | 2022-11-21 | 15,440.0 | |
| 1 | 2023-04-14 | 31,061.7 | 2023-07-13, 31,843.9 (Lily's) |
| 2 | 2023-09-11 | 24,853.4 | 2023-08-17, 24,200.9 (Lily's, the Bybit wick) |
| 3 | 2025-01-20 | 109,951.7 | 2024-12-17, 108,421.6 |
| 4 | 2025-04-07 | 74,456.2 | |
| 5 | 2025-10-06 | 126,150.0 | the red line |

All nine prices rechecked against the Bybit 1D bars. **Decision: your pivots are primary**, since it is your count.

On your pivots, log price and time: W2 0.319 of W1 in 150 d (1.04 x); W3 2.13 x W1 in 497 d (3.45 x); W4 0.262 of W3 in 77 d (0.15 x); W5 0.75 x W1 in 182 d (1.26 x).

**How the engine treats its levels.**

| Level | State | What happens |
|---|---|---|
| Between 15,440 and 126,150 | holds | The tree counts the correction |
| Above 126,150 | **review** | Not a kill. A B of an expanded flat, or an extended fifth. Readings that cannot survive it die by their own rules (a zigzag's B, a first leg); a flat or combination whose B or X passed the origin stays. The panel says so in red. **An extended fifth is yours to make by editing the file**: the engine does not re-count before the line |
| Above 204,442 today | **broken** | The flat ceiling (1.618) of the fall so far, sec 3. No corrective reading is left from this top. The tree searches every root again and says why |
| Below 15,440 | **dead** | Sec 0, UNSPOKEN R1, the origin of a finished 5. Same fallback |

A run cut before the red line knows nothing of the premise, and a test checks that. **The premise itself is hindsight:** you drew it in October 2026. So a replay with it says what a reader with your assumption sees, not what could have been known.

**The correction against the five (sec 1 C, FIB-T3, FIB-T5).** Pull 0-5: 0.5 at 70,795 (log 44,133), 0.618 at 57,731 (log 34,445). The low at 57,756 is 25 dollars from the linear 0.618. Time: base 1,050 days, minimum 2026-06-26 (0.25 x), full length 2028-08-21. So far 0.37 x. The low came at 0.255 x, just over the minimum. A reading that calls the correction finished under that minimum is killed, because that is an R.

## What changed

| Change | Basis | Effect |
|---|---|---|
| **No vetoes.** `veto_cap` is gone; a failed check costs its weight | Sec 0, FND-4: "rules eliminate, guidelines rank" | Items are still named as missed in the panel: "ranks lower, kills nothing" |
| **Only R items kill** | The rule list is unchanged | The minimum time stays a kill: FIB-T3 is marked R, and BTC-3 sets it at 1.25 |
| **`degree_mix` removed** | It was ours. The book's own templates catch the case it was for | r1's W1 of 4 d still scores 0 on W2 and W3 |
| **Fast market** | IMP-T1 "1.0 in a fast market", FIB-T1 "a violent move in price is paid for in sideways time", E5-5 a fifth "squeezes up fast", no longer than earlier corrections | At 1.618 x the base's speed or more: a short W3 or W5 keeps part credit (0.6), a W5 only when also shorter than W2 and W4; a W4 after a fast W3 is fine up to 1.618 x, 0 at 2.618 x. W2 gets no such softening: you rejected that case in r2 |
| **`w5_past_w3`** | Sec 1 G: truncation is possible | A truncated fifth used to pay nothing |
| **`past_ceiling`** | Sec 3: a zigzag C that "hits 1.618: double-check impulsive"; Y "ceiling 1.618, past it W3, C or flat more likely" | **The book's test for what you said.** C or Y over 1.618 x on both scales misses. r2's node had Y at 2.3 x. It also makes a zigzag up to 87,384 lose to the five |
| **`leg_form`** | Sec 0 R1, R2: only an impulse's W1 and a zigzag's A start with a 5; 3-or-5 unreadable holds both | Each finished wave is read both ways on finer thresholds. A corrective label on a move that reads clearly as a 5 loses credit; the worst wave sets the item. Also applies to what a running wave has printed: a Y whose first move reads as a 5 is marked |
| **Insides** | Sec 0, 6: verify sub-waves | Every finished wave gets its best labelling, two levels deep, on the chart and in the panel. A motive wave's inside also counts as evidence (`inside_price`, `_time`, `_structure`): without that, "A = a full 5, B running" looks like one bare leg |
| **Triple combination** | Sec 3: W-X-Y-X-Z, second X not beyond the first | New pattern, from its Y on. Marked rare (`triple_rare`, conflict 9 "simple first") |
| **Root seats go to ideas** | "Three shades of one idea are not three counts" | Which move is running, from where, and whether what came before is finished. Other labels for the same move go in a "Same move" line |
| **FIB-T8 groups by origin** | A different origin is a different count, not another pairing | r2 removed your 15,440 macro reading here, in favour of the one from 24,201 |

## Gold

`gold/counts.yaml` holds one entry per count, with your words as the note. Each is checked at its own date, so later bars cannot move the regression. Tests: `tests/test_gold.py`.

**4H, 57,756 to 87,384: PASS.**

```
PASS 4h-impulse-2026-07-to-09: 4h impulse up, as of 2026-10-30 23:45 UTC
 pass enumerate
  found 0=57,756 1=66,938 2=62,505 3=82,277 4=74,920 5=87,384, at threshold 8: fit 0.597 (price 0.70 · time 0.59 · structure 0.52)
  found 0=57,756 1=66,938 2=62,240 3=82,277 4=74,920 5=87,384, at threshold 8: fit 0.590 (price 0.63 · time 0.62 · structure 0.53)
  found 0=57,756 1=66,938 2=62,240 3=81,500 4=74,920 5=87,384, at threshold 5: fit 0.550 (price 0.65 · time 0.59 · structure 0.43)
  found 0=57,756 1=66,938 2=62,505 3=81,500 4=74,920 5=87,384, at threshold 5: fit 0.518 (price 0.63 · time 0.54 · structure 0.41)
 pass rank_first
  rank 1 of 53 readings that start at its 0 and reach its last label
  1. impulse 0=57,756 1=66,938 2=62,505 3=82,277 4=74,920 5=87,384: fit 0.597 (price 0.70 · time 0.59 · structure 0.52)
  2. impulse 0=57,756 1=66,938 2=62,240 3=82,277 4=74,920 5=87,384: fit 0.590 (price 0.63 · time 0.62 · structure 0.53)
  3. impulse 0=57,756 1=66,938 2=62,505 3=87,384 4=80,350 5=84,880: fit 0.581 (price 0.58 · time 0.68 · structure 0.50)
 pass in_tree
  1d.1 combination in Y (0=126,150 W=59,888 X=87,384): shown at 1d.1, inside X, inside C
  1d.2 combination in after (0=126,150 W=80,608 X=97,963 Y=57,756): shown at 1d.2.1, as its own labels
  1d.3 combination in X (0=126,150 W=57,756): shown at 1d.3.1, inside A
```

All four variants are found. The best is your own 2, Aug 14, with 3 on Sep 3: W2 1.17 x W1 (slightly outlasts, 0.77 credit), W3 0.99 x W1, W4 0.59 x W3 after a fast W3, W5 0.30 x W1 on the fast credit. Lily's 2 on Aug 1 is 0.007 behind. It also has real misses, and I left them: no 3-5 divergence (RSI 89 at W5 against 74 at W3, which sec 5 reads as a fifth still extending); RSI 34 at W2; W5 still not back to its start after 6.4 x its own time; and one frame down only 2 and 4 show as labelled (`1- 2+ 3- 4+ 5-`).

**Where it sits in the premise tree:**

| Root | Where your five is |
|---|---|
| 1d.1 combination in Y | Inside X, a flat: A 82,811, B 57,756, C 87,384, and your five is that C |
| 1d.2 combination finished at 57,756 | The 4H child itself: W1 of whatever starts there, or an A |
| 1d.3 combination in X (or flat or triangle in B) | The 4H child is a zigzag up in B, and your five is its A |

**What would have no room:** a root calling that whole move one corrective wave. "Zigzag, A=57,756, B=87,384" is the example; a B may not be a 5. It ranks 18th of 39, with `leg_form` at 0: "B reads as a 5 (0.58 against 0.43)". Note that 1d.2's and 1d.3's next steps differ only in what your five starts: a new move, or a bounce.

**1D, the macro count, without the premise: PASS, on a narrower reading than you might assume.**

```
PASS 1d-impulse-2022-to-2025: 1d impulse up, as of 2026-10-30 23:45 UTC
 pass kept
  kept among 466 legal root readings: 1 with the same 0 and 5. Best at rank 19: 0=15,440 1=73,949 2=48,914 3=109,952 4=74,456 5=126,150: fit 0.528 (price 0.46 · time 0.58 · structure 0.55)
  his exact pivots are not on the board. Each variant against the hard rules:
    0=15,440 1=31,062 2=24,853 3=109,952 4=74,456 5=126,150: I6_w4_under_min_time
    0=15,440 1=31,062 2=24,201 3=109,952 4=74,456 5=126,150: I6_w4_under_min_time
    0=15,440 1=31,844 2=24,853 3=109,952 4=74,456 5=126,150: I6_w4_under_min_time
    0=15,440 1=31,844 2=24,201 3=109,952 4=74,456 5=126,150: I5_w2_under_min_time, I6_w4_under_min_time
```

So the engine keeps a five from 15,440 to 126,150 with your 3 and your 4, at rank 19, but with 1 at 73,949 and 2 at 48,914. **Your 1 and 2 cannot be on the board with your 3 and 4.** That is the R minimum at work: W4's 77 days fits a W3 of at most about 308 days, so one that starts in 2023 cannot pass. The engine's own reading starts W3 in August 2024. The book's reading of this is "unfinished, or a lower degree than labelled" (IMP-T3/T4 degree check).

**Decision: I did not soften the rule to make your exact pivots pass.** The brief says only R items kill, and this one is marked R. The check therefore passes on the 0 and the 5, and prints what stops the exact pivots. A test holds that claim true, so it cannot quietly drift. If you think W4 at that degree should be exempt, that is a rule change for you to make, in one number.

## The current tree

As of 2026-10-31 00:15 UTC, Bybit perp, rules `counts-r3.0`, close 77,285. Root: 39 legal readings in 26 states; other/unclear 85% of fit.

```
Premise (Tomasz): 5 up ended 126,150 on 2025-10-06; counting the correction since. Holds.
1D [1d.1] Combination down, in Y. W=59,888 X=87,384. Fit 0.60 (price 0.51 · time 0.61 · structure 0.69). Due 2026-12-06 to 2027-01-22, zone 34,796 to 55,141. Dies above 87,384.
   Inside X: flat, A 82,811, B 57,756, C 87,384, and C is your five.
   4H  Combination down, in Y. W=80,350 X=84,880. Fit 0.58 (0.58 · 0.51 · 0.66). Due 2026-11-01 to 2026-11-07.
   1H  Combination down, in Y. W=79,175 X=81,967. Fit 0.58 (0.57 · 0.51 · 0.69). Due 2026-10-31 to 2026-11-01.
   15m Flat down, in C. A=76,455 B=78,072. Fit 0.47 (0.36 · 0.51 · 0.57).
1D [1d.2] Combination down finished at 57,756, next move up. W=80,608 X=97,963 Y=57,756. Fit 0.57 (0.63 · 0.47 · 0.63). Y took 3.65 x W: missed. Dies below 57,756.
   4H  Impulse up finished at 87,384: your five. Fit 0.59 (0.68 · 0.59 · 0.52). Next move down, zone 69,074 to 72,570, due 2026-10-12 to 2026-12-13. Dies above 87,384 or below 57,756.
   1H  Combination down, in Y. W=79,750 X=84,880. Fit 0.57 (0.48 · 0.56 · 0.69). Due 2026-11-05 to 2026-11-14.
   15m Combination down, in Y. W=79,416 X=81,967. Fit 0.58 (0.57 · 0.51 · 0.69).
1D [1d.3] Combination down, in X (flat or triangle in B read the same so far). W=57,756. Fit 0.56 (0.48 · 0.57 · 0.63). X due 2026-09-05 to 2029-06-04. Dies above 204,442.
   4H  Zigzag up, in B. A=87,384 is your five. Fit 0.54 (0.52 · 0.49 · 0.63). B zone 64,096 to 76,066, then C up, 94.5k to 124.2k.
   1H  Combination down, in Y. W=79,750 X=84,880. Fit 0.59 (0.52 · 0.56 · 0.69).
   15m Combination down, in Y. W=79,416 X=81,967. Fit 0.58 (0.57 · 0.51 · 0.69).
```

**In plain words.**

1. **The correction is a double three still falling.** W to 59,888 in February, X an expanded flat ending in your five, Y running down to 34,796-55,141 by January 2027. Other labels for this same move: flat in C 0.53, triple 0.53, zigzag in C 0.52.
2. **The correction ended at 57,756, on the 0.618 and just past the minimum time.** Your five is the first wave of what comes next, and this is its W2 or B. It is the weakest on time. It is also the only one where a new low kills the count.
3. **The fall to 57,756 was the first leg, and the middle leg is still going up.** Your five is its A, this is its B, and a C up above 87,384 is ahead, before the correction's last leg down.

The crossroads: at 1H all three expect up next, first 81,576. **At 1D they split on the next level.** Above 87,384 kills 1 and leaves 2 and 3. Below 57,756 kills 2 and 3 and leaves 1. Above 87,384 and below 57,756 are the two levels that matter, and both are far from 77,285.

The 12H root gives the same three readings. Note that all three 1H and 15m chains are combinations falling into the same place. Below 4H the tree says very little that differs between them.

## r2 against r3

| Frame | r2 | r3 |
|---|---|---|
| 1D | Zigzag up finished at 126,150 (0.66); combination down in Y (0.58); combination up in Y (0.54) | Combination down in Y (0.60); combination down finished at 57,756 (0.57); combination down in X (0.56) |
| 4H | Zigzag down in C (0.55); combination down in Y (0.55); **combination up finished at 87,384 (0.47)** | Combination down in Y (0.58); **impulse up finished at 87,384 (0.59)**; zigzag up in B (0.54) |
| 1H | Ending diagonal down in W5 (0.40); combination down in Y (0.56, 0.54) | Combination down in Y (0.58, 0.57, 0.59) |
| 15m | Zigzag down in C (0.50); flat down in C (0.43); combination down in Y (0.56) | Flat down in C (0.47); combination down in Y (0.58, 0.58) |

Fits are not comparable across rounds: the veto is gone and items changed.

**r2's first root is gone by your instruction:** "zigzag up finished at 126,150" is, in your terms, your own five read as a three. Run without the premise, a zigzag up finished at 126,150 still ranks first, now from the origin 48,914. So the premise decides this, not the engine.

**Your r1 doubts, without the premise, without vetoes.** r1's impulse down, W2 at 3.98 x W1, went from 18th in r2 to 14th (0.514, time 0.34). r1's zigzag down, C at 3.65 x A, went from 29th to 10th (0.531, time 0.43). **Removing the caps does lift them,** though they stay below the top of the board. Under the premise the impulse down cannot appear at all; the zigzag is 12th.

## Replay: r2 and r3 side by side

Dates after the red line only, data cut at each date. **No win rate can come from this:** seven dates, overlapping, one root. r3's column has the premise, which is hindsight, as said. Dates in the r3 column are the running wave's window; one in the past means the wave was already past it.

| as of, close | # | r2: count (price / time / structure), running | r2: plan, vol odds, what came first | r3: count (price / time / structure), running, due | r3: plan, vol odds, what came first |
|---|---|---|---|---|---|
| 2025-12-01, 90,309 | 1 | zigzag up, fit 0.66: 0=15,440 A=73,949 B=48,914 C=126,150 (0.66 / 0.65 / 0.66); after | down 57,731 before 126,150, 42%, open | zigzag down, fit 0.57: 0=126,150 A=101,046 B=116,373 (0.58 / 0.56 / 0.57); C; 2025-10-29 to 2025-10-31 | up 106,313 before 80,608, 40%, invalidation 2026-01-31 |
|  | 2 | zigzag up, fit 0.60: 0=15,440 A=73,949 B=48,914 (0.51 / 0.64 / 0.66); C | down 57,731 before 126,150, 9%, neither 2026-03-31 | zigzag down, fit 0.42: 0=126,150 (0.35 / 0.51 / 0.41); A; none | up 100,840 before 80,608, 51%, invalidation 2026-01-31 |
|  | 3 | impulse up, fit 0.58: 0=24,201 1=73,949 2=48,914 3=126,150 (0.63 / 0.65 / 0.49); 4 | up 111,352 before 73,949, 49%, invalidation 2026-02-03 | combination down, fit 0.56: 0=126,150 W=101,046 X=116,373 (0.53 / 0.56 / 0.57); Y; 2025-10-29 to 2025-10-31 | up 106,313 before 80,608, 40%, invalidation 2026-01-31 |
| 2026-01-01, 87,595 | 1 | zigzag up, fit 0.66: 0=15,440 A=73,949 B=48,914 C=126,150 (0.66 / 0.65 / 0.66); after | down 57,731 before 126,150, 41%, open | zigzag down, fit 0.57: 0=126,150 A=101,046 B=116,373 (0.58 / 0.56 / 0.57); C; 2025-10-29 to 2025-10-31 | up 106,313 before 80,608, 25%, invalidation 2026-01-31 |
|  | 2 | zigzag up, fit 0.60: 0=15,440 A=73,949 B=48,914 (0.51 / 0.63 / 0.66); C | down 57,731 before 126,150, 3%, neither 2026-05-01 | zigzag down, fit 0.42: 0=126,150 (0.35 / 0.51 / 0.41); A; none | up 95,649 before 80,608, 48%, target 2026-01-13 |
|  | 3 | impulse up, fit 0.58: 0=24,201 1=73,949 2=48,914 3=126,150 (0.63 / 0.65 / 0.49); 4 | up 111,352 before 73,949, 41%, invalidation 2026-02-03 | combination down, fit 0.56: 0=126,150 W=101,046 X=116,373 (0.53 / 0.56 / 0.57); Y; 2025-10-29 to 2025-10-31 | up 106,313 before 80,608, 25%, invalidation 2026-01-31 |
| 2026-03-01, 66,940 | 1 | zigzag up, fit 0.66: 0=15,440 A=73,949 B=48,914 C=126,150 (0.66 / 0.65 / 0.66); after | down 15,440 before 126,150, 22%, open | zigzag down, fit 0.56: 0=126,150 A=80,608 B=97,963 (0.51 / 0.61 / 0.57); C; 2026-02-12 to 2026-03-01 | up 94,906 before 59,888, 24%, invalidation 2026-06-05 |
|  | 2 | zigzag up, fit 0.59: 0=15,440 A=73,949 B=48,914 (0.51 / 0.61 / 0.66); C | down 57,731 before 126,150, 75%, neither 2026-06-29 | zigzag down, fit 0.53: 0=126,150 A=101,046 B=116,373 (0.46 / 0.56 / 0.57); C; 2025-10-29 to 2025-10-31 | up 94,906 before 59,888, 24%, invalidation 2026-06-05 |
|  | 3 | combination up, fit 0.56: 0=48,914 W=109,952 X=74,456 Y=126,150 (0.61 / 0.60 / 0.49); after | down 48,914 before 126,150, 64%, open | zigzag down, fit 0.42: 0=126,150 (0.35 / 0.51 / 0.41); A; none | up 79,604 before 59,888, 39%, target 2026-05-04 |
| 2026-05-01, 76,301 | 1 | zigzag up, fit 0.66: 0=15,440 A=73,949 B=48,914 C=126,150 (0.66 / 0.65 / 0.66); after | down 15,440 before 126,150, 0%, open | zigzag down, fit 0.54: 0=126,150 A=80,608 B=97,963 (0.51 / 0.53 / 0.57); C; 2026-02-12 to 2026-03-01 | up 94,906 before 59,888, 30%, invalidation 2026-06-05 |
|  | 2 | zigzag up, fit 0.58: 0=15,440 A=73,949 B=48,914 (0.51 / 0.59 / 0.66); C | down 57,731 before 126,150, 18%, neither 2026-08-29 | triple_combination down, fit 0.53: 0=126,150 W=80,608 X=97,963 Y=59,888 (0.50 / 0.57 / 0.52); X2; 2026-02-11 to 2026-05-05 | down 50,772 before 97,963, 0%, neither 2026-06-21 |
|  | 3 | combination up, fit 0.56: 0=48,914 W=109,952 X=74,456 Y=126,150 (0.61 / 0.60 / 0.49); after | down 48,914 before 126,150, 12%, open | zigzag down, fit 0.42: 0=126,150 (0.35 / 0.51 / 0.41); A; none | up 86,919 before 59,888, 53%, invalidation 2026-06-05 |
| 2026-07-01, 58,604 | 1 | zigzag up, fit 0.66: 0=15,440 A=73,949 B=48,914 C=126,150 (0.66 / 0.65 / 0.66); after | down 15,440 before 126,150, 5%, open | combination down, fit 0.54: 0=126,150 W=80,608 X=97,963 (0.45 / 0.51 / 0.69); Y; 2026-02-12 to 2026-03-01 | up 93,778 before 58,043, 1%, invalidation 2026-07-01 |
|  | 2 | zigzag up, fit 0.58: 0=15,440 A=73,949 B=48,914 (0.51 / 0.57 / 0.66); C | down 15,440 before 126,150, 0%, neither 2026-10-29 | flat down, fit 0.54: 0=126,150 A=59,888 B=82,811 (0.41 / 0.57 / 0.67); C; 2026-07-21 to 2026-09-05 | down 52,256 before 82,811, 56%, neither 2026-09-06 |
|  | 3 | combination up, fit 0.56: 0=48,914 W=109,952 X=74,456 Y=126,150 (0.61 / 0.60 / 0.49); after | down 48,914 before 126,150, 55%, open | zigzag down, fit 0.53: 0=126,150 A=101,046 B=116,373 (0.47 / 0.56 / 0.57); C; 2025-10-29 to 2025-10-31 | up 93,778 before 58,043, 1%, invalidation 2026-07-01 |
| 2026-09-22, 86,580 | 1 | zigzag up, fit 0.66: 0=15,440 A=73,949 B=48,914 C=126,150 (0.66 / 0.65 / 0.66); after | down 15,440 before 126,150, 0%, open | combination down, fit 0.57: 0=126,150 W=80,608 X=97,963 Y=57,756 (0.63 / 0.47 / 0.63); after; 2026-09-05 to 2027-03-25 | up 93,600 before 57,756, 79%, open |
|  | 2 | zigzag up, fit 0.57: 0=15,440 A=73,949 B=48,914 (0.51 / 0.55 / 0.66); C | down 57,731 before 126,150, 10%, open | combination down, fit 0.56: 0=126,150 W=57,756 (0.48 / 0.57 / 0.63); X; 2026-09-05 to 2029-06-04 | down 53,920 before 204,442, 54%, open |
|  | 3 | combination up, fit 0.56: 0=48,914 W=109,952 X=74,456 Y=126,150 (0.61 / 0.60 / 0.49); after | down 48,914 before 126,150, 0%, open | zigzag down, fit 0.53: 0=126,150 A=80,608 B=97,963 (0.51 / 0.51 / 0.57); C; 2026-02-12 to 2026-03-01 | up 93,600 before 57,756, 75%, open |
| 2026-10-15, 81,643 | 1 | zigzag up, fit 0.66: 0=15,440 A=73,949 B=48,914 C=126,150 (0.66 / 0.65 / 0.66); after | down 15,440 before 126,150, 0%, open | combination down, fit 0.57: 0=126,150 W=80,608 X=97,963 Y=57,756 (0.63 / 0.47 / 0.63); after; 2026-09-05 to 2027-03-25 | up 93,600 before 57,756, 60%, open |
|  | 2 | zigzag up, fit 0.57: 0=15,440 A=73,949 B=48,914 (0.51 / 0.55 / 0.66); C | down 57,731 before 126,150, 12%, open | combination down, fit 0.56: 0=126,150 W=57,756 (0.48 / 0.57 / 0.63); X; 2026-09-05 to 2029-06-04 | down 53,920 before 204,442, 56%, open |
|  | 3 | combination up, fit 0.56: 0=48,914 W=109,952 X=74,456 Y=126,150 (0.61 / 0.60 / 0.49); after | down 48,914 before 126,150, 0%, open | zigzag down, fit 0.53: 0=126,150 A=80,608 B=97,963 (0.51 / 0.51 / 0.57); C; 2026-02-12 to 2026-03-01 | up 93,600 before 57,756, 54%, open |

What I read in it, and nothing stronger:

- **r2 repeated its old answer; r3 tracks the correction.** r2's top is the same rally read as a zigzag on every date from 2025-12-01. That is what the premise was meant to end.
- **r3's early rows are weak.** On 2025-12-01 and 2026-01-01 its top is "A=101,046, B=116,373, C running", with a 4-day A and a window that closed in October 2025. It ranks first for lack of better, and the odds column shows the next-level plan failing. With so little printed, the tree knows little.
- **Today's top reading is one day old.** From 2026-09-30 to 2026-10-29 the top is the finished-at-57,756 reading. Reading 1 needs 87,384 confirmed as a 1D pivot, which only the fall on 2026-10-30 did. So the order of 1 and 2 is very recent.

## Against random paths

Two checks, 20 paths each. **A** is r2's check again: every 15m bar's direction flipped, no premise. **B** is new: real bars down to the 2026-02-06 low, flipped after that, with the premise on. (My first version of B flipped from the top itself. A random walk starting at its high almost always prints a new one, so 78 of 80 paths left the premise. I changed it. 1 of 21 paths left in the final version.) Rough checks both: few paths, one date, and it removes BTC's slow trend.

| A: every bar flipped, no premise | BTC | Random, median | Random, range | BTC's percentile |
|---|---|---|---|---|
| Top root fit | 0.598 | 0.606 | 0.549 to 0.644 | 30% |
| Top root's time axis | 0.646 | 0.587 | 0.482 to 0.702 | 90% |
| Legal readings | 466 | 387 | 129 to 824 | 60% |
| Other/unclear | 92% | 92% | 90% to 95% | 40% |
| 4H: a finished 5 ranks first from the low | yes | **1 of 20 paths** | | |
| 4H: fit of a finished 5, where one exists | 0.597 | 0.522 | 0.398 to 0.631 (5 paths) | 80% |

| B: real to Feb 2026, flipped after, premise on | BTC | Random, median | Random, range | BTC's percentile |
|---|---|---|---|---|
| Top root fit | 0.600 | 0.582 | 0.515 to 0.624 | 80% |
| Top root's time axis | 0.610 | 0.589 | 0.442 to 0.679 | 80% |
| Top root's structure axis | 0.690 | 0.690 | 0.571 to 0.690 | at the top, as are most paths |
| Legal readings | 39 | 37 | 10 to 53 | 50% |
| Other/unclear | 85% | 86% | 70% to 90% | 40% |
| Mean 4H fit, kept | 0.571 | 0.504 | 0.438 to 0.566 | 100% |
| 4H: a finished 5 ranks first from the low | yes | **2 of 20 paths** | | |
| 4H: fit of a finished 5, where one exists | 0.597 | 0.520 | 0.435 to 0.563 (7 paths) | above all 7 |

- **The root does not separate BTC from random paths.** Random corrections get root readings about as good. Fit says what a NewWave trader would accept, not what will happen.
- **Your five does look unusual:** a finished 5 ranks first on 1 to 2 of 20 random paths, and in B its fit beats every random 5. **Do not read that as evidence.** The items were chosen while looking at this very count, which is the largest home advantage in this whole round, and it is one count.
- A test that could mean something needs his counts collected over time, a null that keeps the trend, and no tuning between them.

## Decisions, and why

| Decision | Why |
|---|---|
| Your pivots primary, Lily's in `alt` | Your count. The rule notes run over every choice |
| Minimum time stays a kill, even where it stops your macro pivots | Marked R. You did not ask to change it; Lily's "hard rules pass" was on price |
| Your premise is not subject to that kill | The brief: it is your input, not a search result |
| Hold the premise through a new high, under review, up to the flat ceiling | Item 3 of the brief, and sec 3. An extended fifth is not counted automatically: that would be re-counting before the line |
| "Rank first" means among readings that start at its 0 and reach its last label | The brief's "covering". Same-pivot variants with W5 still open are removed as the same reading |
| Fast market credit is 0.6, not 1 | The inner credit of a template. A fast leg is excused, not rewarded |
| No softening for W2 | The book softens W3, W4 and W5, and the case that softening W2 would rescue is the one you rejected |
| Inside evidence weighs 2 items per axis | A labelled 5 was judged on about ten items, and one weight made "A = 5, B running" lose to much weaker counts. Ours, and tuned on this count |
| `triple_rare` weighs 2 | Needed for the double three to beat the triple on the same move. Ours, and tuned |
| `leg_form` skips a motive label with no labellable 5 | `subwaves` already says so, and a failed mechanical parse is no proof of a 3. W1 of your count has no legal 5 on these pivots |
| Root seats by idea, not by family | Otherwise three combinations of one move fill the board. Today's three are all combinations anyway, but three different moves |
| Replay and null kept on the 1D root | The brief asked for r2 against r3 where the premise applies |

## Verified, and assumed

**Verified:** the nine premise prices against the bars; the cause of r2's loss by experiment on a snapshot of r2; every gold result by running it; cutting the data gives the same tree with the premise on, by test; the private file stays out of git and is never requested on the public host, by test.

**Assumed:** that your chart's pivots mean what the brief says they mean. I only had the brief's description, not the screenshots. All the "ours" numbers. That 1.618 x speed means fast: the book gives no number.

## Honest limits

- **Tuned on one count.** `inside_*`, `triple_rare` and the fast-market numbers were set with your count in view, and passing is what they were set for. It should be read as "the engine can reproduce this reading", which is what the master plan asks of a gold test, and no more. Each new entry you add is a real test of these numbers; the first one that fails will say more than this one passing.
- **The reading you doubted is at rank 2.** See the top.
- **Your W1 is not a 5 to the engine.** On the mechanical pivots 57,756 to 66,938 has no legal five: at threshold 4, W3 comes out the shortest. W1, W3 and W5 all fail the sub-wave check on the best variant. You read it as a 5, and I cannot tell whether the pivots or the label should move. So "clearly 5 waves" holds on the outer five waves, not yet on what is inside them.
- **Fit is still not validated as anything.** r1's and r2's limits stand. The items added nothing over volatility in the research.
- **Below 4H the three chains nearly coincide.** Three parents do not mean three independent views of the next day.
- **Only the mechanical pivots can be labelled.** A pivot you would draw can still be missing at every threshold.
- **1D has few pivots.** Threshold 4 is the only one that confirms 87,384 at root level, and it did so only on 2026-10-30. Reading 1 depends on it.
- **The inside of a wave is not nested into the fit deeply.** Only motive waves pass evidence up, one level.
- **No forward log.** As in r1 and r2, nothing stores these trees, so none of this can be scored later.
- **Triple combination is lightly tested** beyond its rules and one planted case.

## Checks

- `uv run pytest -q`: 248 pass, 6 network tests deselected. New: `tests/test_premise.py` (the premise file, root only after the top, cut before the line, the minimum against the five, its levels on synthetic new highs and lows, no cap anywhere, every fast-market side, pivots being the real extreme, triple, insides, twins, `tf_move`) and `tests/test_gold.py` (real bars, skipped where absent: all four variants, rank first, every kept root with room shows it, macro kept, the macro's exact blocker, tree shape).
- `uv run ewave-counts gold`: both entries pass, exit 0.
- `uv run ewave-data status --check`: exit 0.
- `git check-ignore site/data/local/counts.json`: ignored.
- `node tools/shots_counts.mjs`: 23 checks, no console errors or failed requests; I looked at the 4H with your impulse, the 1D root list, the premise block, 1H and phone.
