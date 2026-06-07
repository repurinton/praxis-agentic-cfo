from __future__ import annotations

from agentic_cfo.human_audit.rubric import AuditRating
from agentic_cfo.human_audit.scoring import ReviewerRating


def _paired_scores(ratings: tuple[ReviewerRating, ...]) -> tuple[tuple[int, int], ...]:
    grouped: dict[str, list[ReviewerRating]] = {}
    for rating in ratings:
        grouped.setdefault(rating.blinded_id, []).append(rating)
    pairs = []
    for group in grouped.values():
        if len(group) >= 2:
            ordered = sorted(group[:2], key=lambda r: r.reviewer_id)
            pairs.append((int(ordered[0].rating), int(ordered[1].rating)))
    return tuple(pairs)


def raw_agreement(ratings: tuple[ReviewerRating, ...]) -> float:
    pairs = _paired_scores(ratings)
    if not pairs:
        return 1.0
    return sum(1 for left, right in pairs if left == right) / len(pairs)


def cohen_weighted_kappa(ratings: tuple[ReviewerRating, ...], *, quadratic: bool = True) -> float:
    pairs = _paired_scores(ratings)
    if not pairs:
        return 1.0

    categories = [int(r) for r in AuditRating]
    n_categories = len(categories)
    max_distance = n_categories - 1

    observed = {(i, j): 0 for i in categories for j in categories}
    left_counts = {i: 0 for i in categories}
    right_counts = {i: 0 for i in categories}
    for left, right in pairs:
        observed[(left, right)] += 1
        left_counts[left] += 1
        right_counts[right] += 1

    total = len(pairs)

    def weight(i: int, j: int) -> float:
        distance = abs(i - j) / max_distance
        return distance * distance if quadratic else distance

    observed_disagreement = sum(weight(i, j) * count for (i, j), count in observed.items()) / total
    expected_disagreement = 0.0
    for i in categories:
        for j in categories:
            expected = (left_counts[i] * right_counts[j]) / total
            expected_disagreement += weight(i, j) * expected
    expected_disagreement /= total

    if expected_disagreement == 0:
        return 1.0 if observed_disagreement == 0 else 0.0
    return 1.0 - (observed_disagreement / expected_disagreement)
