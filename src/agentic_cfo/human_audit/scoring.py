from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from agentic_cfo.human_audit.rubric import AuditRating


@dataclass(frozen=True)
class ReviewerRating:
    blinded_id: str
    reviewer_id: str
    rating: AuditRating
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["rating"] = int(self.rating)
        return data


@dataclass(frozen=True)
class AdjudicatedRating:
    blinded_id: str
    rating: AuditRating
    method: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["rating"] = int(self.rating)
        return data


def adjudicate_ratings(ratings: tuple[ReviewerRating, ...]) -> tuple[AdjudicatedRating, ...]:
    grouped: dict[str, list[ReviewerRating]] = {}
    for rating in ratings:
        grouped.setdefault(rating.blinded_id, []).append(rating)

    adjudicated: list[AdjudicatedRating] = []
    for blinded_id, group in sorted(grouped.items()):
        values = sorted(int(r.rating) for r in group)
        if not values:
            continue
        if len(set(values)) == 1:
            score = values[0]
            method = "unanimous"
        else:
            score = round(sum(values) / len(values))
            method = "rounded_mean_adjudication"
        adjudicated.append(AdjudicatedRating(blinded_id, AuditRating(score), method))
    return tuple(adjudicated)


def outcome_distribution(ratings: tuple[ReviewerRating | AdjudicatedRating, ...]) -> dict[str, int]:
    counts = Counter(AuditRating(int(r.rating)).name.lower() for r in ratings)
    return dict(sorted(counts.items()))
