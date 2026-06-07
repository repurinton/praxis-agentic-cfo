#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentic_cfo.audit.artifacts import RunArtifactStore
from agentic_cfo.audit.query import lifecycle_summary
from agentic_cfo.audit.store import ImmutableAuditStore
from agentic_cfo.core.models import stable_hash
from agentic_cfo.ui import backend


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CommandResult:
    name: str
    command: list[str]
    returncode: int
    stdout_tail: str
    stderr_tail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _run(name: str, command: list[str]) -> CommandResult:
    proc = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    result = CommandResult(
        name=name,
        command=command,
        returncode=proc.returncode,
        stdout_tail=proc.stdout[-4000:],
        stderr_tail=proc.stderr[-4000:],
    )
    if proc.returncode != 0:
        raise SystemExit(json.dumps(result.to_dict(), indent=2))
    return result


def _hash_file(path: Path) -> str:
    return stable_hash(path.read_text(encoding="utf-8"))


def _hash_tree(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return {
        str(file.relative_to(REPO_ROOT)): _hash_file(file)
        for file in sorted(path.rglob("*"))
        if file.is_file()
    }


def _package_versions() -> dict[str, str]:
    packages = ("pandas", "pytest", "streamlit", "yaml")
    versions: dict[str, str] = {}
    for package in packages:
        try:
            if package == "yaml":
                import yaml

                versions["PyYAML"] = yaml.__version__
            else:
                module = __import__(package)
                versions[package] = str(getattr(module, "__version__", "unknown"))
        except Exception:
            versions[package] = "not_installed"
    return versions


def build_review_package(*, max_cases_per_condition: int, out_dir: Path, run_checks: bool) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = backend.PlatformPaths(
        repo_root=REPO_ROOT,
        dataset_dir=out_dir / "dataset",
        results_dir=out_dir / "results",
        runs_dir=out_dir / "runs",
        fixture_dir=out_dir / "fixture",
        human_audit_dir=out_dir / "human_audit",
    )
    paths.ensure()

    commands: list[CommandResult] = []
    if run_checks:
        commands.append(_run("pycompile", [sys.executable, "-m", "py_compile", "run.py", "praxis_gui.py"]))
        commands.append(_run("pytest", [sys.executable, "-m", "pytest", "-q"]))

    dataset_status = backend.generate_dataset_from_config(
        config_path=REPO_ROOT / "configs/datasets/paper_synthetic_v1.yaml",
        out_dir=paths.dataset_dir,
    )
    experiment_status = backend.run_experiment_matrix_backend(
        contract_path=REPO_ROOT / "configs/experiment/paper_v1.yaml",
        dataset_out=paths.dataset_dir,
        results_out=paths.results_dir,
        max_cases_per_condition=max_cases_per_condition,
    )
    table_paths = backend.regenerate_chapter4_tables_backend(results_dir=paths.results_dir)
    fixture_run = backend.run_fixture_backend(
        fixture_dir=paths.fixture_dir,
        runs_dir=paths.runs_dir,
        run_id="run:review_ready",
        create_fixture=True,
    )
    run_root = Path(fixture_run["run_root"])
    audit_valid = ImmutableAuditStore(run_root, run_id="run:review_ready").verify()
    artifact_bundle_valid = RunArtifactStore(run_root).verify_bundle()
    human_audit = backend.human_audit_demo_backend(
        results_dir=paths.results_dir,
        out_path=paths.human_audit_dir / "demo_summary.json",
        per_system=120,
    )

    tracked_review_docs = (
        "docs/artifact_scope.md",
        "docs/data_metric_dictionary.md",
        "docs/human_audit_status.md",
        "docs/ai_tool_use_disclosure.md",
        "docs/reproducibility.md",
        "docs/artifact_manifest.md",
    )
    tracked_configs = tuple(str(p.relative_to(REPO_ROOT)) for p in sorted((REPO_ROOT / "configs").rglob("*.yaml")))

    manifest = {
        "manifest_id": "agentic_cfo_review_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "claim": "implemented scaffold and local reproducibility harness",
            "not_claimed": [
                "final provider-backed LLM outputs",
                "actual CPA reviewer ratings",
                "paper-scale final empirical dataset",
                "external FActScore/RAGAS service integrations",
                "IRB/OHR/advisor determination artifacts",
            ],
        },
        "environment": {
            "python": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "packages": _package_versions(),
        },
        "commands": [command.to_dict() for command in commands],
        "paths": paths.to_dict(),
        "dataset": dataset_status,
        "experiment": experiment_status,
        "tables": table_paths,
        "fixture_run": {
            **fixture_run,
            "audit_valid": audit_valid,
            "artifact_bundle_valid": artifact_bundle_valid,
            "audit_lifecycle": lifecycle_summary(run_root),
        },
        "human_audit_demo": human_audit,
        "hashes": {
            "review_docs": {path: _hash_file(REPO_ROOT / path) for path in tracked_review_docs},
            "configs": {path: _hash_file(REPO_ROOT / path) for path in tracked_configs},
            "review_output": _hash_tree(out_dir),
        },
    }
    manifest_path = out_dir / "review_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="review-output")
    parser.add_argument("--max-cases-per-condition", type=int, default=1)
    parser.add_argument("--skip-checks", action="store_true")
    args = parser.parse_args()

    manifest = build_review_package(
        max_cases_per_condition=args.max_cases_per_condition,
        out_dir=REPO_ROOT / args.out_dir,
        run_checks=not args.skip_checks,
    )
    print(json.dumps({
        "manifest": str((REPO_ROOT / args.out_dir / "review_manifest.json")),
        "dataset_cases": manifest["dataset"]["case_count"],
        "result_rows": manifest["experiment"]["rows"],
        "audit_valid": manifest["fixture_run"]["audit_valid"],
        "artifact_bundle_valid": manifest["fixture_run"]["artifact_bundle_valid"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
