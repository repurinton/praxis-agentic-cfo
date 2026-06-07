from __future__ import annotations

from uuid import uuid4

from agentic_cfo.core.models import ReportArtifact, VerificationRecord
from agentic_cfo.evidence.corpus import EvidenceCorpus
from agentic_cfo.verification.engine import VerificationEngine


class AgenticCFOVerifierAgent:
    name = "AgenticCFOVerifierAgent"

    def __init__(self, engine: VerificationEngine | None = None):
        self.engine = engine or VerificationEngine()

    def verify(
        self,
        artifact: ReportArtifact,
        *,
        thresholds: dict[str, float],
        corpus: EvidenceCorpus | None = None,
    ) -> VerificationRecord:
        return self.engine.verify(
            artifact,
            verification_id=f"verification:{uuid4()}",
            thresholds=thresholds,
            corpus=corpus,
        )
