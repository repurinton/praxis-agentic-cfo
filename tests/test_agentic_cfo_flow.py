from __future__ import annotations

from uuid import uuid4

from agentic_cfo.agents import AgenticCFOControllerAgent, AgenticCFOPlannerAgent, AgenticCFOVerifierAgent
from agentic_cfo.audit.store import ImmutableAuditStore
from agentic_cfo.cli import DEFAULT_THRESHOLDS
from agentic_cfo.data.fixtures import write_minimal_fixture
from agentic_cfo.evidence.corpus import load_trial_balance_corpus
from agentic_cfo.release.gate import ReleaseGate


def test_controller_owned_generation_verifies_and_releases(tmp_path):
    fixture = write_minimal_fixture(tmp_path / "fixture")
    corpus = load_trial_balance_corpus(fixture / "trial_balance.csv", dataset_id="minimal_fixture_v1")

    run_id = f"run:{uuid4()}"
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

    assert planner.name == "AgenticCFOPlannerAgent"
    assert controller.name == "AgenticCFOControllerAgent"
    assert verifier.name == "AgenticCFOVerifierAgent"
    assert artifact.generated_by == "AgenticCFOControllerAgent"
    assert all(claim.evidence for claim in artifact.claims)
    assert verification.metrics["numeric_agreement"] == 1.0
    assert verification.metrics["unsupported_claim_rate"] == 0.0
    assert all(verification.threshold_results.values())
    assert release.action.value == "release"


def test_immutable_audit_store_hash_chain(tmp_path):
    store = ImmutableAuditStore(tmp_path / "audit", run_id="run:test")
    first = store.append("run_started", actor="test", payload={"ok": True})
    second = store.append("run_completed", actor="test", payload={"first": first.event_id})

    assert second.previous_event_hash == first.event_hash
    assert store.verify() is True
