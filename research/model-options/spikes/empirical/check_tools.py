"""Checks of the shared tools, on real bars and synthetic paths. Run before trusting any table:

    uv run --with numpy --with scipy --with numba python research/model-options/spikes/empirical/check_tools.py

 1. Causality: the pivots of a prefix of the bars are a prefix of the pivots of all the bars, confirmed before the cut.
 2. Alternation and that the pivot is the extreme of its leg.
 3. A hand-made impulse passes; each rule breaks when it should, and the right rule is named.
 4. Theory: on a fine driftless Gaussian walk, zigzag legs follow threshold x (1 + Exp(1)), so the ratio of two adjacent
    legs has median 1 and a smooth law with no feature at any Fibonacci level. Measured against that law.
 5. Nulls: shuffle keeps the multiset of bars and the end price; signflip keeps absolute bar ranges in place; day nulls
    aggregate to consistent daily bars.
"""
from __future__ import annotations

import itertools

import numpy as np
from scipy import integrate

from common import SCALES, load_series
from impulse import R1, R2, R3, R4, TRUNCATED, check, first_broken, threes
from nulls import KINDS, null_bars, null_days, to_day_rel, to_rel
from zigzag import Pivots, _zigzag, pivots, zigzag_raw


def test_causal() -> None:
    for tf in ("1d", "4h", "1h"):
        s = load_series(tf=tf)
        for scale in [x for x in SCALES if x.tf == tf]:
            full = pivots(s, scale)
            for frac in (0.3, 0.55, 0.8):
                cut = int(len(s) * frac)
                part = zigzag_raw(s.h[:cut], s.l[:cut], s.c[:cut], s.high_first[:cut], scale)
                known = full.confirmed < cut
                assert len(part) == known.sum(), (scale.name, len(part), known.sum())
                assert np.array_equal(part.i, full.i[known]) and np.array_equal(part.x, full.x[known])
                assert np.array_equal(part.confirmed, full.confirmed[known])
            assert np.all(np.diff(full.kind) != 0), "pivots must alternate"
            assert np.all(full.confirmed >= full.i)
            # A pivot is never exceeded before the bar that confirms it. On that bar itself a later extreme is legitimate.
            for j in range(0, len(full) - 1, max(1, len(full) // 50)):
                a, b = full.i[j], full.confirmed[j]
                if a == b:
                    continue
                if full.kind[j] == 1:
                    assert s.h[a:b].max() <= full.x[j] + 1e-12
                else:
                    assert s.l[a:b].min() >= full.x[j] - 1e-12
    print("causal, alternating, extreme: ok")


def _piv(prices: list[float]) -> Pivots:
    x = np.log(np.array(prices, float))
    kind = np.array([-1 if (j % 2 == 0) == (x[1] > x[0]) else 1 for j in range(len(x))], np.int8)
    i = np.arange(len(x), dtype=np.int64) * 10
    return Pivots(i, i + 1, x, kind)


def test_rules() -> None:
    good = check(_piv([100, 120, 110, 150, 135, 160]))
    assert good.legal[0] and good.direction[0] == 1 and good.flags[0] == 0
    assert abs(good.lin["w2"][0] - 0.5) < 1e-9 and abs(good.lin["w3"][0] - 2.0) < 1e-9
    assert abs(good.lin["w4"][0] - 15 / 40) < 1e-9 and abs(good.lin["w5_014"][0] - 25 / 20) < 1e-9
    assert abs(good.lin["w5_012"][0] - 50 / 20) < 1e-9
    assert check(_piv([100, 120, 99, 150, 135, 160])).flags[0] & R1
    assert check(_piv([100, 120, 110, 118, 113, 160])).flags[0] & R2
    assert check(_piv([100, 130, 120, 135, 131, 170])).flags[0] & R3
    assert check(_piv([100, 120, 110, 150, 119, 160])).flags[0] & R4
    assert check(_piv([100, 120, 110, 150, 135, 145])).flags[0] & TRUNCATED
    down = check(_piv([160, 135, 150, 110, 120, 100]))
    assert down.direction[0] == -1 and (down.flags[0] & (R1 | R2 | R3 | R4)) == 0
    killed = check(_piv([100, 120, 99, 118, 113, 160]))
    assert first_broken(killed.flags)["R1 W2 beyond start of W1"] == 1
    t = threes(_piv([100, 80, 90, 70]))
    assert t.legal[0] and t.direction[0] == -1
    print("rule checker: ok")


def _theory_cdf(r: float) -> float:
    """P(L2/L1 <= r) for independent legs L = 1 + Exp(1)."""
    def inner(l1: float) -> float:
        hi = r * l1
        return (1 - np.exp(-(hi - 1))) * np.exp(-(l1 - 1)) if hi > 1 else 0.0
    return integrate.quad(inner, 1, 60, limit=200)[0]


def test_theory() -> None:
    rng = np.random.default_rng(1)
    steps = rng.normal(0, 1, 4_000_000)
    path = np.cumsum(steps)
    theta = 60.0  # about 60 steps of noise, so discreteness is small
    hf = np.ones(path.size, bool)
    i, c, x, k = _zigzag(path, path, hf, np.full(path.size, theta))
    legs = np.abs(np.diff(x)) / theta
    assert 0.95 < legs.min() < 1.25, legs.min()
    assert abs(legs.mean() - 2) < 0.15, legs.mean()
    ratio = legs[1:] / legs[:-1]
    for r in (0.382, 0.618, 1.0, 1.618):
        emp, th = (ratio <= r).mean(), _theory_cdf(r)
        assert abs(emp - th) < 0.035, (r, emp, th)
        print(f"  theory check: P(R <= {r}) measured {emp:.3f}, law {th:.3f}, legs {legs.size}")
    print("zigzag leg law on a fine random walk: ok")


def test_nulls() -> None:
    s = load_series(tf="4h")
    rel = to_rel(s.o, s.h, s.l, s.c, s.high_first)
    rng = np.random.default_rng(2)
    o, h, l, c, hf = null_bars(rel, "shuffle", rng)
    assert abs(c[-1] - s.c[-1]) < 1e-9
    assert np.allclose(np.sort(h - l), np.sort(s.h - s.l))
    o, h, l, c, hf = null_bars(rel, "signflip", rng)
    assert abs(c[-1] - s.c[-1]) < 1e-9
    assert np.allclose(h - l, s.h - s.l)
    assert np.all(h >= l)
    o, h, l, c, hf = null_bars(rel, "block", rng, block=30)
    assert abs(c[-1] - s.c[-1]) < 1e-9 and np.all(h >= np.maximum(o, c) - 1e-9) and np.all(l <= np.minimum(o, c) + 1e-9)
    rel_t = to_rel(s.o, s.h, s.l, s.c, s.high_first, bars_per_day=6)
    o, h, l, c, hf = null_bars(rel_t, "trendflip", rng)
    assert abs(c[-1] - s.c[-1]) < 1e-9 and np.all(h >= l)
    assert np.allclose(h - l, s.h - s.l, atol=1e-9)
    # The regimes survive: 120-day returns follow BTC's on trendflip paths and do not on signflip paths.
    def follows(kind_rel, kind: str) -> float:
        k = 720
        real = s.c[k:] - s.c[:-k]
        values = []
        for _ in range(5):
            path = null_bars(kind_rel, kind, rng)[3]
            values.append(float(np.corrcoef(real, path[k:] - path[:-k])[0, 1]))
        return float(np.mean(values))

    with_trend, without = follows(rel_t, "trendflip"), follows(rel, "signflip")
    assert with_trend > 0.4 > abs(without), (with_trend, without)

    m = (len(s) // 6) * 6
    first = np.argmax((s.ts // 86_400_000 * 86_400_000) == s.ts)
    m = ((len(s) - first) // 6) * 6
    dr = to_day_rel(s.o[first:first + m], s.h[first:first + m], s.l[first:first + m], s.c[first:first + m],
                    s.high_first[first:first + m], 6)
    for kind in KINDS:
        o, h, l, c, hf = null_days(dr, kind, rng)
        assert abs(c[-1] - s.c[first + m - 1]) < 1e-9, kind
        assert np.all(c[5::6][:-1] - o[6::6] < 0.2), kind  # next day opens near the close before it
        assert np.all(h >= l)
    print("null paths: ok")


def _brute_legal(x: np.ndarray, kind: np.ndarray, e: int, lookback: int) -> int:
    """The free-degree count of a5_ambiguity by plain enumeration, for checking the fast walk."""
    y = x if kind[e] == 1 else -x
    floor = max(e - lookback, 0)
    total = 0
    positions = range(floor, e)
    for p0, p1, p2, p3, p4 in itertools.combinations(positions, 5):
        if (p1 - p0) % 2 == 0 or (p2 - p1) % 2 == 0 or (p3 - p2) % 2 == 0 or (p4 - p3) % 2 == 0 or (e - p4) % 2 == 0:
            continue
        ok = (y[p1:p2 + 1].max() <= y[p1] and y[p1:p2 + 1].min() >= y[p2] and y[p0:p1 + 1].min() >= y[p0] and y[p0:p1 + 1].max() <= y[p1]
              and y[p2:p3 + 1].min() >= y[p2] and y[p2:p3 + 1].max() <= y[p3] and y[p3:p4 + 1].max() <= y[p3] and y[p3:p4 + 1].min() >= y[p4]
              and y[p4:e + 1].min() >= y[p4] and y[p4:e + 1].max() <= y[e])
        if not ok:
            continue
        w1, w3, w5 = y[p1] - y[p0], y[p3] - y[p2], y[e] - y[p4]
        if y[p2] > y[p0] and y[p3] > y[p1] and y[p4] > y[p1] and y[e] > y[p3] and not (w3 <= w1 and w3 <= w5):
            total += 1
    return total


def test_ambiguity() -> None:
    from a5_ambiguity import _legal_counts
    rng = np.random.default_rng(5)
    for trial in range(30):
        walk = rng.normal(0, 1, 2000).cumsum()
        i, c, x, k = _zigzag(walk, walk, np.ones(walk.size, bool), np.full(walk.size, 3.0))
        x, k = x[:30], k[:30]
        fast, _ = _legal_counts(x, k, 20)
        for e in range(x.size):
            assert fast[e] == _brute_legal(x, k, e, 20), (trial, e, fast[e], _brute_legal(x, k, e, 20))
    print("free-degree enumeration matches brute force: ok")


if __name__ == "__main__":
    test_rules()
    test_ambiguity()
    test_theory()
    test_nulls()
    test_causal()
    print("all checks passed")
