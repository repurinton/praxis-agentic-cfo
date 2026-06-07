from __future__ import annotations

from agentic_cfo.core.models import ReportArtifact, SystemCondition
from agentic_cfo.data.schema import ReportingCase
from agentic_cfo.systems.base import SystemRunner
from agentic_cfo.systems.util import make_report


class BaselineADeterministicSystem(SystemRunner):
    system_name = "baseline_a_deterministic"

    def run(self, case: ReportingCase, *, run_id: str) -> ReportArtifact:
        return make_report(
            case,
            run_id=run_id,
            system=SystemCondition.BASELINE_A,
            generated_by=self.system_name,
            bind_numeric=True,
            bind_narrative=False,
        )
