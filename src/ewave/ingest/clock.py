"""Clock abstraction so sync logic can be tested with a fake, controllable clock."""
from __future__ import annotations

import time


class SystemClock:
    def now_ms(self) -> int:
        return int(time.time() * 1000)

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)


class FakeClock:
    """Deterministic clock: sleep() advances time instead of waiting."""

    def __init__(self, now_ms: int = 0):
        self._now_ms = now_ms
        self._mono = 0.0

    def now_ms(self) -> int:
        return self._now_ms

    def monotonic(self) -> float:
        return self._mono

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            self._now_ms += int(seconds * 1000)
            self._mono += seconds

    def set(self, now_ms: int) -> None:
        self._now_ms = now_ms

    def advance(self, seconds: float) -> None:
        self.sleep(seconds)
