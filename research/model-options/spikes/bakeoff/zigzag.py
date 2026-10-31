"""Causal zigzag pivots, and the indicators computed from past bars only.

A swing extreme becomes a pivot only when price has moved back from it by the threshold. `conf_i` is the bar whose
close first shows that; nothing may use the pivot before that bar has closed. The running extreme after the last
confirmed pivot is provisional and is returned separately.

The threshold is k x ATR(n), in log price, read from the bar before the one being processed. Inside a bar the 1-minute
derived `hl_order` says whether the high or the low came first; when unknown, the extension of the current leg goes
first. A bar can therefore confirm two pivots when it holds both a reversal and a reversal of that reversal.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ewave.data import load_bars

HIGH_FIRST, LOW_FIRST, UNKNOWN = 1, -1, 0


@dataclass(frozen=True)
class Pivot:
    i: int        # bar of the extreme
    kind: str     # "H" or "L"
    price: float
    conf_i: int   # bar whose close confirmed it


@dataclass
class Series:
    ts: np.ndarray      # ms, bar open
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    order: np.ndarray   # HIGH_FIRST / LOW_FIRST / UNKNOWN
    tf_ms: int

    def __len__(self) -> int:
        return len(self.ts)

    def slice(self, a: int, b: int) -> "Series":
        return Series(self.ts[a:b], self.open[a:b], self.high[a:b], self.low[a:b], self.close[a:b], self.order[a:b], self.tf_ms)


TF_MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}


def load_series(venue: str, tf: str, start: str = "2000-01-01", end: str = "2100-01-01") -> Series:
    df = load_bars(venue, tf, start, end, complete_only=True)
    order = df["hl_order"].to_list()
    code = np.array([HIGH_FIRST if x == "high_first" else LOW_FIRST if x == "low_first" else UNKNOWN for x in order], dtype=np.int8)
    return Series(df["ts"].dt.epoch("ms").to_numpy(), df["open"].to_numpy(), df["high"].to_numpy(), df["low"].to_numpy(),
                  df["close"].to_numpy(), code, TF_MS[tf])


def atr_log(s: Series, n: int = 14) -> np.ndarray:
    """Wilder ATR of log prices. Index t includes bar t: use t-1 to act inside bar t."""
    h, l, c = np.log(s.high), np.log(s.low), np.log(s.close)
    tr = h - l
    tr[1:] = np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])])
    out = np.full(len(tr), np.nan)
    if len(tr) < n:
        return out
    out[n - 1] = tr[:n].mean()
    for t in range(n, len(tr)):
        out[t] = (out[t - 1] * (n - 1) + tr[t]) / n
    return out


def rsi(close: np.ndarray, n: int = 11) -> np.ndarray:
    """Wilder RSI. NewWave TDI uses n = 11."""
    d = np.diff(close, prepend=close[0])
    up, dn = np.maximum(d, 0.0), np.maximum(-d, 0.0)
    out = np.full(len(close), np.nan)
    if len(close) <= n:
        return out
    au, ad = up[1:n + 1].mean(), dn[1:n + 1].mean()
    out[n] = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
    for t in range(n + 1, len(close)):
        au = (au * (n - 1) + up[t]) / n
        ad = (ad * (n - 1) + dn[t]) / n
        out[t] = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
    return out


def sma(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    # NaNs at the start of x stay NaN; pandas is not available, so a plain cumulative sum on the valid part
    start = int(np.argmax(~np.isnan(x)))
    c = np.cumsum(np.nan_to_num(x[start:]))
    v = c.copy()
    v[n:] = c[n:] - c[:-n]
    out[start + n - 1:] = v[n - 1:] / n
    return out


def rolling_std(x: np.ndarray, n: int) -> np.ndarray:
    m = sma(x, n)
    m2 = sma(x * x, n)
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def zigzag(s: Series, thr: np.ndarray | float, start: int = 0) -> tuple[list[Pivot], dict | None]:
    """Pivots confirmed by the end of the series, plus the provisional extreme. `thr` is in log units per bar."""
    n = len(s)
    arr = np.full(n, float(thr)) if np.isscalar(thr) else thr
    high, low, order = s.high.tolist(), s.low.tolist(), s.order.tolist()
    pivots: list[Pivot] = []
    d = 0  # +1: looking for a high, -1: looking for a low, 0: not started
    ext_i, ext = start, 0.0
    hi_i, hi, lo_i, lo = start, -math.inf, start, math.inf
    for t in range(start, n):
        th = arr[t - 1] if t > 0 else arr[t]
        if th != th:  # warm-up
            continue
        h, l = high[t], low[t]
        o = order[t]
        if o == UNKNOWN:
            seq = (("H", h), ("L", l)) if d >= 0 else (("L", l), ("H", h))
        else:
            seq = (("H", h), ("L", l)) if o == HIGH_FIRST else (("L", l), ("H", h))
        for kind, price in seq:
            if d == 0:
                if kind == "H":
                    if price > hi:
                        hi, hi_i = price, t
                    if lo < math.inf and math.log(price / lo) >= th:
                        pivots.append(Pivot(lo_i, "L", lo, t))
                        d, ext, ext_i = 1, hi, hi_i
                else:
                    if price < lo:
                        lo, lo_i = price, t
                    if hi > -math.inf and math.log(hi / price) >= th:
                        pivots.append(Pivot(hi_i, "H", hi, t))
                        d, ext, ext_i = -1, lo, lo_i
            elif d == 1:
                if kind == "H":
                    if price > ext:
                        ext, ext_i = price, t
                elif math.log(ext / price) >= th:
                    pivots.append(Pivot(ext_i, "H", ext, t))
                    d, ext, ext_i = -1, price, t
            else:
                if kind == "L":
                    if price < ext:
                        ext, ext_i = price, t
                elif math.log(price / ext) >= th:
                    pivots.append(Pivot(ext_i, "L", ext, t))
                    d, ext, ext_i = 1, price, t
    prov = None if d == 0 else {"i": ext_i, "kind": "H" if d == 1 else "L", "price": ext}
    return pivots, prov


def threshold(s: Series, k: float, n: int = 14) -> np.ndarray:
    return k * atr_log(s, n)


def day_str(ms: int, with_time: bool = False) -> str:
    from datetime import datetime, timezone
    d = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return d.strftime("%Y-%m-%d %H:%M") if with_time else d.strftime("%Y-%m-%d")


__all__ = ["Pivot", "Series", "load_series", "atr_log", "rsi", "sma", "rolling_std", "zigzag", "threshold", "day_str",
           "HIGH_FIRST", "LOW_FIRST", "UNKNOWN", "TF_MS"]
