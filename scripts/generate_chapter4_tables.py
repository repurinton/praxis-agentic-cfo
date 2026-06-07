#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentic_cfo.eval.chapter4_tables import write_chapter4_tables


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-json", default="results/paper_v1/results.json")
    parser.add_argument("--out-dir", default="results/paper_v1")
    args = parser.parse_args()

    paths = write_chapter4_tables(results_json=Path(args.results_json), out_dir=Path(args.out_dir))
    print(json.dumps(paths, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
