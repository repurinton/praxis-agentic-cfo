# Agentic CFO Praxis Scaffold

Praxis is an evidence-first, verification-aware scaffold for the Agentic CFO doctoral praxis. The praxis PDF remains the source of truth. This repository now implements the first nine build phases needed to move from scaffold to a Chapter 4 reproduction package:

- Phase 1: experiment contract
- Phase 2: dataset layer
- Phase 3: four system runners
- Phase 4: PDF-aligned evaluation metrics
- Phase 5: perturbation framework
- Phase 6: locked run provenance and prompt capture
- Phase 7: durable audit artifact bundles
- Phase 8: release governance workflow
- Phase 9: human audit and Chapter 4 aggregation

## Active Architecture

- `AgenticCFOPlannerAgent`
- `AgenticCFOControllerAgent`
- `AgenticCFOVerifierAgent`
- Controller-owned generation
- Evidence spans and evidence pointers
- Evidence binding for atomic claims
- Immutable hash-chained audit events
- Release gate for `agentic_cfo`
- Baseline A/B/C runners for experimental comparison
- Dataset manifest, validation, partitions, and perturbation conditions
- Prompt records with template, rendered prompt, model config, and hashes
- Run bundles with claims, evidence spans, prompt logs, checksums, and audit events
- Preparer/Reviewer/Approver governance records and release attestations
- Blinded human-audit sampling, four-level rubric, adjudication, and weighted Cohen's kappa
- Chapter 4-ready result tables

## Quickstart

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m agentic_cfo.cli run-fixture --create-fixture
make eval
```

## Academic Review Readiness

Run the minimum defensibility package:

```bash
make review-ready
```

This creates `review-output/review_manifest.json` and validates:

- Python compilation
- unit/integration tests
- dataset generation
- experiment matrix execution
- Chapter 4 table generation
- fixture run bundle generation
- audit-chain verification
- human-audit workflow mechanics using synthetic demo ratings

Read first:

- `docs/artifact_scope.md`
- `docs/data_metric_dictionary.md`
- `docs/human_audit_status.md`
- `docs/ai_tool_use_disclosure.md`

## Platform UI

Install the UI extra and launch the local app:

```bash
python -m pip install -e ".[dev,ui]"
python -m streamlit run praxis_gui.py
```

The UI manages project operations through the Python backend, not through CLI subprocesses. It includes:

- dashboard health checks
- dataset generation
- experiment matrix runs
- run monitoring and audit bundle inspection
- result filtering and Chapter 4 table downloads
- dataset downloads
- audit lifecycle review
- human-audit workflow checks
- configuration previews
- GUI implementation roadmap

## Generate The Paper-Style Dataset

```bash
PYTHONPATH=src python scripts/generate_paper_dataset.py --out data/generated/paper_synthetic_v1
```

This writes:

- `cases.jsonl`
- `trial_balance.csv`
- `manifest.json`

## Run The Experiment Matrix

```bash
PYTHONPATH=src python scripts/run_experiment_matrix.py \
  --contract configs/experiment/paper_v1.yaml \
  --dataset-out data/generated/paper_synthetic_v1 \
  --results-out results/paper_v1
```

The matrix evaluates:

- `baseline_a_deterministic`
- `baseline_b_llm_assisted`
- `baseline_c_rag_only`
- `agentic_cfo`

Across:

- `clean`
- `single_perturbation`
- `compound_perturbation`

Only `agentic_cfo` receives the governed release gate. Baselines are verified for metric comparability, but their `release_action` is `not_applicable_no_release_gate`.

## Generate Chapter 4 Tables

```bash
PYTHONPATH=src python scripts/generate_chapter4_tables.py \
  --results-json results/paper_v1/results.json \
  --out-dir results/paper_v1
```

This writes:

- `table_system_condition_summary.csv`
- `table_perturbation_deltas.csv`

## Human Audit Demo

```bash
PYTHONPATH=src python scripts/run_human_audit_demo.py \
  --results-json results/paper_v1/results.json \
  --out human_audit/demo_summary.json \
  --per-system 120
```

The demo uses deterministic synthetic reviewer ratings to validate the workflow. It is not a substitute for actual CPA ratings.

## Repository Layout

- `configs/` — experiment, dataset, evaluation, run-lock, and perturbation configs.
- `data/latest/` — minimal checked-in fixture.
- `docs/` — methodology, metrics, reproducibility, and artifact notes.
- `scripts/` — dataset and experiment reproduction entry points.
- `src/agentic_cfo/` — active PDF-aligned implementation.
- `src/praxis_core/`, `src/praxis_agents/` — legacy scaffold modules retained for continuity.
- `tests/` — unit and integration coverage for the scaffold phases.

## Boundary

This is now a working scaffold for the first nine implementation phases, not yet a final dissertation reproduction package. Remaining work includes provider-backed LLM calls, actual CPA reviewer inputs, richer paper-scale data, external FActScore/RAGAS integrations, statistical analysis notebooks, and documented IRB/OHR/advisor status for human-review artifacts.
