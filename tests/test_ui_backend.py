from __future__ import annotations

from pathlib import Path

from agentic_cfo.ui import backend


ROOT = Path(__file__).resolve().parents[1]


def test_ui_backend_dataset_experiment_results_and_downloads(tmp_path):
    paths = backend.PlatformPaths(
        repo_root=ROOT,
        dataset_dir=tmp_path / "dataset",
        results_dir=tmp_path / "results",
        runs_dir=tmp_path / "runs",
        fixture_dir=tmp_path / "fixture",
        human_audit_dir=tmp_path / "human_audit",
    )
    paths.ensure()

    dataset = backend.generate_dataset_from_config(
        config_path=ROOT / "configs/datasets/paper_synthetic_v1.yaml",
        out_dir=paths.dataset_dir,
    )
    result = backend.run_experiment_matrix_backend(
        contract_path=ROOT / "configs/experiment/paper_v1.yaml",
        dataset_out=paths.dataset_dir,
        results_out=paths.results_dir,
        max_cases_per_condition=1,
    )
    tables = backend.regenerate_chapter4_tables_backend(results_dir=paths.results_dir)

    assert dataset["exists"] is True
    assert dataset["case_count"] == 12
    assert result["rows"] == 12
    assert backend.result_status(paths.results_dir)["row_count"] == 12
    assert Path(tables["system_condition_summary"]).exists()
    assert backend.zip_directory_bytes(paths.results_dir)


def test_ui_backend_fixture_run_audit_and_human_audit(tmp_path):
    paths = backend.PlatformPaths(
        repo_root=ROOT,
        dataset_dir=tmp_path / "dataset",
        results_dir=tmp_path / "results",
        runs_dir=tmp_path / "runs",
        fixture_dir=tmp_path / "fixture",
        human_audit_dir=tmp_path / "human_audit",
    )
    paths.ensure()
    backend.generate_dataset_from_config(
        config_path=ROOT / "configs/datasets/paper_synthetic_v1.yaml",
        out_dir=paths.dataset_dir,
    )
    backend.run_experiment_matrix_backend(
        contract_path=ROOT / "configs/experiment/paper_v1.yaml",
        dataset_out=paths.dataset_dir,
        results_out=paths.results_dir,
        max_cases_per_condition=1,
    )

    run = backend.run_fixture_backend(
        fixture_dir=paths.fixture_dir,
        runs_dir=paths.runs_dir,
        run_id="run:ui",
        create_fixture=True,
    )
    run_root = Path(run["run_root"])
    detail = backend.run_detail(run_root)
    human = backend.human_audit_demo_backend(
        results_dir=paths.results_dir,
        out_path=paths.human_audit_dir / "demo_summary.json",
        per_system=2,
    )

    assert run["audit_valid"] is True
    assert run["artifact_bundle_valid"] is True
    assert detail["audit_valid"] is True
    assert detail["artifact_bundle_valid"] is True
    assert detail["audit_lifecycle"]["prompt_rendered"] == 3
    assert human["sample_count"] > 0
