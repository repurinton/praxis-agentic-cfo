#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from agentic_cfo.data.generator import generate_cases_from_config, write_dataset
from agentic_cfo.eval.chapter4_tables import write_chapter4_tables
from agentic_cfo.experiment.contract import load_experiment_contract
from agentic_cfo.experiment.runner import run_experiment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default="configs/experiment/paper_v1.yaml")
    parser.add_argument("--dataset-out", default="data/generated/paper_synthetic_v1")
    parser.add_argument("--results-out", default="results/paper_v1")
    parser.add_argument("--max-cases-per-condition", type=int, default=2)
    args = parser.parse_args()

    contract = load_experiment_contract(Path(args.contract))
    cases = generate_cases_from_config(Path(contract.dataset_config))
    write_dataset(cases, Path(args.dataset_out))
    result = run_experiment(
        contract=contract,
        dataset_path=Path(args.dataset_out),
        threshold_path=Path(contract.threshold_config),
        out_dir=Path(args.results_out),
        max_cases_per_condition=args.max_cases_per_condition,
    )
    table_paths = write_chapter4_tables(results_json=Path(args.results_out) / "results.json", out_dir=Path(args.results_out))
    print(f"Wrote {len(result.rows)} result rows to {args.results_out}")
    print(f"Wrote Chapter 4 tables: {', '.join(table_paths.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
