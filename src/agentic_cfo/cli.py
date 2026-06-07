from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import uuid4

from agentic_cfo.agents import AgenticCFOControllerAgent, AgenticCFOPlannerAgent, AgenticCFOVerifierAgent
from agentic_cfo.audit.artifacts import RunArtifactStore
from agentic_cfo.audit.query import lifecycle_summary
from agentic_cfo.audit.store import ImmutableAuditStore
from agentic_cfo.core.models import RunManifest, SystemCondition, stable_hash
from agentic_cfo.data.fixtures import write_minimal_fixture
from agentic_cfo.evidence.corpus import load_trial_balance_corpus
from agentic_cfo.provenance import load_locked_run_config, render_prompt_record
from agentic_cfo.release.gate import ReleaseGate
from agentic_cfo.release.workflow import HumanGovernanceWorkflow


DEFAULT_THRESHOLDS = {
    "numeric_agreement_min": 0.995,
    "factscore_min": 0.800,
    "ragas_faithfulness_min": 0.800,
    "unsupported_claim_rate_max": 0.010,
    "audit_evidence_package_completeness_min": 0.950,
    "claim_traceability_rate_min": 0.950,
}
DEFAULT_LOCKED_CONFIG = Path("configs/run/evaluation_locked.yaml")


def run_fixture(args: argparse.Namespace) -> int:
    root = Path(args.fixture)
    if args.create_fixture:
        write_minimal_fixture(root)

    run_id = args.run_id or f"run:{uuid4()}"
    run_root = Path(args.runs_dir) / run_id.replace(":", "_")
    run_root.mkdir(parents=True, exist_ok=True)

    corpus = load_trial_balance_corpus(root / "trial_balance.csv", dataset_id="minimal_fixture_v1")
    audit = ImmutableAuditStore(run_root, run_id=run_id)

    planner = AgenticCFOPlannerAgent()
    controller = AgenticCFOControllerAgent()
    verifier = AgenticCFOVerifierAgent()
    release_gate = ReleaseGate()
    governance = HumanGovernanceWorkflow()
    locked_config = load_locked_run_config(DEFAULT_LOCKED_CONFIG)

    source_hashes = {
        "trial_balance.csv": stable_hash((root / "trial_balance.csv").read_text(encoding="utf-8")),
        str(DEFAULT_LOCKED_CONFIG): stable_hash(DEFAULT_LOCKED_CONFIG.read_text(encoding="utf-8")),
    }
    manifest = RunManifest(
        run_id=run_id,
        dataset_id="minimal_fixture_v1",
        partition="baseline_validation",
        system=SystemCondition.AGENTIC_CFO,
        config_hash=locked_config.config_hash,
        model_config=locked_config.to_dict(),
        threshold_config=DEFAULT_THRESHOLDS,
        source_hashes=source_hashes,
    )

    audit.append("run_started", actor="cli", payload=manifest.to_dict())
    audit.append("manifest_locked", actor="cli", payload={"config_hash": manifest.config_hash, "source_hashes": source_hashes})
    audit.append("source_loaded", actor="cli", payload={"sources": sorted(source_hashes)})
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
    audit.append(
        "threshold_evaluated",
        actor=verifier.name,
        artifact_id=artifact.artifact_id,
        payload=verification.to_dict(),
    )

    release = release_gate.decide(verification)
    for exception in release.exceptions:
        audit.append("exception_opened", actor="ReleaseGate", artifact_id=artifact.artifact_id, payload=exception.to_dict())
    audit.append("release_decided", actor="ReleaseGate", artifact_id=artifact.artifact_id, payload=release.to_dict())
    governance_record = governance.review(release)
    for disposition in governance_record.dispositions:
        if disposition.status == "dispositioned":
            audit.append("exception_dispositioned", actor="HumanGovernanceWorkflow", artifact_id=artifact.artifact_id, payload=disposition.to_dict())
    if governance_record.attestation is not None:
        audit.append("attestation_signed", actor=governance_record.attestation.actor_id, artifact_id=artifact.artifact_id, payload=governance_record.attestation.to_dict())

    bundle = RunArtifactStore(run_root).write_bundle(
        manifest=manifest,
        report=artifact,
        verification=verification,
        release=release,
        evidence_spans=corpus.spans,
        prompt_records=(planner_prompt, controller_prompt, verifier_prompt),
    )
    audit.append("artifact_bundle_written", actor="RunArtifactStore", artifact_id=artifact.artifact_id, payload=bundle.to_dict())
    audit.append(
        "run_completed",
        actor="cli",
        artifact_id=artifact.artifact_id,
        payload={"audit_valid": audit.verify(), "artifact_bundle_valid": RunArtifactStore(run_root).verify_bundle()},
    )

    print(json.dumps({
        "run_id": run_id,
        "run_root": str(run_root),
        "agents": [planner.name, controller.name, verifier.name],
        "generation_owner": controller.name,
        "verification_status": verification.status.value,
        "release_action": release.action.value,
        "governance_action": governance_record.final_action.value,
        "prompt_records": 3,
        "metrics": verification.metrics,
        "audit_valid": audit.verify(),
        "artifact_bundle_valid": RunArtifactStore(run_root).verify_bundle(),
        "audit_lifecycle": lifecycle_summary(run_root),
    }, indent=2))
    return 0 if release.action.value == "release" and audit.verify() and RunArtifactStore(run_root).verify_bundle() else 1


def verify_audit(args: argparse.Namespace) -> int:
    run_root = Path(args.run_root)
    run_id = args.run_id or run_root.name
    audit = ImmutableAuditStore(run_root, run_id=run_id)
    ok = audit.verify()
    bundle_ok = RunArtifactStore(run_root).verify_bundle()
    print(json.dumps({"run_root": str(run_root), "audit_valid": ok, "artifact_bundle_valid": bundle_ok}, indent=2))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="agentic-cfo")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run-fixture")
    run.add_argument("--fixture", default="data/fixtures/minimal")
    run.add_argument("--runs-dir", default="runs")
    run.add_argument("--run-id", default=None)
    run.add_argument("--create-fixture", action="store_true")
    run.set_defaults(func=run_fixture)

    audit = sub.add_parser("verify-audit")
    audit.add_argument("run_root")
    audit.add_argument("--run-id", default=None)
    audit.set_defaults(func=verify_audit)

    audit_group = sub.add_parser("audit")
    audit_sub = audit_group.add_subparsers(dest="audit_cmd", required=True)
    audit_verify = audit_sub.add_parser("verify")
    audit_verify.add_argument("run_root")
    audit_verify.add_argument("--run-id", default=None)
    audit_verify.set_defaults(func=verify_audit)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
