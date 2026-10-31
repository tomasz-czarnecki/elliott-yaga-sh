"""Bars of every frame as plain lists, cut to what was known at one moment.

`Frames.upto(as_of)` keeps only bars that had closed by then, and everything downstream reads nothing else, so a run at
a past date sees exactly what that date saw. The frames always start at the venue's first bar: indicators and root
pivots then do not depend on where a window happens to begin.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import log
from typing import Callable

from ..data import load_1m, load_bars

TF_MS = {"1m": 60_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "12h": 43_200_000, "1d": 86_400_000}
HIGH_FIRST, LOW_FIRST, UNKNOWN = 1, -1, 0
_ORDER = {"high_first": HIGH_FIRST, "low_first": LOW_FIRST}


def to_ms(when: str) -> int:
    d = datetime.fromisoformat(when)
    return int((d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp() * 1000)


def stamp(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def atr_log(high: list[float], low: list[float], close: list[float], n: int) -> list[float]:
    """Wilder ATR of log prices. Index t includes bar t: use t-1 to act inside bar t."""
    out = [float("nan")] * len(high)
    if len(high) < n:
        return out
    tr = []
    prev = None
    for h, l, c in zip(high, low, close):
        lh, ll = log(h), log(l)
        tr.append(lh - ll if prev is None else max(lh - ll, abs(lh - prev), abs(ll - prev)))
        prev = log(c)
    a = sum(tr[:n]) / n
    out[n - 1] = a
    for t in range(n, len(tr)):
        a = (a * (n - 1) + tr[t]) / n
        out[t] = a
    return out


def rsi(close: list[float], n: int) -> list[float]:
    """Wilder RSI on closes. NewWave TDI uses n = 11 (sec 5)."""
    out = [float("nan")] * len(close)
    if len(close) <= n:
        return out
    up = dn = 0.0
    for t in range(1, n + 1):
        d = close[t] - close[t - 1]
        up += max(d, 0.0)
        dn += max(-d, 0.0)
    up, dn = up / n, dn / n
    out[n] = 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)
    for t in range(n + 1, len(close)):
        d = close[t] - close[t - 1]
        up = (up * (n - 1) + max(d, 0.0)) / n
        dn = (dn * (n - 1) + max(-d, 0.0)) / n
        out[t] = 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)
    return out


@dataclass
class Frame:
    tf: str
    ts: list[int]        # UTC bar open, ms
    open: list[float]
    high: list[float]
    low: list[float]
    close: list[float]
    order: list[int]     # HIGH_FIRST / LOW_FIRST / UNKNOWN inside the bar
    volume: list[float] = field(default_factory=list)
    atr: list[float] = field(default_factory=list)
    rsi: list[float] = field(default_factory=list)
    # after the frame's last complete bar: extremes of the finer bars already closed, so a kill shows without waiting
    tail_high: float = float("-inf")
    tail_low: float = float("inf")
    last_close: float = 0.0
    fine: "Frame | None" = field(default=None, repr=False)  # the frame that dates this one's pivots (FIB-T6)
    _hi: list[float] = field(default_factory=list, repr=False)
    _lo: list[float] = field(default_factory=list, repr=False)

    @property
    def tf_ms(self) -> int:
        return TF_MS[self.tf]

    def __len__(self) -> int:
        return len(self.ts)

    def indicators(self, atr_bars: int, rsi_bars: int) -> None:
        self.atr = atr_log(self.high, self.low, self.close, atr_bars)
        self.rsi = rsi(self.close, rsi_bars)

    def upto(self, as_of_ms: int) -> "Frame":
        n = bisect_right(self.ts, as_of_ms - self.tf_ms)
        return Frame(self.tf, self.ts[:n], self.open[:n], self.high[:n], self.low[:n], self.close[:n], self.order[:n],
                     self.volume[:n], self.atr[:n], self.rsi[:n])

    def set_tail(self, fine: "Frame") -> None:
        """Bars of a finer frame after this frame's last complete bar. Fills the running extremes."""
        end = self.ts[-1] + self.tf_ms if self.ts else 0
        i = bisect_left(fine.ts, end)
        if i < len(fine.ts):
            self.tail_high = max(fine.high[i:])
            self.tail_low = min(fine.low[i:])
        self.last_close = fine.close[-1] if fine.close else (self.close[-1] if self.close else 0.0)
        hi, lo = [0.0] * len(self.ts), [0.0] * len(self.ts)
        h, l = self.tail_high, self.tail_low
        for t in range(len(self.ts) - 1, -1, -1):
            h = max(h, self.high[t])
            l = min(l, self.low[t])
            hi[t], lo[t] = h, l
        self._hi, self._lo = hi, lo

    @property
    def resolution(self) -> float:
        """The candle that measures time on this frame, in this frame's bars."""
        return self.fine.tf_ms / self.tf_ms if self.fine is not None and self.fine.tf_ms < self.tf_ms else 1.0

    def bar_at(self, ts: int) -> int:
        """The last bar opening at or before ts."""
        return max(0, bisect_right(self.ts, ts) - 1)

    def hi_since(self, i: int) -> float:
        return self._hi[i] if i < len(self._hi) else self.tail_high

    def lo_since(self, i: int) -> float:
        return self._lo[i] if i < len(self._lo) else self.tail_low

    def since_ts(self, i: int) -> tuple[float, int, float, int]:
        """Highest high and lowest low from bar i on, with their bar openings (running extremes of a wave)."""
        hi, lo, hi_t, lo_t = float("-inf"), float("inf"), self.ts[-1], self.ts[-1]
        for t in range(i, len(self.ts)):
            if self.high[t] > hi:
                hi, hi_t = self.high[t], self.ts[t]
            if self.low[t] < lo:
                lo, lo_t = self.low[t], self.ts[t]
        end = self.ts[-1] + self.tf_ms if self.ts else 0
        if self.tail_high > hi:
            hi, hi_t = self.tail_high, end
        if self.tail_low < lo:
            lo, lo_t = self.tail_low, end
        return hi, hi_t, lo, lo_t

    def first_cross(self, ts: int, price: float, side: int) -> int | None:
        """Open of the first bar after ts that trades at or past price (side +1: above it, -1: below it)."""
        for t in range(bisect_right(self.ts, ts), len(self.ts)):
            if (side > 0 and self.high[t] >= price) or (side < 0 and self.low[t] <= price):
                return self.ts[t]
        end = self.ts[-1] + self.tf_ms if self.ts else 0
        if (side > 0 and self.tail_high >= price) or (side < 0 and self.tail_low <= price):
            return end
        return None

    def volatility(self, bars: int) -> float:
        """Realised volatility per bar: root mean squared log return over the last `bars` closes."""
        c = self.close[-(bars + 1):]
        if len(c) < 2:
            return 0.0
        return (sum(log(b / a) ** 2 for a, b in zip(c, c[1:])) / (len(c) - 1)) ** 0.5


def resample_12h(fine: Frame) -> Frame:
    """12H bars from 1H, on UTC 00:00 and 12:00. A bar is built only when all of its period has closed."""
    size = TF_MS["12h"]
    out = Frame("12h", [], [], [], [], [], [])
    if not fine.ts:
        return out
    last_end = fine.ts[-1] + fine.tf_ms
    i, n = 0, len(fine.ts)
    while i < n:
        bucket = fine.ts[i] - fine.ts[i] % size
        if bucket + size > last_end:
            break
        j = i
        hi_at = lo_at = i
        while j < n and fine.ts[j] < bucket + size:
            if fine.high[j] > fine.high[hi_at]:
                hi_at = j
            if fine.low[j] < fine.low[lo_at]:
                lo_at = j
            j += 1
        if hi_at != lo_at:
            order = HIGH_FIRST if hi_at < lo_at else LOW_FIRST
        else:
            order = fine.order[hi_at]
        out.ts.append(bucket)
        out.open.append(fine.open[i])
        out.high.append(fine.high[hi_at])
        out.low.append(fine.low[lo_at])
        out.close.append(fine.close[j - 1])
        out.order.append(order)
        if fine.volume:
            out.volume.append(sum(fine.volume[i:j]))
        i = j
    return out


@dataclass
class Frames:
    venue: str
    by_tf: dict[str, Frame]
    as_of_ms: int
    minutes: Callable[[int, int], "Frame | None"] | None = None  # 1m bars of a span, built on demand: too many to hold all of them

    def __getitem__(self, tf: str) -> Frame:
        return self.by_tf[tf]

    def wire_time(self, frames_cfg: dict) -> None:
        """Which frame dates whose pivots (rules: frames.*.time_tf). Those bars are cut at the same moment as these."""
        for tf, f in self.by_tf.items():
            f.fine = self.by_tf.get(frames_cfg[tf].get("time_tf", tf))

    @property
    def price(self) -> float:
        return self.by_tf["15m"].close[-1]

    def upto(self, as_of_ms: int) -> "Frames":
        """What was known once `as_of_ms` had passed. The 12H frame is rebuilt from the cut 1H frame."""
        cut = {tf: f.upto(as_of_ms) for tf, f in self.by_tf.items()}
        return prepared(Frames(self.venue, cut, as_of_ms, self.minutes), indicators=False)


def prepared(frames: Frames, atr_bars: int = 14, rsi_bars: int = 11, indicators: bool = True) -> Frames:
    """Fills indicators (on a full load) and each frame's running tail from the finest frame."""
    if indicators:
        for f in frames.by_tf.values():
            f.indicators(atr_bars, rsi_bars)
    fine = frames.by_tf["15m"]
    if fine.ts:
        frames.as_of_ms = min(frames.as_of_ms, fine.ts[-1] + fine.tf_ms)
    for f in frames.by_tf.values():
        f.set_tail(fine)
    return frames


def from_lists(venue: str, by_tf: dict[str, Frame], atr_bars: int = 14, rsi_bars: int = 11) -> Frames:
    """Frames from bars already in memory; for tests."""
    fine = by_tf["15m"]
    return prepared(Frames(venue, by_tf, fine.ts[-1] + fine.tf_ms), atr_bars, rsi_bars)


def _frame(venue: str, tf: str, root) -> Frame:
    df = load_bars(venue, tf, "2000-01-01", "2100-01-01", complete_only=True, root=root)
    return Frame(tf, df["ts"].dt.epoch("ms").to_list(), df["open"].to_list(), df["high"].to_list(), df["low"].to_list(),
                 df["close"].to_list(), [_ORDER.get(x, UNKNOWN) for x in df["hl_order"].to_list()], df["volume"].to_list())


def minute_loader(venue: str, atr_bars: int, rsi_bars: int, root=None) -> Callable[[int, int], Frame | None]:
    """1m bars from `start_ms` to `end_ms`, traded minutes only as every bar here is built (CLAUDE.md, data rules). Reads
    only what it is asked for, and the caller never asks past the end of a wave."""
    def load(start_ms: int, end_ms: int) -> Frame | None:
        df = load_1m(venue, datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc), datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc), root=root, warn=False)
        if not len(df):
            return None
        df = df.filter(df["volume"] > 0)
        n = len(df)
        f = Frame("1m", df["ts"].dt.epoch("ms").to_list(), df["open"].to_list(), df["high"].to_list(), df["low"].to_list(), df["close"].to_list(), [UNKNOWN] * n, df["volume"].to_list())
        f.indicators(atr_bars, rsi_bars)
        return f
    return load


def load_frames(venue: str, atr_bars: int = 14, rsi_bars: int = 11, root=None) -> Frames:
    """Complete bars of a venue, the whole history. Reads only; holds no lock."""
    by_tf = {tf: _frame(venue, tf, root) for tf in ("1d", "4h", "1h", "15m")}
    by_tf["12h"] = resample_12h(by_tf["1h"])
    fine = by_tf["15m"]
    return prepared(Frames(venue, by_tf, fine.ts[-1] + fine.tf_ms, minute_loader(venue, atr_bars, rsi_bars, root)), atr_bars, rsi_bars)
