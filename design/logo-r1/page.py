"""Writes logos.html, the comparison page. Called by build.py."""

META = {
    "five-strokes": ("Five Strokes", "Count the strokes in </>. There are five, and the middle one is the longest. The yaga tag was an impulse all along."),
    "bracket-impulse": ("Bracket Impulse", "The literal sibling: the yaga tag with the broom swapped for a rulebook impulse."),
    "one-line": ("One Line", "The whole 5-3 cycle drawn in one stroke, in rulebook proportions, nothing else."),
    "broom-candle": ("Broom Candle", "A broom standing on its bristles has the shape of a candle: long upper wick, small body."),
    "fib-lattice": ("Fib Lattice", "An architect's section: solid ground under the impulse, cut along its own Fibonacci levels in price and time."),
    "side-eye": ("Side-Eye", "Pani Yaga reads your count over her glasses. Her fringe is an impulse, her grey streak is wave 3."),
    "broom-five": ("Broom Five", "The witch is riding the wave: the first four legs are the flight path, wave 5 is the broom."),
    "loaded-die": ("Loaded Die", "Five amber pips, three coral, one empty cell. 5-3 against chance, and the empty cell is the other/unclear share."),
}

BASE_NAME = "Baseline: current yaga mark"
BASE_IDEA = "Borrowed from yaga.sh. A raster at 128 px, and nothing in it says Elliott or Bitcoin."

TOP3 = ["five-strokes", "broom-candle", "loaded-die"]


def anatomy(name, DARK, PRICE, TIME, PRICE_ABC, TIME_ABC, fit, five_points, n):
    """Labels over the master, in the mark's 64-unit space, so the construction can be checked."""
    t = []
    guides = ""

    def lab(x, y, s, a="middle", c=DARK["ink"]):
        t.append(f'<text x="{n(x)}" y="{n(y)}" text-anchor="{a}" fill="{c}">{s}</text>')

    if name == "five-strokes":
        pts = five_points()
        for i, (dx, dy) in enumerate([(-6, -3), (-6, 5), (8, 2), (6, -3), (6, 5)]):
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            lab((ax + bx) / 2 + dx, (ay + by) / 2 + dy, str(i + 1))
        lab(32, 68, "stroke 3 = 1.618 x stroke 1", c=DARK["amber"])
    elif name == "bracket-impulse":
        for i, (x, y) in enumerate(fit(TIME, PRICE, 18, 7, 46, 57)):
            lab(x + (3.6 if i % 2 == 0 else -3.6), y + (1 if i else 5), str(i))
    elif name == "one-line":
        for s, (x, y), up in zip("012345ABC", fit(TIME_ABC, PRICE_ABC, 3, 13, 61, 51), [0, 1, 0, 1, 0, 1, 0, 1, 0]):
            lab(x, y - 5 if up else y + 7, s)
    elif name == "broom-candle":
        lab(53, 12, "wick", "start")
        lab(62, 52, "body", "start", DARK["amber"])
        lab(18, 66, "two ordinary candles", c=DARK["grey"])
    elif name == "fib-lattice":
        pts = fit(TIME, PRICE, 2, 2, 62, 62)
        for v, (x, y) in zip(PRICE[1:], pts[1:]):
            lab(65, y + 1, str(v), "start", DARK["grey"])
        for i, (v, (x, y)) in enumerate(zip(TIME[1:], pts[1:])):
            lab(x, 66.5 if i % 2 == 0 else 70, str(v), c=DARK["grey"])
    elif name == "side-eye":
        lab(32, -1, "wave 3 = grey streak", c=DARK["grey"])
        lab(32, 66, "both pupils right, lids flat", c=DARK["amber"])
    elif name == "broom-five":
        for i, (x, y) in enumerate(fit(TIME[:5], PRICE[:5], 4, 16, 42, 61)[1:4]):
            lab(x, y - 5 if i != 1 else y + 7, str(i + 1))
        lab(36, 42, "4", c=DARK["bg"])
        lab(56, 8, "5", "end")
    elif name == "loaded-die":
        lab(32, 68, "5 impulse, 3 correction, 1 other/unclear", c=DARK["amber"])
    href = f"{name}/mark.svg"
    return (f'<svg class="anatomy" viewBox="-8 -6 92 78" aria-hidden="true"><image href="{href}" width="64" height="64"/>'
            f'{guides}<g font-family="Geist Mono, monospace" font-size="2.8">{"".join(t)}</g></svg>')


def header(mark, label="elliott.yaga.sh"):
    # Same markup as site/index.html.
    return f'''<header class="site-header"><div class="site-header-inner">
      <div class="site-brand"><a href="#top" class="brand"><img class="brand-mark" src="{mark}" width="128" height="128" alt=""><span class="brand-name">{label}</span></a></div>
      <a href="#top" class="btn btn-dark btn-sm">Open the chart</a>
    </div></header>'''


def bar():
    # Same markup as site/index.html: the mark stays yaga's here, because the link goes to yaga.sh.
    return '''<div class="yaga-bar"><div class="yaga-bar-inner"><a class="yaga-bar-link" href="#top">
      <svg class="yaga-bar-arrow" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 4L6 8l4 4"/></svg>
      <img class="yaga-bar-mark" src="baseline/yaga-mark-dark.webp" width="128" height="128" alt=""><span>Back to <strong>yaga.sh</strong></span></a></div></div>'''


def tab(icon, light=False):
    cls = "tab light" if light else "tab"
    return f'<div class="{cls}"><img src="{icon}" width="16" height="16" alt=""><span>Elliott waves on Bitcoin</span></div>'


def row(title, idea, m, m16, m16l, mlight, cut, lock_light, anat, rank=None):
    r = f'<span class="rank">{rank}</span>' if rank else ""
    lock = f'<img class="lockup-light" src="{lock_light}" height="36" alt="">' if lock_light else f'<span class="brand light-brand"><img class="brand-mark" src="{mlight}" alt=""><span class="brand-name">elliott.yaga.sh</span></span>'
    return f'''<article class="concept">
  <h2>{r}{title}</h2>
  <p class="idea">{idea}</p>
  {header(m)}
  <div class="grid">
    <figure class="sizes">
      <div class="size"><img src="{m16}" width="16" height="16" alt=""><figcaption>16{cut}</figcaption></div>
      <div class="size"><img src="{m}" width="32" height="32" alt=""><figcaption>32</figcaption></div>
      <div class="size"><img src="{m}" width="36" height="36" alt=""><figcaption>36 header</figcaption></div>
      <div class="size big"><img src="{m}" width="256" height="256" alt=""><figcaption>256</figcaption></div>
    </figure>
    <div class="side">
      {anat}
      <div class="lighttile"><img src="{mlight}" width="64" height="64" alt="">{lock}</div>
      {tab(m16)}{tab(m16l, True)}
    </div>
  </div>
</article>'''


def write(HERE, CONCEPTS, DARK, LIGHT, PRICE, TIME, PRICE_ABC, TIME_ABC, fit, five_points, n):
    from_ranking = {name: i + 1 for i, name in enumerate(
        ["five-strokes", "broom-candle", "loaded-die", "side-eye", "fib-lattice", "broom-five", "bracket-impulse", "one-line"])}
    arts = [row(BASE_NAME, BASE_IDEA, "baseline/yaga-mark-dark.webp", "baseline/yaga-mark-dark.webp",
                "baseline/yaga-mark.webp", "baseline/yaga-mark.webp", " (scaled)", None, "")]
    for name, fn, small in CONCEPTS:
        title, idea = META[name]
        idea = idea.replace("<", "&lt;").replace(">", "&gt;")
        arts.append(row(title, idea, f"{name}/mark.svg", f"{name}/mark-16.svg", f"{name}/mark-16-light.svg",
                        f"{name}/mark-light.svg", " (optical cut)" if small else " (master)", f"{name}/lockup-light.svg",
                        anatomy(name, DARK, PRICE, TIME, PRICE_ABC, TIME_ABC, fit, five_points, n), from_ranking[name]))
    strip = "".join(f'<a href="#{name}" title="{META[name][0]}"><img src="{name}/mark.svg" width="36" height="36" alt="{META[name][0]}"></a>' for name, _, _ in CONCEPTS)
    top3 = "".join(f'<div class="stack">{bar()}{header(m)}</div>' for m in ["baseline/yaga-mark-dark.webp"] + [f"{name}/mark.svg" for name in TOP3])
    html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Logo round 1 · elliott.yaga.sh</title>
<link rel="icon" href="five-strokes/mark-16.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{ --bg:#0C1526; --surface:#131E33; --ink:#F3F5F9; --body:#BFC9D9; --muted:#93A1B7; --line:#223049; --line-strong:#41516E; --accent:#E8B04A; --sans:'Geist',system-ui,sans-serif; --mono:'Geist Mono',ui-monospace,monospace; --gutter:24px; --max:1200px; --header-h:64px; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font-family:var(--sans); -webkit-font-smoothing:antialiased; }}
main {{ max-width:1200px; margin:0 auto; padding:48px 24px 96px; }}
h1 {{ font-size:40px; font-weight:600; letter-spacing:-.02em; margin:0 0 12px; }}
.lead {{ color:var(--body); font-size:18px; line-height:1.5; max-width:70ch; margin:0 0 24px; }}
.strip {{ display:flex; gap:24px; padding:16px; border:1px solid var(--line); margin-bottom:48px; flex-wrap:wrap; }}
.strip img {{ display:block; }}
.concept {{ border-top:1px solid var(--line-strong); padding:32px 0 48px; }}
.concept h2 {{ font-size:24px; font-weight:600; letter-spacing:-.01em; margin:0 0 4px; }}
.rank {{ font-family:var(--mono); font-size:12px; font-weight:400; color:var(--bg); background:var(--accent); padding:2px 8px; margin-right:12px; vertical-align:3px; }}
.idea {{ color:var(--body); margin:0 0 20px; line-height:1.5; }}
.grid {{ display:grid; grid-template-columns:minmax(0,1fr) 340px; gap:24px; margin-top:20px; }}
.sizes {{ margin:0; display:flex; flex-wrap:wrap; align-items:center; gap:32px; padding:24px; background:var(--surface); border:1px solid var(--line); }}
.size {{ display:flex; flex-direction:column; align-items:center; gap:8px; }}
.size img {{ display:block; }}
.big {{ margin-left:auto; }}
figcaption {{ font-family:var(--mono); font-size:12px; color:var(--muted); white-space:nowrap; }}
.side {{ display:flex; flex-direction:column; gap:12px; }}
.anatomy {{ display:block; width:100%; background:var(--bg); border:1px solid var(--line); }}
.lighttile {{ background:#fff; display:flex; align-items:center; gap:24px; padding:16px; }}
.lighttile .brand {{ color:#0C1526; }}
.lockup-light {{ display:block; }}
.tab {{ display:flex; align-items:center; gap:8px; height:32px; padding:0 12px; background:#223049; color:var(--ink); font-size:12px; }}
.tab.light {{ background:#E7EAF0; color:#0C1526; }}
.tab img {{ display:block; }}
/* Header: copied from site/styles.css */
.site-header {{ background:var(--bg); border:1px solid var(--line); }}
.site-header-inner {{ height:var(--header-h); padding:0 var(--gutter); display:flex; align-items:center; justify-content:space-between; gap:16px; }}
.brand {{ display:flex; align-items:center; gap:8px; min-height:44px; text-decoration:none; color:var(--ink); }}
.brand-mark {{ display:block; width:36px; height:36px; flex:none; }}
.brand-name {{ font-size:16px; font-weight:600; letter-spacing:-.01em; }}
.site-brand {{ display:flex; align-items:center; }}
.btn {{ display:inline-flex; align-items:center; justify-content:center; border:1px solid transparent; border-radius:0; font-weight:500; text-decoration:none; }}
.btn-dark {{ background:var(--ink); color:var(--bg); }}
.btn-sm {{ min-height:44px; padding:0 16px; font-size:14px; }}
#top3 {{ border-top:1px solid var(--line-strong); padding:32px 0 0; }}
#top3 h2 {{ font-size:24px; font-weight:600; margin:0 0 16px; }}
.stack {{ margin-bottom:16px; }}
/* Back-to-yaga bar: copied from site/styles.css */
.yaga-bar {{ background:#161514; border:1px solid #2A2826; border-bottom:0; }}
.yaga-bar-inner {{ height:28px; padding:0 var(--gutter); display:flex; align-items:center; }}
.yaga-bar-link {{ display:inline-flex; align-items:center; gap:6px; color:#C4BFB7; text-decoration:none; font-family:var(--mono); font-size:11px; letter-spacing:.02em; }}
.yaga-bar-link strong {{ color:#F5F4F2; font-weight:500; }}
.yaga-bar-arrow {{ display:block; width:12px; height:12px; flex:none; }}
.yaga-bar-mark {{ display:block; width:16px; height:16px; flex:none; }}
@media (max-width:860px) {{ .grid {{ grid-template-columns:minmax(0,1fr); }} .big {{ margin:0; }} .big img {{ max-width:100%; height:auto; }} h1 {{ font-size:32px; }} .site-header-inner {{ padding:0 12px; }} .btn-sm {{ padding:0 10px; font-size:12px; }} .lighttile {{ flex-wrap:wrap; }} }}
</style>
</head>
<body>
<main id="top">
<h1>Logo round 1</h1>
<p class="lead">Eight concepts for elliott.yaga.sh, beside the mark it borrows today. The numbered tags are the ranking; the reasoning is in PROPOSAL.md. Bracket Impulse, One Line and Fib Lattice are drawn exactly on the NewWave rulebook's levels: W2 .618, W3 1.618, W4 .382, W5 2.236. Sizes render at 1x device pixels on a 1x screen.</p>
<div class="strip">{strip}</div>
{"".join(a.replace('<article class="concept">', f'<article class="concept" id="{i}">', 1) for i, a in zip(["baseline"] + [c[0] for c in CONCEPTS], arts))}
<section id="top3"><h2>Baseline and top three in the real header, with the back-to-yaga bar</h2>{top3}</section>
</main>
</body>
</html>
'''
    (HERE / "logos.html").write_text(html)
