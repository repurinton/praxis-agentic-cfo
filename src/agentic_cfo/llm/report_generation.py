"""Build a ReportArtifact from a live LLM call.

Used by the experiment systems when ``AGENTIC_CFO_LLM_MODE=live``. The model is
asked to return a strict JSON object describing the report narrative and a list
of atomic claims. Claims are then optionally bound to the authoritative evidence
corpus (``bind_evidence``); numeric agreement against that evidence is judged
downstream by the VerificationEngine, so a model that misreports a figure is
penalized exactly as a real ungrounded claim would be.
"""

from __future__ import annotations

import json
import re
from uuid import uuid4

from agentic_cfo.core.models import (
    AtomicClaim,
    ClaimType,
    EvidencePointer,
    ReportArtifact,
    SystemCondition,
)
from agentic_cfo.data.schema import ReportingCase
from agentic_cfo.evidence.corpus import EvidenceCorpus, corpus_from_case
from agentic_cfo.llm.client import LLMClient

_SYSTEM_PROMPT = (
    "You are a financial reporting assistant. You will be given a trial balance "
    "for a single reporting entity. Produce a concise management report.\n\n"
    "Respond with a STRICT JSON object only, matching this schema:\n"
    "{\n"
    '  "narrative": "<2-4 sentence report>",\n'
    '  "claims": [\n'
    '    {"account": "<account name or null>", "type": "numeric|derived", '
    '"text": "<claim sentence>", "value": <number or null>, "unit": "USD"}\n'
    "  ]\n"
    "}\n"
    "Rules: report each material account balance as a numeric claim using the "
    "exact figure from the trial balance; include one derived claim about "
    "profitability. Do not invent accounts. Output JSON only, no prose."
)

_CLAIM_TYPES = {
    "numeric": ClaimType.NUMERIC,
    "derived": ClaimType.DERIVED,
    "narrative": ClaimType.NARRATIVE,
    "policy": ClaimType.POLICY,
}


def _render_trial_balance(case: ReportingCase) -> str:
    lines = [f"Entity: {case.entity_id}", f"Period: {case.period}", "Trial balance:"]
    for record in case.records:
        lines.append(f"  - {record.account}: {record.balance:.2f} USD")
    if case.policy_text:
        lines.append(f"Policy: {case.policy_text}")
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    """Tolerant JSON extraction: strips code fences, finds the first object."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _evidence_for(
    account: str | None,
    corpus: EvidenceCorpus,
    *,
    derived_fallback: tuple[str, ...] = ("Revenue", "Expense"),
) -> tuple[EvidencePointer, ...]:
    if account:
        span = corpus.find_by_account(account)
        if span:
            return (corpus.pointer(span.span_id),)
        return ()
    pointers = []
    for name in derived_fallback:
        span = corpus.find_by_account(name)
        if span:
            pointers.append(corpus.pointer(span.span_id))
    return tuple(pointers)


def generate_report_via_llm(
    case: ReportingCase,
    *,
    run_id: str,
    system: SystemCondition,
    generated_by: str,
    bind_evidence: bool,
    client: LLMClient | None = None,
) -> ReportArtifact:
    client = client or LLMClient()
    corpus = corpus_from_case(case)
    response = client.complete(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=_render_trial_balance(case),
        response_json=True,
    )
    payload = _extract_json(response.text)
    raw_claims = payload.get("claims", []) or []

    claims: list[AtomicClaim] = []
    for idx, raw in enumerate(raw_claims, start=1):
        account = raw.get("account")
        if isinstance(account, str) and account.strip().lower() in {"null", "none", ""}:
            account = None
        claim_type = _CLAIM_TYPES.get(str(raw.get("type", "narrative")).lower(), ClaimType.NARRATIVE)
        value = raw.get("value")
        value = float(value) if isinstance(value, (int, float)) else None
        evidence = _evidence_for(account, corpus) if bind_evidence else ()
        claims.append(
            AtomicClaim(
                claim_id=f"claim:{idx}:{(account or 'narrative').lower().replace(' ', '_')}",
                claim_type=claim_type,
                text=str(raw.get("text", "")).strip(),
                value=value,
                unit=str(raw.get("unit", "USD")) if value is not None else None,
                account=account,
                period=case.period,
                evidence=evidence,
                source_location=f"{generated_by}:llm:{idx}",
                metadata={"llm_model": response.model, "llm_mode": response.mode},
            )
        )

    narrative = str(payload.get("narrative", "")).strip() or " ".join(c.text for c in claims)
    return ReportArtifact(
        artifact_id=f"artifact:{uuid4()}",
        system=system,
        run_id=run_id,
        dataset_id=case.dataset_id,
        partition=case.partition,
        title=f"{system.value} report for {case.entity_id}",
        narrative=narrative,
        claims=tuple(claims),
        generated_by=generated_by,
        metadata={
            "case_id": case.case_id,
            "condition": case.condition,
            "llm_model": response.model,
            "llm_mode": response.mode,
            "llm_latency_seconds": response.latency_seconds,
            "llm_usage": response.usage,
        },
    )
