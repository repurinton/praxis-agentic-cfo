from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from agentic_cfo.core.models import EvidencePointer, EvidenceSpan
from agentic_cfo.data.schema import ReportingCase


class EvidenceCorpus:
    def __init__(self, spans: Iterable[EvidenceSpan]):
        self._spans = {span.span_id: span for span in spans}

    @property
    def spans(self) -> tuple[EvidenceSpan, ...]:
        return tuple(self._spans.values())

    def get(self, span_id: str) -> EvidenceSpan | None:
        return self._spans.get(span_id)

    def pointer(self, span_id: str) -> EvidencePointer:
        span = self._spans[span_id]
        return EvidencePointer.from_span(span)

    def find_by_account(self, account: str) -> EvidenceSpan | None:
        account_norm = account.strip().lower()
        for span in self._spans.values():
            if str(span.metadata.get("account", "")).strip().lower() == account_norm:
                return span
        return None

    def find_policy(self, key: str) -> EvidenceSpan | None:
        key_norm = key.strip().lower()
        for span in self._spans.values():
            if span.source_type == "policy" and key_norm in span.text.lower():
                return span
        return None


def load_trial_balance_corpus(path: Path, *, dataset_id: str = "fixture") -> EvidenceCorpus:
    spans: list[EvidenceSpan] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            account = str(row.get("account", "")).strip()
            if not account:
                continue
            amount_raw = row.get("balance", row.get("amount", ""))
            text = f"{account} balance is {amount_raw} USD for dataset {dataset_id}."
            spans.append(
                EvidenceSpan.from_text(
                    span_id=f"tb:{account.lower().replace(' ', '_')}",
                    source_id=path.name,
                    source_type="trial_balance",
                    locator=f"row={idx};account={account}",
                    text=text,
                    metadata={
                        "dataset_id": dataset_id,
                        "account": account,
                        "balance": float(amount_raw),
                        "row": dict(row),
                    },
                )
            )
    return EvidenceCorpus(spans)


def corpus_from_case(case: ReportingCase) -> EvidenceCorpus:
    spans: list[EvidenceSpan] = []
    for record in case.records:
        text = (
            f"{record.account} balance is {record.balance:.2f} USD "
            f"for {record.entity_id} in {record.period}."
        )
        spans.append(
            EvidenceSpan.from_text(
                span_id=f"{case.case_id}:tb:{record.account.lower().replace(' ', '_')}",
                source_id=f"{case.case_id}:trial_balance",
                source_type="trial_balance",
                locator=f"entity={record.entity_id};period={record.period};account={record.account}",
                text=text,
                metadata={
                    "dataset_id": case.dataset_id,
                    "case_id": case.case_id,
                    "entity_id": record.entity_id,
                    "period": record.period,
                    "account": record.account,
                    "balance": record.balance,
                },
            )
        )
    if case.policy_text:
        spans.append(
            EvidenceSpan.from_text(
                span_id=f"{case.case_id}:policy:traceability",
                source_id=f"{case.case_id}:policy",
                source_type="policy",
                locator="policy_text",
                text=case.policy_text,
                metadata={"dataset_id": case.dataset_id, "case_id": case.case_id},
            )
        )
    if case.source_document_text:
        spans.append(
            EvidenceSpan.from_text(
                span_id=f"{case.case_id}:doc:summary",
                source_id=f"{case.case_id}:source_document",
                source_type="source_document",
                locator="source_document_text",
                text=case.source_document_text,
                metadata={"dataset_id": case.dataset_id, "case_id": case.case_id},
            )
        )
    return EvidenceCorpus(spans)
