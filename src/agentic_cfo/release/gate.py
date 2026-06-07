from __future__ import annotations

from uuid import uuid4

from agentic_cfo.core.models import (
    ExceptionRecord,
    ReleaseAction,
    ReleaseDecisionRecord,
    VerificationRecord,
    VerificationStatus,
)


class ReleaseGate:
    def decide(self, verification: VerificationRecord) -> ReleaseDecisionRecord:
        exceptions: list[ExceptionRecord] = []
        for claim_id in verification.unsupported_claim_ids:
            exceptions.append(
                ExceptionRecord(
                    exception_id=f"exception:{uuid4()}",
                    claim_id=claim_id,
                    category="unsupported_claim",
                    material=True,
                    status="open",
                )
            )

        if verification.status == VerificationStatus.PASS:
            return ReleaseDecisionRecord(
                release_id=f"release:{uuid4()}",
                artifact_id=verification.artifact_id,
                run_id=verification.run_id,
                verification_id=verification.verification_id,
                status=VerificationStatus.PASS,
                action=ReleaseAction.RELEASE,
                reason="All verification thresholds passed.",
                attestation={"approver_role": "Approver", "status": "system_ready_for_approval"},
            )

        if exceptions and all(not e.material for e in exceptions):
            action = ReleaseAction.ROUTE_TO_REVIEW
            status = VerificationStatus.CONDITIONAL
            reason = "Non-material exceptions require documented review."
        else:
            action = ReleaseAction.BLOCK
            status = VerificationStatus.FAIL
            reason = "Material verification failures or threshold failures block release."

        return ReleaseDecisionRecord(
            release_id=f"release:{uuid4()}",
            artifact_id=verification.artifact_id,
            run_id=verification.run_id,
            verification_id=verification.verification_id,
            status=status,
            action=action,
            reason=reason,
            exceptions=tuple(exceptions),
        )
