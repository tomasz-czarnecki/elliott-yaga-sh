"""The live layer: a walk-forward state machine, one per level. It is fed one closed day at a time and has no way to
see a later bar: `step` appends to its own arrays and everything it computes reads only those.

Daily level:  after the last confirmed low, track the lowest eligible low; the first signal after it confirms it.
Weekly level: the same on Monday-based UTC weeks, so it moves only when a week has closed.
4-year level: inside a bear that has reached the depth and age of the rules file, a close above the weekly SMA after
              the lowest low confirms it.

A confirmed low is never redrawn. If price undercuts it soon after, it is logged as revised and the cycle reverts to
the low before it; a later undercut leaves it standing and the cycle is a failed cycle (Camel section 2).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .config import DAY_MS, Level, Rules
from .cycle import Cycle, make_cycle
from .fouryear import Bear, qualifies
from .series import Bars, to_ms
from .zones import fouryear_zone, level_zone


@dataclass
class LiveLow:
    level: str
    pos: int           # bar number at this level
    i: int             # day index of the low
    ts_low: int
    price: float
    ts_signal_bar: int  # open time of the bar whose close fired the signal (for the weekly levels: the week's Monday)
    ts_confirmed: int  # that bar's close: when the low could first be known
    signal: str        # swing_low / sma
    status: str = "confirmed"  # or revised
    ts_revised: int | None = None
    ts_undercut: int | None = None  # first trade below it, while it stood
    ts_failed: int | None = None    # first close below it, while it stood
    ts_next: int | None = None      # when the next low of the chain was confirmed


@dataclass
class _Candidate:
    pos: int
    i: int
    price: float


class _Machine:
    """One level. A bar here is a day or a week; lengths are always measured in days, on the day index of the lows."""

    def __init__(self, level: Level, rules: Rules, bar_days: int, engine: "LiveEngine"):
        self.level = level
        self.rules = rules
        self.bar_days = bar_days
        self.engine = engine
        self.lookback = max(2, round(level.lookback_days / bar_days))
        self.period = rules.live["sma_period"]
        self.signals = set(rules.live["signals"])
        self.strict_open = rules.live["swing_low_require_open_above_body"]
        self.since_top = rules.live["candidate_since_top"]
        self.cross = rules.live["sma_requires_cross"]
        self.top: float | None = None  # highest high since the last confirmed low
        self.dipped = False  # a close at or below its SMA since the top: the pullback really went under it
        self.o: list[float] = []
        self.h: list[float] = []
        self.l: list[float] = []
        self.c: list[float] = []
        self.low_i: list[int] = []  # day index of each bar's low
        self.sum = 0.0
        self.chain: list[LiveLow] = []
        self.log: list[LiveLow] = []
        self.cycles: list[Cycle] = []
        self.revisions: list[dict] = []
        self.candidate: _Candidate | None = None
        self.zones_early: dict[int, dict] = {}  # zone of the cycle starting at day i, on the first day it can end
        self.zone_hits: list[dict] = []
        self.swing_seen = 0
        self.swing_strict = 0

    def on_bar(self, ts_open: int, ts_close: int, o, h, l, c, low_i: int, active: bool) -> None:
        self.o.append(o)
        self.h.append(h)
        self.l.append(l)
        self.c.append(c)
        self.low_i.append(low_i)
        pos = len(self.c) - 1
        self.sum += c
        if pos >= self.period:
            self.sum -= self.c[pos - self.period]
        sma = self.sum / self.period if pos >= self.period - 1 else None
        if not active:
            return
        level = self.level

        anchor = self.chain[-1] if self.chain else None
        if anchor and l < anchor.price:
            if low_i - anchor.i <= level.revise_days:
                self._revise(anchor, ts_close, low_i, l)
                anchor = self.chain[-1] if self.chain else None
            elif anchor.ts_undercut is None:
                anchor.ts_undercut = ts_close
        if anchor and c < anchor.price and anchor.ts_failed is None:
            anchor.ts_failed = ts_close

        if self.top is None or h > self.top:
            self.top = h
            self.dipped = False
            if self.since_top and self.candidate is not None:  # a new high ends the pullback that candidate belonged to
                self.candidate = None

        if sma is not None and c <= sma:
            self.dipped = True

        eligible = anchor is None or low_i - anchor.i >= level.min_gap
        if eligible and l <= min(self.l[max(0, pos - self.lookback + 1):pos + 1]):
            if self.candidate is None or l < self.candidate.price:
                self.candidate = _Candidate(pos, low_i, l)

        cand = self.candidate
        if cand and cand.pos < pos:
            swing = False
            if pos == cand.pos + 1 and c > self.h[cand.pos]:
                strict = o > max(self.o[cand.pos], self.c[cand.pos])
                self.swing_seen += 1
                self.swing_strict += strict
                swing = strict or not self.strict_open
            if "swing_low" in self.signals and swing:
                self._confirm(cand, ts_open, ts_close, "swing_low")
            elif "sma" in self.signals and sma is not None and c > sma and (self.dipped or not self.cross):
                self._confirm(cand, ts_open, ts_close, "sma")

    def _confirm(self, cand: _Candidate, ts_open: int, ts_close: int, signal: str) -> None:
        bars = self.engine.bars()
        low = LiveLow(self.level.name, cand.pos, cand.i, bars.ts[cand.i], cand.price, ts_open, ts_close, signal)
        self.top = max(self.h[cand.pos:])
        self.dipped = False
        if self.chain:
            prev = self.chain[-1]
            prev.ts_next = ts_close
            self.cycles.append(make_cycle(self.level.name, bars, prev.i, cand.i, self.rules, status="confirmed"))
            self._score_zone(prev, cand)
        self.chain.append(low)
        self.log.append(low)
        self.candidate = None

    def _revise(self, low: LiveLow, ts_close: int, new_i: int, new_price: float) -> None:
        low.status = "revised"
        low.ts_revised = ts_close
        self.chain.pop()
        self.candidate = None
        self.top = max(self.h[self.chain[-1].pos:]) if self.chain else None
        self.dipped = True  # price has just gone below a confirmed low
        if self.cycles and self.cycles[-1].end_i == low.i:
            self.cycles.pop()
        self.zones_early.pop(low.i, None)
        self.zone_hits = [z for z in self.zone_hits if z["end_i"] != low.i]
        prev = self.chain[-1] if self.chain else None
        if prev:
            prev.ts_next = None
        self.revisions.append({
            "level": self.level.name, "ts_low": low.ts_low, "price": low.price, "ts_confirmed": low.ts_confirmed,
            "ts_undercut": ts_close, "undercut_low": new_price, "days_held": new_i - low.i,
        })

    def after_day(self, day_i: int) -> None:
        """On the first day a cycle can end (at the expected midpoint a top cannot yet be right of it), note its zone:
        scored when the next low confirms."""
        if not self.chain or not self.engine.track_zones:
            return
        anchor = self.chain[-1]
        if anchor.i not in self.zones_early and day_i - anchor.i >= self.level.min_gap:
            self.zones_early[anchor.i] = level_zone(self, day_i)

    def _score_zone(self, prev: LiveLow, cand: _Candidate) -> None:
        zone = self.zones_early.get(prev.i)  # kept: if this low gets revised, the cycle and its zone go on
        if zone is None or zone["p_lo"] is None:
            return
        bars = self.engine.bars()
        ts = bars.ts[cand.i]
        self.zone_hits.append({
            "end_i": cand.i, "translation": zone["translation"], "time_hit": zone["t_from"] <= ts <= zone["t_to"],
            "price_hit": zone["p_lo"] <= cand.price <= zone["p_hi"],
            "below_start": cand.price < prev.price,
        })

    def open_cycle(self, last: int) -> Cycle | None:
        if not self.chain:
            return None
        return make_cycle(self.level.name, self.engine.bars(), self.chain[-1].i, None, self.rules,
                          expected=self.level.centre, last=last)

    def state(self) -> dict:
        return {
            "chain": [asdict(x) for x in self.chain],
            "log": [asdict(x) for x in self.log],
            "cycles": [c.as_dict() for c in self.cycles],
            "revisions": list(self.revisions),
            "candidate": None if self.candidate is None else asdict(self.candidate),
        }


class _FourYear:
    """Bear troughs, live. Runs on days for the ATH and the low, on weeks for the signal."""

    def __init__(self, rules: Rules, engine: "LiveEngine"):
        self.rules = rules
        self.cfg = rules.fouryear
        self.engine = engine
        self.ath_i = 0
        self.ath: float | None = None
        self.low_i: int | None = None
        self.low: float | None = None
        self.low_week = -1
        self.confirmed: LiveLow | None = None  # standing in the current bear
        self.chain: list[LiveLow] = []
        self.log: list[LiveLow] = []
        self.revisions: list[dict] = []
        self.completed: list[Bear] = []  # bears that recovered and qualify
        self.weekly_c: list[float] = []

    def on_day(self, i: int, h: float, l: float, week: int, ts_close: int) -> None:
        if self.ath is None or h > self.ath:
            if self.ath is not None and self.low_i is not None:
                bear = Bear(self.ath_i, self.ath, self.low_i, self.low, i)
                if qualifies(bear, self.cfg):
                    self.completed.append(bear)
            self.ath_i, self.ath = i, h
            self.low_i, self.low = None, None
            self.confirmed = None
        elif self.low is None or l < self.low:
            self.low_i, self.low, self.low_week = i, l, week
            if self.confirmed:
                c = self.confirmed
                c.status = "revised"
                c.ts_revised = ts_close
                self.chain.pop()
                self.revisions.append({
                    "level": "fouryear", "ts_low": c.ts_low, "price": c.price, "ts_confirmed": c.ts_confirmed,
                    "ts_undercut": ts_close, "undercut_low": l, "days_held": i - c.i,
                })
                self.confirmed = None

    def on_week(self, week: int, ts_open: int, ts_close: int, close: float) -> None:
        self.weekly_c.append(close)
        n = self.rules.live["sma_period"]
        if len(self.weekly_c) < n or self.confirmed or self.low_i is None:
            return
        sma = sum(self.weekly_c[-n:]) / n
        bear = Bear(self.ath_i, self.ath, self.low_i, self.low, None)
        if week > self.low_week and close > sma and qualifies(bear, self.cfg):
            bars = self.engine.bars()
            low = LiveLow("fouryear", 0, self.low_i, bars.ts[self.low_i], self.low, ts_open, ts_close, "sma")
            self.confirmed = low
            self.chain.append(low)
            self.log.append(low)

    def state(self) -> dict:
        return {
            "chain": [asdict(x) for x in self.chain],
            "log": [asdict(x) for x in self.log],
            "revisions": list(self.revisions),
            "ath": self.ath, "ath_i": self.ath_i, "low": self.low, "low_i": self.low_i,
            "completed": [asdict(b) for b in self.completed],
        }


class LiveEngine:
    """All three levels. `step` takes the next closed day; `state` is everything known at that moment."""

    def __init__(self, rules: Rules, track_zones: bool = True):
        self.rules = rules
        self.track_zones = track_zones
        self.stats_start = to_ms(rules.series["stats_start"])
        self.ts: list[int] = []
        self.o: list[float] = []
        self.h: list[float] = []
        self.l: list[float] = []
        self.c: list[float] = []
        self.daily = _Machine(rules.levels["daily"], rules, 1, self)
        self.weekly = _Machine(rules.levels["weekly"], rules, 7, self)
        self.fouryear = _FourYear(rules, self)
        self._week: dict | None = None

    def bars(self) -> Bars:
        return Bars(self.ts, self.o, self.h, self.l, self.c)

    @staticmethod
    def _week_of(day: int) -> int:
        return (day + 3) // 7  # epoch day 0 was a Thursday; weeks start on Monday

    def step(self, ts: int, o: float, h: float, l: float, c: float) -> None:
        if self.ts and ts - self.ts[-1] != DAY_MS:
            raise ValueError("live replay needs consecutive days")
        self.ts.append(ts)
        self.o.append(o)
        self.h.append(h)
        self.l.append(l)
        self.c.append(c)
        i = len(self.ts) - 1
        ts_close = ts + DAY_MS
        day = ts // DAY_MS
        week = self._week_of(day)
        active = ts >= self.stats_start

        self.fouryear.on_day(i, h, l, week, ts_close)
        self.daily.on_bar(ts, ts_close, o, h, l, c, i, active)

        wk = self._week
        if (day + 3) % 7 == 0:  # a Monday opens the week; the partial first week of the series is skipped
            wk = self._week = {"ts": ts, "o": o, "h": h, "l": l, "c": c, "low_i": i}
        elif wk is not None:
            wk["h"] = max(wk["h"], h)
            if l < wk["l"]:
                wk["l"], wk["low_i"] = l, i
            wk["c"] = c
        if wk is not None and (day + 3) % 7 == 6:  # Sunday: the week has closed
            self.weekly.on_bar(wk["ts"], ts_close, wk["o"], wk["h"], wk["l"], wk["c"], wk["low_i"],
                               wk["ts"] >= self.stats_start)
            self.fouryear.on_week(week, wk["ts"], ts_close, wk["c"])
            self._week = None
        self.daily.after_day(i)
        self.weekly.after_day(i)

    def state(self) -> dict:
        return {
            "n": len(self.ts),
            "daily": self.daily.state(),
            "weekly": self.weekly.state(),
            "fouryear": self.fouryear.state(),
        }

    def zones(self) -> list[dict]:
        """The prediction boxes as of the last closed day."""
        last = len(self.ts) - 1
        out = [z for z in (level_zone(self.daily, last), level_zone(self.weekly, last)) if z]
        z = fouryear_zone(self.fouryear, self, last)
        if z:
            out.append(z)
        return out


def replay(bars: Bars, rules: Rules, *, track_zones: bool = True) -> LiveEngine:
    engine = LiveEngine(rules, track_zones=track_zones)
    for i in range(len(bars)):
        engine.step(bars.ts[i], bars.open[i], bars.high[i], bars.low[i], bars.close[i])
    return engine
