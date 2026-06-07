from __future__ import annotations

from uuid import uuid4

from agentic_cfo.core.models import AtomicClaim, ClaimType, EvidencePointer, ReportArtifact, SystemCondition
from agentic_cfo.data.schema import ReportingCase
from agentic_cfo.evidence.corpus import EvidenceCorpus, corpus_from_case


def _record_value(case: ReportingCase, account: str) -> float:
    for record in case.records:
        if record.account == account:
            return float(record.balance)
    return 0.0


def _pointer(corpus: EvidenceCorpus, account: str) -> EvidencePointer | None:
    span = corpus.find_by_account(account)
    return corpus.pointer(span.span_id) if span else None


def make_report(
    case: ReportingCase,
    *,
    run_id: str,
    system: SystemCondition,
    generated_by: str,
    bind_numeric: bool,
    bind_narrative: bool,
    numeric_error: float = 0.0,
) -> ReportArtifact:
    corpus = corpus_from_case(case)
    revenue = _record_value(case, "Revenue") + numeric_error
    expense = _record_value(case, "Expense")
    rev_ptr = _pointer(corpus, "Revenue") if bind_numeric else None
    exp_ptr = _pointer(corpus, "Expense") if bind_numeric else None
    narrative_evidence = tuple(p for p in (rev_ptr, exp_ptr) if p is not None) if bind_narrative else ()

    claims = (
        AtomicClaim(
            claim_id="claim:revenue_balance",
            claim_type=ClaimType.NUMERIC,
            text=f"Revenue balance is {revenue:.2f} USD.",
            value=revenue,
            unit="USD",
            account="Revenue",
            period=case.period,
            evidence=(rev_ptr,) if rev_ptr else (),
            source_location=f"{generated_by}:narrative:1",
        ),
        AtomicClaim(
            claim_id="claim:expense_balance",
            claim_type=ClaimType.NUMERIC,
            text=f"Expense balance is {expense:.2f} USD.",
            value=expense,
            unit="USD",
            account="Expense",
            period=case.period,
            evidence=(exp_ptr,) if exp_ptr else (),
            source_location=f"{generated_by}:narrative:2",
        ),
        AtomicClaim(
            claim_id="claim:profitability",
            claim_type=ClaimType.DERIVED,
            text="Revenue exceeds expense, indicating positive operating margin.",
            account="Revenue",
            period=case.period,
            evidence=narrative_evidence,
            source_location=f"{generated_by}:narrative:3",
            metadata={"formula": "Revenue - Expense"},
        ),
    )
    narrative = " ".join(c.text for c in claims)
    return ReportArtifact(
        artifact_id=f"artifact:{uuid4()}",
        system=system,
        run_id=run_id,
        dataset_id=case.dataset_id,
        partition=case.partition,
        title=f"{system.value} report for {case.entity_id}",
        narrative=narrative,
        claims=claims,
        generated_by=generated_by,
        metadata={"case_id": case.case_id, "condition": case.condition},
    )
