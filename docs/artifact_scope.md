# Artifact Scope

## Defensible Claim

This repository is an implemented scaffold and local platform for the Agentic CFO praxis architecture. It demonstrates the software controls needed for evidence-bound generation, verification, release governance, audit bundles, perturbation experiments, result-table generation, and human-audit workflow mechanics.

## What This Repository Supports

- Reproducible local dataset generation from checked-in config.
- Four system-condition runners: Baseline A, Baseline B, Baseline C, and Agentic CFO.
- Clean, single-perturbation, and compound-perturbation experiment runs.
- Deterministic local metric adapters for numeric agreement, FActScore-style factual support, RAGAS-style faithfulness, unsupported-claim rate, audit completeness, and traceability.
- Hash-chained audit events and checksum-protected run bundles.
- Prompt-template capture and locked run configuration capture.
- Human-audit sampling, rubric, adjudication, and agreement computation using synthetic demo ratings.
- A Python-backed Streamlit UI for managing local project operations.

## What This Repository Does Not Yet Prove

- It does not contain final provider-backed LLM outputs.
- It does not contain actual CPA reviewer ratings.
- It does not contain an IRB/OHR/advisor determination for human-review artifacts.
- It does not include external FActScore or RAGAS service runs.
- It does not include the final paper-scale empirical dataset or statistical notebooks.
- It should not be represented as the complete final dissertation reproduction package unless those missing artifacts are added and linked.

## Correct Review Framing

For academic review, describe this repository as:

> An implemented scaffold and reproducibility harness for the Agentic CFO praxis, with deterministic local substitutes for final empirical artifacts that are not yet included.

Do not describe this repository as independently reproducing final Chapter 4 empirical claims until final data, provider outputs, human-review artifacts, and analysis outputs are present.
