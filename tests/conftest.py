from __future__ import annotations

import pytest

from ewave.ingest.clock import FakeClock
from ewave.ingest.sync import Collector

from .fakes import T0, FakeSource

ALL = ["bitstamp_btcusd", "binance_btcusdt", "bybit_btcusdt_perp"]


@pytest.fixture
def clock():
    return FakeClock(T0)


@pytest.fixture
def make_collector(tmp_path, clock):
    made: list[Collector] = []

    def _make(venues=ALL, **source_kwargs):
        sources = {v: FakeSource(v, clock, **source_kwargs.get(v, {})) for v in venues}
        c = Collector(tmp_path / "data", sources=sources, archive=None, clock=clock)
        made.append(c)
        return c

    yield _make
    for c in made:
        c.catalog.close()
