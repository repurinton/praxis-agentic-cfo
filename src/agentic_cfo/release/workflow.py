from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from agentic_cfo.core.models import ExceptionRecord, ReleaseAction, ReleaseDecisionRecord, VerificationStatus
from agentic_cfo.release.attestation import ReleaseAttestation, sign_release_attestation
from agentic_cfo.release.roles import GovernanceRole


@dataclass(frozen=True)
class GovernanceReviewRecord:
    release_id: str
    run_id: str
    artifact_id: str
    prepared_by: str
    reviewed_by: str
    approved_by: str | None
    dispositions: tuple[ExceptionRecord, ...]
    attestation: ReleaseAttestation | None
    final_action: ReleaseAction
    status: VerificationStatus

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["final_action"] = self.final_action.value
        data["status"] = self.status.value
        if self.attestation:
            data["attestation"] = self.attestation.to_dict()
        return data


class HumanGovernanceWorkflow:
    """Deterministic implementation of the PDF role model.

    It records the same control points a human workflow needs. It does not
    represent actual human approval unless actor IDs are supplied from a real
    review process.
    """

    def __init__(
        self,
        *,
        preparer_id: str = "system-preparer",
        reviewer_id: str = "system-reviewer",
        approver_id: str = "system-approver",
    ):
        self.preparer_id = preparer_id
        self.reviewer_id = reviewer_id
        self.approver_id = approver_id

    def review(self, release: ReleaseDecisionRecord) -> GovernanceReviewRecord:
        dispositions: list[ExceptionRecord] = []
        unresolved_material = False
        for exception in release.exceptions:
            if exception.material:
                unresolved_material = True
                dispositions.append(exception)
            else:
                dispositions.append(
                    ExceptionRecord(
                        exception_id=exception.exception_id,
                        claim_id=exception.claim_id,
                        category=exception.category,
                        material=exception.material,
                        status="dispositioned",
                        disposition="Accepted as non-material after reviewer inspection.",
                        reviewer_role=GovernanceRole.REVIEWER.value,
                    )
                )

        if release.action == ReleaseAction.RELEASE and release.status == VerificationStatus.PASS:
            attestation = sign_release_attestation(
                run_id=release.run_id,
                artifact_id=release.artifact_id,
                release_id=release.release_id,
                role=GovernanceRole.APPROVER,
                actor_id=self.approver_id,
                statement="Approver attests that release thresholds passed and required evidence is present.",
                payload=release.to_dict(),
            )
            return GovernanceReviewRecord(
                release_id=release.release_id,
                run_id=release.run_id,
                artifact_id=release.artifact_id,
                prepared_by=self.preparer_id,
                reviewed_by=self.reviewer_id,
                approved_by=self.approver_id,
                dispositions=tuple(dispositions),
                attestation=attestation,
                final_action=ReleaseAction.RELEASE,
                status=VerificationStatus.PASS,
            )

        return GovernanceReviewRecord(
            release_id=release.release_id,
            run_id=release.run_id,
            artifact_id=release.artifact_id,
            prepared_by=self.preparer_id,
            reviewed_by=self.reviewer_id,
            approved_by=None,
            dispositions=tuple(dispositions),
            attestation=None,
            final_action=ReleaseAction.BLOCK if unresolved_material else release.action,
            status=VerificationStatus.FAIL if unresolved_material else release.status,
        )
