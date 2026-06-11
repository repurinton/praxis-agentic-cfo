from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from agentic_cfo.data.manifest import DatasetManifest, file_hashes, write_manifest
from agentic_cfo.data.partitions import assign_partition
from agentic_cfo.data.schema import FinancialRecord, ReportingCase
from agentic_cfo.data.validation import validate_cases
from agentic_cfo.experiment.contract import load_yaml_mapping


DEFAULT_BASE_RECORDS = {
    "Revenue": 1000.0,
    "Expense": 620.0,
    "COGS": 410.0,
    "Operating Expense": 210.0,
    "Cash": 380.0,
    "Accounts Receivable": 140.0,
    "Accounts Payable": 95.0,
}


def _vary_balance(
    base: float,
    account: str,
    rng: random.Random,
    *,
    spread: float,
    non_negative: set[str],
) -> float:
    """Deterministically vary a base balance by +/- ``spread`` for one entity.

    The ``rng`` is seeded per entity so the dataset is fully reproducible. Sign
    discipline is enforced: accounts listed in ``non_negative`` never cross zero.
    """
    if spread <= 0:
        return round(float(base), 2)
    factor = 1.0 + rng.uniform(-spread, spread)
    value = round(float(base) * factor, 2)
    if account in non_negative:
        value = max(0.0, value)
    return value


def generate_cases_from_config(config_path: Path) -> tuple[ReportingCase, ...]:
    config = load_yaml_mapping(config_path)
    dataset_id = str(config.get("dataset_id", "paper_synthetic_v1"))
    period = str(config.get("period", "FY2026-Q1"))
    n_cases = int(config.get("n_cases", 12))
    seed = int(config.get("seed", 42))
    base_records = dict(config.get("base_records", {})) or dict(DEFAULT_BASE_RECORDS)

    variation = dict(config.get("balance_variation", {}) or {})
    variation_enabled = bool(variation.get("enabled", False))
    spread = float(variation.get("spread", 0.0)) if variation_enabled else 0.0
    non_negative = set(variation.get("non_negative", []) or [])

    cases: list[ReportingCase] = []
    for idx in range(n_cases):
        entity_id = f"ENT{idx + 1:03d}"
        partition = assign_partition(idx, n_cases)
        # Per-entity RNG: reproducible from the dataset seed, independent per case.
        rng = random.Random((seed * 100003) + idx)
        balances = {
            account: _vary_balance(
                base, account, rng, spread=spread, non_negative=non_negative
            )
            for account, base in base_records.items()
        }
        records = tuple(
            FinancialRecord(account=account, balance=balance, period=period, entity_id=entity_id)
            for account, balance in balances.items()
        )
        revenue = balances.get("Revenue", 0.0)
        expense = balances.get("Expense", 0.0)
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
                    f"For {entity_id} in {period}, revenue is {revenue:.2f} USD "
                    f"and expense is {expense:.2f} USD."
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
