"""One cycle (low to low) and what is measured on it. Used by both layers, and it reads only bars up to the end low
(or the last bar given, for an open cycle), so it stays causal when the live layer calls it."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import log

from .series import Bars

LT, MT, RT, UNDETERMINED = "LT", "MT", "RT", "?"


@dataclass
class Cycle:
    level: str
    start_i: int
    start_ts: int
    start_price: float
    end_i: int | None
    end_ts: int | None
    end_price: float | None
    length: int | None  # days; None while open
    elapsed: int
    top_i: int
    top_ts: int
    top_price: float
    top_pos: float  # fraction of the cycle (open cycle: of the expected length)
    translation: str
    hcl_i: int | None
    hcl_ts: int | None
    hcl_price: float | None
    hcl_above_start: bool | None
    failed: bool  # a close below the start low, up to and including the end bar (section 2)
    failed_ts: int | None
    status: str  # confirmed / provisional / in_progress

    @property
    def drop_log(self) -> float | None:
        """Top to end low, log price."""
        return None if self.end_price is None else log(self.top_price / self.end_price)

    @property
    def lower_end(self) -> bool | None:
        return None if self.end_price is None else self.end_price < self.start_price

    def as_dict(self) -> dict:
        return asdict(self)


def classify(pos: float, band: float) -> str:
    if pos < 0.5 - band:
        return LT
    if pos > 0.5 + band:
        return RT
    return MT


def _half_cycle_low(bars: Bars, s: int, length: int, last: int, band: tuple[float, float], clear: int):
    a = s + max(1, round(length * band[0]))
    b = min(s + round(length * band[1]), last)
    if b < a:
        return None
    i = min(range(a, b + 1), key=lambda k: (bars.low[k], k))
    around = bars.low[max(s + 1, i - clear):min(last, i + clear) + 1]
    return i if bars.low[i] <= min(around) else None


def make_cycle(level: str, bars: Bars, s: int, e: int | None, rules, *, expected: float | None = None, status: str = "",
               last: int | None = None) -> Cycle:
    """Measure the cycle from low s to low e, or the open cycle from s up to bar `last` against `expected` days."""
    cfg = rules.cycle
    end = e if e is not None else (len(bars) - 1 if last is None else last)
    top = max(range(s, end + 1), key=lambda k: (bars.high[k], -k))
    start_price = bars.low[s]
    if e is not None:
        length = e - s
        pos = (top - s) / length if length else 0.0
        translation = classify(pos, cfg["mid_band"])
        horizon = length
    else:
        length = None
        pos = (top - s) / expected
        # An open cycle has no midpoint yet: it is judged against the expected length, once that midpoint has passed.
        translation = UNDETERMINED if (end - s) < expected / 2 else classify(pos, cfg["mid_band"])
        horizon = round(expected)
    failed_at = next((k for k in range(s + 1, end + 1) if bars.close[k] < start_price), None)
    hcl = _half_cycle_low(bars, s, horizon, end, cfg["hcl_band"], cfg["hcl_clear_days"])
    return Cycle(
        level=level, start_i=s, start_ts=bars.ts[s], start_price=start_price,
        end_i=e, end_ts=None if e is None else bars.ts[e], end_price=None if e is None else bars.low[e],
        length=length, elapsed=end - s, top_i=top, top_ts=bars.ts[top], top_price=bars.high[top], top_pos=pos,
        translation=translation, hcl_i=hcl, hcl_ts=None if hcl is None else bars.ts[hcl],
        hcl_price=None if hcl is None else bars.low[hcl],
        hcl_above_start=None if hcl is None else bars.low[hcl] > start_price,
        failed=failed_at is not None, failed_ts=None if failed_at is None else bars.ts[failed_at],
        status=status or ("in_progress" if e is None else "confirmed"),
    )
