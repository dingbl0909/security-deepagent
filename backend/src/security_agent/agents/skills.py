from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class Skill(BaseModel):
    name: str
    description: str
    triggers: list[str] = Field(default_factory=list)
    body: str
    path: str


class SkillLoadError(ValueError):
    pass


def load_skills(skills_dir: str | Path) -> list[Skill]:
    root = Path(skills_dir)
    if not root.exists():
        return []
    skills: list[Skill] = []
    for path in sorted(root.glob("*/SKILL.md")):
        skills.append(_load_skill(path))
    return skills


def select_skills(skills: list[Skill], message: str) -> list[Skill]:
    lower_message = message.lower()
    return [
        skill
        for skill in skills
        if any(trigger.lower() in lower_message for trigger in skill.triggers)
    ]


def render_skills_prompt(skills: list[Skill]) -> str:
    if not skills:
        return ""
    blocks = []
    for skill in skills:
        blocks.append(
            f"### {skill.name}\n"
            f"描述：{skill.description}\n\n"
            f"{skill.body.strip()}"
        )
    return "## 已加载 Skills\n\n" + "\n\n".join(blocks)


def _load_skill(path: Path) -> Skill:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        raise SkillLoadError(f"skill missing YAML frontmatter: {path}")
    try:
        _, header, body = raw.split("---", 2)
    except ValueError as exc:
        raise SkillLoadError(f"invalid skill frontmatter: {path}") from exc
    metadata = yaml.safe_load(header) or {}
    for field_name in ["name", "description"]:
        if not metadata.get(field_name):
            raise SkillLoadError(f"skill {path} missing required field: {field_name}")
    return Skill(
        name=metadata["name"],
        description=metadata["description"],
        triggers=metadata.get("triggers") or [],
        body=body,
        path=str(path),
    )
