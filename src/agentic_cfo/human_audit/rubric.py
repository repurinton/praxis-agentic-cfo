from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import IntEnum
from typing import Any


class AuditRating(IntEnum):
    UNSUPPORTED = 0
    MATERIAL_ISSUES = 1
    MINOR_ISSUES = 2
    RELEASE_READY = 3


@dataclass(frozen=True)
class RubricLevel:
    rating: AuditRating
    label: str
    definition: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["rating"] = int(self.rating)
        return data


def default_rubric() -> tuple[RubricLevel, ...]:
    return (
        RubricLevel(AuditRating.UNSUPPORTED, "Unsupported", "Evidence is missing or does not support material claims."),
        RubricLevel(AuditRating.MATERIAL_ISSUES, "Material Issues", "One or more material numeric or factual issues remain."),
        RubricLevel(AuditRating.MINOR_ISSUES, "Minor Issues", "Evidence supports the artifact with non-material presentation issues."),
        RubricLevel(AuditRating.RELEASE_READY, "Release Ready", "Claims are adequately supported and ready for governed release."),
    )
