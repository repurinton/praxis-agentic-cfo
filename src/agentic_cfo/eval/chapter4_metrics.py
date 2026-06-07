from __future__ import annotations

from agentic_cfo.core.models import ReportArtifact, VerificationRecord


def result_row(
    artifact: ReportArtifact,
    verification: VerificationRecord,
    *,
    release_action: str,
    release_gate_applied: bool,
    human_audit_eligible: bool,
    cycle_time_seconds: float,
) -> dict:
    return {
        "system": artifact.system.value,
        "partition": artifact.partition,
        "artifact_id": artifact.artifact_id,
        "numeric_agreement": verification.metrics["numeric_agreement"],
        "factscore": verification.metrics["factscore"],
        "ragas_faithfulness": verification.metrics["ragas_faithfulness"],
        "unsupported_claim_rate": verification.metrics["unsupported_claim_rate"],
        "audit_evidence_package_completeness": verification.metrics["audit_evidence_package_completeness"],
        "claim_traceability_rate": verification.metrics["claim_traceability_rate"],
        "release_action": release_action,
        "release_gate_applied": release_gate_applied,
        "human_audit_eligible": human_audit_eligible,
        "cycle_time_seconds": cycle_time_seconds,
    }
