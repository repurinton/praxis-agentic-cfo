# Methodology Alignment

The praxis PDF is treated as the controlling specification. The active package is `src/agentic_cfo`.

| PDF requirement | Current implementation |
| --- | --- |
| Planner Agent | `AgenticCFOPlannerAgent` in `src/agentic_cfo/agents/planner.py` |
| Controller Agent owns generation | `AgenticCFOControllerAgent.generate_report()` |
| Verifier Agent | `AgenticCFOVerifierAgent` in `src/agentic_cfo/agents/verifier.py` |
| Evidence binding | `EvidenceBinder`, `EvidenceSpan`, `EvidencePointer` |
| Immutable audit store | `ImmutableAuditStore` with hash-chained JSONL events |
| Four systems | `baseline_a_deterministic`, `baseline_b_llm_assisted`, `baseline_c_rag_only`, `agentic_cfo` |
| Experiment contract | `configs/experiment/paper_v1.yaml` and `ExperimentContract` |
| Dataset layer | `ReportingCase`, `FinancialRecord`, manifests, partitions, validation |
| Perturbations | Missing evidence, conflicting records, temporal misalignment, compound perturbations |
| Evaluation metrics | Numeric agreement, FActScore adapter, RAGAS faithfulness adapter, unsupported-claim rate, audit completeness, traceability |
| Release gate | Applied only to `agentic_cfo`; baselines are metric-only comparisons |
| Prompt/version capture | `PromptRecord`, locked run config, prompt templates, prompt log artifacts |
| Durable artifact package | `RunArtifactStore` writes manifest, report, claims, evidence spans, prompt logs, verification, release, checksums |
| Human governance | `HumanGovernanceWorkflow`, Preparer/Reviewer/Approver roles, release attestation |
| Human audit | Blinded sampling, four-level rubric, reviewer ratings, adjudication, weighted Cohen's kappa |
| Chapter 4 tables | System-condition summary and perturbation deltas from `results.json` |

## Phase Status

| Phase | Status | Key artifacts |
| --- | --- | --- |
| 1. Experiment contract | Implemented | `configs/experiment/paper_v1.yaml`, `src/agentic_cfo/experiment/contract.py` |
| 2. Dataset layer | Implemented | `src/agentic_cfo/data/`, `scripts/generate_paper_dataset.py` |
| 3. System runners | Implemented | `src/agentic_cfo/systems/` |
| 4. Metrics | Implemented deterministic adapters | `src/agentic_cfo/eval/metrics.py`, `docs/metrics_alignment.md` |
| 5. Perturbations | Implemented | `src/agentic_cfo/perturbations/` |
| 6. Prompt provenance | Implemented | `src/agentic_cfo/provenance/`, `src/agentic_cfo/agents/prompts/` |
| 7. Durable audit artifacts | Implemented | `src/agentic_cfo/audit/artifacts.py`, `src/agentic_cfo/audit/query.py` |
| 8. Governance workflow | Implemented | `src/agentic_cfo/release/workflow.py`, `src/agentic_cfo/release/attestation.py` |
| 9. Human audit and result tables | Implemented | `src/agentic_cfo/human_audit/`, `src/agentic_cfo/eval/chapter4_tables.py` |

## Current Boundary

The deterministic implementation is suitable for local scaffold validation and repeatable matrix runs. It is not yet the final paper reproduction stack because it still needs provider-backed generation, actual CPA reviewer ratings, larger dataset generation, external metric integrations, statistical notebooks, and documented IRB/OHR/advisor status for human-review artifacts.
