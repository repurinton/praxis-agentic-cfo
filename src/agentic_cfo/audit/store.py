from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentic_cfo.audit.events import is_known_event_type


def _json_hash(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True, default=str)
    return sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    event_type: str
    timestamp_utc: str
    actor: str
    run_id: str
    artifact_id: str | None
    previous_event_hash: str
    payload_hash: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def event_hash(self) -> str:
        return _json_hash(self.to_dict())


class ImmutableAuditStore:
    """Append-only JSONL audit store with hash chaining."""

    def __init__(self, root: Path, *, run_id: str):
        self.root = root
        self.run_id = run_id
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "audit_events.jsonl"

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "GENESIS"
        last = ""
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last = line
        if not last:
            return "GENESIS"
        return _json_hash(json.loads(last))

    def append(
        self,
        event_type: str,
        *,
        actor: str,
        payload: dict[str, Any],
        artifact_id: str | None = None,
    ) -> AuditEvent:
        if not is_known_event_type(event_type):
            raise ValueError(f"Unknown audit event type: {event_type}")
        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            run_id=self.run_id,
            artifact_id=artifact_id,
            previous_event_hash=self._last_hash(),
            payload_hash=_json_hash(payload),
            payload=payload,
        )
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")
        return event

    def verify(self) -> bool:
        previous = "GENESIS"
        if not self.path.exists():
            return True
        with self.path.open("r", encoding="utf-8") as f:
            for raw in f:
                if not raw.strip():
                    continue
                event = json.loads(raw)
                if event["previous_event_hash"] != previous:
                    return False
                if event["payload_hash"] != _json_hash(event["payload"]):
                    return False
                previous = _json_hash(event)
        return True
