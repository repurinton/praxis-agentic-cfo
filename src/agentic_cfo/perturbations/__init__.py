"""Deterministic perturbation framework."""

from agentic_cfo.perturbations.compound import apply_compound_perturbation
from agentic_cfo.perturbations.conflicting_records import apply_conflicting_records
from agentic_cfo.perturbations.missing_evidence import apply_missing_evidence
from agentic_cfo.perturbations.temporal_misalignment import apply_temporal_misalignment

__all__ = [
    "apply_missing_evidence",
    "apply_conflicting_records",
    "apply_temporal_misalignment",
    "apply_compound_perturbation",
]
