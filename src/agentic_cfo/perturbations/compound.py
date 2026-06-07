from __future__ import annotations

from agentic_cfo.data.schema import ReportingCase
from agentic_cfo.perturbations.conflicting_records import apply_conflicting_records
from agentic_cfo.perturbations.missing_evidence import apply_missing_evidence
from agentic_cfo.perturbations.temporal_misalignment import apply_temporal_misalignment


def apply_compound_perturbation(case: ReportingCase) -> ReportingCase:
    perturbed = apply_missing_evidence(case)
    perturbed = apply_conflicting_records(perturbed)
    perturbed = apply_temporal_misalignment(perturbed)
    return perturbed
