from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agentic_cfo.core.models import stable_hash


@dataclass(frozen=True)
class DatasetManifest:
    dataset_id: str
    schema_version: str
    seed: int
    n_cases: int
    files: dict[str, str]
    row_counts: dict[str, int]
    validation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def file_hashes(root: Path) -> dict[str, str]:
    return {
        p.name: stable_hash(p.read_text(encoding="utf-8"))
        for p in sorted(root.iterdir())
        if p.is_file() and p.name != "manifest.json"
    }


def write_manifest(root: Path, manifest: DatasetManifest) -> None:
    (root / "manifest.json").write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
