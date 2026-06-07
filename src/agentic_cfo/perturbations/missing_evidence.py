from __future__ import annotations

from dataclasses import replace

from agentic_cfo.data.schema import ReportingCase


def apply_missing_evidence(case: ReportingCase) -> ReportingCase:
    records = tuple(r for r in case.records if r.account != "Expense")
    return replace(
        case,
        case_id=f"{case.case_id}:missing_evidence",
        condition="single_perturbation",
        records=records,
        policy_text="",
        source_document_text="",
        perturbations=case.perturbations + ("missing_evidence",),
    )
