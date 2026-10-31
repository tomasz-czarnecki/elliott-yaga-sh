# Bake-off spike: does an LLM count, does simple ML learn

Scripts behind [`../../03-bakeoff.md`](../../03-bakeoff.md). A spike, not product code: nothing in `src/` imports this.

Run everything from the repo root. Outputs go to `$BAKE_OUT` (default `/opt/data/cache/scratch/elliott_research_r1/bake/`), never into the repo. The rulebook is read at run time from `$BAKE_RULEBOOK` and is never copied here, because it is commercial course material and this repo is public.

```bash
export PATH=/opt/data/.local/bin:$PATH
PY="uv run --with numpy --with scipy --with scikit-learn --with lightgbm python research/model-options/spikes/bakeoff"
```

## Files

| file | what it does |
|---|---|
| `zigzag.py` | causal zigzag (k x ATR(14), log price), ATR, RSI, bar loader over `ewave.data` |
| `rules.py` | NewWave rule checker, sections 0 to 3, and the rule-derived invalidation and target levels |
| `enumerator.py` | every rule-legal reading of a pivot window: a small grammar with nesting |
| `windows.py` | the BTC and shuffled-path windows, masked; pivot tables and raw-bar tables |
| `llm_prompts.py` | the prompt; identical for BTC and null windows |
| `llm_run.py` | calls `claude -p`, with a ledger and a hard budget of 60 calls |
| `render_chart.mjs`, `llm_image.py` | the chart-image condition |
| `llm_eval.py` | scores the answers: JSON, rule breaks, agreement, math, noise, outcomes, cost |
| `ml_features.py` | setups, labels, features, the volatility barrier, null paths |
| `ml_run.py` | walk-forward logistic and LightGBM, on BTC and null paths; planted-effect power test |
| `ml_report.py` | the ML tables |
| `ml_leads.py` | the targeted test of the weekly-window lead, with an `explain` view |
| `ml_flag_on_volatility.py` | the weekly flag on the plain volatility models |
| `ambiguity_null.py` | how common legal structures are on BTC against random paths |
| `check_causal.py` | lookahead checks: truncation, rewriting the future, planted leak |

## Part A: Opus as the counter

```bash
$PY/windows.py
$PY/llm_run.py --plan main null unmasked live --concurrency 3     # 57 calls, about 45 minutes
node research/model-options/spikes/bakeoff/render_chart.mjs $BAKE_OUT/windows/H2.json $BAKE_OUT/llm/H2.png
node research/model-options/spikes/bakeoff/render_chart.mjs $BAKE_OUT/windows/D1.json $BAKE_OUT/llm/D1.png
$PY/llm_image.py H2 D1
$PY/llm_eval.py                                                   # llm_tables.md, llm_counts.csv
```

Answers differ on every rerun: this measures a sampling model, so a rerun reproduces the distribution and not the numbers. The windows, the checker and the enumerator are deterministic.

## Part B: simple ML

```bash
$PY/check_causal.py
$PY/ml_run.py btc
for sc in 4h_k4 4h_k3 1h_k6; do for k in shuffled block; do $PY/ml_run.py null --scale $sc --kind $k --paths 40; done; done
for k in shuffled block; do $PY/ml_run.py null --scale 4h_k6 --kind $k --paths 20; $PY/ml_run.py null --scale 4h_k4 --kind $k --paths 20 --log-target; done
$PY/ml_run.py power --paths 40
$PY/ml_report.py
$PY/ml_leads.py run --scale 4h_k4 --paths 300
$PY/ml_leads.py run --scale 4h_k3 --paths 300
$PY/ml_leads.py run --scale 1h_k6 --paths 150
$PY/ml_leads.py run --scale 4h_k3 --paths 200 --block-days 60
$PY/ml_leads.py run --scale 4h_k4 --paths 200 --block-days 60
$PY/ml_leads.py explain --scale 4h_k4
$PY/ml_leads.py explain --scale 4h_k3
$PY/ml_leads.py report
$PY/ml_flag_on_volatility.py
$PY/ambiguity_null.py --paths 20
```

`ml_run.py btc` takes about a minute, a block of 40 null paths about 2 minutes on 2 workers, the leads about 8 minutes per scale. No GPU. Seeds are fixed, so the ML numbers reproduce exactly on the same data; new bars change them a little.
