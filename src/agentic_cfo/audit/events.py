from __future__ import annotations

RUN_LIFECYCLE_EVENT_TYPES = (
    "run_started",
    "manifest_locked",
    "source_loaded",
    "evidence_span_indexed",
    "prompt_rendered",
    "plan_created",
    "report_generated",
    "claim_extracted",
    "evidence_bound",
    "numeric_verified",
    "claim_verified",
    "threshold_evaluated",
    "exception_opened",
    "exception_dispositioned",
    "release_decided",
    "attestation_signed",
    "artifact_bundle_written",
    "run_completed",
)


def is_known_event_type(event_type: str) -> bool:
    return event_type in RUN_LIFECYCLE_EVENT_TYPES
