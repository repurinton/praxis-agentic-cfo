from __future__ import annotations

import json
from pathlib import Path

from agentic_cfo.data.generator import generate_cases_from_config, load_cases, write_dataset
from agentic_cfo.experiment.contract import load_experiment_contract


ROOT = Path(__file__).resolve().parents[1]


def test_paper_experiment_contract_loads():
    contract = load_experiment_contract(ROOT / "configs/experiment/paper_v1.yaml")

    assert contract.experiment_id == "paper_v1"
    assert contract.systems == (
        "baseline_a_deterministic",
        "baseline_b_llm_assisted",
        "baseline_c_rag_only",
        "agentic_cfo",
    )
    assert "compound_perturbation" in contract.conditions
    assert contract.replications == 5


def test_dataset_has_seven_accounts_and_seeded_per_entity_variation():
    cases = generate_cases_from_config(ROOT / "configs/datasets/paper_synthetic_v1.yaml")

    # Seven accounts per reporting case (paper Chapter 4 dataset spec).
    assert len(cases[0].records) == 7

    # Balances vary across entities (no two entities are identical clones).
    revenues = {next(r.balance for r in c.records if r.account == "Revenue") for c in cases}
    assert len(revenues) > 1

    # Sign discipline: non-negative accounts never cross zero.
    assert all(r.balance >= 0 for c in cases for r in c.records)

    # Generation is deterministic (seeded) -> identical on a second run.
    again = generate_cases_from_config(ROOT / "configs/datasets/paper_synthetic_v1.yaml")
    assert cases == again


def test_dataset_generator_writes_manifest_and_round_trips(tmp_path):
    cases = generate_cases_from_config(ROOT / "configs/datasets/paper_synthetic_v1.yaml")
    out = tmp_path / "dataset"

    write_dataset(cases, out)
    loaded = load_cases(out / "cases.jsonl")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))

    assert len(cases) == 60
    assert loaded[0] == cases[0]
    assert manifest["dataset_id"] == "paper_synthetic_v1"
    assert manifest["row_counts"]["cases"] == 60
    assert manifest["validation"]["valid"] is True
    assert {"baseline_validation", "perturbation", "governance_review", "holdout_audit"} <= {
        c.partition for c in cases
    }
