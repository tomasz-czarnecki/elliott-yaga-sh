from __future__ import annotations

import polars as pl

from ewave.ingest.config import DAY_MS, MINUTE_MS, VENUES, day_start_ms, utc_ms
from ewave.ingest.schema import (
    content_hash, diff_frames, empty_frame, expected_minutes, find_gaps, frame_from_rows, from_disk, grid_bounds,
    merge_frames, to_disk, validate_day,
)
from ewave.ingest.store import Store

from .fakes import synth_row

BYBIT = VENUES["bybit_btcusdt_perp"]
BINANCE = VENUES["binance_btcusdt"]
BITSTAMP = VENUES["bitstamp_btcusd"]
DAY = "2026-10-20"
D0 = day_start_ms(DAY)


def day_frame(venue, n=1440, start=D0, zero=lambda t: False):
    return frame_from_rows([synth_row(venue, start + i * MINUTE_MS, zero=zero(start + i * MINUTE_MS)) for i in range(n)])


def test_expected_minutes_first_day_is_partial():
    assert expected_minutes(BYBIT, "2020-03-25") == 24 * 60 - (10 * 60 + 36)  # starts at 10:36
    assert expected_minutes(BYBIT, "2020-03-24") == 0
    assert expected_minutes(BYBIT, DAY) == 1440
    assert expected_minutes(BYBIT, DAY, upto_ms=D0 + 59 * MINUTE_MS) == 60
    assert grid_bounds(BYBIT, "2020-03-24") is None


def test_find_gaps():
    lo, hi = D0, D0 + 9 * MINUTE_MS
    ts = [D0 + i * MINUTE_MS for i in (0, 1, 4, 5, 8)]
    assert find_gaps(ts, lo, hi) == [
        (D0 + 2 * MINUTE_MS, D0 + 3 * MINUTE_MS, 2),
        (D0 + 6 * MINUTE_MS, D0 + 7 * MINUTE_MS, 2),
        (D0 + 9 * MINUTE_MS, D0 + 9 * MINUTE_MS, 1),
    ]
    assert find_gaps([], lo, lo + 2 * MINUTE_MS) == [(lo, lo + 2 * MINUTE_MS, 3)]
    assert find_gaps([D0 + i * MINUTE_MS for i in range(10)], lo, hi) == []


def test_merge_new_wins_and_nothing_is_deleted():
    a = frame_from_rows([synth_row(BYBIT, D0 + i * MINUTE_MS) for i in range(3)])
    changed = list(synth_row(BYBIT, D0 + MINUTE_MS))
    changed[1:5] = [5.0, 9.0, 4.0, 6.0]
    b = frame_from_rows([tuple(changed), synth_row(BYBIT, D0 + 5 * MINUTE_MS)])
    m = merge_frames(a, b)
    assert m["ts"].to_list() == [D0, D0 + MINUTE_MS, D0 + 2 * MINUTE_MS, D0 + 5 * MINUTE_MS]
    assert m.filter(pl.col("ts") == D0 + MINUTE_MS)["open"][0] == 5.0
    assert diff_frames(a, m) == (1, 1)


def test_content_hash_is_about_rows_not_file_bytes(tmp_path):
    df = day_frame(BYBIT, 100)
    h = content_hash(df)
    assert h == content_hash(df.reverse())  # order independent (sorted internally)
    # rewriting with other writer settings gives different bytes but the same logical content
    p1, p2 = tmp_path / "a.parquet", tmp_path / "b.parquet"
    to_disk(df).write_parquet(p1, compression="zstd", compression_level=3)
    to_disk(df).write_parquet(p2, compression="snappy", row_group_size=7)
    assert p1.read_bytes() != p2.read_bytes()
    assert content_hash(from_disk(pl.read_parquet(p1))) == content_hash(from_disk(pl.read_parquet(p2))) == h
    # any value change changes the hash
    changed = df.with_columns(pl.when(pl.col("ts") == D0).then(pl.col("volume") + 0.5).otherwise(pl.col("volume")).alias("volume"))
    assert content_hash(changed) != h
    assert content_hash(empty_frame()) == content_hash(empty_frame())


def test_disk_roundtrip_keeps_int_ms_and_nulls(tmp_path):
    df = day_frame(BITSTAMP, 10)  # bitstamp: no quote_volume / trades / close_ts
    store = Store(tmp_path)
    store.write_day(BITSTAMP.id, DAY, df)
    back = store.read_day(BITSTAMP.id, DAY)
    assert back.equals(df)
    assert back.schema["ts"] == pl.Int64
    on_disk = pl.read_parquet(store.raw_path(BITSTAMP.id, DAY))
    assert on_disk.schema["ts"] == pl.Datetime("ms", "UTC")


def test_validate_hard_rules():
    ok = day_frame(BYBIT, 60)
    assert validate_day(ok, BYBIT, DAY, D0 + 59 * MINUTE_MS).ok

    # high below low
    rows = [list(r) for r in ok.iter_rows()]
    rows[5][2], rows[5][3] = 1.0, 2.0
    bad = frame_from_rows([tuple(r) for r in rows])
    assert not validate_day(bad, BYBIT, DAY, None).ok

    # off-grid timestamp and out-of-order
    rows = [list(r) for r in ok.iter_rows()]
    rows[3][0] += 1
    assert any("minute boundary" in m for m in validate_day(frame_from_rows([tuple(r) for r in rows]), BYBIT, DAY, None).hard)
    rows = [list(r) for r in ok.iter_rows()]
    rows[4][0] = rows[3][0]
    assert any("increasing" in m for m in validate_day(frame_from_rows([tuple(r) for r in rows]), BYBIT, DAY, None).hard)

    # the forming minute must never be accepted
    assert any("after the last closed" in m for m in validate_day(ok, BYBIT, DAY, D0 + 30 * MINUTE_MS).hard)
    # a row from another day
    other = frame_from_rows([synth_row(BYBIT, D0 + DAY_MS)])
    assert not validate_day(other, BYBIT, DAY, None).ok
    # negative volume / non-positive price
    rows = [list(r) for r in ok.iter_rows()]
    rows[1][5] = -1.0
    assert any("negative volumes" in m for m in validate_day(frame_from_rows([tuple(r) for r in rows]), BYBIT, DAY, None).hard)
    # too many rows for the day
    assert not validate_day(day_frame(BYBIT, 1441, start=D0), BYBIT, DAY, None).ok


def test_validate_binance_candle_duration_and_zero_volume_rows_are_valid():
    df = day_frame(BINANCE, 30, zero=lambda t: t % (5 * MINUTE_MS) == 0)
    assert validate_day(df, BINANCE, DAY, None).ok  # zero-volume flat rows are real rows
    # a short candle at an outage edge (0 <= duration <= 59999 ms) is valid, even a zero-length one
    rows = [list(r) for r in df.iter_rows()]
    rows[2][10] = rows[2][0] + 14_788
    rows[3][10] = rows[3][0]
    assert validate_day(frame_from_rows([tuple(r) for r in rows]), BINANCE, DAY, None).ok
    rows[4][10] = rows[4][0] + 60_000  # a full minute + 1 ms is not
    assert any("duration" in m for m in validate_day(frame_from_rows([tuple(r) for r in rows]), BINANCE, DAY, None).hard)


def test_validate_soft_rules_do_not_block():
    rows = [list(r) for r in day_frame(BYBIT, 5).iter_rows()]
    rows[2][5] = 0.0  # zero volume but the candle is not flat
    v = validate_day(frame_from_rows([tuple(r) for r in rows]), BYBIT, DAY, None, bybit_open_rule=True)
    assert v.ok and v.soft
    assert any("not flat" in m for m in v.soft)
    assert any("previous close" in m for m in v.soft)  # synthetic opens do not chain, so the Bybit rule flags it


def test_raise_nofile_limit_lifts_a_low_soft_limit():
    import resource

    from ewave.ingest.config import raise_nofile_limit

    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (min(512, soft), hard))
        assert raise_nofile_limit(4096) == min(hard, 4096)
        assert resource.getrlimit(resource.RLIMIT_NOFILE)[0] == min(hard, 4096)
    finally:
        resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))
