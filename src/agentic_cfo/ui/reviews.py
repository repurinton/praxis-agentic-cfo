"""Reviewer workflow backend.

Builds a blinded review assignment from retained matrix artifacts, lets reviewers
classify each artifact with the four-level CPA rubric flags, persists ratings in
the SQLite store, and computes progress, inter-rater agreement, and adjudication.

Reviewers see the artifact content (narrative, claims, evidence bindings, source
records, metrics) and the perturbation condition, but NOT the generating system —
the assignment is blinded. The true system is revealed only in analytics.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentic_cfo.human_audit import (
    AuditRating,
    ReviewerRating,
    adjudicate_ratings,
    blinded_sample,
    cohen_weighted_kappa,
    default_rubric,
    outcome_distribution,
    raw_agreement,
)
from agentic_cfo.ui.store import PlatformStore


def rubric_flags() -> list[dict[str, Any]]:
    """The defined review flags (CPA four-level rubric)."""
    return [level.to_dict() for level in default_rubric()]


def load_results_rows(results_dir: Path) -> tuple[dict[str, Any], ...]:
    path = results_dir / "results.json"
    if not path.exists():
        return ()
    return tuple(json.loads(path.read_text(encoding="utf-8")).get("rows", ()))


def load_artifacts(results_dir: Path) -> dict[str, dict[str, Any]]:
    """Map artifact_id -> retained artifact record (from artifacts.jsonl)."""
    path = results_dir / "artifacts.jsonl"
    if not path.exists():
        return {}
    artifacts: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            artifacts[record["artifact_id"]] = record
    return artifacts


def assign_blinded_sample(
    store: PlatformStore,
    *,
    results_dir: Path,
    per_system: int,
    seed: int = 42,
) -> int:
    """Create and persist a blinded review assignment. Existing reviews are kept
    (blinded_ids are deterministic), so re-assigning is non-destructive."""
    rows = load_results_rows(results_dir)
    samples = blinded_sample(rows, per_system=per_system, seed=seed)
    return store.replace_review_samples([s.to_dict() for s in samples])


def record_review(
    store: PlatformStore,
    *,
    blinded_id: str,
    artifact_id: str,
    reviewer_id: str,
    rating: int,
    rationale: str = "",
) -> None:
    store.record_review(
        review_id=f"review:{uuid4()}",
        blinded_id=blinded_id,
        artifact_id=artifact_id,
        reviewer_id=reviewer_id,
        rating=int(rating),
        rationale=rationale,
    )


def reviewer_progress(store: PlatformStore, reviewer_id: str) -> dict[str, Any]:
    samples = store.list_review_samples()
    total = len(samples)
    reviewed = sum(
        1
        for s in samples
        if store.get_review(blinded_id=s["blinded_id"], reviewer_id=reviewer_id)
    )
    return {
        "reviewer_id": reviewer_id,
        "total": total,
        "reviewed": reviewed,
        "remaining": total - reviewed,
        "fraction": (reviewed / total) if total else 0.0,
    }


def next_unrated(store: PlatformStore, reviewer_id: str) -> dict[str, Any] | None:
    for sample in store.list_review_samples():
        if not store.get_review(blinded_id=sample["blinded_id"], reviewer_id=reviewer_id):
            return sample
    return None


def reviewable_item(
    store: PlatformStore,
    artifacts: dict[str, dict[str, Any]],
    *,
    blinded_id: str,
    reviewer_id: str,
) -> dict[str, Any] | None:
    sample = next(
        (s for s in store.list_review_samples() if s["blinded_id"] == blinded_id),
        None,
    )
    if sample is None:
        return None
    artifact = artifacts.get(sample["artifact_id"], {})
    existing = store.get_review(blinded_id=blinded_id, reviewer_id=reviewer_id)
    # Blinded view: expose condition, never the generating system.
    return {
        "blinded_id": blinded_id,
        "artifact_id": sample["artifact_id"],
        "condition": sample["condition"],
        "release_action": sample["release_action"],
        "narrative": artifact.get("narrative", ""),
        "claims": artifact.get("claims", []),
        "source_records": artifact.get("source_records", []),
        "metrics": artifact.get("metrics", {}),
        "verification_status": artifact.get("verification_status", ""),
        "existing_rating": existing["rating"] if existing else None,
        "existing_rationale": existing["rationale"] if existing else "",
    }


def _reviewer_ratings(store: PlatformStore) -> tuple[ReviewerRating, ...]:
    return tuple(
        ReviewerRating(
            blinded_id=r["blinded_id"],
            reviewer_id=r["reviewer_id"],
            rating=AuditRating(int(r["rating"])),
            rationale=r.get("rationale", ""),
        )
        for r in store.list_reviews()
    )


def review_analytics(store: PlatformStore) -> dict[str, Any]:
    ratings = _reviewer_ratings(store)
    reviews = store.list_reviews()
    samples = {s["blinded_id"]: s for s in store.list_review_samples()}

    per_reviewer: dict[str, int] = defaultdict(int)
    for r in reviews:
        per_reviewer[r["reviewer_id"]] += 1

    # Reveal: mean rating grouped by the true generating system.
    by_system: dict[str, list[int]] = defaultdict(list)
    for r in reviews:
        sample = samples.get(r["blinded_id"])
        if sample:
            by_system[sample["system"]].append(int(r["rating"]))
    rating_by_system = {
        system: round(sum(vals) / len(vals), 3)
        for system, vals in sorted(by_system.items())
        if vals
    }

    adjudicated = adjudicate_ratings(ratings)
    return {
        "review_count": len(ratings),
        "reviewer_count": len({r.reviewer_id for r in ratings}),
        "sample_count": len(samples),
        "raw_agreement": raw_agreement(ratings),
        "weighted_cohens_kappa": cohen_weighted_kappa(ratings),
        "rating_distribution": outcome_distribution(ratings),
        "adjudicated_distribution": outcome_distribution(adjudicated),
        "ratings_per_reviewer": dict(sorted(per_reviewer.items())),
        "mean_rating_by_system": rating_by_system,
    }
