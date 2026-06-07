# Appendix: Agent Prompts And Metric Definitions

This appendix excerpt is drawn from the local Agentic CFO scaffold. It is intended for inclusion as supporting implementation detail in the praxis paper. Source paths are included so the appendix can be traced back to repository artifacts.

## A.1 Agent Roles

### Planner Agent

Source: `src/agentic_cfo/agents/planner.py`

```python
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
```

### Controller Agent

Source: `src/agentic_cfo/agents/controller.py`

```python
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
```

### Verifier Agent

Source: `src/agentic_cfo/agents/verifier.py`

```python
class AgenticCFOVerifierAgent:
    name = "AgenticCFOVerifierAgent"

    def __init__(self, engine: VerificationEngine | None = None):
        self.engine = engine or VerificationEngine()

    def verify(
        self,
        artifact: ReportArtifact,
        *,
        thresholds: dict[str, float],
        corpus: EvidenceCorpus | None = None,
    ) -> VerificationRecord:
        return self.engine.verify(
            artifact,
            verification_id=f"verification:{uuid4()}",
            thresholds=thresholds,
            corpus=corpus,
        )
```

## A.2 Agent Prompt Templates

### Planner Prompt

Source: `src/agentic_cfo/agents/prompts/planner.md`

```text
You are AgenticCFOPlannerAgent.

Create a reporting plan for dataset {{dataset_id}} partition {{partition}}.

Requirements:
- Use only lineage-complete sources.
- Declare every required source path.
- Route the Controller through evidence binding before release.
- Preserve run, dataset, partition, and configuration provenance.
```

### Controller Prompt

Source: `src/agentic_cfo/agents/prompts/controller.md`

```text
You are AgenticCFOControllerAgent.

Generate the report artifact for run {{run_id}} using plan {{plan_id}}.

Requirements:
- Own report generation.
- Pull source records from the evidence corpus.
- Bind numeric and narrative claims to evidence pointers.
- Refuse unsupported material claims instead of inventing evidence.
- Emit structured atomic claims and a narrative draft.
```

### Verifier Prompt

Source: `src/agentic_cfo/agents/prompts/verifier.md`

```text
You are AgenticCFOVerifierAgent.

Verify artifact {{artifact_id}} for run {{run_id}}.

Requirements:
- Normalize atomic claims.
- Verify numeric agreement against authoritative records.
- Verify evidence support and retrieved-context faithfulness.
- Evaluate thresholds from the locked evaluation config.
- Emit explicit failure categories and unsupported claim identifiers.
```

## A.3 Metric Definitions

Source: `src/agentic_cfo/eval/metrics.py`

### Support Predicate For Reliable Evidence

This predicate underlies the local FActScore-style factual support adapter. The local implementation treats `AtomicClaim` as the atomic factual unit and `EvidenceCorpus` as the reliable source.

```python
def claim_supported_by_reliable_source(claim: AtomicClaim, corpus: EvidenceCorpus | None = None) -> bool:
    if not claim.evidence:
        return False
    if corpus is None:
        return True
    if claim.value is not None:
        evidence_value = _evidence_value(claim, corpus)
        return evidence_value is not None and abs(float(claim.value) - evidence_value) <= 0.01
    return all(corpus.get(pointer.span_id) is not None for pointer in claim.evidence)
```

Formula:

```text
claim_supported_by_reliable_source =
  evidence_present
  AND, for numeric claims, absolute(claim_value - evidence_value) <= 0.01
  AND, for nonnumeric claims, all evidence pointers resolve in the corpus
```

### Support Predicate For Retrieved Context

This predicate underlies the local RAGAS-style faithfulness adapter. The local implementation represents retrieved context by evidence span identifiers.

```python
def claim_supported_by_retrieved_context(claim: AtomicClaim, retrieved_span_ids: set[str]) -> bool:
    if not claim.evidence:
        return False
    return all(pointer.span_id in retrieved_span_ids for pointer in claim.evidence)
```

Formula:

```text
claim_supported_by_retrieved_context =
  evidence_present AND every evidence span used by the claim is in retrieved_span_ids
```

### Numeric Agreement

```python
def numeric_agreement(
    artifact: ReportArtifact,
    checks: tuple[VerificationCheck, ...] = (),
    *,
    corpus: EvidenceCorpus | None = None,
) -> float:
    numeric_claims = tuple(c for c in artifact.claims if c.value is not None)
    numeric_ids = {c.claim_id for c in numeric_claims}
    if not numeric_ids:
        return 1.0
    if corpus is not None:
        passed = sum(1 for claim in numeric_claims if claim_supported_by_reliable_source(claim, corpus))
        return passed / len(numeric_claims)
    passed = {
        c.claim_id
        for c in checks
        if c.claim_id in numeric_ids and c.category == "numeric_agreement" and c.status == VerificationStatus.PASS
    }
    return len(passed) / len(numeric_ids)
```

Formula:

```text
numeric_agreement = supported_numeric_claims / total_numeric_claims
```

### Claim Traceability Rate

```python
def claim_traceability_rate(artifact: ReportArtifact) -> float:
    if not artifact.claims:
        return 1.0
    return sum(1 for c in artifact.claims if c.evidence) / len(artifact.claims)
```

Formula:

```text
claim_traceability_rate = claims_with_evidence / total_claims
```

### Unsupported Claim Rate

```python
def unsupported_claim_rate(artifact: ReportArtifact) -> float:
    if not artifact.claims:
        return 0.0
    return sum(1 for c in artifact.claims if not c.evidence) / len(artifact.claims)
```

Formula:

```text
unsupported_claim_rate = claims_without_evidence / total_claims
```

### Audit Evidence Package Completeness

```python
def audit_evidence_package_completeness(artifact: ReportArtifact) -> float:
    required = 5
    present = 0
    if artifact.artifact_id:
        present += 1
    if artifact.run_id:
        present += 1
    if artifact.dataset_id:
        present += 1
    if artifact.claims:
        present += 1
    if all(c.evidence for c in artifact.claims):
        present += 1
    return present / required
```

Formula:

```text
audit_evidence_package_completeness =
  present_required_audit_fields / required_audit_fields
```

Required fields in the local scaffold:

- artifact ID
- run ID
- dataset ID
- claims
- evidence for every claim

### FActScore-Style Factual Support

```python
def factscore(artifact: ReportArtifact, *, corpus: EvidenceCorpus | None = None) -> float:
    if not artifact.claims:
        return 1.0
    supported = sum(1 for claim in artifact.claims if claim_supported_by_reliable_source(claim, corpus))
    return supported / len(artifact.claims)
```

Formula:

```text
factscore = supported_atomic_claims / total_atomic_claims
```

### RAGAS-Style Faithfulness

```python
def ragas_faithfulness(artifact: ReportArtifact, *, retrieved_span_ids: set[str] | None = None) -> float:
    if not artifact.claims:
        return 1.0
    if retrieved_span_ids is None:
        retrieved_span_ids = {pointer.span_id for claim in artifact.claims for pointer in claim.evidence}
    supported = sum(1 for claim in artifact.claims if claim_supported_by_retrieved_context(claim, retrieved_span_ids))
    return supported / len(artifact.claims)
```

Formula:

```text
ragas_faithfulness = claims_supported_by_retrieved_context / total_atomic_claims
```

## A.4 Aggregate Result Metrics

Source: `src/agentic_cfo/eval/aggregate.py`

```python
METRIC_COLUMNS = (
    "numeric_agreement",
    "factscore",
    "ragas_faithfulness",
    "unsupported_claim_rate",
    "audit_evidence_package_completeness",
    "claim_traceability_rate",
)
```

System-condition summaries compute mean metric values by system and experimental condition, plus attempted output count, release pass rate, human-audit eligibility count, and median cycle time.

```python
def summarize_by_system_condition(rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["system"]), str(row["condition"]))].append(row)

    summary = []
    for (system, condition), group in sorted(grouped.items()):
        release_eligible = [
            r
            for r in group
            if r.get("release_action") in {"release", "route_to_review", "not_applicable_no_release_gate"}
        ]
        human_audit_eligible = [r for r in group if bool(r.get("human_audit_eligible", False))]
        out = {
            "system": system,
            "condition": condition,
            "attempted_outputs": len(group),
            "release_gate_pass_rate": len(release_eligible) / len(group) if group else 0.0,
            "human_audit_eligible_outputs": len(human_audit_eligible),
            "median_cycle_time_seconds": _median([float(r["cycle_time_seconds"]) for r in group]),
        }
        for metric in METRIC_COLUMNS:
            out[metric] = _mean([float(r[metric]) for r in group])
        summary.append(out)
    return tuple(summary)
```

Perturbation deltas compare perturbation-condition metrics against the clean baseline for each system.

```python
def perturbation_deltas(summary_rows: tuple[dict[str, Any], ...], *, baseline_condition: str = "clean") -> tuple[dict[str, Any], ...]:
    baseline = {
        row["system"]: row
        for row in summary_rows
        if row["condition"] == baseline_condition
    }
    deltas = []
    for row in summary_rows:
        if row["condition"] == baseline_condition or row["system"] not in baseline:
            continue
        base = baseline[row["system"]]
        deltas.append(
            {
                "system": row["system"],
                "condition": row["condition"],
                "numeric_disagreement_increase_bps": (
                    (1.0 - float(row["numeric_agreement"])) - (1.0 - float(base["numeric_agreement"]))
                )
                * 10000,
                "factscore_delta": float(base["factscore"]) - float(row["factscore"]),
                "unsupported_claim_rate_increase": float(row["unsupported_claim_rate"])
                - float(base["unsupported_claim_rate"]),
            }
        )
    return tuple(deltas)
```

