from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from agentic_cfo.eval.aggregate import perturbation_deltas, summarize_by_system_condition


def write_csv(path: Path, rows: tuple[dict[str, Any], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_chapter4_tables(*, results_json: Path, out_dir: Path) -> dict[str, str]:
    payload = json.loads(results_json.read_text(encoding="utf-8"))
    rows = tuple(payload["rows"])
    summary = summarize_by_system_condition(rows)
    deltas = perturbation_deltas(summary)

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "table_system_condition_summary.csv"
    deltas_path = out_dir / "table_perturbation_deltas.csv"
    write_csv(summary_path, summary)
    write_csv(deltas_path, deltas)
    return {
        "system_condition_summary": str(summary_path),
        "perturbation_deltas": str(deltas_path),
    }
