"""LLM integration for the Agentic CFO experiment systems.

Two modes are supported, selected by the ``AGENTIC_CFO_LLM_MODE`` environment
variable:

* ``deterministic`` (default) -- no network calls. The systems use the
  reproducible deterministic stand-ins. This preserves the praxis's locked,
  offline reproducibility property and keeps the test suite hermetic.
* ``live`` -- the LLM-driven systems (baseline B, baseline C, agentic CFO)
  call the OpenAI API. Requires ``OPENAI_API_KEY`` (read from the environment
  or a local ``.env`` file). Real wall-clock latency is captured by the
  experiment runner as ``cycle_time_seconds``.

Configuration:
    AGENTIC_CFO_LLM_MODE   deterministic | live   (default: deterministic)
    AGENTIC_CFO_LLM_MODEL  model name             (default: gpt-4o-mini)
    OPENAI_API_KEY         required only in live mode
"""

from agentic_cfo.llm.client import (
    DETERMINISTIC,
    LIVE,
    LLMClient,
    LLMResponse,
    llm_is_live,
    llm_mode,
    llm_model,
)

__all__ = [
    "DETERMINISTIC",
    "LIVE",
    "LLMClient",
    "LLMResponse",
    "llm_is_live",
    "llm_mode",
    "llm_model",
]
