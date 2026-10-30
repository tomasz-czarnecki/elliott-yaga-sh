from __future__ import annotations

import json

import polars as pl
import pytest

from ewave.data import load_bars
from ewave.ingest.backfill import backfill
from ewave.ingest.cli import main
from ewave.ingest.config import DAY_MS, MINUTE_MS, TIMEFRAMES, VENUES
from ewave.ingest.export import PRICE_SCALE, RECENT_DAYS, VOLUME_SCALE, encode_bars, export_site

from .fakes import T0

BYBIT = "bybit_btcusdt_perp"
BINANCE = "binance_btcusdt"
SINCE = "2026-10-18"


def seeded(make_collector, venues=(BYBIT,)):
    c = make_collector(list(venues))
    for v in venues:
        assert backfill(c, v, since=SINCE).status == "ok"
    return c


def decode(f: dict) -> list[dict]:
    """The same steps as decodeBars() in site/data.js."""
    rows, t, o = [], 0, 0
    for i in range(f["n"]):
        t = f["t"][0] if i == 0 else t + f["t"][i] * f["bar_s"]
        o = f["o"][0] if i == 0 else o + f["o"][i]
        s = f["price_scale"]
        rows.append({"t": t, "open": o / s, "high": (o + f["h"][i]) / s, "low": (o - f["l"][i]) / s,
                     "close": (o + f["c"][i]) / s, "volume": f["v"][i] / f["volume_scale"]})
    return rows


def read(out, vid, tf):
    return json.loads((out / "bars" / vid / f"{tf}.json").read_text())


def bars_df(rows):
    """Bars at given (minutes since the first bar, price, n_minutes)."""
    t0 = 1_700_000_000_000 - 1_700_000_000_000 % DAY_MS
    return pl.DataFrame({
        "ts": [t0 + m * MINUTE_MS for m, _, _ in rows],
        "open": [p for _, p, _ in rows],
        "high": [p + 5.25 for _, p, _ in rows],
        "low": [p - 3.5 for _, p, _ in rows],
        "close": [p + 1.01 for _, p, _ in rows],
        "volume": [1.2345 for _ in rows],
        "n_minutes": [n for _, _, n in rows],
    }).with_columns(pl.col("ts").cast(pl.Datetime("ms", "UTC")))


def test_every_exported_bar_decodes_to_the_stored_complete_bar(make_collector, tmp_path):
    c = seeded(make_collector)
    export_site(c, tmp_path)
    for tf in TIMEFRAMES:
        want = load_bars(BYBIT, tf, "2026-01-01", "2027-01-01", root=c.root)
        got = decode(read(tmp_path, BYBIT, tf))
        assert len(got) == want.height > 0
        assert [r["t"] * 1000 for r in got] == want["ts"].dt.epoch("ms").to_list()
        for col in ("open", "high", "low", "close"):
            assert [r[col] for r in got] == pytest.approx(want[col].to_list(), abs=0.5 / PRICE_SCALE)
        assert [r["volume"] for r in got] == pytest.approx(want["volume"].to_list(), abs=0.5 / VOLUME_SCALE)


def test_the_forming_bars_are_not_exported(make_collector, tmp_path):
    c = seeded(make_collector)
    everything = load_bars(BYBIT, "1h", "2026-01-01", "2027-01-01", complete_only=False, root=c.root)
    forming = everything.filter(~pl.col("complete"))
    assert forming.height > 0  # the fake clock stands mid-hour, so the last bar is still forming
    export_site(c, tmp_path)
    times = {r["t"] * 1000 for r in decode(read(tmp_path, BYBIT, "1h"))}
    assert not times & set(forming["ts"].dt.epoch("ms").to_list())
    assert len(times) == everything.height - forming.height


def test_the_recent_cap_applies_to_15m_only(make_collector, tmp_path, monkeypatch):
    c = seeded(make_collector)
    monkeypatch.setitem(RECENT_DAYS, "15m", 1)
    export_site(c, tmp_path)
    stats = json.loads((tmp_path / "stats.json").read_text())["venues"][BYBIT]["bars"]
    m15, h1 = stats["15m"], stats["1h"]
    assert m15["recent_days"] == 1 and m15["last_ms"] - m15["first_ms"] < DAY_MS
    assert h1["recent_days"] is None and h1["last_ms"] - h1["first_ms"] > DAY_MS
    assert m15["n"] == read(tmp_path, BYBIT, "15m")["n"] == 96


def test_stats_come_from_the_catalog(make_collector, tmp_path):
    c = seeded(make_collector, (BYBIT, BINANCE))
    c.catalog.replace_gaps(BINANCE, 0, 2**62, [(T0 - 10 * MINUTE_MS, T0 - 6 * MINUTE_MS, 5)])
    export_site(c, tmp_path)
    stats = json.loads((tmp_path / "stats.json").read_text())
    assert stats["generated_at_ms"] == T0
    assert stats["default_venue"] in stats["venues"]
    assert set(stats["venues"]) == set(VENUES)
    v = stats["venues"][BINANCE]
    assert (v["missing_minutes"], v["gaps"]) == (5, 1)
    b = stats["venues"][BYBIT]
    assert b["missing_minutes"] == 0
    assert b["rows_1m"] == sum(d["n_rows"] for d in c.catalog.days(BYBIT)) > 0
    assert b["last_minute_ms"] == c.catalog.last_ts(BYBIT)
    assert b["first_minute_ms"] == min(d["first_ts"] for d in c.catalog.days(BYBIT))
    assert b["last_ok_sync_ms"] == c.catalog.venue_state(BYBIT)["last_ok_run"]
    assert b["bars"]["1d"]["file"] == f"bars/{BYBIT}/1d.json"
    assert b["bars"]["1d"]["bytes"] == (tmp_path / b["bars"]["1d"]["file"]).stat().st_size


def test_a_venue_without_data_is_listed_without_bars(make_collector, tmp_path):
    c = seeded(make_collector)  # only Bybit has data
    export_site(c, tmp_path)
    stats = json.loads((tmp_path / "stats.json").read_text())
    assert stats["venues"][BINANCE]["bars"] == {} and stats["venues"][BINANCE]["rows_1m"] == 0
    assert not (tmp_path / "bars" / BINANCE).exists()


def test_rerunning_replaces_the_files_and_leaves_no_temp_files(make_collector, tmp_path, clock):
    c = seeded(make_collector)
    export_site(c, tmp_path)
    n_before = read(tmp_path, BYBIT, "1h")["n"]
    clock.advance(3 * 3600)
    assert c.sync([BYBIT])[0].ok
    export_site(c, tmp_path)
    assert read(tmp_path, BYBIT, "1h")["n"] > n_before
    assert not [p for p in tmp_path.rglob("*") if ".tmp-" in p.name]


def test_encoding_marks_short_bars_and_keeps_gaps_in_time():
    # a bar with 40 of its 60 minutes, then an outage of two whole bars
    f = encode_bars(bars_df([(0, 100.0, 60), (60, 101.5, 40), (240, 99.25, 60)]), BINANCE, "1h")
    assert f["t"][1:] == [1, 3]
    assert f["short"] == [[1, 40]]
    got = decode(f)
    assert [r["t"] - got[0]["t"] for r in got] == [0, 3600, 14400]
    assert [r["open"] for r in got] == [100.0, 101.5, 99.25]
    assert got[2]["high"] == 104.5 and got[2]["low"] == 95.75 and got[2]["close"] == 100.26


def test_encoding_refuses_a_bar_off_the_grid():
    with pytest.raises(ValueError, match="grid"):
        encode_bars(bars_df([(0, 100.0, 60), (61, 101.0, 60)]), BYBIT, "1h")


def test_the_cli_writes_to_out_and_reads_ewave_data(make_collector, tmp_path, monkeypatch, capsys):
    c = seeded(make_collector)
    c.catalog.close()
    monkeypatch.setenv("EWAVE_DATA", str(c.root))
    out = tmp_path / "site_data"
    assert main(["export-site", "--out", str(out)]) == 0
    assert "stats.json written" in capsys.readouterr().out
    assert read(out, BYBIT, "1d")["n"] > 0
