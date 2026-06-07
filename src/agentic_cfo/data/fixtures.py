from __future__ import annotations

import csv
import json
from pathlib import Path

from agentic_cfo.core.models import stable_hash


def write_minimal_fixture(root: Path) -> Path:
    """Create a tiny deterministic reporting case used for smoke tests."""
    root.mkdir(parents=True, exist_ok=True)
    tb_path = root / "trial_balance.csv"
    rows = [
        {"account": "Revenue", "balance": "1000.00"},
        {"account": "Expense", "balance": "620.00"},
        {"account": "Cash", "balance": "380.00"},
        {"account": "Accounts Receivable", "balance": "140.00"},
    ]
    with tb_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["account", "balance"])
        writer.writeheader()
        writer.writerows(rows)

    policy_path = root / "policy_corpus.jsonl"
    policy_text = "Financial narratives must be traceable to source records before release."
    policy_path.write_text(
        json.dumps(
            {
                "span_id": "policy:traceability",
                "source_id": "policy_corpus.jsonl",
                "source_type": "policy",
                "locator": "line=1",
                "text": policy_text,
                "content_hash": stable_hash(policy_text),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = {
        "dataset_id": "minimal_fixture_v1",
        "partition": "baseline_validation",
        "files": {
            "trial_balance.csv": stable_hash(tb_path.read_text(encoding="utf-8")),
            "policy_corpus.jsonl": stable_hash(policy_path.read_text(encoding="utf-8")),
        },
        "row_counts": {"trial_balance": len(rows), "policy_spans": 1},
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return root
