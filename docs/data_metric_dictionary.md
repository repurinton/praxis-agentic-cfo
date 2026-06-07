# Data And Metric Dictionary

## Dataset Files

| Artifact | Producer | Description |
| --- | --- | --- |
| `cases.jsonl` | `agentic_cfo.data.generator.write_dataset` | One `ReportingCase` JSON object per reporting case. |
| `trial_balance.csv` | `agentic_cfo.data.generator.write_dataset` | Flattened trial-balance rows by case, entity, period, account, and balance. |
| `manifest.json` | `agentic_cfo.data.manifest.write_manifest` | Dataset ID, schema version, seed, row counts, file hashes, and validation checks. |

## Case Schema

| Field | Meaning |
| --- | --- |
| `case_id` | Stable case identifier. |
| `dataset_id` | Dataset identifier. |
| `partition` | One of `baseline_validation`, `perturbation`, `governance_review`, `holdout_audit`. |
| `condition` | Experimental condition, initially `clean`; perturbation transforms update this field. |
| `period` | Reporting period. |
| `entity_id` | Synthetic entity identifier. |
| `records` | Tuple of `FinancialRecord` objects. |
| `policy_text` | Policy evidence text for traceability requirements. |
| `source_document_text` | Narrative source evidence text. |
| `perturbations` | Applied perturbation names. |

## Result Row Columns

| Column | Producer | Meaning |
| --- | --- | --- |
| `system` | `agentic_cfo.eval.chapter4_metrics.result_row` | System condition that produced the artifact. |
| `condition` | `agentic_cfo.experiment.runner.run_experiment` | Clean, single-perturbation, or compound-perturbation condition. |
| `artifact_id` | System runner | Report artifact identifier. |
| `case_id` | Experiment runner | Source case identifier. |
| `numeric_agreement` | `agentic_cfo.eval.metrics.numeric_agreement` | Fraction of numeric claims matching authoritative evidence. |
| `factscore` | `agentic_cfo.eval.metrics.factscore` | Atomic factual claims supported by the evidence corpus divided by total claims. |
| `ragas_faithfulness` | `agentic_cfo.eval.metrics.ragas_faithfulness` | Claims supported by retrieved/evidence spans divided by total claims. |
| `unsupported_claim_rate` | `agentic_cfo.eval.metrics.unsupported_claim_rate` | Claims lacking evidence divided by total claims. |
| `audit_evidence_package_completeness` | `agentic_cfo.eval.metrics.audit_evidence_package_completeness` | Required audit fields present divided by required fields. |
| `claim_traceability_rate` | `agentic_cfo.eval.metrics.claim_traceability_rate` | Claims with at least one evidence pointer divided by total claims. |
| `release_action` | `agentic_cfo.experiment.runner.run_experiment` | `release`, `route_to_review`, `block`, or `not_applicable_no_release_gate`. |
| `release_gate_applied` | Experiment runner | Whether the governed release gate was applied. True only for `agentic_cfo`. |
| `human_audit_eligible` | Experiment runner | Whether the row belongs in released-output human-audit sampling. |
| `cycle_time_seconds` | Experiment runner | Runtime from report generation start to verification/release-row creation. |

## Table Outputs

| Artifact | Producer | Description |
| --- | --- | --- |
| `table_system_condition_summary.csv` | `agentic_cfo.eval.chapter4_tables.write_chapter4_tables` | Mean metrics, attempted outputs, release pass rate, human-audit eligibility count, and median cycle time by system and condition. |
| `table_perturbation_deltas.csv` | `agentic_cfo.eval.aggregate.perturbation_deltas` | Perturbation deltas relative to clean condition by system. |

## Run Bundle Artifacts

| Artifact | Producer | Description |
| --- | --- | --- |
| `manifest.json` | `RunArtifactStore.write_bundle` | Run manifest, dataset ID, system, config hash, model config, thresholds, source hashes. |
| `report.json` | `RunArtifactStore.write_bundle` | Report artifact with narrative and atomic claims. |
| `claims.jsonl` | `RunArtifactStore.write_bundle` | One atomic claim per line. |
| `evidence_spans.jsonl` | `RunArtifactStore.write_bundle` | Evidence spans available to the run. |
| `prompt_log.jsonl` | `RunArtifactStore.write_bundle` | Prompt records with template/rendered prompt hashes and model config. |
| `verification.json` | `RunArtifactStore.write_bundle` | Verification checks, metrics, threshold results, unsupported claim IDs. |
| `release.json` | `RunArtifactStore.write_bundle` | Release decision, action, exceptions, attestation metadata. |
| `checksums.json` | `RunArtifactStore.write_bundle` | Hashes for bundle files. |
| `audit_events.jsonl` | `ImmutableAuditStore.append` | Hash-chained audit lifecycle events. |

## Human-Audit Outputs

| Artifact | Producer | Description |
| --- | --- | --- |
| `human_audit/demo_summary.json` | `scripts/run_human_audit_demo.py` or UI backend | Synthetic workflow-check summary with sample count, rating count, raw agreement, weighted Cohen's kappa, and adjudicated distribution. |

The human-audit demo summary is not actual CPA evidence.
