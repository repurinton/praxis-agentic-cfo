from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

DETERMINISTIC = "deterministic"
LIVE = "live"

_DOTENV_LOADED = False


def _ensure_dotenv(env_file: str = ".env") -> None:
    """Load a local .env once so OPENAI_API_KEY is available in live mode."""
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=Path(env_file))
    except Exception:
        # python-dotenv is optional; the key may already be in the environment.
        pass
    _DOTENV_LOADED = True


def llm_mode() -> str:
    return os.environ.get("AGENTIC_CFO_LLM_MODE", DETERMINISTIC).strip().lower()


def llm_is_live() -> bool:
    return llm_mode() == LIVE


def llm_model() -> str:
    return os.environ.get("AGENTIC_CFO_LLM_MODEL", "gpt-4o-mini").strip()


@dataclass(frozen=True)
class LLMResponse:
    text: str
    latency_seconds: float
    model: str
    mode: str
    usage: dict[str, int] = field(default_factory=dict)


class LLMClient:
    """Thin OpenAI chat-completions wrapper with a deterministic offline mode.

    In ``deterministic`` mode ``complete`` performs no network I/O and returns an
    empty response (callers fall back to their deterministic logic). In ``live``
    mode it calls the OpenAI API and measures latency. The API key is required
    only in live mode, so importing/constructing this class never needs a key.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1200,
        env_file: str = ".env",
    ) -> None:
        _ensure_dotenv(env_file)
        self.mode = llm_mode()
        self.model = model or llm_model()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None

    def _openai(self):
        if self._client is None:
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
            if not api_key:
                raise RuntimeError(
                    "AGENTIC_CFO_LLM_MODE=live requires OPENAI_API_KEY. "
                    "Set it in the environment or a local .env file, or use the "
                    "default deterministic mode for offline/reproducible runs."
                )
            from openai import OpenAI

            self._client = OpenAI(api_key=api_key)
        return self._client

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_json: bool = False,
    ) -> LLMResponse:
        if self.mode != LIVE:
            return LLMResponse(
                text="",
                latency_seconds=0.0,
                model="deterministic-local",
                mode=DETERMINISTIC,
            )

        client = self._openai()
        kwargs: dict = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if response_json:
            kwargs["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        resp = client.chat.completions.create(**kwargs)
        latency = time.perf_counter() - started

        text = resp.choices[0].message.content or ""
        usage: dict[str, int] = {}
        if getattr(resp, "usage", None) is not None:
            usage = {
                "prompt_tokens": int(resp.usage.prompt_tokens or 0),
                "completion_tokens": int(resp.usage.completion_tokens or 0),
                "total_tokens": int(resp.usage.total_tokens or 0),
            }
        return LLMResponse(
            text=text,
            latency_seconds=latency,
            model=self.model,
            mode=LIVE,
            usage=usage,
        )
