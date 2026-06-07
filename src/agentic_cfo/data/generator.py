from __future__ import annotations

import csv
import json
from pathlib import Path

from agentic_cfo.data.manifest import DatasetManifest, file_hashes, write_manifest
from agentic_cfo.data.partitions import assign_partition
from agentic_cfo.data.schema import FinancialRecord, ReportingCase
from agentic_cfo.data.validation import validate_cases
from agentic_cfo.experiment.contract import load_yaml_mapping


def generate_cases_from_config(config_path: Path) -> tuple[ReportingCase, ...]:
    config = load_yaml_mapping(config_path)
    dataset_id = str(config.get("dataset_id", "paper_synthetic_v1"))
    period = str(config.get("period", "FY2026-Q1"))
    n_cases = int(config.get("n_cases", 12))
    base_records = dict(config.get("base_records", {})) or {
        "Revenue": 1000.0,
        "Expense": 620.0,
        "Cash": 380.0,
        "Accounts Receivable": 140.0,
    }

    cases: list[ReportingCase] = []
    for idx in range(n_cases):
        entity_id = f"ENT{idx + 1:03d}"
        partition = assign_partition(idx, n_cases)
        records = tuple(
            FinancialRecord(account=account, balance=float(balance), period=period, entity_id=entity_id)
            for account, balance in base_records.items()
        )
        cases.append(
            ReportingCase(
                case_id=f"{dataset_id}:case:{idx + 1:04d}",
                dataset_id=dataset_id,
                partition=partition,
                condition="clean",
                period=period,
                entity_id=entity_id,
                records=records,
                policy_text="Financial narratives must be traceable to source records before release.",
                source_document_text=(
                    f"For {entity_id} in {period}, revenue is {base_records['Revenue']} USD "
                    f"and expense is {base_records['Expense']} USD."
                ),
            )
        )
    return tuple(cases)


def write_dataset(cases: tuple[ReportingCase, ...], root: Path, *, schema_version: str = "1.0", seed: int = 42) -> None:
    root.mkdir(parents=True, exist_ok=True)
    with (root / "cases.jsonl").open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case.to_dict(), sort_keys=True) + "\n")

    with (root / "trial_balance.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "entity_id", "period", "account", "balance"])
        writer.writeheader()
        for case in cases:
            for record in case.records:
                writer.writerow({
                    "case_id": case.case_id,
                    "entity_id": record.entity_id,
                    "period": record.period,
                    "account": record.account,
                    "balance": record.balance,
                })

    validation = validate_cases(cases)
    manifest = DatasetManifest(
        dataset_id=cases[0].dataset_id if cases else "empty",
        schema_version=schema_version,
        seed=seed,
        n_cases=len(cases),
        files=file_hashes(root),
        row_counts={"cases": len(cases), "trial_balance_rows": sum(len(c.records) for c in cases)},
        validation=validation,
    )
    write_manifest(root, manifest)


def load_cases(path: Path) -> tuple[ReportingCase, ...]:
    cases = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(ReportingCase.from_dict(json.loads(line)))
    return tuple(cases)
