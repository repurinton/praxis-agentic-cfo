from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any


METRIC_COLUMNS = (
    "numeric_agreement",
    "factscore",
    "ragas_faithfulness",
    "unsupported_claim_rate",
    "audit_evidence_package_completeness",
    "claim_traceability_rate",
)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _median(values: list[float]) -> float:
    return float(statistics.median(values)) if values else 0.0


def summarize_by_system_condition(rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["system"]), str(row["condition"]))].append(row)

    summary = []
    for (system, condition), group in sorted(grouped.items()):
        release_eligible = [
            r
            for r in group
            if r.get("release_action") in {"release", "route_to_review", "not_applicable_no_release_gate"}
        ]
        human_audit_eligible = [r for r in group if bool(r.get("human_audit_eligible", False))]
        out = {
            "system": system,
            "condition": condition,
            "attempted_outputs": len(group),
            "release_gate_pass_rate": len(release_eligible) / len(group) if group else 0.0,
            "human_audit_eligible_outputs": len(human_audit_eligible),
            "median_cycle_time_seconds": _median([float(r["cycle_time_seconds"]) for r in group]),
        }
        for metric in METRIC_COLUMNS:
            out[metric] = _mean([float(r[metric]) for r in group])
        summary.append(out)
    return tuple(summary)


def perturbation_deltas(summary_rows: tuple[dict[str, Any], ...], *, baseline_condition: str = "clean") -> tuple[dict[str, Any], ...]:
    baseline = {
        row["system"]: row
        for row in summary_rows
        if row["condition"] == baseline_condition
    }
    deltas = []
    for row in summary_rows:
        if row["condition"] == baseline_condition or row["system"] not in baseline:
            continue
        base = baseline[row["system"]]
        deltas.append(
            {
                "system": row["system"],
                "condition": row["condition"],
                "numeric_disagreement_increase_bps": (
                    (1.0 - float(row["numeric_agreement"])) - (1.0 - float(base["numeric_agreement"]))
                )
                * 10000,
                "factscore_delta": float(base["factscore"]) - float(row["factscore"]),
                "unsupported_claim_rate_increase": float(row["unsupported_claim_rate"])
                - float(base["unsupported_claim_rate"]),
            }
        )
    return tuple(deltas)
