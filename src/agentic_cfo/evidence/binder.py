from __future__ import annotations

from agentic_cfo.core.models import AtomicClaim, EvidencePointer
from agentic_cfo.evidence.corpus import EvidenceCorpus


class EvidenceBinder:
    """Binds claims to stable evidence spans without treating retrieval as proof."""

    def __init__(self, corpus: EvidenceCorpus):
        self.corpus = corpus

    def bind_account_claim(self, claim: AtomicClaim) -> AtomicClaim:
        if not claim.account:
            return claim
        span = self.corpus.find_by_account(claim.account)
        if span is None:
            return claim
        return AtomicClaim(
            claim_id=claim.claim_id,
            claim_type=claim.claim_type,
            text=claim.text,
            value=claim.value,
            unit=claim.unit,
            account=claim.account,
            period=claim.period,
            material=claim.material,
            evidence=(EvidencePointer.from_span(span),),
            source_location=claim.source_location,
            metadata={**claim.metadata, "binding_method": "account_lookup"},
        )

    def bind_policy_claim(self, claim: AtomicClaim, key: str) -> AtomicClaim:
        span = self.corpus.find_policy(key)
        if span is None:
            return claim
        return AtomicClaim(
            claim_id=claim.claim_id,
            claim_type=claim.claim_type,
            text=claim.text,
            value=claim.value,
            unit=claim.unit,
            account=claim.account,
            period=claim.period,
            material=claim.material,
            evidence=(EvidencePointer.from_span(span),),
            source_location=claim.source_location,
            metadata={**claim.metadata, "binding_method": "policy_lookup"},
        )
