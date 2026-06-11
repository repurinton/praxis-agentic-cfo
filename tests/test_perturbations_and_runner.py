from __future__ import annotations

import json
from pathlib import Path

from agentic_cfo.data.generator import generate_cases_from_config, write_dataset
import pytest

from agentic_cfo.experiment.contract import load_experiment_contract
from agentic_cfo.experiment.runner import (
    ExperimentCancelled,
    cases_for_condition,
    run_experiment,
)
from agentic_cfo.perturbations import (
    apply_compound_perturbation,
    apply_conflicting_records,
    apply_missing_evidence,
    apply_temporal_misalignment,
)


ROOT = Path(__file__).resolve().parents[1]


def test_perturbations_encode_missing_conflicting_and_temporal_conditions():
    case = generate_cases_from_config(ROOT / "configs/datasets/paper_synthetic_v1.yaml")[0]

    missing = apply_missing_evidence(case)
    conflicting = apply_conflicting_records(case)
    temporal = apply_temporal_misalignment(case)
    compound = apply_compound_perturbation(case)

    revenue_base = next(r.balance for r in case.records if r.account == "Revenue")
    assert "Expense" not in {r.account for r in missing.records}
    assert missing.policy_text == ""
    assert next(r for r in conflicting.records if r.account == "Revenue").balance == revenue_base + 50.0
    assert next(r for r in temporal.records if r.account == "Expense").period.endswith("MISALIGNED")
    assert compound.perturbations == ("missing_evidence", "conflicting_records", "temporal_misalignment")


def test_experiment_runner_writes_matrix_rows_and_applies_gate_only_to_agentic_cfo(tmp_path):
    contract = load_experiment_contract(ROOT / "configs/experiment/paper_v1.yaml")
    cases = generate_cases_from_config(ROOT / "configs/datasets/paper_synthetic_v1.yaml")
    dataset_dir = tmp_path / "dataset"
    out_dir = tmp_path / "results"
    write_dataset(cases, dataset_dir)

    result = run_experiment(
        contract=contract,
        dataset_path=dataset_dir,
        threshold_path=ROOT / contract.threshold_config,
        out_dir=out_dir,
        max_cases_per_condition=1,
    )
    payload = json.loads((out_dir / "results.json").read_text(encoding="utf-8"))

    # 3 conditions x 1 case (capped) x 4 systems x 5 replications = 60 rows.
    assert len(result.rows) == 60
    assert len(payload["rows"]) == 60
    assert {r["trial"] for r in result.rows} == {0, 1, 2, 3, 4}
    assert {r["condition"] for r in result.rows} == {"clean", "single_perturbation", "compound_perturbation"}
    assert all(r["release_gate_applied"] is False for r in result.rows if r["system"] != "agentic_cfo")
    assert all(r["release_action"] == "not_applicable_no_release_gate" for r in result.rows if r["system"] != "agentic_cfo")
    assert all(r["release_gate_applied"] is True for r in result.rows if r["system"] == "agentic_cfo")


def test_run_experiment_reports_progress_and_supports_cancellation(tmp_path):
    contract = load_experiment_contract(ROOT / "configs/experiment/paper_v1.yaml")
    cases = generate_cases_from_config(ROOT / "configs/datasets/paper_synthetic_v1.yaml")
    dataset_dir = tmp_path / "dataset"
    write_dataset(cases, dataset_dir)

    seen: list[tuple[int, int]] = []
    run_experiment(
        contract=contract,
        dataset_path=dataset_dir,
        threshold_path=ROOT / contract.threshold_config,
        out_dir=tmp_path / "results",
        max_cases_per_condition=1,
        on_progress=lambda done, total: seen.append((done, total)),
    )
    # Progress is monotonic and ends at the total (60 units for max_cases=1).
    assert seen[-1] == (60, 60)
    assert [d for d, _ in seen] == sorted(d for d, _ in seen)

    # Cooperative cancellation raises before completing.
    with pytest.raises(ExperimentCancelled):
        run_experiment(
            contract=contract,
            dataset_path=dataset_dir,
            threshold_path=ROOT / contract.threshold_config,
            out_dir=tmp_path / "results_cancelled",
            max_cases_per_condition=1,
            should_cancel=lambda: True,
        )


def test_cases_for_condition_expands_single_perturbations():
    case = generate_cases_from_config(ROOT / "configs/datasets/paper_synthetic_v1.yaml")[0]

    expanded = cases_for_condition((case,), "single_perturbation")

    assert len(expanded) == 3
    assert {c.perturbations[-1] for c in expanded} == {
        "missing_evidence",
        "conflicting_records",
        "temporal_misalignment",
    }
