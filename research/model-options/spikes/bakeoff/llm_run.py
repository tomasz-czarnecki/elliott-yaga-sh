"""Calls `claude -p` for the planned window x condition x run cells, with a hard budget and a ledger.

    uv run --with numpy python research/model-options/spikes/bakeoff/llm_run.py --jobs D1.pivot.1 [--concurrency 3]
    ... --plan main|null|unmasked|live

Each call: no tools, Opus at high effort, run from the scratch folder so that no repo file enters its context. Finished
calls are never repeated; an answer that fails to parse is a measurement, not a retry. Only transport errors can be
rerun, and they still count against the budget.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from llm_prompts import prompt

OUT = Path(os.environ.get("BAKE_OUT", "/opt/data/cache/scratch/elliott_research_r1/bake"))
LLM = OUT / "llm"
LEDGER = LLM / "ledger.jsonl"
BUDGET = 60
RUNS = 3
_lock = threading.Lock()

PLANS = {
    "main": [(w, c) for w in ("D1", "D2", "D3", "H1", "H2", "H3") for c in ("pivot", "raw")],
    "null": [("N1", "pivot"), ("N1", "raw"), ("N2", "pivot"), ("N2", "raw"), ("N3", "pivot")],
    "unmasked": [("D1u", "pivot")],
    "live": [("L1", "pivot")],
}


def ledger() -> list[dict]:
    return [json.loads(x) for x in LEDGER.read_text().splitlines()] if LEDGER.exists() else []


def spent() -> int:
    return len(ledger())


def finished() -> set[str]:
    return {x["id"] for x in ledger() if x.get("ok")}


def call(job: str) -> dict:
    wid, condition, run = job.split(".")
    w = json.loads((OUT / "windows" / f"{wid}.json").read_text())
    text = prompt(w, condition)
    with _lock:
        if spent() >= BUDGET:
            return {"id": job, "skipped": "budget"}
        LEDGER.open("a").write(json.dumps({"id": job, "state": "started", "ts": time.time(), "ok": False, "placeholder": True}) + "\n")
    t0 = time.time()
    env = {**os.environ, "PATH": "/opt/data/.local/bin:" + os.environ.get("PATH", ""), "HOME": "/opt/data"}
    cmd = ["claude", "-p", text, "--model", "opus", "--effort", "high", "--tools", "", "--output-format", "json", "--no-session-persistence"]
    try:
        r = subprocess.run(cmd, cwd=OUT, env=env, capture_output=True, text=True, timeout=1500)
        out, err, code = r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        out, err, code = (e.stdout or ""), f"timeout {e}", -1
    secs = time.time() - t0
    (LLM / f"{job}.out.json").write_text(out if isinstance(out, str) else out.decode())
    if err:
        (LLM / f"{job}.err.txt").write_text(err if isinstance(err, str) else err.decode())
    rec = {"id": job, "window": wid, "condition": condition, "run": int(run), "secs": round(secs, 1), "exit": code, "prompt_chars": len(text), "ts": time.time()}
    try:
        j = json.loads(out)
        u = j.get("usage", {})
        m = next(iter(j.get("modelUsage", {}).items()), (None, {}))
        rec.update(ok=not j.get("is_error"), model=m[0], cost_usd=j.get("total_cost_usd"), input=u.get("input_tokens"),
                   cache_write=u.get("cache_creation_input_tokens"), cache_read=u.get("cache_read_input_tokens"), output=u.get("output_tokens"),
                   thinking=(u.get("output_tokens_details") or {}).get("thinking_tokens"), api_ms=j.get("duration_api_ms"), stop=j.get("stop_reason"))
    except Exception as e:  # noqa: BLE001  a crash here must not lose the ledger line
        rec.update(ok=False, parse_error=str(e)[:200])
    with _lock:
        lines = ledger()
        # replace this call's placeholder
        for i, x in enumerate(lines):
            if x.get("placeholder") and x["id"] == job:
                lines[i] = rec
                break
        LEDGER.write_text("".join(json.dumps(x) + "\n" for x in lines))
    print(f"{job}: ok={rec.get('ok')} {secs:.0f}s output={rec.get('output')} thinking={rec.get('thinking')} ${rec.get('cost_usd')}", flush=True)
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", nargs="*", default=[])
    ap.add_argument("--plan", nargs="*", default=[])
    ap.add_argument("--concurrency", type=int, default=3)
    args = ap.parse_args()
    LLM.mkdir(parents=True, exist_ok=True)
    jobs = list(args.jobs)
    for name in args.plan:
        jobs += [f"{w}.{c}.{r}" for w, c in PLANS[name] for r in range(1, RUNS + 1)]
    done = finished()
    jobs = [j for j in jobs if j not in done]
    random.Random(7).shuffle(jobs)  # so that no window is always first against a cold cache or a rate limit
    print(f"{len(jobs)} calls to run; {spent()} of {BUDGET} spent", flush=True)
    with ThreadPoolExecutor(args.concurrency) as pool:
        results = list(pool.map(call, jobs))
    print(f"done; {spent()} of {BUDGET} spent; ok {sum(1 for r in results if r.get('ok'))} of {len(results)}", flush=True)


if __name__ == "__main__":
    main()
