from __future__ import annotations

from agentic_cfo.systems.agentic_cfo import AgenticCFOSystem
from agentic_cfo.systems.base import SystemRunner
from agentic_cfo.systems.baseline_a_deterministic import BaselineADeterministicSystem
from agentic_cfo.systems.baseline_b_llm_assisted import BaselineBLLMAssistedSystem
from agentic_cfo.systems.baseline_c_rag_only import BaselineCRAGOnlySystem


def system_runner(name: str) -> SystemRunner:
    mapping = {
        "baseline_a_deterministic": BaselineADeterministicSystem,
        "baseline_b_llm_assisted": BaselineBLLMAssistedSystem,
        "baseline_c_rag_only": BaselineCRAGOnlySystem,
        "agentic_cfo": AgenticCFOSystem,
    }
    if name not in mapping:
        raise KeyError(f"Unknown system: {name}")
    return mapping[name]()
