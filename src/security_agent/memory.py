from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from security_agent.config import get_settings
from security_agent.database import Database


class MemoryStore:
    def __init__(self, database: Database | None = None, memory_dir: Path | None = None):
        settings = get_settings()
        self.database = database or Database(settings.db_path)
        self.memory_dir = memory_dir or settings.memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def load(self, thread_id: str) -> dict[str, Any]:
        path = self._path(thread_id)
        if not path.exists():
            return {"thread_id": thread_id, "recent_summary": "", "important_facts": []}
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, thread_id: str, summary: str, important_facts: list[str] | None = None) -> None:
        payload = {
            "thread_id": thread_id,
            "recent_summary": summary,
            "important_facts": important_facts or [],
        }
        self._path(thread_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.database.update_thread_summary(thread_id, summary)

    def append_fact(self, thread_id: str, fact: str) -> None:
        payload = self.load(thread_id)
        facts = payload.setdefault("important_facts", [])
        if fact not in facts:
            facts.append(fact)
        self.save(thread_id, payload.get("recent_summary", ""), facts)

    def _path(self, thread_id: str) -> Path:
        safe_thread_id = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in thread_id)
        return self.memory_dir / f"{safe_thread_id}.json"

