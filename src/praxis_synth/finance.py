"""Experimental synthetic finance generator placeholder.

The prior scaffold contained an incomplete module here. The canonical dataset
path for the praxis implementation now lives under `agentic_cfo.data`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SynthConfig:
    seed: int = 42
    n_rows: int = 0
    n_companies: int = 0
