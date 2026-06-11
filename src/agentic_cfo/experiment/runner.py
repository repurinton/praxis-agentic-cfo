from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from agentic_cfo.agents import AgenticCFOVerifierAgent
from agentic_cfo.data.generator import load_cases
from agentic_cfo.data.schema import ReportingCase
from agentic_cfo.evidence.corpus import corpus_from_case
from agentic_cfo.eval.chapter4_metrics import result_row
from agentic_cfo.experiment.contract import ExperimentContract, load_yaml_mapping
from agentic_cfo.perturbations import (
    apply_compound_perturbation,
    apply_conflicting_records,
    apply_missing_evidence,
    apply_temporal_misalignment,
)
from agentic_cfo.release.gate import ReleaseGate
from agentic_cfo.systems.registry import system_runner

GATED_SYSTEM = "agentic_cfo"


@dataclass(frozen=True)
class ExperimentResult:
    rows: tuple[dict, ...]
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"meta": dict(self.meta), "rows": list(self.rows)}


def cases_for_condition(cases: tuple[ReportingCase, ...], condition: str) -> tuple[ReportingCase, ...]:
    if condition == "clean":
        return cases
    if condition == "single_perturbation":
        out = []
        for case in cases:
            out.extend([
                apply_missing_evidence(case),
                apply_conflicting_records(case),
                apply_temporal_misalignment(case),
            ])
        return tuple(out)
    if condition == "compound_perturbation":
        return tuple(apply_compound_perturbation(case) for case in cases)
    raise KeyError(condition)


def run_experiment(
    *,
    contract: ExperimentContract,
    dataset_path: Path,
    threshold_path: Path,
    out_dir: Path,
    max_cases_per_condition: int | None = None,
) -> ExperimentResult:
    thresholds = load_yaml_mapping(threshold_path)
    base_cases = load_cases(dataset_path / "cases.jsonl")
    verifier = AgenticCFOVerifierAgent()
    release_gate = ReleaseGate()
    rows: list[dict] = []

    # Replication protocol (paper Chapter 4): each (condition, case, system) cell
    # is executed `contract.replications` times so that run-to-run variation can be
    # characterized. Deterministic systems yield identical trials (zero variance);
    # live-model systems exhibit genuine nondeterminism across trials.
    replications = max(1, int(contract.replications))

    for condition in contract.conditions:
        condition_cases = cases_for_condition(base_cases, condition)
        if max_cases_per_condition is not None:
            condition_cases = condition_cases[:max_cases_per_condition]
        for case in condition_cases:
            corpus = corpus_from_case(case)
            for system_name in contract.systems:
                runner = system_runner(system_name)
                for trial in range(replications):
                    run_id = f"run:{uuid4()}"
                    started = time.perf_counter()
                    artifact = runner.run(case, run_id=run_id)
                    verification = verifier.verify(artifact, thresholds=thresholds, corpus=corpus)
                    if system_name == GATED_SYSTEM:
                        release_action = release_gate.decide(verification).action.value
                        release_gate_applied = True
                        human_audit_eligible = release_action in {"release", "route_to_review"}
                    else:
                        release_action = "not_applicable_no_release_gate"
                        release_gate_applied = False
                        human_audit_eligible = True
                    elapsed = time.perf_counter() - started
                    row = result_row(
                        artifact,
                        verification,
                        release_action=release_action,
                        release_gate_applied=release_gate_applied,
                        human_audit_eligible=human_audit_eligible,
                        cycle_time_seconds=elapsed,
                    )
                    row.update({
                        "experiment_id": contract.experiment_id,
                        "condition": condition,
                        "case_id": case.case_id,
                        "trial": trial,
                        "verification_status": verification.status.value,
                    })
                    rows.append(row)

    from agentic_cfo.llm import llm_mode, llm_model

    mode = llm_mode()
    meta = {
        "experiment_id": contract.experiment_id,
        "systems": list(contract.systems),
        "conditions": list(contract.conditions),
        "replications": replications,
        "llm_mode": mode,
        # Model name is only meaningful when generation is live.
        "llm_model": llm_model() if mode == "live" else "deterministic-local",
        "row_count": len(rows),
    }
    result = ExperimentResult(rows=tuple(rows), meta=meta)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return result
