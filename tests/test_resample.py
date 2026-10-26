from __future__ import annotations

import polars as pl
from hypothesis import given, settings
from hypothesis import strategies as st

from ewave.ingest.config import DAY_MS, MINUTE_MS, VENUES, day_start_ms, utc_ms
from ewave.ingest.resample import has_traded_minute, last_traded_close, resample_day
from ewave.ingest.schema import frame_from_rows, make_row

BITSTAMP = VENUES["bitstamp_btcusd"]
BYBIT = VENUES["bybit_btcusdt_perp"]
DAY = "2026-10-20"
D0 = day_start_ms(DAY)


def m(i, o, h, l, c, v, day0=D0):
    return make_row(day0 + i * MINUTE_MS, o, h, l, c, v)


def flat(i, price, day0=D0):
    return m(i, price, price, price, price, 0.0, day0)


def bars(rows, tf="15m", carry=None, covered=None, closed=True, venue=BYBIT, day=DAY):
    df = frame_from_rows(rows)
    return resample_day(df, venue, day, tf, carry, covered if covered is not None else day_start_ms(day) + DAY_MS, closed)


def test_bitstamp_2012_example_matches_the_exchanges_own_candle():
    # Bitstamp 2012-01-01 15:15 15m: only minute 15:30?-style trades; the flat 4.58 minutes must not make a fake low.
    day, d0 = "2012-01-01", day_start_ms("2012-01-01")
    rows = [flat(i, 4.58, d0) for i in range(15 * 60 + 15, 15 * 60 + 30)]
    # replace one minute with a real trade at 4.84 (volume 10)
    rows[5] = m(15 * 60 + 20, 4.84, 4.84, 4.84, 4.84, 10.0, d0)
    # make the minutes after it flat at the new price, as the exchange does
    for k in range(6, 15):
        rows[k] = flat(15 * 60 + 15 + k, 4.84, d0)
    b = bars(rows, "15m", venue=BITSTAMP, day=day, carry=4.58, closed=True)
    bar = b.filter(pl.col("n_minutes") == 15).row(0, named=True)
    # traded-minutes rule: open/high/low/close all 4.84 (a plain aggregate would give open 4.58 and low 4.58)
    assert (bar["open"], bar["high"], bar["low"], bar["close"], bar["volume"]) == (4.84, 4.84, 4.84, 4.84, 10.0)
    assert bar["n_traded"] == 1 and bar["hl_order"] == "flat"


def test_ohlc_volume_and_high_low_order():
    rows = [
        m(0, 10, 12, 9, 11, 1.0),   # high 12 first printed here, low 9 here too (same minute as high)
        flat(1, 11),
        m(2, 11, 13, 8, 10, 2.0),   # new high 13 and new low 8, same minute
        m(3, 10, 11, 10, 11, 1.5),
    ] + [flat(i, 11) for i in range(4, 15)]
    bar = bars(rows).row(0, named=True)
    assert (bar["open"], bar["high"], bar["low"], bar["close"]) == (10, 13, 8, 11)  # open of first TRADED minute
    assert bar["volume"] == 4.5 and bar["n_minutes"] == 15 and bar["n_traded"] == 3
    assert bar["hl_order"] == "same_minute"

    rows = [m(0, 10, 12, 10, 11, 1.0), m(5, 11, 11, 7, 8, 1.0)] + [flat(i, 8) for i in range(6, 15)]
    bar = bars(rows).row(0, named=True)
    assert bar["hl_order"] == "high_first"
    assert bar["ts_high"] < bar["ts_low"]

    rows = [m(0, 10, 10, 7, 8, 1.0), m(5, 8, 12, 8, 11, 1.0)]
    assert bars(rows).row(0, named=True)["hl_order"] == "low_first"


def test_bar_without_traded_minutes_is_flat_at_the_carried_close():
    rows = [m(0, 10, 11, 9, 10.5, 1.0)] + [flat(i, 10.5) for i in range(1, 15)] + [flat(i, 10.5) for i in range(15, 30)]
    b = bars(rows, "15m")
    second = b.row(1, named=True)
    assert second["n_traded"] == 0 and second["hl_order"] == "flat"
    assert (second["open"], second["high"], second["low"], second["close"], second["volume"]) == (10.5, 10.5, 10.5, 10.5, 0.0)
    assert second["ts_high"] is None and second["ts_low"] is None


def test_day_that_starts_inside_a_gap_uses_the_carry_in():
    # first 20 minutes missing (exchange outage), then trading
    rows = [m(i, 20, 21, 19, 20, 1.0) for i in range(20, 40)]
    b = bars(rows, "15m", carry=17.25)
    first, second = b.row(0, named=True), b.row(1, named=True)
    assert first["n_minutes"] == 0 and first["open"] == first["close"] == 17.25
    assert second["n_minutes"] == 10 and second["open"] == 20
    # no carry (very first day of a venue) -> unknown, not invented
    b = bars(rows, "15m", carry=None)
    assert b.row(0, named=True)["open"] is None


def test_grid_starts_at_the_venue_first_minute():
    d0 = day_start_ms("2020-03-25")
    first = utc_ms(2020, 3, 25, 10, 36)
    rows = [make_row(first + i * MINUTE_MS, 6500, 6500, 6500, 6500, 0.001 if i == 0 else 0.0) for i in range(60)]
    b = resample_day(frame_from_rows(rows), BYBIT, "2020-03-25", "1h", None, d0 + DAY_MS, True)
    assert b["ts"].dt.epoch("ms")[0] == utc_ms(2020, 3, 25, 10, 0)  # the bar containing the first minute
    assert b.height == 14  # 10:00 .. 23:00
    d = resample_day(frame_from_rows(rows), BYBIT, "2020-03-25", "1d", None, d0 + DAY_MS, True)
    assert d.height == 1 and d["n_minutes"][0] == 60


def test_complete_flag_comes_from_covered_until_not_the_clock():
    rows = [m(i, 10, 11, 9, 10, 1.0) for i in range(0, 130)]  # 02:10 of data
    covered = D0 + 130 * MINUTE_MS
    b = bars(rows, "1h", covered=covered, closed=False)
    flags = dict(zip(b["ts"].dt.epoch("ms").to_list(), b["complete"].to_list()))
    assert flags[D0] is True and flags[D0 + 3600_000] is True
    assert flags[D0 + 7200_000] is False  # 02:00 bar is still forming
    # a venue that failed to fetch: covered_until stuck at 00:50 -> the 00:00 bar is NOT complete even though rows exist
    b = bars(rows, "1h", covered=D0 + 50 * MINUTE_MS, closed=False)
    assert b["complete"].to_list()[0] is False
    # 1d needs the day to be closed
    d = bars(rows, "1d", covered=D0 + DAY_MS, closed=False)
    assert d["complete"][0] is False
    assert bars(rows, "1d", covered=D0 + DAY_MS, closed=True)["complete"][0] is True


def test_open_day_emits_bars_only_up_to_what_exists():
    rows = [m(i, 10, 11, 9, 10, 1.0) for i in range(0, 20)]
    b = bars(rows, "15m", covered=D0 + 20 * MINUTE_MS, closed=False)
    assert b.height == 2  # 00:00 and 00:15 (forming)
    assert b["complete"].to_list() == [True, False]


def test_last_traded_close_and_has_traded_minute():
    df = frame_from_rows([m(0, 10, 11, 9, 10.5, 1.0), flat(1, 10.5), flat(2, 10.5)])
    assert last_traded_close(df, 99.0) == 10.5 and has_traded_minute(df)
    zero = frame_from_rows([flat(0, 3.0), flat(1, 3.0)])
    assert last_traded_close(zero, 99.0) == 99.0 and not has_traded_minute(zero)
    assert last_traded_close(None, 7.0) == 7.0


@settings(max_examples=60, deadline=None)
@given(st.lists(st.tuples(st.booleans(), st.integers(1, 5), st.integers(0, 4), st.integers(0, 4)), min_size=240, max_size=240))
def test_1m_to_15m_to_1h_equals_1m_to_1h(spec):
    """Aggregating 15m bars (traded-minutes rule) into 1h gives the same bar as aggregating the minutes directly."""
    rows, price = [], 100.0
    for i, (traded, vol, up, down) in enumerate(spec):
        if traded:
            o = price
            c = price + up - down
            rows.append(m(i, o, max(o, c) + 1, min(o, c) - 1, c, float(vol)))
            price = c
        else:
            rows.append(flat(i, price))
    carry = 100.0
    b15 = bars(rows, "15m", carry=carry)
    b1h = bars(rows, "1h", carry=carry)
    for k in range(4):
        grp = b15.slice(4 * k, 4)
        traded = grp.filter(pl.col("n_traded") > 0)
        h = b1h.row(k, named=True)
        assert h["n_minutes"] == grp["n_minutes"].sum() and h["n_traded"] == grp["n_traded"].sum()
        assert abs(h["volume"] - grp["volume"].sum()) < 1e-9
        if traded.height:
            assert h["open"] == traded["open"][0] and h["close"] == traded["close"][-1]
            assert h["high"] == traded["high"].max() and h["low"] == traded["low"].min()
        else:
            assert h["open"] == h["close"] == h["high"] == h["low"]


def test_ts_high_and_ts_low_are_the_FIRST_traded_minute_at_the_extreme():
    # the high (12) prints at minute 0 and again at minute 5; the low (8) first prints at minute 5 and again at 9
    rows = [m(0, 10, 12, 10, 11, 1.0), m(5, 11, 12, 8, 9, 1.0), m(9, 9, 11, 8, 10, 1.0)] + [flat(i, 10) for i in (1, 2, 3, 4, 6, 7, 8, 10, 11, 12, 13, 14)]
    rows.sort(key=lambda r: r[0])
    bar = bars(rows).row(0, named=True)
    assert (bar["high"], bar["low"]) == (12, 8)
    assert bar["ts_high"].timestamp() * 1000 == D0 and bar["ts_low"].timestamp() * 1000 == D0 + 5 * MINUTE_MS
    assert bar["hl_order"] == "high_first"  # taking the LAST tie for the high would wrongly give same_minute

    # mirror image: the low (8) prints at minute 0 and again at 5; the high (11) first prints at minute 5 and again at 9
    rows = [m(0, 10, 10, 8, 9, 1.0), m(5, 9, 11, 8, 10, 1.0), m(9, 10, 11, 9, 10, 1.0)] + [flat(i, 10) for i in (1, 2, 3, 4, 6, 7, 8, 10, 11, 12, 13, 14)]
    rows.sort(key=lambda r: r[0])
    bar = bars(rows).row(0, named=True)
    assert bar["ts_low"].timestamp() * 1000 == D0 and bar["ts_high"].timestamp() * 1000 == D0 + 5 * MINUTE_MS
    assert bar["hl_order"] == "low_first"
