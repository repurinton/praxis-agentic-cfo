from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentic_cfo.core.models import stable_hash


PROMPT_DIR = Path(__file__).resolve().parents[1] / "agents" / "prompts"


@dataclass(frozen=True)
class PromptRecord:
    prompt_record_id: str
    run_id: str
    agent_name: str
    template_name: str
    template_hash: str
    rendered_prompt_hash: str
    rendered_prompt: str
    variables: dict[str, Any]
    model_config: dict[str, Any]
    tools: tuple[str, ...] = ()
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tools"] = list(self.tools)
        return data


class PromptRegistry:
    def __init__(self, prompt_dir: Path = PROMPT_DIR):
        self.prompt_dir = prompt_dir

    def template_path(self, template_name: str) -> Path:
        path = self.prompt_dir / template_name
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    def load(self, template_name: str) -> str:
        return self.template_path(template_name).read_text(encoding="utf-8")


def _render_template(template: str, variables: dict[str, Any]) -> str:
    rendered = template
    for key, value in sorted(variables.items()):
        rendered = rendered.replace("{{" + key + "}}", str(value))
    return rendered


def render_prompt_record(
    *,
    run_id: str,
    agent_name: str,
    template_name: str,
    variables: dict[str, Any],
    model_config: dict[str, Any],
    tools: tuple[str, ...] = (),
    registry: PromptRegistry | None = None,
) -> PromptRecord:
    registry = registry or PromptRegistry()
    template = registry.load(template_name)
    rendered = _render_template(template, variables)
    return PromptRecord(
        prompt_record_id=f"prompt:{uuid4()}",
        run_id=run_id,
        agent_name=agent_name,
        template_name=template_name,
        template_hash=stable_hash(template),
        rendered_prompt_hash=stable_hash(rendered),
        rendered_prompt=rendered,
        variables=json.loads(json.dumps(variables, sort_keys=True, default=str)),
        model_config=json.loads(json.dumps(model_config, sort_keys=True, default=str)),
        tools=tools,
    )
