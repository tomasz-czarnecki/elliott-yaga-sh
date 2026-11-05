# Logo round 1 for elliott.yaga.sh

Open `logos.html` for the comparison (`python3 -m http.server 8083 --bind 127.0.0.1 --directory design/logo-r1`). Each concept folder holds `mark.svg`, `mark-light.svg`, `mark-16.svg`, `mark-16-light.svg`, `lockup.svg` and `lockup-light.svg`.

## Recommendation

**Five Strokes.** Count the strokes in `</>`: five, with a long one in the middle. An impulse has five waves and, in the rulebook, wave 3 is never the shortest. So the yaga tag needs no added chart. It only needs to be read as a count. It is the one concept that could only belong to this site and this family, and it is the only top candidate that needs no separate 16 px drawing.

Runner-up: **Broom Candle**. It is the funniest and has the best 16 px cut of the character ideas. If Tomasz wants more witch and less cleverness, take this one. It would also work as a secondary graphic on the og image even if Five Strokes wins.

## Ranking

1. Five Strokes
2. Broom Candle
3. Loaded Die
4. Side-Eye
5. Fib Lattice
6. Broom Five
7. Bracket Impulse
8. One Line

## Concepts

Ratings for 16 px come from renders at one device pixel, enlarged without smoothing (`shots/qa_sizes.png`).

### 1. Five Strokes (family-true)
- **Idea:** `</>` drawn as one continuous line, each stroke a wave. Stroke 3, the slash, takes the place of the broom and is exactly 1.618 times the bracket strokes.
- **Why it fits:** keeps yaga's coral brackets, adds the site's amber, and has the mischief he likes: the company's own tag was an impulse all along. No crypto signals in it.
- **Risks:** the idea needs one sentence of explanation. It is a stroke count, not a chart: the line runs backwards in x, so read as price it is not a valid impulse. An Elliott purist may point that out, and the sentence should say so first. It also loses the broom, so the witch is gone.
- **16 px:** good, master used unchanged. Reads as a tag; the amber slash survives.

### 2. Broom Candle (candlestick)
- **Idea:** two ordinary candles and a third that is a broom standing on its bristles. Handle is the wick, bristles are the body.
- **Why it fits:** one joke, instantly seen, tying the mascot to the subject. Teal and coral are the site's own candle colours. Birch flecks and a red cord echo the yaga broom.
- **Risks:** three candles at a glance is the most common trading icon, and only the broom rescues it. The candle colours add a third and fourth hue. A chart reader will notice that a long upper wick on a small body is a known bearish shape, which suits the site's scepticism but is not a claim we should make.
- **16 px:** very good with its optical cut, which sits on whole pixels. The broom becomes a line on a block, so it reads as a candle there and not as a broom. The joke needs 32 px or more.

### 3. Loaded Die (wildcard)
- **Idea:** a square die with eight pips that no die has: five amber in the 5 pattern, three coral, and one cell left empty. That is 5-3 against chance, and the empty cell is the "other/unclear" share the project must always report.
- **Why it fits:** it is the site's actual question, whether the structure beats chance, in one image. It is the opposite of a signals brand. Pure pixel grid: frame 1, pad 2, pip 2, gap 2 at 16 px.
- **Risks:** the least like a yaga sibling, sharing only colour. Square pips can read as an app grid or keypad before they read as a die. Dice next to Bitcoin can suggest gambling, which is the joke but will not land for everyone. The story cannot be guessed from the mark.
- **16 px:** the crispest of all eight. At 36 px it relies on `crispEdges`, so pip gaps can differ by a pixel; if chosen, render it at 32 or 48 px in the header.

### 4. Side-Eye (Pani Yaga)
- **Idea:** only her glasses and fringe. Both pupils slide right under flat lids, she does not believe your count. The fringe is an impulse and her grey streak is wave 3.
- **Why it fits:** the most character of the set, and the mascot's scepticism is the site's stance.
- **Risks:** a lot of parts for a small mark. Round lenses are the one break from the square language, kept because square glasses stop being hers. It could drift to a generic cartoon if she is not already known, and it is unclear whether it should be shared across the family.
- **16 px:** fair. A pixel-fitted cut keeps rings and pupils, but the fringe is only a wiggle.

### 5. Fib Lattice (construction)
- **Idea:** an architect's section. Solid ground under the impulse, with every pivot's price and time level cut through it and carried on as a thin construction line above.
- **Why it fits:** the construction grid is the mark, and its labels on the comparison page can be checked against the rulebook. It should appeal to the parametric architect.
- **Risks:** still an area chart with lines on it, which is the closest of the set to stock analytics. The thin lines go dim at header size and the cuts look slightly busy there. The cuts also split each peak.
- **16 px:** good as a silhouette, but its optical cut drops the whole grid, so the idea is gone.

### 6. Broom Five (broom riding the wave)
- **Idea:** the first legs of the impulse are the flight path, and wave 5 is the broom.
- **Why it fits:** vector broom, moving subject, clear story at large sizes.
- **Risks:** the bristles cover most of wave 4, so the count is hard to read. The amber wedge is close to a traffic cone at small sizes. An upward-flying object with a rising line also comes nearer the "to the moon" look than I would like.
- **16 px:** weak. Red zigzag and a wedge merge.

### 7. Bracket Impulse (family-true, literal)
- **Idea:** the yaga tag, with the broom swapped for a rulebook impulse.
- **Why it fits:** the safest sibling, understood at once by anyone who has seen yaga.sh.
- **Risks:** the steep amber zigzag reads as a lightning bolt, which is a crypto-brand cliche. It is the obvious answer, and Five Strokes makes the same family point without adding anything.
- **16 px:** weak. Even in the optical cut, the zigzag turns to a blur between two brackets.

### 8. One Line (pure wave)
- **Idea:** the full 5-3 cycle in one mitred stroke, white for the impulse and amber for A-B-C.
- **Why it fits:** the most honest statement of the subject and very quiet in a header.
- **Risks:** it looks like every trading app's logo, which is what he dislikes. No family link. Eight legs need width, so the mark sits low in its square and looks small.
- **16 px:** weak. Reads as a generic squiggle.

## Decisions I made

- **Proportions come from the NewWave rulebook, not textbook values** (v2.0c; the vault copy and the skill snapshot are identical). Price: W2 retraces .618, W3 = 1.618 and W5 = 2.236 extensions of 0-1-2, W4 retraces .382 of W3, so W4 stays above W1. Time: W2 = W4 = .618 of W1, W3 = 1.618, W5 = 1. A-B-C in One Line: A = 1, B retraces .618, C = A, ending at a .528 retrace of 0-5. Bracket Impulse, One Line and Fib Lattice sit exactly on these levels. Broom Five keeps them through wave 3, and Side-Eye's fringe is drawn by eye. These are a single template chosen to look good, not a claim about what BTC does.
- **Colours:** site palette, plus yaga's coral (#E0524A) for family marks in place of the site's candle red. Light-background versions use darker amber (#B27A12) and coral (#D5443C) because the originals are too weak on white.
- **Square corners and mitred joints everywhere**, except Side-Eye's lenses and pupils.
- **Separate 16 px drawings** for seven of the eight concepts. Only Five Strokes uses its master. The page labels which is which.
- **All vector**, no broom raster. The wordmark is Geist 600 converted to paths with the site's tracking, so `lockup*.svg` needs no font. The site itself can keep live text.
- **`build.py` writes the SVGs and the page.** The shapes are written out by hand; the code only adds the impulse and mitre arithmetic. This is a working convenience, not something the site needs.

## What is weak in this round

- **Nothing here has been seen by anyone but me.** Whether Five Strokes reads as more than a heavy `</>` before it is explained is an open question. Show it to someone without the sentence.
- Bracket Impulse, One Line and Broom Five do not hold up at 16 px, and I would not take them further.
- Side-Eye's fringe and the Fib Lattice construction lines are both thin in the header.
- I compared only with the yaga mark files, not beside the live yagalabs.io and game.yaga.sh headers.
- `site/` gained the back-to-yaga bar while I was working. It is another session's uncommitted work, so the plan and the last section of the page match it as of now, and the plan should be rechecked against `site/` when it is carried out.

## Integration plan (not done)

For the chosen concept, say `five-strokes`:

1. **Assets:** add to `site/assets/`: `elliott-mark.svg` (master), `favicon.svg`, `favicon-32.png`, `apple-touch-icon.png` (180 px, on #0C1526 with about 15% padding, since iOS rounds and masks the corners), and `og.png` (1200 x 630).
2. **`site/index.html` and `site/chart.html`:**
   - Header: change `.brand-mark` to `assets/elliott-mark.svg`; keep the existing `width`, `height` and `alt`, updating the numbers to 36. The `.brand-name` text stays.
   - Head: replace `<link rel="icon" href="assets/yaga-mark-dark.webp">` with `<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">`, `<link rel="icon" href="assets/favicon-32.png" sizes="32x32">` and `<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">`.
   - Head: neither page has an `og:image` today, so add `og:image`, `og:title`, `og:description` and `twitter:card`.
3. **`site/styles.css`:** no change for a square mark at 36 px. Loaded Die would change `.brand-mark` to 32 px.
4. **`site/assets/yaga-mark-dark.webp`: keep it.** The back-to-yaga bar (`.yaga-bar-mark`) and the footer's Yaga.sh link (`.footer-mark`) point at yaga.sh, so they should keep showing yaga's mark. Only `.brand-mark` and the favicon change. The two marks then stack directly: yaga's at 16 px in the bar, this one at 36 px under it. `logos.html` shows that pairing in its last section.
5. **og image:** navy background, mark at about 280 px on the left, wordmark and the line "Do Elliott waves hold up on Bitcoin?" on the right. For Five Strokes, add the labels 1 to 5 from the anatomy panel, since this is where the idea can be explained.
6. **Family:** yaga.sh could list the experiment with this mark. Editing it is out of scope here.
7. **Checks:** `tools/shots_site.mjs`, then look at the header, chart page and a real browser tab on both light and dark browser themes.
