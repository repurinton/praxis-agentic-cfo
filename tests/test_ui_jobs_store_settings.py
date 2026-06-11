from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from agentic_cfo.ui import backend, settings
from agentic_cfo.ui.jobs import JobManager
from agentic_cfo.ui.store import PlatformStore

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _restore_managed_env():
    """apply_settings mutates os.environ directly; snapshot/restore so the live
    mode + test key never leak into other tests in the same process."""
    saved = {k: os.environ.get(k) for k in settings.MANAGED_KEYS}
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _paths(tmp_path: Path) -> backend.PlatformPaths:
    paths = backend.PlatformPaths(
        repo_root=ROOT,
        dataset_dir=tmp_path / "dataset",
        results_dir=tmp_path / "results",
        runs_dir=tmp_path / "runs",
        fixture_dir=tmp_path / "fixture",
        human_audit_dir=tmp_path / "human_audit",
    )
    paths.ensure()
    return paths


def _wait_terminal(store: PlatformStore, job_id: str, *, timeout: float = 60.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = store.get_job(job_id)
        if job and job.is_terminal:
            return job
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not finish within {timeout}s")


# ----- store --------------------------------------------------------------


def test_store_job_lifecycle(tmp_path):
    store = PlatformStore(tmp_path / "platform.db")
    job = store.create_job(job_id="job:1", kind="run_experiment_matrix", params={"max_cases_per_condition": 1})
    assert job.status == "queued"

    store.mark_started("job:1", total=10)
    store.mark_progress("job:1", progress=5, total=10)
    mid = store.get_job("job:1")
    assert mid.status == "running" and mid.progress == 5 and mid.fraction == 0.5

    store.mark_finished("job:1", status="succeeded", result={"rows": 10}, message="done")
    done = store.get_job("job:1")
    assert done.is_terminal and done.result == {"rows": 10}
    assert len(store.list_jobs()) == 1
    assert store.clear_terminal_jobs() == 1
    assert store.list_jobs() == ()


def test_store_settings_kv(tmp_path):
    store = PlatformStore(tmp_path / "platform.db")
    assert store.get_setting("missing", "fallback") == "fallback"
    store.set_setting("k", "v1")
    store.set_setting("k", "v2")  # upsert
    assert store.get_setting("k") == "v2"


# ----- settings -----------------------------------------------------------


def test_settings_env_roundtrip_preserves_other_lines(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# header\nPRAXIS_RUNS_DIR=runs\nOPENAI_API_KEY=\n", encoding="utf-8")

    settings.write_env_file(env, {"OPENAI_API_KEY": "sk-test", "AGENTIC_CFO_LLM_MODE": "live"})
    parsed = settings.parse_env_file(env)
    assert parsed["OPENAI_API_KEY"] == "sk-test"
    assert parsed["AGENTIC_CFO_LLM_MODE"] == "live"
    assert parsed["PRAXIS_RUNS_DIR"] == "runs"  # untouched
    assert "# header" in env.read_text(encoding="utf-8")  # comment preserved


def test_apply_settings_updates_environment_and_masks_key(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AGENTIC_CFO_LLM_MODE", raising=False)

    result = settings.apply_settings(
        env_path=env, mode="live", model="gpt-4o-mini", api_key="sk-secret-1234", persist=True
    )
    assert result["mode"] == "live"
    assert result["live_ready"] is True
    assert result["api_key_masked"].endswith("1234)")
    assert "sk-secret-1234" not in result["api_key_masked"]
    # Applied to the process so jobs in this process see it.
    import os

    assert os.environ["OPENAI_API_KEY"] == "sk-secret-1234"
    assert os.environ["AGENTIC_CFO_LLM_MODE"] == "live"
    # Persisted to .env.
    assert settings.parse_env_file(env)["OPENAI_API_KEY"] == "sk-secret-1234"


def test_current_settings_defaults_to_deterministic(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENTIC_CFO_LLM_MODE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    s = settings.current_settings(tmp_path / "missing.env")
    assert s["mode"] == "deterministic"
    assert s["api_key_present"] is False
    assert s["live_ready"] is False


# ----- job manager --------------------------------------------------------


def test_job_manager_runs_matrix_to_completion(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENTIC_CFO_LLM_MODE", raising=False)  # deterministic
    paths = _paths(tmp_path)
    store = PlatformStore(tmp_path / "platform.db")
    manager = JobManager(store, paths=paths, log_dir=tmp_path / "logs")

    job_id = manager.submit(
        "run_experiment_matrix",
        {"contract_path": str(ROOT / "configs/experiment/paper_v1.yaml"), "max_cases_per_condition": 1},
    )
    job = _wait_terminal(store, job_id)
    assert job.status == "succeeded"
    assert job.result["rows"] == 60
    assert job.progress == job.total == 60
    assert manager.read_log(job_id)  # non-empty log


def test_job_manager_records_failure(tmp_path):
    paths = _paths(tmp_path)
    store = PlatformStore(tmp_path / "platform.db")
    manager = JobManager(store, paths=paths, log_dir=tmp_path / "logs")

    job_id = manager.submit(
        "run_experiment_matrix",
        {"contract_path": str(tmp_path / "does_not_exist.yaml"), "max_cases_per_condition": 1},
    )
    job = _wait_terminal(store, job_id)
    assert job.status == "failed"
    assert job.error


def test_cancel_unknown_job_returns_false(tmp_path):
    store = PlatformStore(tmp_path / "platform.db")
    manager = JobManager(store, paths=_paths(tmp_path), log_dir=tmp_path / "logs")
    assert manager.cancel("job:nope") is False
