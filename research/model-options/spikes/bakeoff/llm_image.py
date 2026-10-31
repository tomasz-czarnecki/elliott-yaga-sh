"""The chart-image condition: the same prompt with a PNG chart instead of numbers.

`claude -p --tools ""` has no Read tool, so a file path alone gives the model nothing. The image goes in as a base64
block through --input-format stream-json.

    node research/model-options/spikes/bakeoff/render_chart.mjs $BAKE_OUT/windows/H2.json $BAKE_OUT/llm/H2.png
    uv run --with numpy python research/model-options/spikes/bakeoff/llm_image.py H2 D1
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from llm_prompts import prompt

OUT = Path(os.environ.get("BAKE_OUT", "/opt/data/cache/scratch/elliott_research_r1/bake"))
LLM = OUT / "llm"
LEDGER = LLM / "ledger.jsonl"
BUDGET = 60


def main() -> None:
    env = {**os.environ, "PATH": "/opt/data/.local/bin:" + os.environ.get("PATH", ""), "HOME": "/opt/data"}
    for wid in sys.argv[1:]:
        lines = LEDGER.read_text().splitlines()
        if len(lines) >= BUDGET:
            print("budget spent, stopping")
            return
        job = f"{wid}.image.1"
        w = json.loads((OUT / "windows" / f"{wid}.json").read_text())
        img = base64.b64encode((LLM / f"{wid}.png").read_bytes()).decode()
        msg = {"type": "user", "message": {"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img}},
            {"type": "text", "text": prompt(w, "image")}]}}
        t0 = time.time()
        r = subprocess.run(["claude", "-p", "--model", "opus", "--effort", "high", "--tools", "", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", "--no-session-persistence"],
                           input=json.dumps(msg) + "\n", cwd=OUT, env=env, capture_output=True, text=True, timeout=1500)
        secs = time.time() - t0
        (LLM / f"{job}.stream.jsonl").write_text(r.stdout)
        if r.stderr:
            (LLM / f"{job}.err.txt").write_text(r.stderr)
        final = None
        for line in r.stdout.splitlines():
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "result":
                final = ev
        if final is None:
            print(job, "no result event; exit", r.returncode, r.stderr[:400], r.stdout[:400])
            continue
        (LLM / f"{job}.out.json").write_text(json.dumps(final))
        u = final.get("usage", {})
        rec = {"id": job, "window": wid, "condition": "image", "run": 1, "secs": round(secs, 1), "exit": r.returncode, "prompt_chars": len(prompt(w, "image")), "ts": time.time(),
               "ok": not final.get("is_error"), "cost_usd": final.get("total_cost_usd"), "input": u.get("input_tokens"), "cache_write": u.get("cache_creation_input_tokens"),
               "cache_read": u.get("cache_read_input_tokens"), "output": u.get("output_tokens"), "thinking": (u.get("output_tokens_details") or {}).get("thinking_tokens"), "stop": final.get("stop_reason")}
        with LEDGER.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(job, "ok", rec["ok"], f"{secs:.0f}s", "$", rec["cost_usd"])


if __name__ == "__main__":
    main()
