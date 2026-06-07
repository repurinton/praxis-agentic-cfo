from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_events(run_root: Path) -> tuple[dict[str, Any], ...]:
    path = run_root / "audit_events.jsonl"
    if not path.exists():
        return ()
    events = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return tuple(events)


def events_by_type(run_root: Path, event_type: str) -> tuple[dict[str, Any], ...]:
    return tuple(event for event in read_events(run_root) if event.get("event_type") == event_type)


def lifecycle_summary(run_root: Path) -> dict[str, int]:
    summary: dict[str, int] = {}
    for event in read_events(run_root):
        event_type = str(event.get("event_type", "unknown"))
        summary[event_type] = summary.get(event_type, 0) + 1
    return summary
