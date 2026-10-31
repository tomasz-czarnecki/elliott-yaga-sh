# Top-down count board, round 1

What this is: the top-down tree you asked for. 1D (or 12H) counts first, then 4H, 1H and 15m counts built inside each of them, with the crossroads and Y's on top. Package `src/ewave/counts/`, config `rules/counts.yaml` (version `counts-r1.0`), command `ewave-counts`, private chart panel `site/counts.js`. Nothing here is committed or public.

**Read this first.** The ranking is **rulebook fit, not a win chance**. No probability that "count X is the true count" can be measured, because there is no true count to check against. The only probability on the board is the volatility odds: how often a random walk at today's volatility reaches the target before the invalidation. It knows nothing about waves. Any count has to beat it to be worth anything, and nothing has shown that a count does.

## How to use it

```bash
uv run ewave-counts report --root 1d          # the whole tree as text (--root 12h, --root both, --brief, --as-of 2026-05-01T00:00)
uv run ewave-counts export                    # writes site/data/local/counts.json for the chart panel (gitignored)
uv run ewave-counts replay --dates 2025-01-01,2026-01-01 --days 30
uv run ewave-counts --venue binance_btcusdt report --brief
```

On the chart page, the **Counts** button appears only when `data/local/counts.json` loads, and never on yaga.sh or vercel.app hosts. The panel lists the crossroads and Y's per frame, then the tree. Clicking a count moves the chart to that count's timeframe and draws:

- its labels and those of its parents, with one notation per degree: ringed at the root, then (1), then 1, then i. A/B/C follow the same pattern, and darker violet means a lower degree;
- the running wave, dashed;
- the invalidation line and the nearest kill;
- the zone where the running wave should end, as a grey box;
- the next wave's levels, as a coloured box.

**The panel does not update itself.** Nothing schedules `ewave-counts export`. Run it to refresh; it takes about 2 seconds.

## How it works

1. **Bars.** Only complete bars, cut at the last complete 15m bar. Frames always start at the venue's first bar, so indicators and root pivots do not depend on where a window begins. Finer bars after the last complete coarse bar still count for kills: a break today kills a 1D count straight away, with no wait for the daily close.
2. **Pivots.** A causal zigzag, k x ATR(14) in log price, using `hl_order` inside a bar. A count may label a pivot only after its confirming bar has closed. The running extreme is never labelled.
3. **Enumerate.** From each possible start, every labelling that breaks no R rule. The last label sits on a confirmed pivot, and everything printed since then is inside the **running wave**.
4. **Score.** Each legal count gets a fit from the G, C and B items of sections 0 to 5, with reasons listed.
5. **Keep.** The top 3 at the root, the top 2 per parent below, with one reading per state before any second helping. At most 3 / 6 / 8 / 8 nodes per level.
6. **Step down.** Each parent's running wave defines the child's job: same start pivot, same direction, and only a pattern that wave allows. Parent in W4 up: the child is a correction down from the W3 end. Parent in W3: the child is an impulse from the W2 end. If a child has already finished, the parent's wave closes there, but only if the parent's own rules allow it, and the next frame then reads the parent's next wave.
7. **Levels and odds.** Zone, next-wave levels, kills, barrier odds, reward:risk.
8. **Crossroads and Y's** per frame, as defined in section 6.

## The current tree

As of 2026-10-30 21:45 UTC, Bybit perp, close 76,783.8. Rules `counts-r1.0`.

**Crossroads: none right now.** On every frame the kept counts disagree on the next move:

| Frame | Kept counts: next move | Nearest Y above | Nearest Y below |
|---|---|---|---|
| 1D | 1 up (first 93,600), 2 down (first 57,731) | 126,150 | 57,756 |
| 4H | 1 up (first 93,600), 5 down (first 72,570) | 87,384 | 74,920 |
| 1H | 4 up (first 81,808), 4 down (first 72,570) | 81,967 | 74,920 |
| 15m | 4 up (first 83,124), 4 down (first 74,333) | 78,774 | 74,920 |

The level that matters most is **74,920**, the 15 September 2026 low. Below it, the "W5 still running from 74,920" and "W2 of a new impulse" readings die on 4H and 1H. **81,967** does the same job above price: it ends the "W5 down still running" reading on 1H. On 1D nothing is close: 57,756 and 126,150.

```
Tree. Root: 497 legal readings in 97 states. Kept: top 3; other/unclear 93% of fit.
1D [1d.1] Impulse down finished at 57,756, next move up running. Fit 0.82, share 2.6%.
    4H [1d.1.1] Impulse up, in W5. Fit 0.81, share 4.7%.
        1H [1d.1.1.1] Impulse up, in W2. Fit 0.64, share 60.6%.
            15m [1d.1.1.1.1] Combination down, in Y. Fit 0.76, share 12.5%.
    4H [1d.1.2] Impulse up finished at 87,384, next move down running. Fit 0.80, share 4.3%.
        1H [1d.1.2.1] Impulse down, in W5. Fit 0.74, share 9.6%.
            15m [1d.1.2.1.1] Impulse down, in W3. Fit 0.67, share 32.0%.
1D [1d.2] Zigzag up finished at 126,150, next move down running. Fit 0.81, share 2.4%.
    4H [1d.2.1] Impulse down finished at 57,756, next move up running. Fit 0.81, share 4.5%.
        1H [1d.2.1.1] Impulse up finished at 87,384, next move down running. Fit 0.81, share 12.6%.
            15m [1d.2.1.1.1] Leading diagonal down, in W5. Fit 0.77, share 8.9%.
        1H [1d.2.1.2] Impulse up, in W5. Fit 0.81, share 12.0%.
            15m [1d.2.1.2.1] Impulse up, in W2. Fit 0.62, share 58.4%.
    4H [1d.2.2] Zigzag down finished at 57,756, next move up running. Fit 0.77, share 3.6%.
        1H [1d.2.2.1] Impulse up finished at 87,384, next move down running. Fit 0.82, share 13.3%.
            15m [1d.2.2.1.1] Leading diagonal down, in W5. Fit 0.77, share 8.9%.
        1H [1d.2.2.2] Impulse up, in W5. Fit 0.80, share 11.7%.
            15m [1d.2.2.2.1] Impulse up, in W2. Fit 0.62, share 58.4%.
1D [1d.3] Zigzag down finished at 57,756, next move up running. Fit 0.77, share 1.8%.
    4H [1d.3.1] Impulse up, in W5. Fit 0.81, share 4.6%.
        1H [1d.3.1.1] Impulse up, in W2. Fit 0.64, share 60.6%.
            15m [1d.3.1.1.1] Combination down, in Y. Fit 0.76, share 12.5%.
    4H [1d.3.2] Impulse up finished at 87,384, next move down running. Fit 0.81, share 4.6%.
        1H [1d.3.2.1] Impulse down, in W5. Fit 0.74, share 9.6%.
            15m [1d.3.2.1.1] Impulse down, in W3. Fit 0.67, share 32.0%.
```

Many lower nodes repeat under different roots, because several roots share the same running wave. That is real information: what they share does not depend on which root is right.

12H root, top 3:

```
Tree. Root: 564 legal readings in 118 states. Kept: top 3; other/unclear 93% of fit.
12H [12h.1] Impulse down finished at 57,756, next move up running. Fit 0.82, share 2.7%.
12H [12h.2] Zigzag up finished at 126,150, next move down running. Fit 0.80, share 2.3%.
12H [12h.3] Impulse up finished at 126,150, next move down running. Fit 0.79, share 2.1%.
```

The full text, with labels, levels, reasons and odds, comes from `ewave-counts report`.

**The three 1D counts, in plain words.**

1. **Five waves down from the ATH finished at 57,756.** W1 101,046, W2 116,373, W3 59,888, W4 82,811, W5 57,756. The up move since then is a correction, zone 85,357 to 93,600. It has reached 87,384. The next structure would be a next-degree W3 down. Invalidation: 126,150.
2. **The whole 2022-2025 rally was a three, finished at 126,150.** A 73,949, B 48,914, C 126,150. The decline since then is the next move. It has come within 25 dollars of the 0.618 retracement (57,731 against the 57,756 low).
3. **Three waves down from the ATH finished at 57,756.** A 80,608, B 97,963, C 57,756. It treats the decline as a correction: the leg now running is up, zone 93,600 to 126,150. A new low kills it.

Counts 1 and 3 expect the same next move, up, but for opposite reasons. 57,756 kills both. Only 126,150 separates them, and that is far away.

**Sanity check by eye.** I looked at all three on the 1D chart (`counts_bybit_1d`, `counts_root_1d.2`, `counts_root_1d.3` in the screenshots) and checked the numbers by hand: labels sit on real pivots, and no hard rule breaks. Count 1 is the weakest on time: W1 took 4 days and W3 took 102 days. The misses list says so.

## Decisions, and why

**Frames and roots**

| Decision | Value | Why |
|---|---|---|
| Root | 1D default, 12H alternative | You asked for this. 12H is resampled from 1H at UTC 00:00 and 12:00, and only a finished period makes a bar |
| 12H on the chart | Drawn on the 1D chart | The chart has no 12H bars and nothing may be added under tracked `site/data/`. A 12H pivot sits inside its day |
| Root window | 1,500 days back | One 4-year cycle (gaps 1,431 and 1,437 days), so it reaches the last bear low |
| Root starts | Pivots no price has passed since, plus up to 2 same-kind pivots before one of those for flats and combinations | An up move can only start at a low that still stands. This set is causal and small: 5 to 15 starts per threshold, plus the flat origins. A flat's B may pass its origin, hence the extra ones |
| Minimum root span | 45 bars on 1D, 90 on 12H | A shorter move is not root degree |
| Thresholds | Ladder per frame, in `rules/counts.yaml`. Below the root, the finest lists with at most 23 pivots, up to 3 per window | One threshold misses structure, and the right one depends on how long the parent's wave is |

**Rules** (a break kills the count)

| Decision | Why |
|---|---|
| The minimum correction time (sec 4) is a hard rule, with 1 bar of tolerance | The book marks it R. The spikes treated it as soft |
| A rule limit holds for every pivot inside a wave, not only its end | Without this, a W4 could enter W1 territory on its A and still pass |
| A motive wave never passes its own start and ends at its extreme, except for a truncation that wins back at least 0.618 of the fall from the extreme | **Ours.** The book allows truncation with no number. Without a limit, a "W3" could end at 82,811 with 126,150 inside it. The number mirrors sec 2's W5 against W4 |
| X below the flat ceiling of W | **Ours.** A WXY is a flat ending in a 3 (sec 3). Without this, a W4 could hide a 3x "X" |
| Y may not be a zigzag | Sec 3 says this as R, while the same section's list of forms says otherwise once. The R wins |
| A diagonal appears only once W4 has overlapped W1 | Before that it reads the same as an impulse. So overlap-less diagonals, which sec 2 says are common in crypto, are **not found**. Listed under limits |
| Left out: expanding triangles and W-X-Y-X-Z | Rare by the book, and they would add noise to a tree meant to stay readable |
| A running wave with 2 or more printed legs must be the legal start of what it claims to be | Otherwise any odd shape can sit inside a running wave. |

**Ranking**

| Decision | Why |
|---|---|
| Fit is a sum of evidence, net = sum of w x (f - 0.35), mapped to 0..1 | An average let a bare "B running" with 5 easy items outrank a fully labelled five with about 20. The book's method is converging evidence (sec 6). 0.35 and the mapping scale are ours |
| The other/unclear share is an exp(7 x fit) share over all legal states, with a floor of 10% | Your rule: always report it. It is a share of fit, **not a probability**. Today the top 3 at the root hold 7%. That number is the honest one: nearly 100 readings fit about equally well |
| Alternation counts both ways, K | Sec 1 holds both. Only a muddle in between loses credit |
| TDI: RSI(11) on closes at the pivot bar, mirrored for down moves | W3 stronger than W1, W3 through 70, W2 holding 40, 3-5 divergence. No bands or detector. The book itself warns that close-based readings miss wick divergences |
| Sec 5's move table on D, 4H and 15m only | The book has no 1H or 12H row, so none is invented |
| Both directions at the root; not forced below it | Sec 9. Forcing it on every level would make a crossroads impossible |
| Parent's level near the child's: credit | Sec 1, sub-degree clustering |
| Ties go to the corrective count | "Unsure means corrective" |

**Levels and odds**

| Decision | Why |
|---|---|
| Log and linear on 1D, 12H and 4H, taking the nearer level; linear only on 1H and 15m | Sec 4: conservative first, immaterial below 4H |
| Two plans per count. "Next": the following wave's first level against the running wave's limit. "Leg": the running wave to its zone against what would end it. A correction leads with next; a motive wave leads with leg until its zone is reached | A W4 has its zone and its invalidation on the same side, so the odds only mean something for what comes after it |
| Next-wave levels are measured from the running wave's extreme so far | It has not ended yet. They move with price and are labelled "so far" |
| Levels after a finished correction: 0.618 and 1.0 of the whole correction | **Ours.** The book has no pull for this, and the panel says "no further pull" beyond it |
| Horizon: 120 bars on 1D, 180 on 12H, 150 on 4H, 1H and 15m. No-limit odds shown next to them | The research used 150 on 4H. A time limit changes the answer a lot, so both are shown |
| Volatility: root mean squared log return over 30 bars on 1D, 60 on 12H, 14 days on the rest | Same as the research spikes (14 days), longer on the high frames for enough bars |
| A level within 3 bars of volatility of price is skipped | It is already there. It would show 97% with R:R 0.02 |

**Crossroads and Y's**

- **Crossroads:** the kept counts of one frame all expect the same next move. It reports that move's first level and the level that guards it. Otherwise it reports the split. Next to it stands the split among **all** legal counts on that frame.
- **Y:** a price where crossing kills some of the counts and leaves the others.

**Page**

- `counts.json` carries the last 5 days of bars. The public bar files refresh once a day, so the newest labels would otherwise float past the end of the candles. This is private, like the rest of the file.
- Degree colours are one violet ramp, because degree is ordered. It passed the palette validator's ordinal check against the navy background, and each degree also has its own notation.

I did not edit `CLAUDE.md`: its Status section still says Phases 1-5 are not started. Whether this counts as Phase 1 is your call.

## Replay: what it said against what came next

Eight dates, picked by the calendar, every 6 months, so that I could not pick good ones. Data cut at each date. **No win rate can come from this:** it is 8 dates, the three rows of a date overlap, and it uses the same root each time. "What came first" uses the first row of odds, read on 15m bars, with the invalidation first when one bar holds both. "Neither" means the horizon ran out.

| as of | close | root count | running | target before invalidation | vol odds | R:R | what came first | high / low / close after |
|---|---|---|---|---|---|---|---|---|
| 2023-01-01 | 16,550 | impulse down, fit 0.83: 0=69,138 1=32,906 2=48,185 3=17,600 4=25,199 5=15,440 | after | down 1,625 before 69,138 | 0% | 0.28 | neither 2023-05-01 | 23,966 / 16,511 / 22,830 (30 d) |
| 2023-01-01 | 16,550 | impulse down, fit 0.81: 0=69,138 1=32,906 2=48,185 3=17,600 4=25,199 | 5 | up 32,673 before 15,440 | 0% | 14.53 | neither 2023-05-01 | 23,966 / 16,511 / 22,830 (30 d) |
| 2023-01-01 | 16,550 | impulse down, fit 0.76: 0=69,138 1=32,906 2=48,185 3=17,600 | 4 | down 11,993 before 32,906 | 4% | 0.28 | neither 2023-05-01 | 23,966 / 16,511 / 22,830 (30 d) |
| 2023-07-01 | 30,466 | impulse down, fit 0.83: 0=69,138 1=32,906 2=48,185 3=17,600 4=25,199 5=16,203 | after | down 3,006 before 69,138 | 0% | 0.71 | neither 2023-10-29 | 31,844 / 28,851 / 29,273 (30 d) |
| 2023-07-01 | 30,466 | impulse up, fit 0.78: 0=15,440 1=18,379 2=16,353 3=31,062 4=24,780 | 5 | down 23,442 before 31,444 | 10% | 7.18 | invalidation 2023-07-06 | 31,844 / 28,851 / 29,273 (30 d) |
| 2023-07-01 | 30,466 | combination down, fit 0.78: 0=69,138 W=32,906 X=48,185 Y=19,535 | after | up 42,662 before 19,535 | 22% | 1.12 | neither 2023-10-29 | 31,844 / 28,851 / 29,273 (30 d) |
| 2024-01-01 | 42,325 | impulse down, fit 0.83: 0=69,138 1=32,906 2=48,185 3=17,600 4=25,199 5=16,353 | after | down 4,345 before 69,138 | 0% | 1.42 | invalidation 2024-03-05 | 49,054 / 38,532 / 42,919 (30 d) |
| 2024-01-01 | 42,325 | combination down, fit 0.78: 0=69,138 W=32,906 X=48,185 Y=19,535 | after | up 69,138 before 19,535 | 5% | 1.18 | target 2024-03-05 | 49,054 / 38,532 / 42,919 (30 d) |
| 2024-01-01 | 42,325 | flat down, fit 0.74: 0=69,138 A=19,535 | B | down 20,504 before 150,989 | 0% | 0.20 | neither 2024-04-30 | 49,054 / 38,532 / 42,919 (30 d) |
| 2024-07-01 | 62,750 | combination up, fit 0.79: 0=6,466 W=69,138 X=17,600 Y=73,949 | after | down 32,244 before 73,949 | 0% | 2.72 | neither 2024-10-29 | 70,137 / 53,314 / 66,170 (30 d) |
| 2024-07-01 | 62,750 | impulse up, fit 0.78: 0=15,440 1=18,379 2=16,353 3=31,062 4=24,201 5=73,949 | after | up 151,173 before 15,440 | 0% | 1.87 | neither 2024-10-29 | 70,137 / 53,314 / 66,170 (30 d) |
| 2024-07-01 | 62,750 | impulse up, fit 0.77: 0=19,535 1=31,844 2=24,201 3=73,949 | 4 | up 68,814 before 31,844 | 62% | 0.20 | target 2024-07-27 | 70,137 / 53,314 / 66,170 (30 d) |
| 2025-01-01 | 93,530 | impulse up, fit 0.83: 0=15,440 1=31,062 2=24,201 3=73,949 4=48,914 | 5 | down 61,931 before 108,422 | 10% | 2.12 | invalidation 2025-01-20 | 109,952 / 89,100 / 104,685 (30 d) |
| 2025-01-01 | 93,530 | zigzag up, fit 0.78: 0=24,853 A=73,949 B=52,500 C=108,422 | after | down 56,776 before 108,422 | 5% | 2.47 | invalidation 2025-01-20 | 109,952 / 89,100 / 104,685 (30 d) |
| 2025-01-01 | 93,530 | impulse up, fit 0.76: 0=15,440 1=73,949 2=48,914 | 3 | up 143,582 before 48,914 | 9% | 1.12 | neither 2025-05-01 | 109,952 / 89,100 / 104,685 (30 d) |
| 2025-07-01 | 107,081 | impulse up, fit 0.83: 0=15,440 1=31,062 2=24,201 3=73,949 4=48,914 | 5 | down 63,704 before 111,968 | 0% | 8.88 | invalidation 2025-07-09 | 123,250 / 105,059 / 117,782 (30 d) |
| 2025-07-01 | 107,081 | impulse up, fit 0.79: 0=15,440 1=25,296 2=19,535 3=108,422 | 4 | down 63,978 before 120,362 | 0% | 3.25 | invalidation 2025-07-14 | 123,250 / 105,059 / 117,782 (30 d) |
| 2025-07-01 | 107,081 | impulse up, fit 0.78: 0=38,532 1=73,949 2=52,500 3=108,422 4=74,456 5=111,968 | after | up 216,945 before 38,532 | 0% | 1.60 | neither 2025-10-29 | 123,250 / 105,059 / 117,782 (30 d) |
| 2026-01-01 | 87,595 | zigzag up, fit 0.81: 0=15,440 A=73,949 B=48,914 C=126,150 | after | down 57,731 before 126,150 | 3% | 0.77 | neither 2026-05-01 | 97,963 / 81,000 / 84,222 (30 d) |
| 2026-01-01 | 87,595 | impulse up, fit 0.80: 0=16,353 1=31,062 2=24,201 3=73,949 4=48,914 | 5 | down 71,252 before 126,150 | 29% | 0.42 | target 2026-02-05 | 97,963 / 81,000 / 84,222 (30 d) |
| 2026-01-01 | 87,595 | impulse up, fit 0.78: 0=24,201 1=73,949 2=48,914 3=126,150 | 4 | up 111,352 before 73,949 | 21% | 1.74 | invalidation 2026-02-03 | 97,963 / 81,000 / 84,222 (30 d) |
| 2026-07-01 | 58,604 | zigzag up, fit 0.81: 0=15,440 A=73,949 B=48,914 C=126,150 | after | down 15,440 before 126,150 | 0% | 0.64 | neither 2026-10-29 | 66,938 / 57,756 / 64,751 (30 d) |
| 2026-07-01 | 58,604 | impulse down, fit 0.78: 0=126,150 1=101,046 2=116,373 3=59,888 4=82,811 | 5 | up 85,569 before 58,043 | 2% | 48.08 | invalidation 2026-07-01 | 66,938 / 57,756 / 64,751 (30 d) |
| 2026-07-01 | 58,604 | zigzag up, fit 0.77: 0=15,440 A=73,949 B=48,914 | C | down 15,440 before 126,150 | 0% | 0.64 | neither 2026-10-29 | 66,938 / 57,756 / 64,751 (30 d) |

What I read in it, and nothing stronger:

- **The structure holds up as a description.** 2023-01-01 has "five down from 69,138 finished at 15,440" on top, which is the usual reading of that bear. "Zigzag up, finished at 126,150" appears in January 2026 and has stayed.
- **It does not know the big turns in advance.** On 2025-07-01 the top count said "W5 up, its zone reached, a correction next", and price made new highs. That plan was stopped within 8 days, at the level it named.
- **The far next-degree targets are mostly not tradeable.** "Down 1,625 before 69,138" is what the pull says. Its odds of 0% within the horizon are the honest part. Those rows say the arithmetic is unreachable, not that a crash is due.
- **Invalidation levels are clear.** When a plan in the table went wrong, it was stopped at its named level. That is what the rulebook and the research both value them for. Nothing here shows the ranking adds anything.
- **Early dates show a Bybit artefact.** "0=6,466" in the 2024 rows is Bybit's first days of data in 2020, not a real low. Use `--venue bitstamp_btcusd` for older structure.

## Against random paths

Your rule is that every statistic goes against a null, so I ran the same code on 20 sign-flipped paths: Bybit's own 15m bars, each with a random direction, which keeps the volatility and removes direction. The 1D root at today's date, script in scratch. This is one date and 20 paths, so a rough check only.

| | BTC | Random, median | Random, range |
|---|---|---|---|
| Top root fit | 0.823 | 0.793 | 0.771 to 0.829 |
| Third root fit | 0.771 | 0.772 | 0.627 to 0.797 |
| Legal readings at the root | 497 | 422 | 122 to 1,124 |
| Distinct states at the root | 97 | 112 | 49 to 171 |
| Other/unclear share | 93% | 94% | 90% to 96% |
| Mean fit of the 4H nodes | 0.802 | 0.739 | 0.643 to 0.786 |
| Mean fit of the 1H nodes | 0.750 | 0.715 | 0.635 to 0.774 |
| Mean fit of the 15m nodes | 0.704 | 0.715 | 0.602 to 0.762 |

**A random path gets counts that fit about as well, in about as many readings.** BTC's top fit is near the top of the random range, and its 4H mean is above all 20, but that is one date, several rows and few paths, so I read nothing into it. This matches the research: a good fit is not evidence the market is doing what the count says.

## Honest limits

- **Fit is not validated as anything.** Its items added nothing over volatility in the research (0 of 60 comparisons), and the weights are my judgement. It tells you which legal count follows the book best. Do not size from it.
- **The odds are a floor, not a forecast.** They use no drift and no wave information. They have not been calibrated forward for these levels.
- **A zigzag stands in for your eye.** It finds pivots mechanically, so a pivot you would draw can be missing at every threshold, and then no count can use it.
- **Sub-wave checks are generous.** A single leg is accepted at any degree, because its inside is not visible, and a 5 may show as 3 legs. The separate check one frame down only ranks.
- **Not found:** overlap-less diagonals, expanding triangles, W-X-Y-X-Z, order blocks, TDI bands.
- **Crossroads rarely appear.** The counts come from different roots and the root keeps both directions. When there is none, the Y levels are the useful line. Today there is none on any frame.
- **The share is small on purpose.** 7% for the top 3 is not a bug.
- **Bybit starts in March 2020,** so its older roots cannot see the 2018 low.
- **Chart display:** 15m bars on the chart are capped at 365 days by the site export, so a 15m label older than that falls off the left edge. No such label exists in today's tree.
- **No forward log.** Nothing stores these trees yet, so none of this can be scored later. If you want the board tested, that is the next thing to add.

## Checks

- `uv run pytest -q`: the count tests cover rule breaks, planted impulses, zigzags and flats, nesting against the parent, causality (cut data, walk-forward and rewritten future all agree), determinism, and the barrier against Monte Carlo. No network, no real data.
- `node tools/shots_counts.mjs` from `tools/`: every view, console errors, failed requests, the page with no private file, and the public host, which never asks for the file. The public page matched the committed page pixel for pixel.
