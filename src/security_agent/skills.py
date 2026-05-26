from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from security_agent.config import get_settings

try:
    import yaml
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    yaml = None


@dataclass(frozen=True)
class AgentSkill:
    name: str
    description: str
    path: Path
    content: str
    triggers: tuple[str, ...] = ()


def load_skills(skills_dir: Path | None = None) -> list[AgentSkill]:
    root = skills_dir or get_settings().skills_dir
    if not root.exists():
        return []

    skills: list[AgentSkill] = []
    for skill_path in sorted(root.glob("*/SKILL.md")):
        text = skill_path.read_text(encoding="utf-8")
        metadata, body = _split_frontmatter(text)
        name = str(metadata.get("name") or skill_path.parent.name).strip()
        description = str(metadata.get("description") or _fallback_description(body)).strip()
        triggers = _as_tuple(metadata.get("triggers"))
        skills.append(
            AgentSkill(
                name=name,
                description=description,
                path=skill_path,
                content=body.strip(),
                triggers=triggers,
            )
        )
    return skills


def select_skills(message: str, skills: list[AgentSkill], limit: int | None = None) -> list[AgentSkill]:
    if not message.strip():
        return skills[:limit] if limit else skills

    normalized = message.lower()
    scored: list[tuple[int, AgentSkill]] = []
    for skill in skills:
        score = 0
        candidates = (skill.name, skill.description, *skill.triggers)
        for candidate in candidates:
            if candidate and candidate.lower() in normalized:
                score += 1
        if score:
            scored.append((score, skill))

    selected = [skill for _, skill in sorted(scored, key=lambda item: item[0], reverse=True)]
    if not selected:
        selected = skills
    return selected[:limit] if limit else selected


def render_skills_prompt(skills: list[AgentSkill]) -> str:
    if not skills:
        return ""

    lines = [
        "## 可用 Agent Skills",
        "",
        "以下 Skill 是按需加载的业务能力说明。需要相关能力时，遵循对应 Skill 的能力边界、工具要求、安全要求和输出格式。",
    ]
    for skill in skills:
        lines.extend(
            [
                "",
                f"### {skill.name}",
                "",
                f"描述：{skill.description}",
                "",
                skill.content,
            ]
        )
    return "\n".join(lines).strip()


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text

    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text

    raw_metadata = text[4:end]
    body = text[end + len("\n---\n") :]
    if yaml is None:
        return {}, body
    metadata = yaml.safe_load(raw_metadata) or {}
    return metadata if isinstance(metadata, dict) else {}, body


def _fallback_description(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return "未提供描述。"


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(str(item) for item in value if str(item).strip())
    return ()
