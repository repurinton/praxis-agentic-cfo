from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_cfo.data.generator import generate_cases_from_config, write_dataset
from agentic_cfo.experiment.contract import load_experiment_contract
from agentic_cfo.experiment.runner import run_experiment
from agentic_cfo.ui import analytics, reviews
from agentic_cfo.ui.store import PlatformStore

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def results_dir(tmp_path) -> Path:
    contract = load_experiment_contract(ROOT / "configs/experiment/paper_v1.yaml")
    cases = generate_cases_from_config(ROOT / "configs/datasets/paper_synthetic_v1.yaml")
    dataset_dir = tmp_path / "dataset"
    out = tmp_path / "results"
    write_dataset(cases, dataset_dir)
    run_experiment(
        contract=contract,
        dataset_path=dataset_dir,
        threshold_path=ROOT / contract.threshold_config,
        out_dir=out,
        max_cases_per_condition=1,
    )
    return out


# ----- artifact retention -------------------------------------------------


def test_matrix_run_retains_hashed_artifacts(results_dir):
    artifacts_path = results_dir / "artifacts.jsonl"
    assert artifacts_path.exists()
    records = [json.loads(line) for line in artifacts_path.read_text().splitlines() if line.strip()]
    assert len(records) == 60
    sample = records[0]
    assert {"artifact_id", "narrative", "claims", "source_records", "metrics"} <= set(sample)

    meta = json.loads((results_dir / "results.json").read_text())["meta"]
    assert meta["artifacts_count"] == 60
    # Recorded digest matches the file content (tamper-evidence).
    from hashlib import sha256

    assert meta["artifacts_sha256"] == sha256(artifacts_path.read_bytes()).hexdigest()


# ----- store reviews ------------------------------------------------------


def test_store_review_sample_and_rating_upsert(tmp_path):
    store = PlatformStore(tmp_path / "db.sqlite")
    store.replace_review_samples([
        {"blinded_id": "blind:a", "artifact_id": "art:1", "system": "agentic_cfo", "condition": "clean", "release_action": "release"},
        {"blinded_id": "blind:b", "artifact_id": "art:2", "system": "baseline_a_deterministic", "condition": "clean", "release_action": "not_applicable_no_release_gate"},
    ])
    assert len(store.list_review_samples()) == 2

    reviews.record_review(store, blinded_id="blind:a", artifact_id="art:1", reviewer_id="rev:1", rating=3, rationale="ok")
    reviews.record_review(store, blinded_id="blind:a", artifact_id="art:1", reviewer_id="rev:1", rating=2, rationale="revised")
    got = store.get_review(blinded_id="blind:a", reviewer_id="rev:1")
    assert got["rating"] == 2 and got["rationale"] == "revised"  # upsert, not duplicate
    assert len(store.list_reviews()) == 1


# ----- reviewer workflow --------------------------------------------------


def test_reviewer_workflow_blinding_progress_and_agreement(results_dir, tmp_path):
    store = PlatformStore(tmp_path / "db.sqlite")
    n = reviews.assign_blinded_sample(store, results_dir=results_dir, per_system=2, seed=42)
    assert n > 0

    artifacts = reviews.load_artifacts(results_dir)
    samples = store.list_review_samples()

    # Blinded item never exposes the generating system.
    first = reviews.reviewable_item(store, artifacts, blinded_id=samples[0]["blinded_id"], reviewer_id="rev:A")
    assert "system" not in first
    assert "narrative" in first and "claims" in first and "metrics" in first

    # Two reviewers rate every sampled item.
    for s in samples:
        reviews.record_review(store, blinded_id=s["blinded_id"], artifact_id=s["artifact_id"], reviewer_id="rev:A", rating=3)
        reviews.record_review(store, blinded_id=s["blinded_id"], artifact_id=s["artifact_id"], reviewer_id="rev:B", rating=2)

    prog = reviews.reviewer_progress(store, "rev:A")
    assert prog["reviewed"] == prog["total"] == n and prog["remaining"] == 0
    assert reviews.next_unrated(store, "rev:A") is None

    stats = reviews.review_analytics(store)
    assert stats["reviewer_count"] == 2
    assert stats["review_count"] == 2 * n
    assert 0.0 <= stats["raw_agreement"] <= 1.0
    # Reveal: mean rating grouped by true system is present.
    assert stats["mean_rating_by_system"]


# ----- analytics ----------------------------------------------------------


def test_analytics_summaries(results_dir, tmp_path):
    dataset_dir = tmp_path / "dataset"  # written by the fixture's run? no -> regenerate
    cases = generate_cases_from_config(ROOT / "configs/datasets/paper_synthetic_v1.yaml")
    write_dataset(cases, dataset_dir)

    syn = analytics.synthetic_data_summary(dataset_dir)
    assert syn["case_count"] == 60
    assert len(syn["accounts"]) == 7
    assert set(syn["partitions"]) == {"baseline_validation", "perturbation", "governance_review", "holdout_audit"}

    mets = analytics.metrics_summary(results_dir)
    assert {"agentic_cfo", "baseline_a_deterministic", "baseline_b_llm_assisted", "baseline_c_rag_only"} <= set(
        mets["clean_metric_by_system"]
    )

    arts = analytics.artifact_summary(results_dir)
    assert arts["retained_artifacts"] == 60
    assert arts["artifacts_sha256"]
