from __future__ import annotations

from agentic_cfo.core.models import ReportArtifact, SystemCondition
from agentic_cfo.data.schema import ReportingCase
from agentic_cfo.systems.base import SystemRunner
from agentic_cfo.systems.util import make_report


class BaselineCRAGOnlySystem(SystemRunner):
    """RAG-only baseline (deterministic stand-in).

    Represents retrieval-augmented generation: every claim is grounded in a
    retrieved evidence span, but there is no verification/release gate. In live
    mode (``AGENTIC_CFO_LLM_MODE=live``) a real model generates the report and
    each claim is bound to the authoritative corpus.
    """

    system_name = "baseline_c_rag_only"

    def run(self, case: ReportingCase, *, run_id: str) -> ReportArtifact:
        from agentic_cfo.llm import llm_is_live

        if llm_is_live():
            from agentic_cfo.llm.report_generation import generate_report_via_llm

            return generate_report_via_llm(
                case,
                run_id=run_id,
                system=SystemCondition.BASELINE_C,
                generated_by=self.system_name,
                bind_evidence=True,
            )

        return make_report(
            case,
            run_id=run_id,
            system=SystemCondition.BASELINE_C,
            generated_by=self.system_name,
            bind_numeric=True,
            bind_narrative=True,
        )
