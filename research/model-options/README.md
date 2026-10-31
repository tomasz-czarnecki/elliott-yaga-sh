# Model options: how to teach a model how BTC behaves

Research round `elliott_research_r1`, 2026-10-30. The question: Opus, JEPA ("jev"), simple math, or something else? **Start with [`RECOMMENDATION.md`](RECOMMENDATION.md).**

Nothing in this folder is imported by `src/`. Nothing here is committed yet.

## Files

| File | What it is |
|---|---|
| [`RECOMMENDATION.md`](RECOMMENDATION.md) | The call: the answer in 10 lines, your questions answered, options compared and scored, architecture, plan with gates, what to stop believing, open questions, numbers checked |
| [`01-literature.md`](01-literature.md) | Worker LIT: what is published on JEPA, LLMs, foundation models, classical ML, Elliott and Fibonacci, engines, and the honesty machinery. Includes small first-look runs and a full bibliography |
| [`02-empirical.md`](02-empirical.md) | Worker EMP: what BTC's own history says. Sample sizes, Fibonacci against random paths, the weekly-cycle hypothesis, TDI |
| [`03-bakeoff.md`](03-bakeoff.md) | Worker BAKE: 60 Opus calls on real and random paths, then walk-forward simple ML against nulls. Includes the late-cycle lead |
| [`spikes/bakeoff/`](spikes/bakeoff/README.md) | BAKE's scripts: zigzag, rule checker, enumerator, Opus harness, ML pipeline, lead tests. A spike, not product code |
| [`spikes/empirical/`](spikes/empirical/) | EMP's scripts: zigzag, null paths, impulse checker, one script per test, `check_tools.py` |

Related, one level up: [`../cycles-r1.md`](../cycles-r1.md) (cycle marks and their nulls) and [`../probabilistic-elliott-wave-engine-plan.md`](../probabilistic-elliott-wave-engine-plan.md) (the master plan, not edited here; LIT section 11 lists corrections).

## Not in the repo

Raw outputs, downloads and some scripts live in `/opt/data/cache/scratch/elliott_research_r1/`, a scratch folder that may be cleaned:

| Folder | Holds |
|---|---|
| `lit/scripts/`, `lit/research_notes/` | LIT's own-run scripts, saved outputs, and stream notes |
| `emp/` | EMP's CSVs, figures, and `tables.md` with every table |
| `bake/` | Opus answers, windows, ML results, `llm_tables.md`, `ml/report.md`, `ml/leads_report.md` |
| `synth/` | The five synthesis scripts: `flag_replication.py`, `opus_vs_geometry.py`, `today_card.py`, `power.py`, `score_sensitivity.py` |
| `sources/` | Read-only copies of the rulebook and the course material. Commercial text: never copy it into this public repo |

## Reproduce

From the repo root, no GPU. The Python layer is ephemeral and leaves `pyproject.toml` and `uv.lock` alone:

```bash
export PATH=/opt/data/.local/bin:$PATH
```

- **EMP:** the commands are under "Reproduce" in [`02-empirical.md`](02-empirical.md), about 45 minutes. Seeded.
- **BAKE:** the commands are in [`spikes/bakeoff/README.md`](spikes/bakeoff/README.md). The ML part is seeded and reproduces on the same data. Opus answers differ on each run, so that part reproduces the distribution, not the numbers. It needs `claude` on the PATH and `$BAKE_RULEBOOK` set.
- **LIT:** own-run scripts are listed in section 12 of [`01-literature.md`](01-literature.md) and live in `lit/scripts/`.
- **Synthesis:**

```bash
SYN=/opt/data/cache/scratch/elliott_research_r1/synth
uv run --with numpy --with scipy --with scikit-learn --with lightgbm python $SYN/flag_replication.py btc     # a few minutes
uv run --with numpy --with scipy --with scikit-learn --with lightgbm python $SYN/flag_replication.py null --paths 100 --workers 2   # about 15 minutes
uv run --with numpy --with scipy python $SYN/today_card.py
python3 $SYN/opus_vs_geometry.py
python3 $SYN/power.py
python3 $SYN/score_sensitivity.py
```

The data grows every 15 minutes, so a rerun will move the last bars and a few counts slightly. Keep heavy runs sequential: this is a shared 4-core machine.
