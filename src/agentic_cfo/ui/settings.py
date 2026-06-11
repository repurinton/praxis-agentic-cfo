"""LLM/runtime settings management for the platform UI.

Provides a single place to view and change the OpenAI API key and the
deterministic/live generation mode. Values are read from (and persisted to) the
gitignored ``.env`` file, and applied to ``os.environ`` so subsequently launched
jobs in the same process pick them up. The API key is never echoed in full.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agentic_cfo.llm.client import DETERMINISTIC, LIVE

LLM_MODE_KEY = "AGENTIC_CFO_LLM_MODE"
LLM_MODEL_KEY = "AGENTIC_CFO_LLM_MODEL"
API_KEY = "OPENAI_API_KEY"
MANAGED_KEYS = (API_KEY, LLM_MODE_KEY, LLM_MODEL_KEY)

DEFAULT_MODE = DETERMINISTIC
DEFAULT_MODEL = "gpt-4o-mini"
MODES = (DETERMINISTIC, LIVE)


def mask_key(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "not set"
    if len(value) <= 8:
        return "set (****)"
    return f"set (…{value[-4:]})"


def parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file (ignores comments/blank lines)."""
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, raw = stripped.partition("=")
        key = key.strip()
        val = raw.strip().strip('"').strip("'")
        values[key] = val
    return values


def write_env_file(env_path: Path, updates: dict[str, str]) -> None:
    """Update the given keys in .env, preserving other lines and comments."""
    env_path.parent.mkdir(parents=True, exist_ok=True)
    existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    remaining = dict(updates)
    out: list[str] = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.partition("=")[0].strip()
            if key in remaining:
                out.append(f"{key}={remaining.pop(key)}")
                continue
        out.append(line)
    for key, value in remaining.items():
        out.append(f"{key}={value}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def current_settings(env_path: Path) -> dict[str, Any]:
    """Effective settings: process environment takes priority over .env."""
    file_values = parse_env_file(env_path)

    def resolve(key: str, default: str) -> str:
        return os.environ.get(key) or file_values.get(key) or default

    mode = resolve(LLM_MODE_KEY, DEFAULT_MODE).strip().lower()
    if mode not in MODES:
        mode = DEFAULT_MODE
    api_key = os.environ.get(API_KEY) or file_values.get(API_KEY) or ""
    return {
        "env_path": str(env_path),
        "mode": mode,
        "model": resolve(LLM_MODEL_KEY, DEFAULT_MODEL),
        "api_key_present": bool(api_key.strip()),
        "api_key_masked": mask_key(api_key),
        "live_ready": mode == LIVE and bool(api_key.strip()),
    }


def apply_settings(
    *,
    env_path: Path,
    mode: str,
    model: str,
    api_key: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Apply settings to os.environ and optionally persist them to .env.

    ``api_key`` of ``None`` leaves the existing key untouched; an empty string
    clears it. Returns the resulting effective settings.
    """
    mode = (mode or DEFAULT_MODE).strip().lower()
    if mode not in MODES:
        raise ValueError(f"Invalid mode: {mode!r}; expected one of {MODES}")
    model = (model or DEFAULT_MODEL).strip()

    os.environ[LLM_MODE_KEY] = mode
    os.environ[LLM_MODEL_KEY] = model
    updates = {LLM_MODE_KEY: mode, LLM_MODEL_KEY: model}

    if api_key is not None:
        api_key = api_key.strip()
        if api_key:
            os.environ[API_KEY] = api_key
        else:
            os.environ.pop(API_KEY, None)
        updates[API_KEY] = api_key

    if persist:
        write_env_file(env_path, updates)

    return current_settings(env_path)
