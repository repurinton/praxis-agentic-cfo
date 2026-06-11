"""Analytics aggregations for the platform UI.

Summarizes the synthetic dataset, the retained artifacts, the six evaluation
metrics across all baselines and the agentic system, and reviewer progress and
ratings. Returns plain dict/tuple structures; the UI renders charts and tables.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from agentic_cfo.eval.aggregate import (
    METRIC_COLUMNS,
    perturbation_deltas,
    summarize_by_system_condition,
)
from agentic_cfo.ui import backend, reviews
from agentic_cfo.ui.store import PlatformStore


def synthetic_data_summary(dataset_dir: Path) -> dict[str, Any]:
    status = backend.dataset_status(dataset_dir)
    manifest = status.get("manifest", {})

    tb_rows = backend.read_csv_rows(dataset_dir / "trial_balance.csv")
    by_account: dict[str, list[float]] = defaultdict(list)
    for row in tb_rows:
        try:
            by_account[row["account"]].append(float(row["balance"]))
        except (TypeError, ValueError):
            continue
    account_stats = {
        account: {
            "n": len(values),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "mean": round(sum(values) / len(values), 2),
        }
        for account, values in sorted(by_account.items())
    }

    partitions: Counter = Counter()
    cases_path = dataset_dir / "cases.jsonl"
    if cases_path.exists():
        for line in cases_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                partitions[json.loads(line)["partition"]] += 1

    return {
        "exists": status["exists"],
        "case_count": status["case_count"],
        "trial_balance_rows": status["trial_balance_rows"],
        "accounts": sorted(by_account.keys()),
        "account_stats": account_stats,
        "partitions": dict(sorted(partitions.items())),
        "seed": manifest.get("seed"),
        "validation": manifest.get("validation", {}),
    }


def metrics_summary(results_dir: Path) -> dict[str, Any]:
    rows = reviews.load_results_rows(results_dir)
    summary = summarize_by_system_condition(rows)
    deltas = perturbation_deltas(summary)

    # Clean-condition metric profile per system (for comparison charts).
    clean_by_system: dict[str, dict[str, float]] = {}
    gate_pass_by_system_condition: list[dict[str, Any]] = []
    for entry in summary:
        if entry["condition"] == "clean":
            clean_by_system[entry["system"]] = {m: round(float(entry[m]), 4) for m in METRIC_COLUMNS}
        gate_pass_by_system_condition.append({
            "system": entry["system"],
            "condition": entry["condition"],
            "release_gate_pass_rate": round(float(entry["release_gate_pass_rate"]), 4),
            "median_cycle_time_seconds": round(float(entry["median_cycle_time_seconds"]), 6),
        })

    return {
        "summary": summary,
        "deltas": deltas,
        "clean_metric_by_system": clean_by_system,
        "gate_pass_by_system_condition": gate_pass_by_system_condition,
        "metric_columns": list(METRIC_COLUMNS),
    }


def artifact_summary(results_dir: Path) -> dict[str, Any]:
    rows = reviews.load_results_rows(results_dir)
    path = results_dir / "results.json"
    meta = json.loads(path.read_text(encoding="utf-8")).get("meta", {}) if path.exists() else {}

    by_system_condition: Counter = Counter()
    release_actions: Counter = Counter()
    eligible = 0
    for row in rows:
        by_system_condition[(row.get("system"), row.get("condition"))] += 1
        release_actions[row.get("release_action")] += 1
        if row.get("human_audit_eligible"):
            eligible += 1

    artifacts_path = results_dir / "artifacts.jsonl"
    retained = 0
    if artifacts_path.exists():
        retained = sum(1 for line in artifacts_path.read_text(encoding="utf-8").splitlines() if line.strip())

    return {
        "total_rows": len(rows),
        "retained_artifacts": retained,
        "artifacts_sha256": meta.get("artifacts_sha256", ""),
        "llm_mode": meta.get("llm_mode", ""),
        "llm_model": meta.get("llm_model", ""),
        "replications": meta.get("replications"),
        "release_actions": dict(sorted(release_actions.items(), key=lambda kv: str(kv[0]))),
        "human_audit_eligible": eligible,
        "by_system_condition": [
            {"system": s, "condition": c, "count": n}
            for (s, c), n in sorted(by_system_condition.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1])))
        ],
    }


def full_analytics(*, dataset_dir: Path, results_dir: Path, store: PlatformStore) -> dict[str, Any]:
    return {
        "synthetic_data": synthetic_data_summary(dataset_dir),
        "artifacts": artifact_summary(results_dir),
        "metrics": metrics_summary(results_dir),
        "reviews": reviews.review_analytics(store),
    }
