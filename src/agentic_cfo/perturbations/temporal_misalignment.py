from __future__ import annotations

from dataclasses import replace

from agentic_cfo.data.schema import FinancialRecord, ReportingCase


def apply_temporal_misalignment(case: ReportingCase) -> ReportingCase:
    shifted = f"{case.period}-MISALIGNED"
    records = tuple(
        FinancialRecord(r.account, r.balance, shifted if r.account == "Expense" else r.period, r.entity_id)
        for r in case.records
    )
    return replace(
        case,
        case_id=f"{case.case_id}:temporal_misalignment",
        condition="single_perturbation",
        records=records,
        perturbations=case.perturbations + ("temporal_misalignment",),
    )
