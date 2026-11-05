#!/usr/bin/env python3
"""Writes every logo SVG for round 1. Run: python3 design/logo-r1/build.py

Each concept is a few literal shapes on a 64-unit square. The only computed
geometry is the impulse (from the rulebook's levels) and mitred stroke outlines.
"""
import json, math, pathlib

HERE = pathlib.Path(__file__).parent
WORD = json.loads((HERE / "wordmark.json").read_text())
PHI = 1.618

DARK = dict(ink="#F3F5F9", amber="#E8B04A", coral="#E0524A", teal="#2CB7A8", grey="#93A1B7",
            line="#41516E", bg="#0C1526")
LIGHT = dict(ink="#0C1526", amber="#B27A12", coral="#D5443C", teal="#148A7D", grey="#5C6B84",
             line="#B9C3D3", bg="#FFFFFF")

# The canonical impulse. NewWave rulebook v2.0c: W2 retraces .618, W3 = 1.618 ext of 0-1-2,
# W4 retraces .382 of W3, W5 = 2.236 ext of 0-1-2. Time: W2 = .618 W1, W3 = 1.618 W1, W4 = W2, W5 = W1.
PRICE = [0, 1, .382, 2, 1.382, 2.618]
TIME = [0, 1, 1.618, 3.236, 3.854, 4.854]
# Zigzag after it: A = 1, B retraces .618, C = A. Ends at a .528 retrace of 0-5.
PRICE_ABC = PRICE + [1.618, 2.236, 1.236]
TIME_ABC = TIME + [5.854, 6.472, 7.472]


def n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def fit(xs, ys, x0, y0, x1, y1):
    """Lattice to box. y1 is the bottom, price runs upward."""
    sx, sy = (x1 - x0) / max(xs), (y1 - y0) / max(ys)
    return [(x0 + x * sx, y1 - y * sy) for x, y in zip(xs, ys)]


def d(pts):
    return "M" + " ".join(f"{n(x)} {n(y)}" for x, y in pts)


def line(pts, color, w, extra=""):
    return f'<path d="{d(pts)}" fill="none" stroke="{color}" stroke-width="{n(w)}" stroke-miterlimit="12"{extra}/>'


def rect(x, y, w, h, color, extra=""):
    return f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="{color}"{extra}/>'


def poly(pts, color):
    return f'<path d="{d(pts)}Z" fill="{color}"/>'


def mitre_quads(pts, w):
    """One polygon per leg of a mitred polyline, so legs can take different colours and still share the joint."""
    h = w / 2
    dirs = []
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        L = math.hypot(bx - ax, by - ay)
        dirs.append(((bx - ax) / L, (by - ay) / L))
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        d0 = dirs[max(i - 1, 0)]
        d1 = dirs[min(i, len(dirs) - 1)]
        tx, ty = d0[0] + d1[0], d0[1] + d1[1]
        L = math.hypot(tx, ty)
        tx, ty = tx / L, ty / L
        nx, ny = -ty, tx
        k = h / (nx * -d1[1] + ny * d1[0])
        left.append((x + nx * k, y + ny * k))
        right.append((x - nx * k, y - ny * k))
    return [[left[i], left[i + 1], right[i + 1], right[i]] for i in range(len(pts) - 1)]


# ---------------------------------------------------------------- concepts
# Each returns inner SVG for a palette p. `small` is an optical cut for 16 px, used only where the master fails there.

def five_points():
    # `</>` as one line. Slash = 1.618 x a bracket stroke: h 20, d 18, g 17.1.
    return [(23.45, 12), (5.45, 32), (23.45, 52), (40.55, 12), (58.55, 32), (40.55, 52)]


def five(p):
    pts = five_points()
    return line(pts, p["coral"], 8) + poly(mitre_quads(pts, 8)[2], p["amber"])


def bracket_impulse(p, w=5.5):
    z = fit(TIME, PRICE, 18, 7, 46, 57)
    return (line([(15, 20), (4.5, 32), (15, 44)], p["coral"], 6.5)
            + line([(49, 20), (59.5, 32), (49, 44)], p["coral"], 6.5)
            + line(z, p["amber"], w))


def bracket_impulse_small(p):
    z = fit(TIME, PRICE, 14, 4, 50, 60)
    return (line([(12.5, 22), (4.5, 32), (12.5, 42)], p["coral"], 7)
            + line([(51.5, 22), (59.5, 32), (51.5, 42)], p["coral"], 7)
            + line(z, p["amber"], 5.5))


def one_line(p, w=4.5, x0=3, x1=61, y0=13, y1=51):
    pts = fit(TIME_ABC, PRICE_ABC, x0, y0, x1, y1)
    q = mitre_quads(pts, w)
    return line(pts, p["ink"], w) + "".join(poly(a, p["amber"]) for a in q[5:])


def one_line_small(p):
    return one_line(p, 6, 3, 61, 9, 56)


def broom_candle(p):
    # On a 4-unit grid, so the candles land on whole pixels at 16.
    out = rect(4, 36, 12, 16, p["teal"]) + rect(8.5, 28, 3, 32, p["teal"])
    out += rect(20, 28, 12, 14, p["coral"]) + rect(24.5, 20, 3, 28, p["coral"])
    # The broom: handle = upper wick, bristles = body, tails = lower wick.
    out += rect(46, 2, 4, 36, p["ink"])
    out += "".join(rect(x, y, l, 1, p["line"]) for x, y, l in
                   [(46, 8, 2.2), (47.8, 15, 2.2), (46, 22, 1.8), (48.1, 29, 1.9)])
    out += rect(42, 37, 12, 4, p["coral"])
    out += poly([(42, 41), (54, 41), (60, 61), (36, 61)], p["amber"])
    out += "".join(line([(a, 45), (b, 61.5)], p["bg"], 1.3) for a, b in [(45.5, 43.5), (48, 48), (50.5, 52.5)])
    return out


def broom_candle_small(p):
    return (rect(4, 32, 12, 20, p["teal"]) + rect(8, 24, 4, 36, p["teal"])
            + rect(20, 24, 12, 16, p["coral"]) + rect(24, 16, 4, 32, p["coral"])
            + rect(44, 0, 4, 36, p["ink"]) + rect(40, 36, 12, 4, p["coral"]) + rect(36, 40, 20, 24, p["amber"]))


def fib_lattice(p):
    # Section drawing: the ground under the impulse is solid, every Fibonacci level is cut through it.
    pts = fit(TIME, PRICE, 2, 2, 62, 62)
    ground = poly(pts + [(62, 62)], p["amber"])
    cuts = "".join(f"M{n(x)} 2V62M2 {n(y)}H62" for x, y in pts[1:5])
    return (f'<path d="{cuts}" fill="none" stroke="{p["line"]}" stroke-width=".75"/>' + ground
            + f'<clipPath id="g"><path d="{d(pts + [(62, 62)])}Z"/></clipPath>'
            + f'<path d="{cuts}" clip-path="url(#g)" fill="none" stroke="{p["bg"]}" stroke-width="1.4"/>')


def fib_lattice_small(p):
    return poly(fit(TIME, PRICE, 0, 0, 64, 64) + [(64, 64)], p["amber"])


def side_eye(p):
    fringe = [(4, 31), (12, 14), (19, 25), (38, 8), (45, 20), (60, 10)]
    q = mitre_quads(fringe, 6.5)
    hair = line(fringe, p["coral"], 6.5) + poly(q[2], p["grey"])
    sw, r = 4.5, 11.5
    specs = f'<g fill="none" stroke="{p["ink"]}" stroke-width="{sw}">'
    specs += f'<circle cx="17" cy="47" r="{r}"/><circle cx="47" cy="47" r="{r}"/><path d="M28 45H36"/></g>'
    pr = 4.4
    # Both pupils pushed right under a flat lid: she does not believe the count.
    eyes = f'<circle cx="21" cy="48.5" r="{pr}" fill="{p["amber"]}"/><circle cx="51" cy="48.5" r="{pr}" fill="{p["amber"]}"/>'
    lids = line([(7, 41), (27, 43.5)], p["ink"], 3) + line([(37, 43.5), (57, 41)], p["ink"], 3)
    return hair + specs + eyes + lids


def side_eye_small(p):
    # Pixel-fitted: rings 1 px wide, pupils 2 px square, everything on the 4-unit grid.
    return (line([(3, 27), (12, 10), (20, 21), (37, 6), (44, 17), (61, 7)], p["coral"], 6)
            + f'<g fill="none" stroke="{p["ink"]}" stroke-width="4"><circle cx="16" cy="46" r="10"/><circle cx="48" cy="46" r="10"/><path d="M28 42H36"/></g>'
            + rect(16, 44, 8, 8, p["amber"]) + rect(48, 44, 8, 8, p["amber"]))


def broom_five(p, small=False):
    pts = fit(TIME[:5], PRICE[:5], 4, 16, 42, 61)
    pts[4] = (42, 36)
    x4, y4 = pts[4]
    tip = (61, 3)
    ang = math.degrees(math.atan2(tip[1] - y4, tip[0] - x4))
    L = math.hypot(tip[0] - x4, tip[1] - y4)
    sw = 6 if small else 4.5
    g = f'<g transform="translate({n(x4)} {n(y4)}) rotate({n(ang)})">'
    g += poly([(0, -4), (0, 4), (-21, 12), (-18, 7), (-23, 4), (-19, 0), (-23, -4), (-18, -7), (-21, -12)], p["amber"])
    if not small:
        g += "".join(line([(-3, y), (-15, y * 3)], p["bg"], 1) for y in (-1.6, 1.6))
    g += rect(0, -5, 4, 10, p["ink"] if small else p["bg"])
    g += rect(.7, -5, 2.6, 10, p["ink"] if small else p["amber"])
    g += rect(4, -sw / 2, L - 4, sw, p["ink"])
    return line(pts, p["coral"], 7 if small else 5) + g + "</g>"


def broom_five_small(p):
    return broom_five(p, True)


def loaded_die(p, small=False):
    # 16 x 16 pixel grid x 4: frame 1, pad 2, pip 2, gap 2. crispEdges keeps it sharp at sizes off that grid, like 36.
    out = f'<g shape-rendering="crispEdges"><path d="M2 2H62V62H2Z" fill="none" stroke="{p["ink"]}" stroke-width="4"/>'
    for x, y in [(12, 12), (44, 12), (28, 28), (12, 44), (44, 44)]:
        out += rect(x, y, 8, 8, p["amber"])
    for x, y in [(28, 12), (12, 28), (44, 28)]:
        out += rect(x, y, 8, 8, p["coral"])
    if not small:
        # The ninth cell: the "other/unclear" share.
        out += f'<path d="M28.75 44.75H35.25V51.25H28.75Z" fill="none" stroke="{p["line"]}" stroke-width="1.5"/>'
    return out + "</g>"


def loaded_die_small(p):
    return loaded_die(p, True)


CONCEPTS = [
    ("five-strokes", five, None),
    ("bracket-impulse", bracket_impulse, bracket_impulse_small),
    ("one-line", one_line, one_line_small),
    ("broom-candle", broom_candle, broom_candle_small),
    ("fib-lattice", fib_lattice, fib_lattice_small),
    ("side-eye", side_eye, side_eye_small),
    ("broom-five", broom_five, broom_five_small),
    ("loaded-die", loaded_die, loaded_die_small),
]


def svg(inner, w=64, h=64, title="elliott.yaga.sh"):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n(w)} {n(h)}" role="img" aria-label="{title}">'
            f"\n{inner}\n</svg>\n")


def lockup(inner, p):
    """Header lockup at its real proportions: 36 mark, 8 gap, 16 px Geist 600, outlined."""
    k = 36 / 64
    base = 18 + WORD["x_height"] / 2
    return svg(f'<g transform="scale({k})">{inner}</g>\n'
               f'<path transform="translate(44 {n(base)})" d="{WORD["d"]}" fill="{p["ink"]}"/>',
               44 + WORD["width"], 36)


def main():
    for name, fn, small in CONCEPTS:
        out = HERE / name
        out.mkdir(exist_ok=True)
        (out / "mark.svg").write_text(svg(fn(DARK)))
        (out / "mark-light.svg").write_text(svg(fn(LIGHT)))
        (out / "lockup.svg").write_text(lockup(fn(DARK), DARK))
        (out / "lockup-light.svg").write_text(lockup(fn(LIGHT), LIGHT))
        s = small or fn
        (out / "mark-16.svg").write_text(svg(s(DARK)))
        (out / "mark-16-light.svg").write_text(svg(s(LIGHT)))
    import sys
    sys.dont_write_bytecode = True
    import page
    page.write(HERE, CONCEPTS, DARK, LIGHT, PRICE, TIME, PRICE_ABC, TIME_ABC, fit, five_points, n)


if __name__ == "__main__":
    main()
