# Top-down count board, round 4: what is inside a wave is a rule

What this is: round 3 with the inside check promoted from a soft score to a rule. Your request: "when creating waves make sure you count wave inside for rules". Package `src/ewave/counts/`, config `rules/counts.yaml` (version `counts-r4.0`), private chart panel `site/counts.js`. Nothing here is committed or public.

**Read this first.**

- **Every finished wave of every candidate is now checked against what its label says it must hold, on every frame.** A count dies when a wave can be read and does not hold that form.
- **Your 4H five passes.** All 4 variants, no failing wave, and it still ranks first of 51 readings that cover that move. **Your W1 is a 5 to the engine now:** 1=61,325, 2=59,556, 3=64,703, 4=61,500, 5=66,938, at 4H threshold 1.75. r3's weak spot had two causes. Its thresholds stopped at 3, and its time minimum blocked the labelling. It took both changes: with the time kill still on, threshold 1.75 finds nothing.
- **Your macro count's exact pivots are on the board now,** at rank 27 of 557 run without the premise. The time minimum was the only thing stopping them. No variant has a failing wave. W4 is held: its 3 and 5 readings are 0.01 apart.
- **The rule caught what you objected to in r2.** Your five labelled as a corrective wave now dies outright: as X, B, X2, A or W of 11 readings across 1D and 4H. In r3 those only ranked lower.
- **It removed one root.** r3's third root, "W=57,756, in X", died because the fall reads as a 5. **That kill is weak:** the gap is 0.53 against 0.50, and at a margin of 0.05 it would have been held. The root in its seat, a zigzag with A=57,756, outranks it at any margin, so the board is the same either way.
- **The 5 check is lenient, and most kills come from guideline scores.** A legal 5 exists inside 96% of the BTC waves that need one, and 89% on random paths. Most kills are "this 3 reads as a clear 5", and "clear" is a gap in fit, which is made of guidelines. I used the brief's margin of 0.02 and show below what changes at other margins.
- **It is not evidence.** The rule kills about 30% of readings on random paths at every frame down to 1H and 21% at 15m, at least as many as on BTC. It makes the labels consistent with the book. It says nothing about what happens next.

## How to use it

```bash
uv run ewave-counts report --root 1d --brief   # each node with an "inside:" line, and readings killed per frame
uv run ewave-counts gold                       # your counts: every variant, wave by wave, what was found and where
uv run ewave-counts export                     # site/data/local/counts.json, about 1.3 s warm
```

On the chart, choosing a count adds a line such as "W1 5 ok (4H) · W2 3 ok (4H) · W3 5 ok (4H) · W4 3 or 5 held · W5 5 ok (4H)". Each word has the reason as a tooltip. "Killed by what is inside" above the tree opens the count per frame.

## The rule

For every finished wave, three answers:

| Answer | When |
|---|---|
| **Pass** | A rule-legal labelling of the required form exists, on some frame at some threshold. Existence, not best score |
| **Fail, the count dies** | Must be a 5: the wave is readable and no legal 5 exists anywhere on the ladder. Must be a 3: it reads clearly as a 5 |
| **Hold** | Too short to read at the finest frame, nothing visible at any threshold, or a 3 and a 5 within the margin (sec 0: hold both). Ranked as r3 ranks it |

The wave still running can only be held, never killed. The panel says "Y running, 3 so far".

**The search.** Own frame first, then down: 1D, 4H, 1H, 15m, and 1m from `load_1m` where nothing coarser read the wave. On each frame, 17 thresholds from 16 ATR to 1 ATR. A frame is skipped when the wave has under 12 bars on it or over 3,000, and a threshold when it shows over 33 legs. Only bars up to the wave's end are read.

**Depth 2.** A labelled 5 counts only if its largest motive wave (log price) holds a 5 itself, or cannot be read (FND-8, FND-9). The others of 1, 3 and 5 are not required to, as the brief allows.

**What "readable" means for a 5.** At least one threshold shows 5 or more legs, or the wave shows exactly 3 legs and never gets too fine to label. So a straight leg is held, and a clean up-down-up is a clear 3.

**What "clearly a 5" means for a 3.** An impulse on the frames a reader looks at (r3's `inside_tf`), whose largest wave holds and which ends at its own extreme, beating the best allowed 3 by more than the margin. Or the same impulse with no legal 3 at any resolution. A diagonal never makes it clear, because overlap reads as corrective or diagonal (sec 0, 2).

## Inside-rule table with sources

IDs refer to the NewWave files. The complete file and the theory file carry the same IDs for these statements. The table is `grammar` in `rules/counts.yaml`.

| Wave | Must hold | Form | Source |
|---|---|---|---|
| Impulse W1 | Impulse, or rarely a leading diagonal | 5 | Compact sec 1 R, IMP-R2; DIAG table |
| Impulse W2 | Zigzag, flat, combination | 3 | IMP-R5; TRI-R7 (never a triangle) |
| Impulse W3 | Impulse only | 5 | IMP-R3 |
| Impulse W4 | Zigzag, flat, triangle, combination | 3 | IMP-R6 |
| Impulse W5 | Impulse or ending diagonal | 5 | IMP-R4; DIAG table |
| Leading diagonal 1, 3, 5 | Impulse or zigzag (5-3-5-3-5 or 3-3-3-3-3) | 3 or 5 | DIAG table, DIAG-R5, DIAG-2 |
| Leading diagonal 2, 4 | Zigzag | 3 | PDF rules after DIAG-R7 |
| Ending diagonal 1 to 5 | Zigzag | 3 | DIAG-R5, PDF rules after DIAG-R7 |
| Zigzag A | Impulse or leading diagonal | 5 | Sec 3 zigzag R, COR-0.3, COR-0.4 |
| Zigzag B | Any 3, may be a triangle | 3 | Sec 3 zigzag R, TRI-R8 |
| Zigzag C | Impulse or ending diagonal | 5 | COR-0.1, CONFLICT-4 |
| Flat A | Zigzag, flat, combination, never a triangle | 3 | FLAT-R1 |
| Flat B | Zigzag, flat, combination | 3 | FLAT-R1 (see the note below) |
| Flat C | Impulse or ending diagonal | 5 | FLAT-R2, CONFLICT-4 |
| Triangle A to D | Zigzag, flat, combination | 3 | TRI-R1, TRI-R2 |
| Triangle E | The same, or a triangle | 3 | TRI-R3 |
| Combination W | Zigzag, flat, combination, never a triangle | 3 | CPX-R2 |
| Combination X | Any 3 | 3 | CPX-R2, TRI-R8 |
| Combination Y | Flat, triangle, combination, never a zigzag | 3 | CPX-R1 |
| Triple Y, second X, Z | Y no triangle; second X any 3; Z flat, triangle, combination | 3 | CPX-R7, sec 3 |

Other inner-structure statements I found, and how they are used:

| Statement | Use |
|---|---|
| FND-1, FND-2, IMP-R1, COR-3: only 3s and 5s, and they nest | The basis of the table |
| FND-3 (UNSPOKEN R1, R2): what starts or ends with a 5 | Already in the grammar |
| FND-8, FND-9: largest wave subdivides visibly; verify 1, 3, 5 | Depth 2, the search order |
| Posture, sec 6 Programmer: 3-or-5 unreadable, hold both | Hold |
| TRI-P3, TRI-P4: a triangle leg that is a 5 is a false triangle | Triangle legs die on a clear 5 |
| CPX-0, sec 6 look-alikes: C is 5, Y is 3; an apparent B with 5 is no B | The 3 side of the rule |
| TDI-D3, LB rules: a fifth has 5 inside, a B has 3 | The 3 side of the rule |
| DIAG-G1: all-threes diagonal without overlap, common in crypto | Not implemented: the diagonal rules still need overlap |

**Where the grammar differs from the book, and I left it:**

- **Flat B.** TRI-R8 finds triangles in a B, and FLAT-R1 bars one only from A. I added it, then took it back. Adding it changes X of root 1 from "A 82,811, B 57,756, C 87,384" (0.492) to "A 82,811, B 62,505, C 87,384" (0.496), a B that holds 57,756 inside it, and the `in_tree` gold check fails at that root. The reading itself is unchanged. It was not what this round asked for. It is one line in `rules/counts.yaml` if you want it, and that gold check would need to change with it.
- **Triangle "4 of 5 zigzags"** (TRI-R1) is not counted, only which patterns are allowed.
- **A wave allowed only zigzags that reads only as a flat** is held, not killed. The brief's two kill cases do not cover it.

## The time minimum

r3 killed on it. r4 ranks. FIB-T3 and T4 are filed under CONVENTION, and their stated consequence is wrong pivots or an unfinished correction, not an invalid count. On our data about 63% of mechanical BTC W4s break it, about half on random paths (`02-empirical.md` B3).

It is now item `min_time`, weight 2 on the time axis, credit (time / minimum) squared, and a pass counts for nothing. **My first version let a pass add credit, and that lifted the triple combination to root 3 by giving it more items to pass.** Penalty-only fixed that. A correction that calls the whole fall finished under the minimum of your five now scores 0 on `premise_time` and stays on the board.

## r3 against r4

Same moment: 2026-10-31 01:15 UTC, close 77,466. Axes are price / time / structure.

**r3**

| Node | Frame | Reading | Labels | Fit | Axes |
|---|---|---|---|---|---|
| 1d.1 | 1D | Combination, in Y | W=59,888 X=87,384 | 0.60 | 0.51 / 0.61 / 0.69 |
| 1d.1.1 | 4H | Combination, in Y | W=80,350 X=84,880 | 0.58 | 0.58 / 0.51 / 0.66 |
| 1d.1.1.1 | 1H | Combination, in Y | W=79,175 X=81,967 | 0.58 | 0.57 / 0.51 / 0.69 |
| 1d.1.1.1.1 | 15m | Flat, in C | A=76,455 B=78,072 | 0.47 | 0.36 / 0.51 / 0.57 |
| 1d.2 | 1D | Combination, finished | W=80,608 X=97,963 Y=57,756 | 0.57 | 0.63 / 0.47 / 0.63 |
| 1d.2.1 | 4H | Impulse, finished | 1=66,938 2=62,505 3=82,277 4=74,920 5=87,384 | 0.59 | 0.68 / 0.59 / 0.52 |
| 1d.2.1.1 | 1H | Combination, in Y | W=79,750 X=84,880 | 0.57 | 0.48 / 0.56 / 0.69 |
| 1d.2.1.1.1 | 15m | Combination, finished | W=79,175 X=81,779 Y=76,232 | 0.62 | 0.58 / 0.60 / 0.69 |
| 1d.3 | 1D | Combination, in X | W=57,756 | 0.56 | 0.48 / 0.57 / 0.63 |
| 1d.3.1 | 4H | Zigzag, in B | A=87,384 | 0.54 | 0.52 / 0.49 / 0.63 |
| 1d.3.1.1 | 1H | Combination, in Y | W=79,750 X=84,880 | 0.59 | 0.52 / 0.56 / 0.69 |
| 1d.3.1.1.1 | 15m | Combination, finished | W=79,175 X=81,779 Y=76,232 | 0.62 | 0.58 / 0.60 / 0.69 |

**r4**

| Node | Frame | Reading | Labels | Fit | Axes | Inside |
|---|---|---|---|---|---|---|
| 1d.1 | 1D | Combination, in Y | W=59,888 X=87,384 | 0.60 | 0.51 / 0.61 / 0.69 | W 3 ok (4H) · X 3 ok (4H) · Y running, 3 so far |
| 1d.1.1 | 4H | Combination, in Y | W=80,350 X=84,880 | 0.58 | 0.58 / 0.51 / 0.66 | W 3 ok (1H) · X 3 ok (1H) · Y running, 3 so far |
| 1d.1.1.1 | 1H | Combination, in Y | W=79,175 X=81,967 | 0.58 | 0.57 / 0.51 / 0.69 | W 3 ok (1H) · X 3 ok (1H) · Y running, 3 so far |
| 1d.1.1.1.1 | 15m | Combination, finished | W=78,192 X=79,793 Y=76,232 | 0.52 | 0.57 / 0.44 / 0.57 | W 3 ok (15m) · X 3 ok (1m) · Y 3 ok (15m) |
| 1d.2 | 1D | Combination, finished | W=80,608 X=97,963 Y=57,756 | 0.57 | 0.63 / 0.47 / 0.63 | W 3 ok (4H) · X 3 ok (4H) · Y 3 ok (4H) |
| 1d.2.1 | 4H | Impulse, finished: your five | 1=66,938 2=62,240 3=82,277 4=74,920 5=87,384 | 0.59 | 0.63 / 0.59 / 0.55 | W1 5 ok (4H) · W2 3 ok (4H) · W3 5 ok (4H) · W4 3 or 5 held · W5 5 ok (4H) |
| 1d.2.1.1 | 1H | Combination, in Y | W=79,750 X=84,880 | 0.57 | 0.48 / 0.56 / 0.69 | W 3 ok (1H) · X 3 ok (15m) · Y running, 3 so far |
| 1d.2.1.1.1 | 15m | Combination, finished | W=79,175 X=81,779 Y=76,232 | 0.62 | 0.58 / 0.60 / 0.69 | W 3 ok (15m) · X 3 ok (15m) · Y 3 ok (15m) |
| 1d.3 | 1D | **Zigzag, in B** | A=57,756 | 0.55 | 0.50 / 0.53 / 0.63 | A 5 ok (1D) · B running, 5 so far |
| 1d.3.1 | 4H | Zigzag, in B | A=87,384 | 0.54 | 0.52 / 0.49 / 0.63 | A 5 ok (4H) · B running, 3 so far |
| 1d.3.1.1 | 1H | Combination, in Y | W=79,750 X=84,880 | 0.59 | 0.52 / 0.56 / 0.69 | W 3 ok (1H) · X 3 ok (15m) · Y running, 3 so far |
| 1d.3.1.1.1 | 15m | Combination, finished | W=79,175 X=81,779 Y=76,232 | 0.62 | 0.58 / 0.60 / 0.69 | W 3 ok (15m) · X 3 ok (15m) · Y 3 ok (15m) |

**What moved, and why:**

- **Root 3.** The fall to 57,756 now has a legal 5, so as a zigzag's A it earns credit it could not earn in r3, and it outranks W=57,756 even with the kill switched off.
- **Your five.** Same pivots except 2, which is now Aug 1 instead of Aug 14: 0.593 against 0.589, near a tie. r3 had the opposite order by a similar gap.
- **The 15m chain under root 1.** The flat in C gave way to a finished combination, because X took 30 minutes, 0.11 x W, which r3's time kill forbade. It is legal now and ranks lower for it, yet it is still the best 15m child there. **All three 15m chains now expect up,** first 81,576, and all three die below 76,232. In r3 that frame was split 2 up, 1 down. This comes from the time change, not the inside rule.
- **1H is unchanged at both ends:** all three expect up, first 81,576.

The 1D crossroads are unchanged: above 87,384 kills 1, below 57,756 kills 2 and 3. As in r3, below 4H the three chains nearly coincide.

**In plain words, the three roots today.**

1. The correction is a double three still falling: W to 59,888, X an expanded flat whose C is your five, Y running to 34,796-55,141 by January 2027.
2. The correction ended at 57,756, on the 0.618, and your five starts what comes next. Weakest on time: Y took 3.65 x W.
3. The fall to 57,756 is the A of a zigzag, and the bounce is its B, with your five as the A of that B. A C down comes later.

## How many readings died at each frame, and why

| Frame | Read | Died | Why |
|---|---|---|---|
| 1D | 39 | **11** | A reads as a 5: 4. B: 3. W: 2. Z: 2. X2: 2. X: 1 |
| 4H | 109 | **11** | W5 holds no 5: 5. A reads as a 5: 4. W: 1. Y: 1 |
| 1H | 76 | **6** | A reads as a 5: 3. W: 3 |
| 15m | 52 | **0** | |

Each reading counts once per frame. One can fail on two waves, so the reasons can add to more than the readings. The 12H root is the same picture: 11 of 51.

**The readings that died, grouped:**

- **Your five as a 3.** 57,756 to 87,384 as an X, B or X2 at 1D, an A or W at 4H, 11 readings: impulse 0.58 against zigzag 0.43. Clear, and the case you raised.
- **The fall as a 3.** 126,150 to 57,756 as an A or W: impulse 0.53 against zigzag 0.50. **Thin.**
- **The fall from 82,811 as a Z.** 82,811 to 57,756: impulse 0.62 against flat 0.40. Clear.
- **The move from 62,240 as a Y.** 62,240 to 87,384 in a 4H combination: impulse 0.50 against combination 0.46. **Thin.**
- **The only real "holds no 5".** W5 from 80,350 to 84,880, in five impulses such as 1=66,938, 2=62,240, 3=87,384, 4=80,350, 5=84,880. r3 ranked one of these third among the readings covering your move, at 0.581. It reads as a flat: up to 31 legs on 4H and no legal 5 anywhere. This is the check working as you asked.
- **The small first leg down.** 87,384 to 82,800 as an A or W at 1H: impulse 0.48 against flat 0.43. All 6 1H kills are this leg. **They are within 0.05, so they are soft.**

### The margin, since it decides most kills

| Margin | 1D | 4H | 1H | 15m | Roots |
|---|---|---|---|---|---|
| 0.02 (the brief's, in use) | 11 | 11 | 6 | 0 | as above |
| 0.05 to 0.15 | 8 | 10 | 0 | 0 | the same |
| No clear-5 kill at all | 0 | 5 | 0 | 0 | the same |

**So on today's bars the three roots do not depend on it.** Most kills at 1D and 4H survive a margin of 0.15: 8 of 11 and 10 of 11. All 6 at 1H do not. `inside.clear_margin` is one number.

### Against random paths

r3's check B: real bars to the 2026-02-06 low, each 15m bar's direction flipped after that, premise on, 20 paths, 1m off on both sides. None left the premise. A rough check: few paths, one date, BTC's trend removed.

| Share of readings killed, margin 0.02 | BTC | Random, all paths | Random, range | Paths below BTC |
|---|---|---|---|---|
| 1D | 28% | 30% | 3% to 56% | 11 of 20 |
| 4H | 10% | 30% | 8% to 67% | 1 of 20 |
| 1H | 8% | 31% | 0% to 54% | 3 of 20 |
| 15m | 0% | 21% | 0% to 33% | 0 of 20 |

| Verdicts on waves read | BTC | Random |
|---|---|---|
| Must be a 5: pass / fail / hold | 96% / 4% / 0% (69) | 89% / 6% / 5% (2,055) |
| Must be a 3: pass / fail / hold | 89% / 4% / 8% (193) | 76% / 17% / 7% (3,371) |

- **Random paths pass the 5 check nearly as often as BTC.** A legal 5 can be found inside most moves on a ladder this wide, so "W3 holds a 5" rules out little beyond a clean 3.
- **BTC loses fewer readings below 1D.** Do not read that as evidence. It is one path, the first months are shared, and I did not run this before choosing the rule.

## Gold

`uv run ewave-counts gold` exits 0: both entries pass. The check `inside` is new, and prints this per variant.

**4H, 57,756 to 87,384. No failing wave on any of the 4 variants.**

| Wave | Verdict | What the engine found |
|---|---|---|
| W1 | 5 ok | Impulse, 4H threshold 1.75: 1=61,325 2=59,556 3=64,703 4=61,500 5=66,938 |
| W2, to 62,240 | 3 ok | Zigzag, 4H threshold 4: A=63,701 B=65,392 C=62,240 |
| W2, to 62,505 | 3 ok | Zigzag, 4H threshold 4: A=62,707 B=65,547 C=62,505 |
| W3, 62,240 to 81,500 | 5 ok | Impulse, 4H threshold 3: 1=65,547 2=62,505 3=79,559 4=75,550 5=81,500 |
| W3, 62,240 to 82,277 | 5 ok | Impulse, 4H threshold 5: 1=65,547 2=62,505 3=81,500 4=76,199 5=82,277 |
| W3, 62,505 to 81,500 | 5 ok | Impulse, 4H threshold 2.5: 1=69,893 2=67,792 3=79,559 4=75,550 5=81,500 |
| W3, 62,505 to 82,277 | 5 ok | Impulse, 4H threshold 2.5: 1=69,893 2=67,792 3=79,559 4=76,199 5=82,277 |
| W4, from 81,500 | 3 ok | Flat, 1H threshold 6: A=76,199 B=79,910 C=74,920 |
| W4, from 82,277 | **Held, 3 or 5** | Combination 0.49 against impulse 0.48 |
| W5 | 5 ok | Impulse, 4H threshold 1.5: 1=76,529 2=75,000 3=81,955 4=80,092 5=87,384 |

It ranks 1 of 51 and shows under all three roots. Its one remaining soft miss on this question: `leg_form` still says W1 and W5 score a little better as 3s (0.50 against 0.46, 0.44 against 0.42). Legal 5s exist and pass, and those gaps cost rank.

Two labellings to look at, since you may place them differently: W2 to 62,505 has its A at 62,707 with the 62,240 low inside that A, which the mechanical rules allow. And the W3 from 62,240 uses your own Aug 14 low, 62,505, as its W2.

**1D macro, run without the premise. No failing wave on any of the 4 variants.**

| Wave | Verdict | What the engine found |
|---|---|---|
| W1 | 5 ok | Impulse, 1D threshold 5: 1=18,379 2=16,203 3=25,296 4=19,535, then your 1 |
| W2 | 3 ok | Flat or zigzag on 4H, depending on the pivots |
| W3 | 5 ok | Impulse, 1D threshold 5: 1=73,949 2=48,914 3=108,422 4=89,100 5=109,952 |
| W4 | **Held, 3 or 5** | Zigzag 0.50 against impulse 0.49 |
| W5 | 5 ok | Impulse, 1D threshold 1.75: 1=81,217 2=74,566 3=111,968 4=108,550 5=126,150 |

Your exact pivots rank 27 of 557 root readings. The best five with the same 0 and 5 is rank 19: 1=31,844, 2=24,201, 3=73,949, 4=48,914. In the premise panel the time miss is now a plain note: W4 took 77 days, 0.15 x W3, under the 0.25 minimum.

**No wave fails at every resolution, so there is no failing leg to show you.** There is one leg worth seeing, because it exposed a mistake of mine. Lily's 1 with your 2 (31,844 to 24,853) first failed as "a clear 5". The chart showed why that was wrong: the 5 ends at 24,853 with the 24,201 wick printed inside it, so it does not end at its own extreme. I had meant to exclude truncated fives, but tested only the labels, not the bars. Now fixed for every wave, and that W2 passes as a zigzag. Screenshot: `r4_macro_w2_inside.png`.

## Export timing

| Run | Time | Verdicts |
|---|---|---|
| r3, no rule, no cache | 3.5 s | |
| r4, cold | **4.3 s** | 1,137 read |
| r4, warm | **1.3 s** | 788 from the cache, 0 read |

Well under the 60 s limit, and far under the cron's 5 minute timeout. The cache is `.cache/counts/inside-{rules digest}-{code digest}.sqlite`, gitignored, keyed by venue, frame, start, end, form and depth. Any change to the rules or to the code that reads waves starts a new file, so the first run after one is cold. It commits every 200 entries, so a run cut short keeps its work. A damaged file is read again rather than crashing.

## Decisions, and why

| Decision | Why |
|---|---|
| Margin 0.02 | The brief's. Shown above with what changes at other margins |
| "Clear 5" is judged on r3's frames, not the whole ladder | A chart reader's view. At 1 ATR on 1m, a 5 can be found in almost anything, and 3-required waves would die at random |
| A diagonal or a 5 that does not end at its extreme never makes a clear 5 | Overlap reads as corrective or diagonal; such a shape is a 3 as easily |
| Neither a 3 nor a 5 legal: hold | The brief lists two kill cases; this is neither |
| An impulse is tried at every threshold before a diagonal | The book lists it first and calls the diagonal rare in W1. Otherwise W1 passed as a diagonal one rung earlier |
| 1m only when nothing coarser read the wave, only under 3,000 bars | The brief's "if needed and cheap" |
| `min_time` is penalty-only, weight 2, credit squared | Strong, and a floor says nothing when passed. The numbers are ours |
| `leg_form` also sees the 5 the rule found | Otherwise the panel said "W1 5 ok" and "W1 reads as a 3 (0.50 against 0.35)" together |

**Taken with your count in view, so discount them accordingly.** All four came from looking at your five's or the macro's result. The rule itself came first, and it passed your 4H five on its first run.

1. **Impulse before diagonal.** Changed W1's verdict from a diagonal to an impulse. It passed either way.
2. **`leg_form` sees the rule's 5.** Lifted your five's structure from 0.44 to 0.55 and its fit from 0.547 to 0.593. It applies to every reading, and your five ranked first with or without it.
3. **A 5 must end at its extreme.** Cleared the macro's one failing variant, which was Lily's 1 with your 2.
4. **Flat B left without a triangle.** Keeps the `in_tree` check passing at root 1. Told above, yours to change.

## Verified, and assumed

**Verified:** each planted case by test (below); cold and warm runs give identical output; a verdict does not change when the data is cut right after the wave or when the future is different; 1m is never asked for past a wave's last bar; every gold result by running it; every screenshot by looking at it; the three kept roots at each margin.

**Assumed:** that 12 bars is enough to read a wave, that 1 ATR is the noise floor, and that 33 legs is the most a wave can reasonably be labelled over. All ours. That "any reasonable resolution" means this ladder.

## Honest limits

- **"Clear 5" is a guideline deciding a rule.** The book says never promote a G to an R. The legal 5 and the legal 3 both exist in these cases, and fit separates them. That is what the brief asked for, and the 0.15-wide gaps look right to me, but the thin ones do not.
- **The 5 check is weak.** See above: 89% of random waves pass. It kills clean 3s, and little else.
- **15m has no teeth:** 0 of 52. Short waves pass on 1m, and "clear 5" does not read below 15m.
- **The rule looks only so deep.** Only the largest of 1, 3, 5 recurses. A 3's own inside is not recursed at all, so a zigzag whose C holds no 5 still counts as a 3.
- **Only mechanical pivots can be labelled.** A pivot you would draw can still be missing at every threshold, and a wave's verdict depends on what the zigzag shows. The search can jump from 3 legs to too many, and then it holds.
- **Legal is not pretty.** Labellings that pass can have a wave with its low inside it, as in W2 to 62,505. The rules allow it.
- **The panel draws no inside labels on a very narrow wave:** your W5 on 4H is too narrow, so its 1 to 5 are in the panel only.
- **Replay not rerun.** r3's replay table is not comparable to this tree. Nothing here says the board forecasts better.
- **Fit is still not validated as anything.** No forward log, as in r1 to r3.

## Checks

- `uv run pytest -q`: 296 pass, 6 network tests deselected. New: `tests/test_inside.py` (the table; a W3 that is a clear 3 dies and takes the count; a textbook impulse passes on a finer frame where 4H cannot see it; a short wave and a straight leg are held; 1m reads what 15m cannot, and nothing later is asked for; the margin decides between clear and hold; depth 2; a running wave is never killed; causality, two ways; the cache cold, warm and absent gives identical output; a damaged file; the time minimum ranks and does not kill). `tests/test_gold.py` now records each wave's verdict and that the macro's exact pivots are on the board.
- `uv run ewave-counts gold`: both entries pass, exit 0.
- `uv run ewave-data status --check`: exit 0.
- `git check-ignore site/data/local/counts.json .cache/counts`: both ignored. Nothing new tracked under `site/data/`.
- `node tools/shots_counts.mjs`: 23 checks, no console errors or failed requests. I looked at 1D with insides, 4H with your five, 1H, the panel, the kill block and the phone.
