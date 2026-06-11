from __future__ import annotations

from agentic_cfo.core.models import ReportArtifact, SystemCondition
from agentic_cfo.data.schema import ReportingCase
from agentic_cfo.systems.base import SystemRunner
from agentic_cfo.systems.util import make_report


class BaselineBLLMAssistedSystem(SystemRunner):
    """LLM-assisted baseline (deterministic stand-in).

    Represents an LLM that drafts the report and cites figures from the trial
    balance but is *not* verification-gated. It binds the numbers it reports
    (so they are traceable) yet transcribes one of them inaccurately
    (``numeric_error``) and leaves the derived/narrative claim ungrounded.
    This yields a realistic mid-tier profile: partial numeric agreement, low
    factual grounding, and a nonzero unsupported-claim rate -- between the
    deterministic baseline (A) and the RAG baseline (C).

    In live mode (``AGENTIC_CFO_LLM_MODE=live``) this is replaced by a real
    model call; see ``agentic_cfo.llm``.
    """

    system_name = "baseline_b_llm_assisted"

    def run(self, case: ReportingCase, *, run_id: str) -> ReportArtifact:
        from agentic_cfo.llm import llm_is_live

        if llm_is_live():
            from agentic_cfo.llm.report_generation import generate_report_via_llm

            return generate_report_via_llm(
                case,
                run_id=run_id,
                system=SystemCondition.BASELINE_B,
                generated_by=self.system_name,
                bind_evidence=False,
            )

        return make_report(
            case,
            run_id=run_id,
            system=SystemCondition.BASELINE_B,
            generated_by=self.system_name,
            bind_numeric=True,
            bind_narrative=False,
            numeric_error=5.0,
        )
