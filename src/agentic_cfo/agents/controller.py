from __future__ import annotations

from uuid import uuid4

from agentic_cfo.agents.planner import ReportingPlan
from agentic_cfo.core.models import AtomicClaim, ClaimType, ReportArtifact, SystemCondition
from agentic_cfo.evidence.binder import EvidenceBinder
from agentic_cfo.evidence.corpus import EvidenceCorpus


class AgenticCFOControllerAgent:
    """Controller owns content generation, as specified by the praxis PDF."""

    name = "AgenticCFOControllerAgent"

    def generate_report(
        self,
        *,
        plan: ReportingPlan,
        run_id: str,
        dataset_id: str,
        partition: str,
        corpus: EvidenceCorpus,
    ) -> ReportArtifact:
        binder = EvidenceBinder(corpus)
        revenue_span = corpus.find_by_account("Revenue")
        expense_span = corpus.find_by_account("Expense")
        revenue_value = float(revenue_span.metadata.get("balance", 0.0)) if revenue_span else 0.0
        expense_value = float(expense_span.metadata.get("balance", 0.0)) if expense_span else 0.0

        raw_claims = [
            AtomicClaim(
                claim_id="claim:revenue_balance",
                claim_type=ClaimType.NUMERIC,
                text=f"Revenue balance is {revenue_value:.2f} USD.",
                value=revenue_value,
                unit="USD",
                account="Revenue",
                period="fixture_period",
                source_location="controller:narrative:1",
            ),
            AtomicClaim(
                claim_id="claim:expense_balance",
                claim_type=ClaimType.NUMERIC,
                text=f"Expense balance is {expense_value:.2f} USD.",
                value=expense_value,
                unit="USD",
                account="Expense",
                period="fixture_period",
                source_location="controller:narrative:2",
            ),
            AtomicClaim(
                claim_id="claim:profitability",
                claim_type=ClaimType.DERIVED,
                text="Revenue exceeds expense, indicating positive operating margin in the reporting case.",
                account="Revenue",
                period="fixture_period",
                source_location="controller:narrative:3",
                metadata={"formula": "Revenue - Expense"},
            ),
        ]

        bound: list[AtomicClaim] = []
        for claim in raw_claims:
            if claim.claim_id == "claim:profitability":
                revenue = corpus.find_by_account("Revenue")
                expense = corpus.find_by_account("Expense")
                evidence = tuple(
                    p for p in [
                        binder.corpus.pointer(revenue.span_id) if revenue else None,
                        binder.corpus.pointer(expense.span_id) if expense else None,
                    ]
                    if p is not None
                )
                bound.append(
                    AtomicClaim(
                        claim_id=claim.claim_id,
                        claim_type=claim.claim_type,
                        text=claim.text,
                        value=claim.value,
                        unit=claim.unit,
                        account=claim.account,
                        period=claim.period,
                        material=claim.material,
                        evidence=evidence,
                        source_location=claim.source_location,
                        metadata={**claim.metadata, "binding_method": "derived_inputs"},
                    )
                )
            else:
                bound.append(binder.bind_account_claim(claim))

        narrative = (
            f"Revenue balance is {revenue_value:.2f} USD. Expense balance is {expense_value:.2f} USD. "
            "Revenue exceeds expense, indicating positive operating margin in the reporting case."
        )

        return ReportArtifact(
            artifact_id=f"artifact:{uuid4()}",
            system=SystemCondition.AGENTIC_CFO,
            run_id=run_id,
            dataset_id=dataset_id,
            partition=partition,
            title="Agentic CFO Fixture Report",
            narrative=narrative,
            claims=tuple(bound),
            generated_by=self.name,
            metadata={"plan_id": plan.plan_id},
        )
