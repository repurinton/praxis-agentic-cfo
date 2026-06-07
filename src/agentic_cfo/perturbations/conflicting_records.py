from __future__ import annotations

from dataclasses import replace

from agentic_cfo.data.schema import FinancialRecord, ReportingCase


def apply_conflicting_records(case: ReportingCase) -> ReportingCase:
    records = []
    for record in case.records:
        if record.account == "Revenue":
            records.append(FinancialRecord(record.account, record.balance + 50.0, record.period, record.entity_id))
        else:
            records.append(record)
    return replace(
        case,
        case_id=f"{case.case_id}:conflicting_records",
        condition="single_perturbation",
        records=tuple(records),
        source_document_text=case.source_document_text,
        perturbations=case.perturbations + ("conflicting_records",),
    )
