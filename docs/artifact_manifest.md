# Artifact Manifest

## Included

- Active `agentic_cfo` package under `src/agentic_cfo`.
- Experiment contract and locked config files under `configs/`.
- Minimal checked-in fixture under `data/latest`.
- Deterministic paper-style dataset generator.
- Baseline A/B/C and Agentic CFO system runners.
- Perturbation framework for missing evidence, conflicting records, temporal misalignment, and compound conditions.
- PDF-aligned deterministic metric adapters.
- Hash-chained audit events for fixture runs.
- Prompt templates and prompt-capture records.
- Run artifact bundle writer with file checksums.
- Governance workflow with role records and release attestations.
- Human-audit rubric, blinded sampling, rating, adjudication, and agreement modules.
- Chapter 4 table-generation scripts.
- Unit and integration tests for the implemented scaffold phases.

## Generated Locally

These outputs are intentionally not checked in by default:

- `data/generated/paper_synthetic_v1/`
- `results/paper_v1/`
- `runs/<run_id>/`
- `human_audit/demo_summary.json`

## Not Included Yet

- Provider-backed LLM outputs.
- Actual CPA human-audit ratings.
- Paper-scale final dataset and statistical analysis artifacts.
- External FActScore/RAGAS service integrations.
- External object-store-backed immutable audit storage.
- IRB/OHR/advisor determination artifacts for human-review status.

The repository should be described as an implemented scaffold for phases 1-9, not yet as the final dissertation reproduction package.
