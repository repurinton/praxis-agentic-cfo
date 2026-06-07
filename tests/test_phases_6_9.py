from __future__ import annotations

import json
from pathlib import Path

from agentic_cfo.agents import AgenticCFOControllerAgent, AgenticCFOPlannerAgent, AgenticCFOVerifierAgent
from agentic_cfo.audit.artifacts import RunArtifactStore
from agentic_cfo.audit.store import ImmutableAuditStore
from agentic_cfo.cli import DEFAULT_THRESHOLDS
from agentic_cfo.core.models import RunManifest, SystemCondition, stable_hash
from agentic_cfo.data.fixtures import write_minimal_fixture
from agentic_cfo.evidence.corpus import load_trial_balance_corpus
from agentic_cfo.eval.aggregate import perturbation_deltas, summarize_by_system_condition
from agentic_cfo.human_audit import (
    AuditRating,
    ReviewerRating,
    adjudicate_ratings,
    blinded_sample,
    cohen_weighted_kappa,
    raw_agreement,
)
from agentic_cfo.provenance import load_locked_run_config, render_prompt_record
from agentic_cfo.release.gate import ReleaseGate
from agentic_cfo.release.workflow import HumanGovernanceWorkflow


ROOT = Path(__file__).resolve().parents[1]


def _release_ready_bundle(tmp_path):
    fixture = write_minimal_fixture(tmp_path / "fixture")
    corpus = load_trial_balance_corpus(fixture / "trial_balance.csv", dataset_id="minimal_fixture_v1")
    run_id = "run:test"
    planner = AgenticCFOPlannerAgent()
    controller = AgenticCFOControllerAgent()
    verifier = AgenticCFOVerifierAgent()
    plan = planner.create_plan(dataset_id="minimal_fixture_v1", partition="baseline_validation")
    artifact = controller.generate_report(
        plan=plan,
        run_id=run_id,
        dataset_id="minimal_fixture_v1",
        partition="baseline_validation",
        corpus=corpus,
    )
    verification = verifier.verify(artifact, thresholds=DEFAULT_THRESHOLDS, corpus=corpus)
    release = ReleaseGate().decide(verification)
    manifest = RunManifest(
        run_id=run_id,
        dataset_id="minimal_fixture_v1",
        partition="baseline_validation",
        system=SystemCondition.AGENTIC_CFO,
        config_hash="hash:test",
        model_config={"model": "deterministic-local"},
        threshold_config=DEFAULT_THRESHOLDS,
        source_hashes={"trial_balance.csv": stable_hash((fixture / "trial_balance.csv").read_text(encoding="utf-8"))},
    )
    return corpus, manifest, artifact, verification, release


def test_phase6_locked_config_and_prompt_capture():
    locked = load_locked_run_config(ROOT / "configs/run/evaluation_locked.yaml")
    record = render_prompt_record(
        run_id="run:test",
        agent_name="AgenticCFOPlannerAgent",
        template_name="planner.md",
        variables={"dataset_id": "dataset:v1", "partition": "holdout_audit"},
        model_config=locked.models["planner"],
        tools=("load_sources",),
    )

    assert locked.generation_owner == "AgenticCFOControllerAgent"
    assert locked.config_hash
    assert "dataset:v1" in record.rendered_prompt
    assert record.template_hash != record.rendered_prompt_hash


def test_phase7_artifact_bundle_and_hash_chain(tmp_path):
    corpus, manifest, artifact, verification, release = _release_ready_bundle(tmp_path)
    run_root = tmp_path / "run"
    audit = ImmutableAuditStore(run_root, run_id=manifest.run_id)
    audit.append("run_started", actor="test", payload=manifest.to_dict())
    audit.append("run_completed", actor="test", artifact_id=artifact.artifact_id, payload={"ok": True})

    store = RunArtifactStore(run_root)
    store.write_bundle(
        manifest=manifest,
        report=artifact,
        verification=verification,
        release=release,
        evidence_spans=corpus.spans,
        prompt_records=(),
    )

    assert audit.verify() is True
    assert store.verify_bundle() is True
    assert (run_root / "claims.jsonl").exists()
    assert (run_root / "evidence_spans.jsonl").exists()
    assert (run_root / "checksums.json").exists()


def test_phase8_governance_workflow_signs_release_attestation(tmp_path):
    _corpus, _manifest, _artifact, _verification, release = _release_ready_bundle(tmp_path)

    review = HumanGovernanceWorkflow().review(release)

    assert review.final_action.value == "release"
    assert review.approved_by == "system-approver"
    assert review.attestation is not None
    assert review.attestation.signature_hash


def test_phase9_human_audit_agreement_and_sampling():
    rows = (
        {"artifact_id": "a1", "system": "agentic_cfo", "condition": "clean", "release_action": "release"},
        {"artifact_id": "a2", "system": "agentic_cfo", "condition": "clean", "release_action": "block"},
        {"artifact_id": "b1", "system": "baseline_a_deterministic", "condition": "clean", "release_action": "release"},
    )
    samples = blinded_sample(rows, per_system=2, seed=7)
    ratings = (
        ReviewerRating(samples[0].blinded_id, "r1", AuditRating.RELEASE_READY),
        ReviewerRating(samples[0].blinded_id, "r2", AuditRating.RELEASE_READY),
        ReviewerRating(samples[1].blinded_id, "r1", AuditRating.MINOR_ISSUES),
        ReviewerRating(samples[1].blinded_id, "r2", AuditRating.MATERIAL_ISSUES),
    )

    assert len(samples) == 2
    assert raw_agreement(ratings) == 0.5
    assert -1.0 <= cohen_weighted_kappa(ratings) <= 1.0
    assert len(adjudicate_ratings(ratings)) == 2


def test_phase9_chapter4_aggregation():
    rows = (
        {
            "system": "agentic_cfo",
            "condition": "clean",
            "artifact_id": "a1",
            "numeric_agreement": 1.0,
            "factscore": 1.0,
            "ragas_faithfulness": 1.0,
            "unsupported_claim_rate": 0.0,
            "audit_evidence_package_completeness": 1.0,
            "claim_traceability_rate": 1.0,
            "release_action": "release",
            "cycle_time_seconds": 1.0,
        },
        {
            "system": "agentic_cfo",
            "condition": "compound_perturbation",
            "artifact_id": "a2",
            "numeric_agreement": 0.5,
            "factscore": 0.8,
            "ragas_faithfulness": 0.8,
            "unsupported_claim_rate": 0.2,
            "audit_evidence_package_completeness": 0.8,
            "claim_traceability_rate": 0.8,
            "release_action": "block",
            "cycle_time_seconds": 3.0,
        },
    )

    summary = summarize_by_system_condition(rows)
    deltas = perturbation_deltas(summary)

    assert len(summary) == 2
    assert next(r for r in summary if r["condition"] == "clean")["release_gate_pass_rate"] == 1.0
    assert deltas[0]["numeric_disagreement_increase_bps"] == 5000.0
