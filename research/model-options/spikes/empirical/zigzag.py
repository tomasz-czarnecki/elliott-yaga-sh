"""Causal multi-scale zigzag pivots in log price.

A pivot is the extreme of a leg; it is confirmed on the bar where price has reversed by the threshold from it. The
threshold for bar t is known before bar t (fixed, or k x ATR of the bars up to t-1), and a bar's high and low are visited
in the order they traded, so pivots never repaint: a run on a prefix of the bars gives a prefix of the pivots. The leg in
progress is never returned. check_tools.py tests all of this.

Not a script. pivots(series, scale) returns the pivots of one Series and Scale; zigzag_raw works on bare arrays for the
null paths.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    from numba import njit
except ImportError:  # slow, but the code still runs
    def njit(f=None, **_):
        return f if f is not None else (lambda g: g)

from common import ATR_N, Scale, Series


@njit
def _zigzag(hi: np.ndarray, lo: np.ndarray, high_first: np.ndarray, thr: np.ndarray):
    n = hi.size
    cap = 2 * n + 2
    p_i = np.empty(cap, np.int64)
    p_c = np.empty(cap, np.int64)
    p_x = np.empty(cap, np.float64)
    p_k = np.empty(cap, np.int8)
    m = 0
    direction = 0  # 0 not started, +1 in an up leg (tracking the high), -1 in a down leg
    run_hi, run_hi_i, run_lo, run_lo_i = hi[0], 0, lo[0], 0
    e, e_i = 0.0, 0
    for t in range(n):
        th = thr[t]
        ready = th == th  # not NaN
        for step in range(2):
            is_high = (step == 0) == bool(high_first[t])
            x = hi[t] if is_high else lo[t]
            if direction == 0:
                if is_high:
                    if x > run_hi:
                        run_hi, run_hi_i = x, t
                    if ready and x - run_lo >= th:
                        p_i[m], p_c[m], p_x[m], p_k[m] = run_lo_i, t, run_lo, -1
                        m += 1
                        direction, e, e_i = 1, x, t
                else:
                    if x < run_lo:
                        run_lo, run_lo_i = x, t
                    if ready and run_hi - x >= th:
                        p_i[m], p_c[m], p_x[m], p_k[m] = run_hi_i, t, run_hi, 1
                        m += 1
                        direction, e, e_i = -1, x, t
            elif direction == 1:
                if is_high:
                    if x > e:
                        e, e_i = x, t
                elif ready and e - x >= th:
                    p_i[m], p_c[m], p_x[m], p_k[m] = e_i, t, e, 1
                    m += 1
                    direction, e, e_i = -1, x, t
            else:
                if not is_high:
                    if x < e:
                        e, e_i = x, t
                elif ready and x - e >= th:
                    p_i[m], p_c[m], p_x[m], p_k[m] = e_i, t, e, -1
                    m += 1
                    direction, e, e_i = 1, x, t
    return p_i[:m], p_c[:m], p_x[:m], p_k[:m]


@njit
def atr_log(hi: np.ndarray, lo: np.ndarray, c: np.ndarray, n: int) -> np.ndarray:
    """Wilder ATR of the log true range. Element t uses bars up to and including t."""
    size = hi.size
    out = np.full(size, np.nan)
    total = 0.0
    prev = c[0]
    value = np.nan
    for t in range(size):
        tr = max(hi[t] - lo[t], abs(hi[t] - prev), abs(lo[t] - prev)) if t else hi[t] - lo[t]
        prev = c[t]
        if t < n:
            total += tr
            if t == n - 1:
                value = total / n
                out[t] = value
        else:
            value = (value * (n - 1) + tr) / n
            out[t] = value
    return out


def thresholds(scale: Scale, hi: np.ndarray, lo: np.ndarray, c: np.ndarray) -> np.ndarray:
    """The log threshold for each bar, using only earlier bars. NaN during the ATR warm-up: no reversal is called then."""
    if scale.kind == "pct":
        return np.full(hi.size, np.log1p(scale.value / 100))
    atr = atr_log(hi, lo, c, ATR_N)
    out = np.empty(hi.size)
    out[0] = np.nan
    out[1:] = scale.value * atr[:-1]
    return out


@dataclass(frozen=True)
class Pivots:
    """Alternating confirmed pivots. i: bar of the extreme; confirmed: bar on which it became known (usable after that
    bar's close); x: log price; kind: +1 high, -1 low."""
    i: np.ndarray
    confirmed: np.ndarray
    x: np.ndarray
    kind: np.ndarray

    def __len__(self) -> int:
        return self.i.size


def zigzag_raw(hi, lo, c, high_first, scale: Scale) -> Pivots:
    return Pivots(*_zigzag(hi, lo, high_first, thresholds(scale, hi, lo, c)))


def pivots(series: Series, scale: Scale) -> Pivots:
    if series.tf != scale.tf:
        raise ValueError(f"scale {scale.name} on {series.tf} bars")
    return zigzag_raw(series.h, series.l, series.c, series.high_first, scale)
