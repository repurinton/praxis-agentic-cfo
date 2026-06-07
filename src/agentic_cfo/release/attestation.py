from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from agentic_cfo.core.models import stable_hash
from agentic_cfo.release.roles import GovernanceRole


@dataclass(frozen=True)
class ReleaseAttestation:
    attestation_id: str
    run_id: str
    artifact_id: str
    release_id: str
    role: GovernanceRole
    actor_id: str
    statement: str
    payload_hash: str
    signature_hash: str
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["role"] = self.role.value
        return data


def sign_release_attestation(
    *,
    run_id: str,
    artifact_id: str,
    release_id: str,
    role: GovernanceRole,
    actor_id: str,
    statement: str,
    payload: dict[str, Any],
) -> ReleaseAttestation:
    payload_hash = stable_hash(json.dumps(payload, sort_keys=True, default=str))
    signature_material = json.dumps(
        {
            "actor_id": actor_id,
            "artifact_id": artifact_id,
            "payload_hash": payload_hash,
            "release_id": release_id,
            "role": role.value,
            "run_id": run_id,
            "statement": statement,
        },
        sort_keys=True,
    )
    return ReleaseAttestation(
        attestation_id=f"attestation:{uuid4()}",
        run_id=run_id,
        artifact_id=artifact_id,
        release_id=release_id,
        role=role,
        actor_id=actor_id,
        statement=statement,
        payload_hash=payload_hash,
        signature_hash=stable_hash(signature_material),
    )
