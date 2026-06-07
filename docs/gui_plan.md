# Platform UI Plan

## Implemented Now

The Streamlit platform UI is available through `praxis_gui.py` and uses `src/agentic_cfo/ui/backend.py` as its Python backend.

Implemented surfaces:

- Dashboard health checks.
- Dataset generation and download.
- Experiment matrix execution through Python functions.
- Chapter 4 table generation.
- Run creation for the Agentic CFO fixture flow.
- Run monitoring with audit lifecycle counts.
- Audit event inspection and checksum verification.
- Results filtering by system, condition, and human-audit eligibility.
- Result, table, dataset, and run-bundle downloads.
- Human-audit demo workflow with sampling, adjudication, raw agreement, and weighted Cohen's kappa.
- Configuration preview.
- GUI roadmap page.

## Principles

- The UI must call Python backend functions directly.
- User-facing experiment operations must not require CLI commands.
- Generated artifacts remain filesystem-backed until a persistent metadata store is introduced.
- The UI should expose auditability, not hide it.
- Baselines remain metric-comparison systems without release gates, while Agentic CFO remains the governed release-gated system.

## Next GUI Work

| Area | Planned work |
| --- | --- |
| Access control | Add authentication and RBAC for Preparer, Reviewer, Approver, and Admin roles. |
| Background jobs | Add job queue, cancellation, retry, progress, and live logs for long matrix runs. |
| Persistent state | Add SQLite or Postgres metadata for datasets, runs, artifacts, jobs, and reviewer assignments. |
| Reviewer workflow | Add CPA rating import, double-blind assignment, reviewer packets, adjudication queue, comments, and rubric locks. |
| Prompt governance | Add template versioning, prompt diffs, approval states, and provider/runtime capture. |
| Metric integrations | Add external FActScore and RAGAS adapters with cached scoring payloads and evaluator manifests. |
| Analytics | Add hypothesis views, confidence intervals, statistical exports, and exact dissertation table/figure generation. |
| Artifact registry | Add search and filters across evidence spans, claims, exceptions, release attestations, and checksum manifests. |
| Operations | Add alerts for failed thresholds, stale datasets, broken audit chains, incomplete audit samples, and missing artifacts. |
| Deployment | Package as a service with environment profiles, health checks, backups, and object-store support. |

## Non-Goals For The Current Local UI

- It does not authenticate users.
- It does not run jobs asynchronously.
- It does not replace actual CPA review with synthetic ratings.
- It does not claim final dissertation result reproduction without provider-backed runs, actual reviewer inputs, and paper-scale artifacts.
