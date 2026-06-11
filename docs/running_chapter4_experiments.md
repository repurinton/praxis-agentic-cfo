# Running the Chapter 4 Experiments

This document describes how to reproduce the Chapter 4 evaluation matrix and how
to switch between deterministic (reproducible, offline) and live (OpenAI-backed)
generation.

## Pipeline overview

The experiment compares four systems across three perturbation conditions:

| System                     | Generation                         | Release gate |
| -------------------------- | ---------------------------------- | ------------ |
| `baseline_a_deterministic` | deterministic templating           | no           |
| `baseline_b_llm_assisted`  | LLM draft, figures cited, unverified | no         |
| `baseline_c_rag_only`      | retrieval-grounded generation      | no           |
| `agentic_cfo`              | planner → controller → verifier    | **yes**      |

Conditions: `clean`, `single_perturbation`, `compound_perturbation`.
Each (system × condition × case) cell is executed `replications` times
(`configs/experiment/paper_v1.yaml`, default **5**) so run-to-run variation can
be characterized. The dataset is 60 reporting entities × 7 accounts with seeded
per-entity balance variation (`configs/datasets/paper_synthetic_v1.yaml`).

## Setup

```bash
make bootstrap        # creates .venv and installs the package
# or, minimally:
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev,synth]"        # deterministic mode
.venv/bin/pip install -e ".[dev,synth,agents]" # also enables live mode
```

## Deterministic mode (default — reproducible, no API key)

```bash
export PYTHONPATH=src
.venv/bin/python scripts/run_experiment_matrix.py \
  --max-cases-per-condition 1000 \
  --results-out results/paper_v1
```

Outputs:

- `results/paper_v1/results.json` — every result row plus a `meta` block
  recording `llm_mode`, `llm_model`, `replications`, and `row_count`.
- `results/paper_v1/table_system_condition_summary.csv` — the six metrics by
  system × condition, plus `release_gate_pass_rate` and `median_cycle_time_seconds`.
- `results/paper_v1/table_perturbation_deltas.csv` — degradation under perturbation.

Deterministic mode produces identical trials (zero variance) and sub-millisecond
cycle times; it exists for hermetic reproducibility and CI, not for latency
reporting.

## Live mode (OpenAI-backed — real outputs and latency)

1. Put a key in `.env`:

   ```bash
   cp .env.example .env
   # edit .env: OPENAI_API_KEY=sk-...
   ```

2. Run with live generation:

   ```bash
   export PYTHONPATH=src
   AGENTIC_CFO_LLM_MODE=live AGENTIC_CFO_LLM_MODEL=gpt-4o-mini \
     .venv/bin/python scripts/run_experiment_matrix.py \
     --max-cases-per-condition 1000 \
     --results-out results/paper_v1_live
   ```

In live mode:

- `baseline_b_llm_assisted`, `baseline_c_rag_only`, and `agentic_cfo` call the
  OpenAI API (`agentic_cfo/llm/`). `baseline_a_deterministic` stays deterministic
  by design.
- `cycle_time_seconds` is the **measured** wall-clock latency of each run, so the
  Chapter 4 cycle-time figures come from real model calls — no modeled or
  fabricated latencies.
- Trials now exhibit genuine nondeterminism, which the replication protocol
  captures.
- `results.json` `meta.llm_mode` is `live` and `meta.llm_model` records the model,
  so every result file is self-describing for provenance.

### Cost control

A full live run is `(60 + 180 + 60) × 3 LLM systems × replications` API calls.
Use `--max-cases-per-condition` and a smaller `replications` value (edit the
contract) to bound cost while validating, then scale up for the final run.

## Provenance

The `meta` block in `results.json` records exactly how a result set was produced
(mode, model, replications). Always report the mode used for any figure that
appears in the paper: deterministic results are reproducible illustrations of the
evaluation harness; live results are the empirical measurements.

## Platform UI

A Streamlit operator console manages the whole suite without touching the CLI:

```bash
.venv/bin/pip install -e ".[ui]"
.venv/bin/streamlit run praxis_gui.py
```

- **Experiments / Runs / Human Audit** enqueue work as **background jobs** so the
  UI never blocks. The **Jobs** page shows live progress, cancellation, per-job
  logs, and results. Job history is persisted in a SQLite store at
  `.agentic_cfo/platform.db` (gitignored) and survives restarts.
- **Settings** sets the `OPENAI_API_KEY` and toggles deterministic/live mode +
  model. Values are written to the gitignored `.env` and applied to subsequently
  launched jobs; the key is never displayed in full.
- **Results** surfaces the `meta` provenance (mode/model/replications) alongside
  the Chapter 4 tables.

The UI is a local single-user research console. Remaining production hardening
(reviewer workflow, prompt governance, external metric adapters, analytics,
deployment packaging) is enumerated on the in-app **GUI Plan** page.
