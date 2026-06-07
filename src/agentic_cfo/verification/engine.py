from __future__ import annotations

from agentic_cfo.core.models import (
    ReportArtifact,
    VerificationCheck,
    VerificationRecord,
    VerificationStatus,
)
from agentic_cfo.eval.metrics import (
    audit_evidence_package_completeness,
    claim_traceability_rate,
    factscore,
    numeric_agreement,
    ragas_faithfulness,
    unsupported_claim_rate,
)
from agentic_cfo.evidence.corpus import EvidenceCorpus


class VerificationEngine:
    def verify(
        self,
        artifact: ReportArtifact,
        *,
        verification_id: str,
        thresholds: dict[str, float],
        corpus: EvidenceCorpus | None = None,
    ) -> VerificationRecord:
        checks: list[VerificationCheck] = []
        unsupported: list[str] = []

        for claim in artifact.claims:
            if not claim.evidence:
                unsupported.append(claim.claim_id)
                checks.append(
                    VerificationCheck(
                        claim_id=claim.claim_id,
                        status=VerificationStatus.FAIL,
                        category="missing_evidence",
                        reason="Claim has no bound evidence span.",
                    )
                )
                continue

            checks.append(
                VerificationCheck(
                    claim_id=claim.claim_id,
                    status=VerificationStatus.PASS,
                    category="evidence_binding",
                    reason="Claim has one or more bound evidence spans.",
                    evidence_span_ids=tuple(e.span_id for e in claim.evidence),
                )
            )

            if claim.value is not None:
                evidence_value = None
                for pointer in claim.evidence:
                    span = corpus.get(pointer.span_id) if corpus is not None else None
                    if span and span.metadata.get("account") == claim.account:
                        raw_value = span.metadata.get("balance")
                        if isinstance(raw_value, (int, float)):
                            evidence_value = float(raw_value)
                ok = evidence_value is not None and abs(float(claim.value) - evidence_value) <= 0.01
                checks.append(
                    VerificationCheck(
                        claim_id=claim.claim_id,
                        status=VerificationStatus.PASS if ok else VerificationStatus.FAIL,
                        category="numeric_agreement",
                        reason="Numeric claim matches bound evidence." if ok else "Numeric claim does not match bound evidence.",
                        evidence_span_ids=tuple(e.span_id for e in claim.evidence),
                        metric_value=1.0 if ok else 0.0,
                    )
                )

        metrics = {
            "numeric_agreement": numeric_agreement(artifact, tuple(checks), corpus=corpus),
            "factscore": factscore(artifact, corpus=corpus),
            "ragas_faithfulness": ragas_faithfulness(artifact),
            "unsupported_claim_rate": unsupported_claim_rate(artifact),
            "audit_evidence_package_completeness": audit_evidence_package_completeness(artifact),
            "claim_traceability_rate": claim_traceability_rate(artifact),
        }

        threshold_results = {
            "numeric_agreement": metrics["numeric_agreement"] >= thresholds.get("numeric_agreement_min", 0.995),
            "factscore": metrics["factscore"] >= thresholds.get("factscore_min", 0.800),
            "ragas_faithfulness": metrics["ragas_faithfulness"] >= thresholds.get("ragas_faithfulness_min", 0.800),
            "unsupported_claim_rate": metrics["unsupported_claim_rate"] <= thresholds.get("unsupported_claim_rate_max", 0.010),
            "audit_evidence_package_completeness": metrics["audit_evidence_package_completeness"] >= thresholds.get("audit_evidence_package_completeness_min", 0.950),
            "claim_traceability_rate": metrics["claim_traceability_rate"] >= thresholds.get("claim_traceability_rate_min", 0.950),
        }

        failed_checks = [c for c in checks if c.status == VerificationStatus.FAIL]
        if failed_checks or not all(threshold_results.values()):
            status = VerificationStatus.FAIL
        else:
            status = VerificationStatus.PASS

        return VerificationRecord(
            verification_id=verification_id,
            artifact_id=artifact.artifact_id,
            run_id=artifact.run_id,
            status=status,
            checks=tuple(checks),
            metrics=metrics,
            threshold_results=threshold_results,
            unsupported_claim_ids=tuple(unsupported),
        )
