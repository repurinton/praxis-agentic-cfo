"""System runners for the four PDF conditions."""

from agentic_cfo.systems.agentic_cfo import AgenticCFOSystem
from agentic_cfo.systems.baseline_a_deterministic import BaselineADeterministicSystem
from agentic_cfo.systems.baseline_b_llm_assisted import BaselineBLLMAssistedSystem
from agentic_cfo.systems.baseline_c_rag_only import BaselineCRAGOnlySystem

__all__ = [
    "AgenticCFOSystem",
    "BaselineADeterministicSystem",
    "BaselineBLLMAssistedSystem",
    "BaselineCRAGOnlySystem",
]
