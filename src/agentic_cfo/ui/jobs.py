"""Background job manager for the platform UI.

Long operations (experiment matrix, dataset generation, fixture runs, human-audit
demo) run on daemon worker threads so the Streamlit UI thread never blocks. Job
state is persisted to the SQLite :class:`~agentic_cfo.ui.store.PlatformStore`, so
progress survives Streamlit's script reruns and the UI simply polls the store.

Cancellation is cooperative: each job owns a ``threading.Event`` that the
experiment runner polls via ``should_cancel``. Per-job logs are written to a file
under ``log_dir`` and surfaced in the UI.

The manager is a process-level singleton (``get_job_manager``) so it outlives
individual reruns. It depends only on the streamlit-free backend, keeping it
unit-testable.
"""

from __future__ import annotations

import threading
import time
import traceback
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentic_cfo.ui import backend
from agentic_cfo.ui.store import PlatformStore, default_db_path

JOB_KINDS = (
    "generate_dataset",
    "run_experiment_matrix",
    "regenerate_tables",
    "fixture_run",
    "human_audit_demo",
)

# Progress is throttled so a 6000-row run does not issue 6000 SQLite writes.
_PROGRESS_MIN_INTERVAL_S = 0.25
_PROGRESS_MIN_STEP_FRAC = 0.01


class JobManager:
    def __init__(self, store: PlatformStore, *, paths: backend.PlatformPaths, log_dir: Path):
        self.store = store
        self.paths = paths
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._cancels: dict[str, threading.Event] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    # ----- public API -----------------------------------------------------

    def submit(self, kind: str, params: dict[str, Any]) -> str:
        if kind not in JOB_KINDS:
            raise ValueError(f"Unknown job kind: {kind}")
        job_id = f"job:{uuid4()}"
        self.store.create_job(job_id=job_id, kind=kind, params=params)
        cancel = threading.Event()
        thread = threading.Thread(target=self._run, args=(job_id, kind, params, cancel), daemon=True)
        with self._lock:
            self._cancels[job_id] = cancel
            self._threads[job_id] = thread
        thread.start()
        return job_id

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            event = self._cancels.get(job_id)
        if event is None:
            return False
        event.set()
        return True

    def log_path(self, job_id: str) -> Path:
        return self.log_dir / f"{job_id.replace(':', '_')}.log"

    def read_log(self, job_id: str, *, tail: int | None = None) -> str:
        path = self.log_path(job_id)
        if not path.exists():
            return ""
        lines = path.read_text(encoding="utf-8").splitlines()
        if tail is not None:
            lines = lines[-tail:]
        return "\n".join(lines)

    def is_active(self, job_id: str) -> bool:
        with self._lock:
            thread = self._threads.get(job_id)
        return bool(thread and thread.is_alive())

    # ----- worker ---------------------------------------------------------

    def _log(self, job_id: str, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        with self.log_path(job_id).open("a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {message}\n")

    def _run(self, job_id: str, kind: str, params: dict[str, Any], cancel: threading.Event) -> None:
        from agentic_cfo.experiment.runner import ExperimentCancelled

        self._log(job_id, f"job {kind} started")
        self.store.mark_started(job_id, total=0)
        try:
            result = self._dispatch(job_id, kind, params, cancel)
            self.store.mark_finished(job_id, status="succeeded", result=result, message="completed")
            self._log(job_id, "job succeeded")
        except ExperimentCancelled as exc:
            self.store.mark_finished(job_id, status="cancelled", message=str(exc))
            self._log(job_id, f"job cancelled: {exc}")
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            self.store.mark_finished(
                job_id,
                status="failed",
                error=f"{type(exc).__name__}: {exc}",
                message="failed",
            )
            self._log(job_id, "job failed:\n" + traceback.format_exc())
        finally:
            with self._lock:
                self._cancels.pop(job_id, None)
                self._threads.pop(job_id, None)

    def _dispatch(self, job_id: str, kind: str, params: dict[str, Any], cancel: threading.Event) -> dict[str, Any]:
        paths = self.paths
        if kind == "generate_dataset":
            self.store.mark_progress(job_id, progress=0, total=1)
            status = backend.generate_dataset_from_config(
                config_path=Path(params["config_path"]),
                out_dir=paths.dataset_dir,
            )
            self.store.mark_progress(job_id, progress=1, total=1)
            return {"dataset": status}

        if kind == "run_experiment_matrix":
            progress_state = {"t": 0.0, "frac": 0.0}

            def on_progress(done: int, total: int) -> None:
                now = time.time()
                frac = (done / total) if total else 0.0
                if (
                    done >= total
                    or now - progress_state["t"] >= _PROGRESS_MIN_INTERVAL_S
                    or frac - progress_state["frac"] >= _PROGRESS_MIN_STEP_FRAC
                ):
                    progress_state["t"] = now
                    progress_state["frac"] = frac
                    self.store.mark_progress(job_id, progress=done, total=total)

            max_cases = params.get("max_cases_per_condition")
            self._log(job_id, f"running matrix (max_cases_per_condition={max_cases})")
            result = backend.run_experiment_matrix_backend(
                contract_path=Path(params["contract_path"]),
                dataset_out=paths.dataset_dir,
                results_out=paths.results_dir,
                max_cases_per_condition=max_cases,
                on_progress=on_progress,
                should_cancel=cancel.is_set,
            )
            return result

        if kind == "regenerate_tables":
            self.store.mark_progress(job_id, progress=0, total=1)
            tables = backend.regenerate_chapter4_tables_backend(results_dir=paths.results_dir)
            self.store.mark_progress(job_id, progress=1, total=1)
            return {"tables": tables}

        if kind == "fixture_run":
            self.store.mark_progress(job_id, progress=0, total=1)
            run = backend.run_fixture_backend(
                fixture_dir=paths.fixture_dir,
                runs_dir=paths.runs_dir,
                run_id=params.get("run_id") or None,
                create_fixture=True,
            )
            self.store.mark_progress(job_id, progress=1, total=1)
            return {"run": run}

        if kind == "human_audit_demo":
            self.store.mark_progress(job_id, progress=0, total=1)
            summary = backend.human_audit_demo_backend(
                results_dir=paths.results_dir,
                out_path=paths.human_audit_dir / "demo_summary.json",
                per_system=int(params.get("per_system", 10)),
            )
            self.store.mark_progress(job_id, progress=1, total=1)
            return {"human_audit": summary}

        raise ValueError(f"Unhandled job kind: {kind}")


_MANAGER: JobManager | None = None
_MANAGER_LOCK = threading.Lock()


def get_job_manager(paths: backend.PlatformPaths | None = None) -> JobManager:
    """Return the process-level JobManager singleton (created on first use)."""
    global _MANAGER
    with _MANAGER_LOCK:
        if _MANAGER is None:
            resolved = paths or backend.default_paths()
            store = PlatformStore(default_db_path(resolved.repo_root))
            _MANAGER = JobManager(
                store,
                paths=resolved,
                log_dir=resolved.repo_root / ".agentic_cfo" / "logs",
            )
        return _MANAGER


def reset_job_manager() -> None:
    """Test helper: drop the singleton so the next call rebuilds it."""
    global _MANAGER
    with _MANAGER_LOCK:
        _MANAGER = None
