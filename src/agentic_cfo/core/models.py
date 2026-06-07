from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Optional


def stable_hash(payload: str) -> str:
    return sha256(payload.encode("utf-8")).hexdigest()


class ClaimType(str, Enum):
    NUMERIC = "numeric"
    NARRATIVE = "narrative"
    POLICY = "policy"
    DERIVED = "derived"


class SystemCondition(str, Enum):
    BASELINE_A = "baseline_a_deterministic"
    BASELINE_B = "baseline_b_llm_assisted"
    BASELINE_C = "baseline_c_rag_only"
    AGENTIC_CFO = "agentic_cfo"


class VerificationStatus(str, Enum):
    PASS = "pass"
    CONDITIONAL = "conditional_pass"
    FAIL = "fail"


class ReleaseAction(str, Enum):
    RELEASE = "release"
    ROUTE_TO_REVIEW = "route_to_review"
    BLOCK = "block"


@dataclass(frozen=True)
class EvidenceSpan:
    span_id: str
    source_id: str
    source_type: str
    locator: str
    text: str
    content_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_text(
        cls,
        *,
        span_id: str,
        source_id: str,
        source_type: str,
        locator: str,
        text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "EvidenceSpan":
        return cls(
            span_id=span_id,
            source_id=source_id,
            source_type=source_type,
            locator=locator,
            text=text,
            content_hash=stable_hash(text),
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidencePointer:
    span_id: str
    source_id: str
    locator: str
    content_hash: str

    @classmethod
    def from_span(cls, span: EvidenceSpan) -> "EvidencePointer":
        return cls(
            span_id=span.span_id,
            source_id=span.source_id,
            locator=span.locator,
            content_hash=span.content_hash,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AtomicClaim:
    claim_id: str
    claim_type: ClaimType
    text: str
    value: Optional[float] = None
    unit: Optional[str] = None
    account: Optional[str] = None
    period: Optional[str] = None
    material: bool = True
    evidence: tuple[EvidencePointer, ...] = ()
    source_location: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["claim_type"] = self.claim_type.value
        return data


@dataclass(frozen=True)
class ReportArtifact:
    artifact_id: str
    system: SystemCondition
    run_id: str
    dataset_id: str
    partition: str
    title: str
    narrative: str
    claims: tuple[AtomicClaim, ...]
    generated_by: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["system"] = self.system.value
        return data


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    dataset_id: str
    partition: str
    system: SystemCondition
    config_hash: str
    model_config: dict[str, Any]
    threshold_config: dict[str, Any]
    source_hashes: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["system"] = self.system.value
        return data


@dataclass(frozen=True)
class VerificationCheck:
    claim_id: str
    status: VerificationStatus
    category: str
    reason: str
    evidence_span_ids: tuple[str, ...] = ()
    metric_value: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True)
class VerificationRecord:
    verification_id: str
    artifact_id: str
    run_id: str
    status: VerificationStatus
    checks: tuple[VerificationCheck, ...]
    metrics: dict[str, float]
    threshold_results: dict[str, bool]
    unsupported_claim_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True)
class ExceptionRecord:
    exception_id: str
    claim_id: str
    category: str
    material: bool
    status: str
    disposition: Optional[str] = None
    reviewer_role: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReleaseDecisionRecord:
    release_id: str
    artifact_id: str
    run_id: str
    verification_id: str
    status: VerificationStatus
    action: ReleaseAction
    reason: str
    exceptions: tuple[ExceptionRecord, ...] = ()
    attestation: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["action"] = self.action.value
        return data
