# Reproducibility

## Install

```bash
python -m pip install -e ".[dev]"
```

## Smoke Run

```bash
python -m agentic_cfo.cli run-fixture --create-fixture
```

The smoke run creates:

- `manifest.json`
- `report.json`
- `claims.jsonl`
- `evidence_spans.jsonl`
- `prompt_log.jsonl`
- `verification.json`
- `release.json`
- `checksums.json`
- `audit_events.jsonl`

Verify the audit chain:

```bash
python -m agentic_cfo.cli verify-audit runs/<run_id>
```

Equivalent nested audit command:

```bash
python -m agentic_cfo.cli audit verify runs/<run_id>
```

## Dataset Generation

```bash
PYTHONPATH=src python scripts/generate_paper_dataset.py --out data/generated/paper_synthetic_v1
```

## Experiment Matrix

```bash
PYTHONPATH=src python scripts/run_experiment_matrix.py \
  --contract configs/experiment/paper_v1.yaml \
  --dataset-out data/generated/paper_synthetic_v1 \
  --results-out results/paper_v1
```

For a fast local check:

```bash
PYTHONPATH=src python scripts/run_experiment_matrix.py \
  --dataset-out /tmp/praxis_dataset_matrix_check \
  --results-out /tmp/praxis_results_check \
  --max-cases-per-condition 1
```

The experiment matrix also writes:

- `table_system_condition_summary.csv`
- `table_perturbation_deltas.csv`

## Chapter 4 Tables

```bash
PYTHONPATH=src python scripts/generate_chapter4_tables.py \
  --results-json results/paper_v1/results.json \
  --out-dir results/paper_v1
```

## Human Audit Workflow Check

```bash
PYTHONPATH=src python scripts/run_human_audit_demo.py \
  --results-json results/paper_v1/results.json \
  --out human_audit/demo_summary.json \
  --per-system 120
```

This command validates sampling, de-identified ratings, adjudication, raw agreement, weighted Cohen's kappa, and outcome distributions using synthetic ratings. Actual CPA ratings must be supplied separately for dissertation-result claims.

## Verification

```bash
python -m pytest -q
make eval
```

## Academic Review Package

```bash
make review-ready
```

This command generates `review-output/review_manifest.json` and a bounded review package under `review-output/`. The manifest records environment details, command results, generated dataset status, experiment status, run-bundle validity, human-audit demo summary, and SHA-256-style hashes for review docs, configs, and generated review outputs.

## Boundary

The local matrix is deterministic and does not require external LLM calls. It validates experiment plumbing, evidence binding, verification metrics, prompt capture, audit bundles, release governance, perturbation behavior, human-audit mechanics, and table generation. It does not yet claim to reproduce final paper results until the full dataset, provider configurations, actual human-audit artifacts, external metric integrations, and statistical analysis outputs are added.
