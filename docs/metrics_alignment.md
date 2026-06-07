# Metrics Alignment

Phase 4 implements deterministic local adapters for the metrics named in the praxis PDF. The adapters intentionally keep the scoring unit explicit so the implementation can later swap in external model-assisted evaluators without changing experiment outputs.

## Numeric Agreement

`numeric_agreement` is the fraction of numeric atomic claims whose value agrees with the authoritative evidence corpus within a one-cent tolerance.

Formula:

```text
supported_numeric_claims / total_numeric_claims
```

Implementation:

- Numeric claims are `AtomicClaim` records with `value != None`.
- A numeric claim is supported only when it has a bound evidence pointer whose corpus span metadata matches the claim account and value.
- Missing evidence or mismatched values fail the claim.

## FActScore Adapter

FActScore is defined as a fine-grained factual precision score: generated text is decomposed into atomic facts, and the score is the percentage of atomic facts supported by a reliable knowledge source. Source: [Min et al., FActScore, arXiv:2305.14251](https://arxiv.org/abs/2305.14251).

Local adapter:

```text
supported_atomic_claims_by_reliable_source / total_atomic_claims
```

Implementation mapping:

- `AtomicClaim` is the atomic fact.
- `EvidenceCorpus` is the reliable knowledge source.
- Numeric claims require evidence-bound value agreement.
- Narrative, policy, and derived claims require resolvable bound evidence spans.

## RAGAS Faithfulness Adapter

RAGAS faithfulness measures whether generated claims are supported by retrieved context. The current RAGAS documentation defines the score as supported response claims divided by total response claims, with support checked against retrieved context. Sources: [RAGAS faithfulness docs](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/faithfulness/) and [Es et al., RAGAs, EACL 2024](https://aclanthology.org/2024.eacl-demo.16/).

Local adapter:

```text
claims_supported_by_retrieved_spans / total_atomic_claims
```

Implementation mapping:

- Retrieved context is represented by evidence span IDs supplied to generation.
- A claim is faithful when every bound evidence pointer resolves into the retrieved span set.
- Claims without evidence are unfaithful.

## Unsupported Claim Rate

`unsupported_claim_rate` is the fraction of atomic claims with no bound evidence.

Formula:

```text
claims_without_evidence / total_atomic_claims
```

## Audit Evidence Package Completeness

`audit_evidence_package_completeness` checks whether the artifact contains the minimum fields needed for audit review:

- artifact ID
- run ID
- dataset ID
- claims
- evidence for every claim

Formula:

```text
present_required_fields / required_fields
```

## Claim Traceability Rate

`claim_traceability_rate` is the fraction of atomic claims with at least one evidence pointer.

Formula:

```text
claims_with_evidence / total_atomic_claims
```

## Thresholds

The current PDF-aligned scaffold thresholds live in `configs/eval/paper_thresholds.yaml`:

- `numeric_agreement_min: 0.995`
- `factscore_min: 0.800`
- `ragas_faithfulness_min: 0.800`
- `unsupported_claim_rate_max: 0.010`
- `audit_evidence_package_completeness_min: 0.950`
- `claim_traceability_rate_min: 0.950`

Perturbation delta thresholds are also declared in that file for later aggregate analysis.
