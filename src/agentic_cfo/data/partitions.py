from __future__ import annotations


DEFAULT_PARTITIONS = (
    "baseline_validation",
    "perturbation",
    "governance_review",
    "holdout_audit",
)


def assign_partition(index: int, n_cases: int) -> str:
    if n_cases <= 1:
        return "baseline_validation"
    frac = index / n_cases
    if frac < 0.4:
        return "baseline_validation"
    if frac < 0.7:
        return "perturbation"
    if frac < 0.9:
        return "governance_review"
    return "holdout_audit"
