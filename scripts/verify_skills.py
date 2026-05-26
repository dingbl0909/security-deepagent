from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from security_agent.skills import load_skills, render_skills_prompt


def main() -> None:
    skills = load_skills(PROJECT_ROOT / "skills")
    print(f"Loaded skills: {len(skills)}")
    for skill in skills:
        print(f"- {skill.name}: {skill.description}")

    prompt = render_skills_prompt(skills)
    if not prompt:
        raise SystemExit("No skills prompt was rendered.")
    print(f"Rendered skills prompt chars: {len(prompt)}")


if __name__ == "__main__":
    main()
