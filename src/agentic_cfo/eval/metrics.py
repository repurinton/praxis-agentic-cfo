from __future__ import annotations

from agentic_cfo.core.models import AtomicClaim, ReportArtifact, VerificationCheck, VerificationStatus
from agentic_cfo.evidence.corpus import EvidenceCorpus


def _evidence_value(claim: AtomicClaim, corpus: EvidenceCorpus | None) -> float | None:
    if corpus is None:
        return None
    for pointer in claim.evidence:
        span = corpus.get(pointer.span_id)
        if span and claim.account and span.metadata.get("account") == claim.account:
            value = span.metadata.get("balance")
            if isinstance(value, (int, float)):
                return float(value)
    return None


def claim_supported_by_reliable_source(claim: AtomicClaim, corpus: EvidenceCorpus | None = None) -> bool:
    """Support test used for the local FActScore adapter.

    FActScore scores atomic facts by whether each is supported by a reliable
    knowledge source. In this financial-reporting implementation, `AtomicClaim`
    is the atomic-fact unit and the reliable source is the authoritative evidence
    corpus. Numeric claims require value agreement; narrative/derived claims
    require resolvable bound evidence spans.
    """
    if not claim.evidence:
        return False
    if corpus is None:
        return True
    if claim.value is not None:
        evidence_value = _evidence_value(claim, corpus)
        return evidence_value is not None and abs(float(claim.value) - evidence_value) <= 0.01
    return all(corpus.get(pointer.span_id) is not None for pointer in claim.evidence)


def claim_supported_by_retrieved_context(claim: AtomicClaim, retrieved_span_ids: set[str]) -> bool:
    """Support test used for the local RAGAS faithfulness adapter.

    RAGAS faithfulness asks whether generated claims can be inferred from the
    retrieved context. In the deterministic local implementation, the retrieved
    context is represented by evidence span IDs supplied to generation.
    """
    if not claim.evidence:
        return False
    return all(pointer.span_id in retrieved_span_ids for pointer in claim.evidence)


def numeric_agreement(
    artifact: ReportArtifact,
    checks: tuple[VerificationCheck, ...] = (),
    *,
    corpus: EvidenceCorpus | None = None,
) -> float:
    numeric_claims = tuple(c for c in artifact.claims if c.value is not None)
    numeric_ids = {c.claim_id for c in numeric_claims}
    if not numeric_ids:
        return 1.0
    if corpus is not None:
        passed = sum(1 for claim in numeric_claims if claim_supported_by_reliable_source(claim, corpus))
        return passed / len(numeric_claims)
    passed = {
        c.claim_id
        for c in checks
        if c.claim_id in numeric_ids and c.category == "numeric_agreement" and c.status == VerificationStatus.PASS
    }
    return len(passed) / len(numeric_ids)


def claim_traceability_rate(artifact: ReportArtifact) -> float:
    if not artifact.claims:
        return 1.0
    return sum(1 for c in artifact.claims if c.evidence) / len(artifact.claims)


def unsupported_claim_rate(artifact: ReportArtifact) -> float:
    if not artifact.claims:
        return 0.0
    return sum(1 for c in artifact.claims if not c.evidence) / len(artifact.claims)


def audit_evidence_package_completeness(artifact: ReportArtifact) -> float:
    required = 5
    present = 0
    if artifact.artifact_id:
        present += 1
    if artifact.run_id:
        present += 1
    if artifact.dataset_id:
        present += 1
    if artifact.claims:
        present += 1
    if all(c.evidence for c in artifact.claims):
        present += 1
    return present / required


def factscore(artifact: ReportArtifact, *, corpus: EvidenceCorpus | None = None) -> float:
    if not artifact.claims:
        return 1.0
    supported = sum(1 for claim in artifact.claims if claim_supported_by_reliable_source(claim, corpus))
    return supported / len(artifact.claims)


def ragas_faithfulness(artifact: ReportArtifact, *, retrieved_span_ids: set[str] | None = None) -> float:
    if not artifact.claims:
        return 1.0
    if retrieved_span_ids is None:
        retrieved_span_ids = {pointer.span_id for claim in artifact.claims for pointer in claim.evidence}
    supported = sum(1 for claim in artifact.claims if claim_supported_by_retrieved_context(claim, retrieved_span_ids))
    return supported / len(artifact.claims)
