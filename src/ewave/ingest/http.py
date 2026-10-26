"""HTTP client with per-host pacing, bounded retries and cooldown signalling.

Policy (per request): at most ``max_attempts`` tries, exponential backoff 1/2/4/8 s with jitter (capped at 30 s) on
timeouts, connect errors, 5xx, 429 and whatever the venue's ``interpret`` callback calls retryable. 429/418 honour
Retry-After; a Retry-After over 60 s becomes a CooldownError for the caller to store. The fallback host is used only
after repeated connect/timeout/5xx failures - never for rate limits or bans, because the hosts share them.
"""
from __future__ import annotations

import random
import time
from collections.abc import Callable
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from .clock import SystemClock

USER_AGENT = "ewave-data/0.1 (personal research data collector)"


class HttpError(Exception):
    pass


class RetryableError(HttpError):
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class CooldownError(HttpError):
    """Stop talking to this venue for ``seconds`` (rate-limit ban or Retry-After > 60 s)."""

    def __init__(self, message: str, seconds: float):
        super().__init__(message)
        self.seconds = seconds


class GeoBlockedError(HttpError):
    pass


class FatalError(HttpError):
    """A request or response that retrying cannot fix."""


def retry_after_seconds(resp: httpx.Response) -> float | None:
    raw = resp.headers.get("retry-after")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        try:  # HTTP-date form
            return max(0.0, parsedate_to_datetime(raw).timestamp() - time.time())
        except (TypeError, ValueError):
            return None


def date_header_ms(resp: httpx.Response) -> int | None:
    raw = resp.headers.get("date")
    if not raw:
        return None
    try:
        return int(parsedate_to_datetime(raw).timestamp() * 1000)
    except (TypeError, ValueError):
        return None


class HttpClient:
    def __init__(
        self,
        name: str,
        bases: list[str],
        rate_per_s: float,
        *,
        clock=None,
        timeout: float = 20.0,
        max_attempts: int = 4,
        transport: httpx.BaseTransport | None = None,
        rng: random.Random | None = None,
    ):
        self.name = name
        self.bases = [b.rstrip("/") for b in bases]
        self.min_interval = 1.0 / rate_per_s
        self.clock = clock or SystemClock()
        self.max_attempts = max_attempts
        self.rng = rng or random.Random()
        self._next_ok = 0.0
        self.last_date_ms: int | None = None
        self.client = httpx.Client(
            timeout=httpx.Timeout(timeout),
            transport=transport,
            headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"},
            follow_redirects=True,
        )

    def close(self) -> None:
        self.client.close()

    def _pace(self) -> None:
        now = self.clock.monotonic()
        if now < self._next_ok:
            self.clock.sleep(self._next_ok - now)
            now = self.clock.monotonic()
        self._next_ok = now + self.min_interval

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        interpret: Callable[[httpx.Response], Any],
        headers: dict[str, str] | None = None,
        absolute: bool = False,
    ) -> Any:
        """GET and return ``interpret(response)``. ``path`` is appended to the base (or is a full URL if absolute)."""
        transient = 0
        last: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            base = self.bases[1] if (transient >= 2 and len(self.bases) > 1) else self.bases[0]
            url = path if absolute else base + path
            self._pace()
            retry_after: float | None = None
            try:
                resp = self.client.get(url, params=params, headers=headers)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                transient += 1
                last = RetryableError(f"{type(e).__name__}: {e}")
            else:
                d = date_header_ms(resp)
                if d is not None:
                    self.last_date_ms = d
                try:
                    if resp.status_code >= 500:
                        transient += 1
                        raise RetryableError(f"HTTP {resp.status_code}")
                    if resp.status_code in (429, 418):
                        retry_after = retry_after_seconds(resp)
                        if resp.status_code == 418:
                            raise CooldownError("HTTP 418 (IP banned)", max(retry_after or 0, 120.0))
                        if retry_after is not None and retry_after > 60:
                            raise CooldownError(f"HTTP 429, Retry-After {retry_after:.0f}s", retry_after)
                        raise RetryableError("HTTP 429", retry_after)
                    return interpret(resp)
                except RetryableError as e:
                    last = e
                    retry_after = e.retry_after if e.retry_after is not None else retry_after
            if attempt < self.max_attempts:
                delay = min(30.0, 2.0 ** (attempt - 1)) * (0.75 + 0.5 * self.rng.random())
                if retry_after:
                    delay = max(delay, min(retry_after, 60.0))
                self.clock.sleep(delay)
        raise RetryableError(f"{self.name}: giving up after {self.max_attempts} attempts: {last}")
