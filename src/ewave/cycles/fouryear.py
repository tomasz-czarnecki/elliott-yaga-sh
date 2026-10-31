"""The 4-year level: bear-market troughs. A trough is the lowest low between an all-time high and the day price
trades above that high again.

A "lowest within +-N days" pivot fails at this level: the exponential uptrend makes earlier prices lower.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log

from .series import Bars


@dataclass(frozen=True)
class Bear:
    ath_i: int
    ath: float
    low_i: int
    low: float
    recovered_i: int | None  # first bar trading above the ATH; None while the bear is still running

    @property
    def drawdown(self) -> float:
        return 1 - self.low / self.ath

    @property
    def log_drop(self) -> float:
        return log(self.ath / self.low)

    @property
    def ath_to_low_days(self) -> int:
        return self.low_i - self.ath_i


def qualifies(bear: Bear, rules: dict) -> bool:
    return bear.drawdown >= rules["drawdown_min"] and bear.ath_to_low_days >= rules["ath_to_low_min_days"]


def all_bears(bars: Bars) -> list[Bear]:
    """Every stretch below an ATH that has at least one bar, in order; the last one may still be running."""
    out: list[Bear] = []
    ath_i, ath = 0, bars.high[0]
    low_i, low = None, None
    for i in range(1, len(bars)):
        if bars.high[i] > ath:
            if low_i is not None:
                out.append(Bear(ath_i, ath, low_i, low, i))
            ath_i, ath = i, bars.high[i]
            low_i, low = None, None
        elif low is None or bars.low[i] < low:
            low_i, low = i, bars.low[i]
    if low_i is not None:
        out.append(Bear(ath_i, ath, low_i, low, None))
    return out


def completed_troughs(bars: Bars, rules: dict) -> list[Bear]:
    """Completed bears passing the thresholds of the rules file: the 4-year lows."""
    return [b for b in all_bears(bars) if b.recovered_i is not None and qualifies(b, rules)]


def running_bear(bars: Bars) -> Bear | None:
    bears = all_bears(bars)
    return bears[-1] if bears and bears[-1].recovered_i is None else None
