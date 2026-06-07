from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class FinancialRecord:
    account: str
    balance: float
    period: str
    entity_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReportingCase:
    case_id: str
    dataset_id: str
    partition: str
    condition: str
    period: str
    entity_id: str
    records: tuple[FinancialRecord, ...]
    policy_text: str
    source_document_text: str
    perturbations: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportingCase":
        return cls(
            case_id=data["case_id"],
            dataset_id=data["dataset_id"],
            partition=data["partition"],
            condition=data["condition"],
            period=data["period"],
            entity_id=data["entity_id"],
            records=tuple(FinancialRecord(**r) for r in data["records"]),
            policy_text=data["policy_text"],
            source_document_text=data["source_document_text"],
            perturbations=tuple(data.get("perturbations", ())),
            metadata=dict(data.get("metadata", {})),
        )
