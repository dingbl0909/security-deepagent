from __future__ import annotations

from pathlib import Path
from typing import Any

from security_agent.config import get_settings
from security_agent.tools import TOOL_REGISTRY

try:
    import yaml
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    yaml = None


def load_subagents(config_path: Path | None = None) -> list[dict[str, Any]]:
    if yaml is None:
        return []
    path = config_path or get_settings().subagents_path
    if not path.exists():
        return []
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    subagents: list[dict[str, Any]] = []
    for name, spec in config.items():
        tool_names = spec.get("tools", [])
        tools = [TOOL_REGISTRY[tool_name] for tool_name in tool_names if tool_name in TOOL_REGISTRY]
        subagent: dict[str, Any] = {
            "name": name,
            "description": spec.get("description", ""),
            "system_prompt": spec.get("system_prompt", ""),
        }
        if tools:
            subagent["tools"] = tools
        if spec.get("model"):
            subagent["model"] = spec["model"]
        subagents.append(subagent)
    return subagents

