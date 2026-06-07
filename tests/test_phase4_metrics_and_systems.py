from __future__ import annotations

from pathlib import Path

from agentic_cfo.agents import AgenticCFOVerifierAgent
from agentic_cfo.data.generator import generate_cases_from_config
from agentic_cfo.evidence.corpus import corpus_from_case
from agentic_cfo.eval.metrics import factscore, numeric_agreement, ragas_faithfulness
from agentic_cfo.experiment.contract import load_yaml_mapping
from agentic_cfo.systems.registry import system_runner


ROOT = Path(__file__).resolve().parents[1]


def _case_and_thresholds():
    case = generate_cases_from_config(ROOT / "configs/datasets/paper_synthetic_v1.yaml")[0]
    thresholds = load_yaml_mapping(ROOT / "configs/eval/paper_thresholds.yaml")
    return case, thresholds


def test_phase4_metric_adapters_are_claim_level_and_evidence_grounded():
    case, _thresholds = _case_and_thresholds()
    corpus = corpus_from_case(case)
    artifact = system_runner("baseline_a_deterministic").run(case, run_id="run:test")

    assert numeric_agreement(artifact, corpus=corpus) == 1.0
    assert factscore(artifact, corpus=corpus) == 2 / 3
    assert ragas_faithfulness(artifact) == 2 / 3


def test_system_runners_expose_pdf_baselines_and_agentic_cfo():
    case, thresholds = _case_and_thresholds()
    corpus = corpus_from_case(case)
    verifier = AgenticCFOVerifierAgent()

    baseline_b = system_runner("baseline_b_llm_assisted").run(case, run_id="run:b")
    agentic = system_runner("agentic_cfo").run(case, run_id="run:a")

    baseline_b_verification = verifier.verify(baseline_b, thresholds=thresholds, corpus=corpus)
    agentic_verification = verifier.verify(agentic, thresholds=thresholds, corpus=corpus)

    assert baseline_b.generated_by == "baseline_b_llm_assisted"
    assert baseline_b_verification.metrics["numeric_agreement"] == 0.0
    assert baseline_b_verification.metrics["unsupported_claim_rate"] == 1.0
    assert agentic.generated_by == "AgenticCFOControllerAgent"
    assert agentic_verification.metrics["numeric_agreement"] == 1.0
    assert agentic_verification.metrics["factscore"] == 1.0
    assert agentic_verification.metrics["ragas_faithfulness"] == 1.0
