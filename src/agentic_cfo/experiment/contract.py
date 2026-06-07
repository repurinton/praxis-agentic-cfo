from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ExperimentContract:
    experiment_id: str
    systems: tuple[str, ...]
    conditions: tuple[str, ...]
    partitions: tuple[str, ...]
    replications: int
    dataset_config: str
    threshold_config: str
    locked_run_config: str

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ExperimentContract":
        return cls(
            experiment_id=str(data["experiment_id"]),
            systems=tuple(data["systems"]),
            conditions=tuple(data["conditions"]),
            partitions=tuple(data["partitions"]),
            replications=int(data["replications"]),
            dataset_config=str(data["dataset_config"]),
            threshold_config=str(data["threshold_config"]),
            locked_run_config=str(data["locked_run_config"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "systems": list(self.systems),
            "conditions": list(self.conditions),
            "partitions": list(self.partitions),
            "replications": self.replications,
            "dataset_config": self.dataset_config,
            "threshold_config": self.threshold_config,
            "locked_run_config": self.locked_run_config,
        }


def _parse_simple_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def load_experiment_contract(path: Path) -> ExperimentContract:
    return ExperimentContract.from_mapping(_parse_simple_yaml(path))


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    return _parse_simple_yaml(path)
