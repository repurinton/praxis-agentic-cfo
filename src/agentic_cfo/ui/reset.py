"""Factory reset for the platform.

Returns the workspace to its default empty state: removes all generated
synthetic data, results, retained artifacts, run bundles, job history, review
samples, and ratings. Source configs and the API key (.env) are preserved
unless ``clear_settings`` is requested (which only resets mode/model, never the
key).

This is destructive; the UI gates it behind double confirmation. The backend is
pure and unit-tested.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from agentic_cfo.ui import backend
from agentic_cfo.ui.store import PlatformStore

# The exact phrase a user must type to enable the reset action.
CONFIRM_PHRASE = "RESET"

# Files preserved inside otherwise-wiped directories (placeholders kept in git).
_PRESERVE = {"README.md", ".gitkeep"}


def generated_targets(paths: backend.PlatformPaths) -> list[Path]:
    """Directories whose generated contents a reset removes."""
    return [
        paths.dataset_dir,
        paths.results_dir,
        paths.runs_dir,
        paths.human_audit_dir,
        paths.fixture_dir,
        paths.repo_root / ".agentic_cfo" / "logs",
    ]


def _count_files(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(1 for p in directory.rglob("*") if p.is_file() and p.name not in _PRESERVE)


def _wipe_dir_contents(directory: Path) -> int:
    if not directory.exists():
        return 0
    removed = _count_files(directory)
    for entry in directory.iterdir():
        if entry.name in _PRESERVE:
            continue
        if entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)
        else:
            entry.unlink(missing_ok=True)
    return removed


def platform_state_summary(paths: backend.PlatformPaths, store: PlatformStore) -> dict[str, Any]:
    """What currently exists — shown to the user before they confirm a reset."""
    dataset = backend.dataset_status(paths.dataset_dir)
    results = backend.result_status(paths.results_dir)
    runs = backend.list_run_roots(paths.runs_dir)
    return {
        "synthetic_cases": dataset["case_count"],
        "result_rows": results["row_count"],
        "runs": len(runs),
        "jobs": len(store.list_jobs()),
        "review_samples": len(store.list_review_samples()),
        "reviews": len(store.list_reviews()),
        "files": sum(_count_files(t) for t in generated_targets(paths)),
        "has_generated_data": bool(dataset["case_count"] or results["row_count"] or runs),
    }


def reset_platform(
    *,
    paths: backend.PlatformPaths,
    store: PlatformStore,
    clear_settings: bool = False,
) -> dict[str, Any]:
    """Delete all generated state and return a summary of what was removed."""
    files_removed = 0
    for target in generated_targets(paths):
        files_removed += _wipe_dir_contents(target)

    jobs_cleared = store.clear_all_jobs()
    samples_cleared = len(store.list_review_samples())
    store.clear_review_samples()
    reviews_cleared = len(store.list_reviews())
    store.clear_reviews()

    settings_reset = False
    if clear_settings:
        from agentic_cfo.ui import settings as settings_backend

        settings_backend.apply_settings(
            env_path=paths.repo_root / ".env",
            mode=settings_backend.DEFAULT_MODE,
            model=settings_backend.DEFAULT_MODEL,
            api_key=None,  # preserve the API key; only reset mode/model
            persist=True,
        )
        settings_reset = True

    return {
        "files_removed": files_removed,
        "jobs_cleared": jobs_cleared,
        "review_samples_cleared": samples_cleared,
        "reviews_cleared": reviews_cleared,
        "settings_reset": settings_reset,
    }
