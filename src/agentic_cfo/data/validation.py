from __future__ import annotations

from collections import Counter

from agentic_cfo.data.schema import ReportingCase


def validate_cases(cases: tuple[ReportingCase, ...]) -> dict:
    partitions = Counter(c.partition for c in cases)
    ids = [c.case_id for c in cases]
    checks = {
        "case_ids_unique": len(ids) == len(set(ids)),
        "partitions": dict(partitions),
        "all_cases_have_records": all(bool(c.records) for c in cases),
        "all_cases_have_policy_text": all(bool(c.policy_text) for c in cases),
    }
    checks["valid"] = (
        checks["case_ids_unique"]
        and checks["all_cases_have_records"]
        and checks["all_cases_have_policy_text"]
        and bool(checks["partitions"])
    )
    return checks
