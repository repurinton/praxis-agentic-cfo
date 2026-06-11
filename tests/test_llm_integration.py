from __future__ import annotations

import json

import pytest

from agentic_cfo.core.models import SystemCondition
from agentic_cfo.data.schema import FinancialRecord, ReportingCase
from agentic_cfo.llm import LLMClient, llm_is_live
from agentic_cfo.llm.client import DETERMINISTIC, LIVE, LLMResponse
from agentic_cfo.llm.report_generation import generate_report_via_llm


def _case() -> ReportingCase:
    return ReportingCase(
        case_id="t:case:0001",
        dataset_id="t",
        partition="baseline_validation",
        condition="clean",
        period="FY2026-Q1",
        entity_id="ENT001",
        records=(
            FinancialRecord("Revenue", 1000.0, "FY2026-Q1", "ENT001"),
            FinancialRecord("Expense", 620.0, "FY2026-Q1", "ENT001"),
        ),
        policy_text="Trace before release.",
        source_document_text="Revenue 1000 expense 620.",
    )


class _FakeClient:
    """Stand-in returning a canned JSON payload, no network."""

    def __init__(self, payload: dict, *, model: str = "fake-model"):
        self._payload = payload
        self.model = model

    def complete(self, *, system_prompt, user_prompt, response_json=False) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(self._payload),
            latency_seconds=0.123,
            model=self.model,
            mode=LIVE,
            usage={"total_tokens": 42},
        )


def test_default_mode_is_deterministic_and_makes_no_network_call(monkeypatch):
    monkeypatch.delenv("AGENTIC_CFO_LLM_MODE", raising=False)
    assert llm_is_live() is False
    client = LLMClient(env_file="/nonexistent.env")
    resp = client.complete(system_prompt="s", user_prompt="u")
    assert resp.mode == DETERMINISTIC
    assert resp.text == ""


def test_live_mode_without_api_key_raises_clear_error(monkeypatch):
    monkeypatch.setenv("AGENTIC_CFO_LLM_MODE", "live")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert llm_is_live() is True
    client = LLMClient(env_file="/nonexistent.env")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        client.complete(system_prompt="s", user_prompt="u")


def test_generate_report_binds_evidence_and_penalizes_wrong_numbers():
    # Model reports Revenue correctly but Expense wrong; one derived claim.
    payload = {
        "narrative": "Revenue exceeds expense.",
        "claims": [
            {"account": "Revenue", "type": "numeric", "text": "Revenue is 1000.", "value": 1000.0, "unit": "USD"},
            {"account": "Expense", "type": "numeric", "text": "Expense is 999.", "value": 999.0, "unit": "USD"},
            {"account": None, "type": "derived", "text": "Operating margin positive.", "value": None},
        ],
    }
    artifact = generate_report_via_llm(
        _case(),
        run_id="run:t",
        system=SystemCondition.AGENTIC_CFO,
        generated_by="AgenticCFOControllerAgent",
        bind_evidence=True,
        client=_FakeClient(payload),
    )

    assert artifact.generated_by == "AgenticCFOControllerAgent"
    assert len(artifact.claims) == 3
    # Bound to corpus evidence when requested.
    assert all(c.evidence for c in artifact.claims)

    from agentic_cfo.agents import AgenticCFOVerifierAgent
    from agentic_cfo.evidence.corpus import corpus_from_case

    verification = AgenticCFOVerifierAgent().verify(
        artifact, thresholds={}, corpus=corpus_from_case(_case())
    )
    # Revenue right, Expense wrong -> numeric agreement 0.5.
    assert verification.metrics["numeric_agreement"] == 0.5


def test_generate_report_without_binding_leaves_claims_ungrounded():
    payload = {
        "narrative": "n",
        "claims": [
            {"account": "Revenue", "type": "numeric", "text": "Revenue is 1000.", "value": 1000.0, "unit": "USD"},
        ],
    }
    artifact = generate_report_via_llm(
        _case(),
        run_id="run:t",
        system=SystemCondition.BASELINE_B,
        generated_by="baseline_b_llm_assisted",
        bind_evidence=False,
        client=_FakeClient(payload),
    )
    assert all(not c.evidence for c in artifact.claims)
