#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentic_cfo.human_audit import (
    AuditRating,
    ReviewerRating,
    adjudicate_ratings,
    blinded_sample,
    cohen_weighted_kappa,
    outcome_distribution,
    raw_agreement,
)


def _synthetic_rating(index: int, reviewer_offset: int = 0) -> AuditRating:
    score = min(3, max(0, 3 - ((index + reviewer_offset) % 4 == 0)))
    return AuditRating(score)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-json", default="results/paper_v1/results.json")
    parser.add_argument("--out", default="human_audit/demo_summary.json")
    parser.add_argument("--per-system", type=int, default=120)
    args = parser.parse_args()

    rows = tuple(json.loads(Path(args.results_json).read_text(encoding="utf-8"))["rows"])
    samples = blinded_sample(rows, per_system=args.per_system)
    ratings: list[ReviewerRating] = []
    for idx, sample in enumerate(samples):
        ratings.append(ReviewerRating(sample.blinded_id, "reviewer:blind_a", _synthetic_rating(idx)))
        ratings.append(ReviewerRating(sample.blinded_id, "reviewer:blind_b", _synthetic_rating(idx, reviewer_offset=1)))

    adjudicated = adjudicate_ratings(tuple(ratings))
    payload = {
        "sample_count": len(samples),
        "rating_count": len(ratings),
        "raw_agreement": raw_agreement(tuple(ratings)),
        "weighted_cohens_kappa": cohen_weighted_kappa(tuple(ratings)),
        "adjudicated_distribution": outcome_distribution(adjudicated),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
