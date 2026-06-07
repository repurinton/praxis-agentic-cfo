from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from typing import Any

from agentic_cfo.core.models import stable_hash


@dataclass(frozen=True)
class AuditSample:
    blinded_id: str
    artifact_id: str
    system: str
    condition: str
    release_action: str
    inclusion_basis: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def blinded_sample(
    rows: tuple[dict[str, Any], ...],
    *,
    per_system: int,
    seed: int = 42,
    include_actions: tuple[str, ...] = ("release", "route_to_review", "not_applicable_no_release_gate"),
) -> tuple[AuditSample, ...]:
    rng = random.Random(seed)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if "human_audit_eligible" in row and not bool(row["human_audit_eligible"]):
            continue
        if row.get("release_action") not in include_actions:
            continue
        grouped.setdefault(str(row["system"]), []).append(row)

    samples: list[AuditSample] = []
    for system, system_rows in sorted(grouped.items()):
        shuffled = list(system_rows)
        rng.shuffle(shuffled)
        for row in shuffled[:per_system]:
            blinded_payload = json.dumps(
                {
                    "artifact_id": row["artifact_id"],
                    "condition": row["condition"],
                    "seed": seed,
                    "system": system,
                },
                sort_keys=True,
            )
            samples.append(
                AuditSample(
                    blinded_id=f"blind:{stable_hash(blinded_payload)[:16]}",
                    artifact_id=str(row["artifact_id"]),
                    system=system,
                    condition=str(row["condition"]),
                    release_action=str(row["release_action"]),
                    inclusion_basis="released_or_conditionally_released",
                )
            )
    return tuple(samples)
