from __future__ import annotations

import csv
import io
import json
import shutil
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentic_cfo.agents import AgenticCFOControllerAgent, AgenticCFOPlannerAgent, AgenticCFOVerifierAgent
from agentic_cfo.audit.artifacts import RunArtifactStore
from agentic_cfo.audit.query import lifecycle_summary, read_events
from agentic_cfo.audit.store import ImmutableAuditStore
from agentic_cfo.cli import DEFAULT_THRESHOLDS
from agentic_cfo.core.models import RunManifest, SystemCondition, stable_hash
from agentic_cfo.data.fixtures import write_minimal_fixture
from agentic_cfo.data.generator import generate_cases_from_config, load_cases, write_dataset
from agentic_cfo.eval.aggregate import perturbation_deltas, summarize_by_system_condition
from agentic_cfo.eval.chapter4_tables import write_chapter4_tables
from agentic_cfo.experiment.contract import ExperimentContract, load_experiment_contract, load_yaml_mapping
from agentic_cfo.experiment.runner import run_experiment
from agentic_cfo.evidence.corpus import load_trial_balance_corpus
from agentic_cfo.human_audit import (
    AuditRating,
    ReviewerRating,
    adjudicate_ratings,
    blinded_sample,
    cohen_weighted_kappa,
    outcome_distribution,
    raw_agreement,
)
from agentic_cfo.provenance import load_locked_run_config, render_prompt_record
from agentic_cfo.release.gate import ReleaseGate
from agentic_cfo.release.workflow import HumanGovernanceWorkflow


REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class PlatformPaths:
    repo_root: Path = REPO_ROOT
    dataset_dir: Path = REPO_ROOT / "data" / "generated" / "paper_synthetic_v1"
    results_dir: Path = REPO_ROOT / "results" / "paper_v1"
    runs_dir: Path = REPO_ROOT / "runs"
    fixture_dir: Path = REPO_ROOT / "data" / "fixtures" / "minimal"
    human_audit_dir: Path = REPO_ROOT / "human_audit"

    def ensure(self) -> None:
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.human_audit_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict[str, str]:
        return {key: str(value) for key, value in asdict(self).items()}


def default_paths() -> PlatformPaths:
    paths = PlatformPaths()
    paths.ensure()
    return paths


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> tuple[dict[str, str], ...]:
    if not path.exists() or path.stat().st_size == 0:
        return ()
    with path.open("r", newline="", encoding="utf-8") as f:
        return tuple(csv.DictReader(f))


def list_configs(repo_root: Path = REPO_ROOT) -> dict[str, tuple[Path, ...]]:
    return {
        "experiments": tuple(sorted((repo_root / "configs" / "experiment").glob("*.yaml"))),
        "datasets": tuple(sorted((repo_root / "configs" / "datasets").glob("*.yaml"))),
        "eval": tuple(sorted((repo_root / "configs" / "eval").glob("*.yaml"))),
        "run": tuple(sorted((repo_root / "configs" / "run").glob("*.yaml"))),
        "human_audit": tuple(sorted((repo_root / "configs" / "human_audit").glob("*.yaml"))),
    }


def dataset_status(dataset_dir: Path) -> dict[str, Any]:
    manifest = dataset_dir / "manifest.json"
    cases_path = dataset_dir / "cases.jsonl"
    trial_balance = dataset_dir / "trial_balance.csv"
    status = {
        "exists": manifest.exists() and cases_path.exists() and trial_balance.exists(),
        "dataset_dir": str(dataset_dir),
        "case_count": 0,
        "trial_balance_rows": 0,
        "manifest": {},
    }
    if cases_path.exists():
        status["case_count"] = sum(1 for line in cases_path.read_text(encoding="utf-8").splitlines() if line.strip())
    if trial_balance.exists():
        status["trial_balance_rows"] = max(0, len(trial_balance.read_text(encoding="utf-8").splitlines()) - 1)
    if manifest.exists():
        status["manifest"] = read_json(manifest)
    return status


def generate_dataset_from_config(*, config_path: Path, out_dir: Path) -> dict[str, Any]:
    cases = generate_cases_from_config(config_path)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    write_dataset(cases, out_dir)
    return dataset_status(out_dir)


def load_results(results_dir: Path) -> tuple[dict[str, Any], ...]:
    path = results_dir / "results.json"
    if not path.exists():
        return ()
    return tuple(read_json(path).get("rows", ()))


def result_status(results_dir: Path) -> dict[str, Any]:
    rows = load_results(results_dir)
    summary_path = results_dir / "table_system_condition_summary.csv"
    deltas_path = results_dir / "table_perturbation_deltas.csv"
    return {
        "exists": bool(rows),
        "results_dir": str(results_dir),
        "row_count": len(rows),
        "systems": sorted({str(row.get("system")) for row in rows}),
        "conditions": sorted({str(row.get("condition")) for row in rows}),
        "summary_rows": read_csv_rows(summary_path),
        "delta_rows": read_csv_rows(deltas_path),
    }


def run_experiment_matrix_backend(
    *,
    contract_path: Path,
    dataset_out: Path,
    results_out: Path,
    max_cases_per_condition: int | None,
) -> dict[str, Any]:
    contract = load_experiment_contract(contract_path)
    if not (dataset_out / "cases.jsonl").exists():
        cases = generate_cases_from_config(REPO_ROOT / contract.dataset_config)
        write_dataset(cases, dataset_out)
    result = run_experiment(
        contract=contract,
        dataset_path=dataset_out,
        threshold_path=REPO_ROOT / contract.threshold_config,
        out_dir=results_out,
        max_cases_per_condition=max_cases_per_condition,
    )
    table_paths = write_chapter4_tables(results_json=results_out / "results.json", out_dir=results_out)
    return {
        "rows": len(result.rows),
        "results_dir": str(results_out),
        "table_paths": table_paths,
        "status": result_status(results_out),
    }


def regenerate_chapter4_tables_backend(*, results_dir: Path) -> dict[str, str]:
    return write_chapter4_tables(results_json=results_dir / "results.json", out_dir=results_dir)


def system_condition_summary(results_dir: Path) -> tuple[dict[str, Any], ...]:
    rows = load_results(results_dir)
    if not rows:
        return ()
    return summarize_by_system_condition(rows)


def perturbation_delta_summary(results_dir: Path) -> tuple[dict[str, Any], ...]:
    summary = system_condition_summary(results_dir)
    return perturbation_deltas(summary)


def _fixture_manifest(
    *,
    run_id: str,
    fixture_dir: Path,
    locked_config_path: Path,
    locked_config: Any,
) -> RunManifest:
    source_hashes = {
        "trial_balance.csv": stable_hash((fixture_dir / "trial_balance.csv").read_text(encoding="utf-8")),
        str(locked_config_path): stable_hash(locked_config_path.read_text(encoding="utf-8")),
    }
    return RunManifest(
        run_id=run_id,
        dataset_id="minimal_fixture_v1",
        partition="baseline_validation",
        system=SystemCondition.AGENTIC_CFO,
        config_hash=locked_config.config_hash,
        model_config=locked_config.to_dict(),
        threshold_config=DEFAULT_THRESHOLDS,
        source_hashes=source_hashes,
    )


def run_fixture_backend(*, fixture_dir: Path, runs_dir: Path, run_id: str | None = None, create_fixture: bool = True) -> dict[str, Any]:
    if create_fixture:
        write_minimal_fixture(fixture_dir)
    run_id = run_id or f"run:{uuid4()}"
    run_root = runs_dir / run_id.replace(":", "_")
    run_root.mkdir(parents=True, exist_ok=True)

    locked_config_path = REPO_ROOT / "configs" / "run" / "evaluation_locked.yaml"
    locked_config = load_locked_run_config(locked_config_path)
    corpus = load_trial_balance_corpus(fixture_dir / "trial_balance.csv", dataset_id="minimal_fixture_v1")
    audit = ImmutableAuditStore(run_root, run_id=run_id)
    planner = AgenticCFOPlannerAgent()
    controller = AgenticCFOControllerAgent()
    verifier = AgenticCFOVerifierAgent()
    manifest = _fixture_manifest(
        run_id=run_id,
        fixture_dir=fixture_dir,
        locked_config_path=locked_config_path,
        locked_config=locked_config,
    )

    audit.append("run_started", actor="ui", payload=manifest.to_dict())
    audit.append("manifest_locked", actor="ui", payload={"config_hash": manifest.config_hash})
    audit.append("source_loaded", actor="ui", payload={"sources": sorted(manifest.source_hashes)})
    for span in corpus.spans:
        audit.append("evidence_span_indexed", actor="EvidenceCorpus", payload=span.to_dict())

    planner_prompt = render_prompt_record(
        run_id=run_id,
        agent_name=planner.name,
        template_name="planner.md",
        variables={"dataset_id": manifest.dataset_id, "partition": manifest.partition},
        model_config=locked_config.models.get("planner", {}),
        tools=("load_sources", "policy_check"),
    )
    audit.append("prompt_rendered", actor=planner.name, payload=planner_prompt.to_dict())
    plan = planner.create_plan(dataset_id=manifest.dataset_id, partition=manifest.partition)
    audit.append("plan_created", actor=planner.name, payload=plan.to_dict())

    controller_prompt = render_prompt_record(
        run_id=run_id,
        agent_name=controller.name,
        template_name="controller.md",
        variables={"run_id": run_id, "plan_id": plan.plan_id},
        model_config=locked_config.models.get("controller", {}),
        tools=("evidence_binder", "report_artifact_writer"),
    )
    audit.append("prompt_rendered", actor=controller.name, payload=controller_prompt.to_dict())
    artifact = controller.generate_report(
        plan=plan,
        run_id=run_id,
        dataset_id=manifest.dataset_id,
        partition=manifest.partition,
        corpus=corpus,
    )
    audit.append("report_generated", actor=controller.name, artifact_id=artifact.artifact_id, payload=artifact.to_dict())
    for claim in artifact.claims:
        audit.append("claim_extracted", actor=controller.name, artifact_id=artifact.artifact_id, payload=claim.to_dict())
        audit.append(
            "evidence_bound",
            actor=controller.name,
            artifact_id=artifact.artifact_id,
            payload={"claim_id": claim.claim_id, "evidence_span_ids": [p.span_id for p in claim.evidence]},
        )

    verifier_prompt = render_prompt_record(
        run_id=run_id,
        agent_name=verifier.name,
        template_name="verifier.md",
        variables={"artifact_id": artifact.artifact_id, "run_id": run_id},
        model_config=locked_config.models.get("verifier", {}),
        tools=("numeric_reconciliation", "threshold_evaluator"),
    )
    audit.append("prompt_rendered", actor=verifier.name, payload=verifier_prompt.to_dict(), artifact_id=artifact.artifact_id)
    verification = verifier.verify(artifact, thresholds=DEFAULT_THRESHOLDS, corpus=corpus)
    audit.append("numeric_verified", actor=verifier.name, artifact_id=artifact.artifact_id, payload={"numeric_agreement": verification.metrics["numeric_agreement"]})
    audit.append("claim_verified", actor=verifier.name, artifact_id=artifact.artifact_id, payload={"unsupported_claim_ids": list(verification.unsupported_claim_ids)})
    audit.append("threshold_evaluated", actor=verifier.name, artifact_id=artifact.artifact_id, payload=verification.to_dict())

    release = ReleaseGate().decide(verification)
    for exception in release.exceptions:
        audit.append("exception_opened", actor="ReleaseGate", artifact_id=artifact.artifact_id, payload=exception.to_dict())
    audit.append("release_decided", actor="ReleaseGate", artifact_id=artifact.artifact_id, payload=release.to_dict())
    governance = HumanGovernanceWorkflow().review(release)
    for disposition in governance.dispositions:
        if disposition.status == "dispositioned":
            audit.append("exception_dispositioned", actor="HumanGovernanceWorkflow", artifact_id=artifact.artifact_id, payload=disposition.to_dict())
    if governance.attestation is not None:
        audit.append("attestation_signed", actor=governance.attestation.actor_id, artifact_id=artifact.artifact_id, payload=governance.attestation.to_dict())

    store = RunArtifactStore(run_root)
    bundle = store.write_bundle(
        manifest=manifest,
        report=artifact,
        verification=verification,
        release=release,
        evidence_spans=corpus.spans,
        prompt_records=(planner_prompt, controller_prompt, verifier_prompt),
    )
    audit.append("artifact_bundle_written", actor="RunArtifactStore", artifact_id=artifact.artifact_id, payload=bundle.to_dict())
    audit.append("run_completed", actor="ui", artifact_id=artifact.artifact_id, payload={"audit_valid": audit.verify(), "artifact_bundle_valid": store.verify_bundle()})

    return {
        "run_id": run_id,
        "run_root": str(run_root),
        "artifact_id": artifact.artifact_id,
        "verification_status": verification.status.value,
        "release_action": release.action.value,
        "governance_action": governance.final_action.value,
        "metrics": verification.metrics,
        "audit_valid": audit.verify(),
        "artifact_bundle_valid": store.verify_bundle(),
        "audit_lifecycle": lifecycle_summary(run_root),
    }


def list_run_roots(runs_dir: Path) -> tuple[Path, ...]:
    if not runs_dir.exists():
        return ()
    return tuple(sorted((p for p in runs_dir.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True))


def run_detail(run_root: Path) -> dict[str, Any]:
    detail: dict[str, Any] = {
        "run_root": str(run_root),
        "files": sorted(p.name for p in run_root.iterdir() if p.is_file()) if run_root.exists() else [],
        "audit_lifecycle": lifecycle_summary(run_root),
        "audit_events": read_events(run_root),
        "audit_valid": ImmutableAuditStore(run_root, run_id=run_root.name).verify(),
        "artifact_bundle_valid": RunArtifactStore(run_root).verify_bundle(),
    }
    for name in ("manifest", "report", "verification", "release", "checksums"):
        path = run_root / f"{name}.json"
        if path.exists():
            detail[name] = read_json(path)
    return detail


def zip_directory_bytes(path: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if path.is_file():
            zf.write(path, arcname=path.name)
        elif path.exists():
            for item in sorted(path.rglob("*")):
                if item.is_file():
                    zf.write(item, arcname=str(item.relative_to(path.parent)))
    return buffer.getvalue()


def human_audit_demo_backend(*, results_dir: Path, out_path: Path, per_system: int = 120) -> dict[str, Any]:
    rows = load_results(results_dir)
    samples = blinded_sample(rows, per_system=per_system)
    ratings: list[ReviewerRating] = []
    for idx, sample in enumerate(samples):
        score_a = AuditRating(min(3, max(0, 3 - int(idx % 4 == 0))))
        score_b = AuditRating(min(3, max(0, 3 - int((idx + 1) % 4 == 0))))
        ratings.append(ReviewerRating(sample.blinded_id, "reviewer:blind_a", score_a))
        ratings.append(ReviewerRating(sample.blinded_id, "reviewer:blind_b", score_b))
    adjudicated = adjudicate_ratings(tuple(ratings))
    payload = {
        "sample_count": len(samples),
        "rating_count": len(ratings),
        "raw_agreement": raw_agreement(tuple(ratings)),
        "weighted_cohens_kappa": cohen_weighted_kappa(tuple(ratings)),
        "adjudicated_distribution": outcome_distribution(adjudicated),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def project_health(paths: PlatformPaths) -> dict[str, Any]:
    dataset = dataset_status(paths.dataset_dir)
    results = result_status(paths.results_dir)
    runs = list_run_roots(paths.runs_dir)
    return {
        "dataset_ready": dataset["exists"],
        "result_rows": results["row_count"],
        "run_count": len(runs),
        "latest_run": str(runs[0]) if runs else "",
        "config_count": sum(len(v) for v in list_configs(paths.repo_root).values()),
    }
