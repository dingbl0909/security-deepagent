from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from security_agent.config import get_settings
from security_agent.database import Database, utc_now


class AuditLogger:
    def __init__(self, database: Database | None = None, log_dir: Path | None = None):
        settings = get_settings()
        self.database = database or Database(settings.db_path)
        self.log_dir = log_dir or settings.log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def record(self, thread_id: str, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "thread_id": thread_id,
            "event_type": event_type,
            "payload": payload,
            "created_at": utc_now(),
        }
        self.database.add_audit_event(thread_id, event_type, payload)
        path = self.log_dir / f"{thread_id}.jsonl"
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")

