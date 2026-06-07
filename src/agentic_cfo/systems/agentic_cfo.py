from __future__ import annotations

from agentic_cfo.agents import AgenticCFOControllerAgent, AgenticCFOPlannerAgent
from agentic_cfo.core.models import ReportArtifact
from agentic_cfo.data.schema import ReportingCase
from agentic_cfo.evidence.corpus import corpus_from_case
from agentic_cfo.systems.base import SystemRunner


class AgenticCFOSystem(SystemRunner):
    system_name = "agentic_cfo"

    def __init__(self) -> None:
        self.planner = AgenticCFOPlannerAgent()
        self.controller = AgenticCFOControllerAgent()

    def run(self, case: ReportingCase, *, run_id: str) -> ReportArtifact:
        plan = self.planner.create_plan(dataset_id=case.dataset_id, partition=case.partition)
        return self.controller.generate_report(
            plan=plan,
            run_id=run_id,
            dataset_id=case.dataset_id,
            partition=case.partition,
            corpus=corpus_from_case(case),
        )
