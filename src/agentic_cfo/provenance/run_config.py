from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agentic_cfo.core.models import stable_hash
from agentic_cfo.experiment.contract import load_yaml_mapping


@dataclass(frozen=True)
class LockedRunConfig:
    run_profile: str
    generation_owner: str
    models: dict[str, dict[str, Any]]
    artifacts: dict[str, Any]
    source_path: str
    config_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_locked_run_config(path: Path) -> LockedRunConfig:
    data = load_yaml_mapping(path)
    config_hash = stable_hash(json.dumps(data, sort_keys=True, default=str))
    return LockedRunConfig(
        run_profile=str(data["run_profile"]),
        generation_owner=str(data["generation_owner"]),
        models=dict(data.get("models", {})),
        artifacts=dict(data.get("artifacts", {})),
        source_path=str(path),
        config_hash=config_hash,
    )
