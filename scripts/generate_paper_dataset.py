#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from agentic_cfo.data.generator import generate_cases_from_config, write_dataset


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/datasets/paper_synthetic_v1.yaml")
    parser.add_argument("--out", default="data/generated/paper_synthetic_v1")
    args = parser.parse_args()

    cases = generate_cases_from_config(Path(args.config))
    write_dataset(cases, Path(args.out))
    print(f"Wrote {len(cases)} cases to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
