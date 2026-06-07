from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    description: str
    required_sources: tuple[str, ...]


@dataclass(frozen=True)
class ReportingPlan:
    plan_id: str
    steps: tuple[PlanStep, ...]

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "steps": [
                {
                    "step_id": s.step_id,
                    "description": s.description,
                    "required_sources": list(s.required_sources),
                }
                for s in self.steps
            ],
        }


class AgenticCFOPlannerAgent:
    name = "AgenticCFOPlannerAgent"

    def create_plan(self, *, dataset_id: str, partition: str) -> ReportingPlan:
        return ReportingPlan(
            plan_id=f"plan:{dataset_id}:{partition}",
            steps=(
                PlanStep("load_sources", "Load lineage-complete financial sources.", ("trial_balance.csv",)),
                PlanStep("generate_report", "Generate controller-owned report artifact.", ("trial_balance.csv",)),
                PlanStep("verify_release", "Verify claims and evaluate release thresholds.", ("trial_balance.csv",)),
            ),
        )
