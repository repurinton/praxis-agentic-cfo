from __future__ import annotations

from pathlib import Path

from agentic_cfo.data.generator import generate_cases_from_config, write_dataset
from agentic_cfo.experiment.contract import load_experiment_contract
from agentic_cfo.experiment.runner import run_experiment
from agentic_cfo.ui import backend, reset, reviews
from agentic_cfo.ui.store import PlatformStore

ROOT = Path(__file__).resolve().parents[1]


def _populated(tmp_path):
    paths = backend.PlatformPaths(
        repo_root=tmp_path,
        dataset_dir=tmp_path / "dataset",
        results_dir=tmp_path / "results",
        runs_dir=tmp_path / "runs",
        fixture_dir=tmp_path / "fixture",
        human_audit_dir=tmp_path / "human_audit",
    )
    paths.ensure()
    store = PlatformStore(tmp_path / ".agentic_cfo" / "platform.db")

    contract = load_experiment_contract(ROOT / "configs/experiment/paper_v1.yaml")
    cases = generate_cases_from_config(ROOT / "configs/datasets/paper_synthetic_v1.yaml")
    write_dataset(cases, paths.dataset_dir)
    run_experiment(
        contract=contract,
        dataset_path=paths.dataset_dir,
        threshold_path=ROOT / contract.threshold_config,
        out_dir=paths.results_dir,
        max_cases_per_condition=1,
    )
    store.create_job(job_id="job:1", kind="run_experiment_matrix", params={})
    reviews.assign_blinded_sample(store, results_dir=paths.results_dir, per_system=2)
    sample = store.list_review_samples()[0]
    reviews.record_review(store, blinded_id=sample["blinded_id"], artifact_id=sample["artifact_id"], reviewer_id="rev:1", rating=3)
    return paths, store


def test_state_summary_reports_generated_data(tmp_path):
    paths, store = _populated(tmp_path)
    summary = reset.platform_state_summary(paths, store)
    assert summary["synthetic_cases"] == 60
    assert summary["result_rows"] == 60
    assert summary["jobs"] == 1
    assert summary["review_samples"] > 0
    assert summary["reviews"] == 1
    assert summary["files"] > 0
    assert summary["has_generated_data"] is True


def test_reset_returns_platform_to_default_empty_state(tmp_path):
    paths, store = _populated(tmp_path)
    result = reset.reset_platform(paths=paths, store=store)

    assert result["files_removed"] > 0
    assert result["jobs_cleared"] == 1
    assert result["reviews_cleared"] == 1

    # No synthetic data remains; directories are preserved but empty.
    assert backend.dataset_status(paths.dataset_dir)["case_count"] == 0
    assert backend.result_status(paths.results_dir)["row_count"] == 0
    assert not (paths.results_dir / "artifacts.jsonl").exists()
    assert store.list_jobs() == ()
    assert store.list_reviews() == ()
    assert store.list_review_samples() == ()

    after = reset.platform_state_summary(paths, store)
    assert after["has_generated_data"] is False
    assert after["files"] == 0


def test_reset_preserves_readme_placeholders(tmp_path):
    paths, store = _populated(tmp_path)
    (paths.runs_dir / "README.md").write_text("keep me", encoding="utf-8")
    reset.reset_platform(paths=paths, store=store)
    assert (paths.runs_dir / "README.md").exists()
