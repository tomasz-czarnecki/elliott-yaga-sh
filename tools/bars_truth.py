"""Sample of real bars for tools/shots_site.mjs --truth: the first, last and some random bars of every exported file.

    uv run python tools/bars_truth.py /opt/data/cache/scratch/elliott_site_r1/truth.json
"""
import json
import random
import sys

from ewave.data import load_bars
from ewave.ingest.config import TIMEFRAMES, VENUES
from ewave.ingest.export import site_data_dir

stats = json.loads((site_data_dir() / "stats.json").read_text())
rng = random.Random(7)
out = []
for vid in VENUES:
    for tf in TIMEFRAMES:
        e = stats["venues"][vid]["bars"][tf]
        df = load_bars(vid, tf, "2000-01-01", "2100-01-01")
        df = df.with_columns(df["ts"].dt.epoch("ms").alias("ms")).filter(df["ts"].dt.epoch("ms").is_between(e["first_ms"], e["last_ms"]))
        picks = [0, df.height - 1] + [rng.randrange(df.height) for _ in range(18)]
        for i in picks:
            r = df.row(i, named=True)
            out.append({"venue": vid, "tf": tf, "ts": r["ms"], "want": [r["open"], r["high"], r["low"], r["close"], r["volume"]]})
with open(sys.argv[1], "w") as f:
    json.dump(out, f)
print(len(out), "bars sampled")
