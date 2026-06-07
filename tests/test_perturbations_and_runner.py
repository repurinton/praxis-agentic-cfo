from __future__ import annotations

import json
from pathlib import Path

from agentic_cfo.data.generator import generate_cases_from_config, write_dataset
from agentic_cfo.experiment.contract import load_experiment_contract
from agentic_cfo.experiment.runner import cases_for_condition, run_experiment
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

    assert "Expense" not in {r.account for r in missing.records}
    assert missing.policy_text == ""
    assert next(r for r in conflicting.records if r.account == "Revenue").balance == 1050.0
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

    assert len(result.rows) == 12
    assert len(payload["rows"]) == 12
    assert {r["condition"] for r in result.rows} == {"clean", "single_perturbation", "compound_perturbation"}
    assert all(r["release_gate_applied"] is False for r in result.rows if r["system"] != "agentic_cfo")
    assert all(r["release_action"] == "not_applicable_no_release_gate" for r in result.rows if r["system"] != "agentic_cfo")
    assert all(r["release_gate_applied"] is True for r in result.rows if r["system"] == "agentic_cfo")


def test_cases_for_condition_expands_single_perturbations():
    case = generate_cases_from_config(ROOT / "configs/datasets/paper_synthetic_v1.yaml")[0]

    expanded = cases_for_condition((case,), "single_perturbation")

    assert len(expanded) == 3
    assert {c.perturbations[-1] for c in expanded} == {
        "missing_evidence",
        "conflicting_records",
        "temporal_misalignment",
    }
