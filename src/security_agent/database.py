from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from security_agent.config import Settings, get_settings


TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9_./:-]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, db_path: Path | None = None):
        settings = get_settings()
        self.db_path = db_path or settings.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    location TEXT NOT NULL,
                    status TEXT NOT NULL,
                    ip TEXT,
                    last_seen TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS alarms (
                    id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    alarm_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS threads (
                    thread_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    summary TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'medium',
                    details TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS review_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    proposed_action TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def seed_defaults(self) -> None:
        now = utc_now()
        devices = [
            {
                "id": "cam-north-gate",
                "name": "仓库北门摄像头",
                "location": "一号仓库北门",
                "status": "offline",
                "ip": "192.168.10.21",
                "last_seen": "2026-05-25T06:40:00+00:00",
                "metadata_json": {"vendor": "YituCam", "stream": "rtsp"},
            },
            {
                "id": "cam-lobby-01",
                "name": "大厅入口摄像头",
                "location": "办公楼大厅",
                "status": "online",
                "ip": "192.168.10.31",
                "last_seen": now,
                "metadata_json": {"vendor": "YituCam", "stream": "gb28181"},
            },
        ]
        alarms = [
            {
                "id": "alarm-1001",
                "device_id": "cam-north-gate",
                "alarm_type": "device_offline",
                "severity": "high",
                "status": "open",
                "occurred_at": "2026-05-25T06:45:00+00:00",
                "summary": "仓库北门摄像头连续 5 分钟心跳丢失，视频流不可用。",
                "metadata_json": {"rule": "offline_5m", "project": "warehouse"},
            },
            {
                "id": "alarm-1002",
                "device_id": "cam-lobby-01",
                "alarm_type": "false_positive",
                "severity": "medium",
                "status": "closed",
                "occurred_at": "2026-05-24T09:10:00+00:00",
                "summary": "大厅入口人员聚集告警误报，原因是反光区域触发。",
                "metadata_json": {"rule": "crowd_detect", "project": "office"},
            },
        ]
        with self.connect() as conn:
            for device in devices:
                self._upsert(conn, "devices", device)
            for alarm in alarms:
                self._upsert(conn, "alarms", alarm)

    def upsert_thread(self, thread_id: str, user_id: str, title: str | None = None) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO threads(thread_id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(thread_id) DO UPDATE SET
                    user_id=excluded.user_id,
                    title=COALESCE(excluded.title, threads.title),
                    updated_at=excluded.updated_at
                """,
                (thread_id, user_id, title, now, now),
            )

    def add_message(self, thread_id: str, role: str, content: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO messages(thread_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (thread_id, role, content, utc_now()),
            )

    def update_thread_summary(self, thread_id: str, summary: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE threads SET summary=?, updated_at=? WHERE thread_id=?",
                (summary, utc_now(), thread_id),
            )

    def get_thread(self, thread_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            thread = conn.execute(
                "SELECT * FROM threads WHERE thread_id=?",
                (thread_id,),
            ).fetchone()
            if thread is None:
                return None
            messages = conn.execute(
                "SELECT role, content, created_at FROM messages WHERE thread_id=? ORDER BY id ASC",
                (thread_id,),
            ).fetchall()
            tasks = conn.execute(
                "SELECT id, title, status, priority, details, created_at, updated_at FROM tasks WHERE thread_id=?",
                (thread_id,),
            ).fetchall()
            reviews = conn.execute(
                "SELECT id, risk_level, reason, proposed_action, status, created_at, updated_at FROM review_requests WHERE thread_id=?",
                (thread_id,),
            ).fetchall()
        return {
            "thread": dict(thread),
            "messages": [dict(row) for row in messages],
            "tasks": [dict(row) for row in tasks],
            "reviews": [dict(row) for row in reviews],
        }

    def list_threads(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    t.thread_id,
                    t.user_id,
                    t.title,
                    t.summary,
                    t.created_at,
                    t.updated_at,
                    COUNT(DISTINCT m.id) AS message_count,
                    COUNT(DISTINCT CASE WHEN r.status = 'pending' THEN r.id END) AS pending_review_count
                FROM threads t
                LEFT JOIN messages m ON m.thread_id = t.thread_id
                LEFT JOIN review_requests r ON r.thread_id = t.thread_id
                GROUP BY t.thread_id
                ORDER BY t.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_reviews(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as conn:
            if status:
                rows = conn.execute(
                    """
                    SELECT id, thread_id, risk_level, reason, proposed_action, status, created_at, updated_at
                    FROM review_requests
                    WHERE status = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, thread_id, risk_level, reason, proposed_action, status, created_at, updated_at
                    FROM review_requests
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [dict(row) for row in rows]

    def list_devices(self, query: str = "") -> list[dict[str, Any]]:
        if query.strip():
            return self.search_devices(query)
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM devices ORDER BY name").fetchall()
        return [self._decode_json(row) for row in rows]

    def list_alarms(self, query: str = "") -> list[dict[str, Any]]:
        if query.strip():
            return self.search_alarms(query)
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM alarms ORDER BY occurred_at DESC").fetchall()
        return [self._decode_json(row) for row in rows]

    def search_devices(self, query: str) -> list[dict[str, Any]]:
        terms = self._query_terms(query)
        with self.connect() as conn:
            rows = self._search_rows(
                conn=conn,
                table="devices",
                columns=["id", "name", "location", "status", "ip"],
                terms=terms,
                order_by="name",
            )
        return [self._decode_json(row) for row in rows]

    def search_alarms(self, query: str) -> list[dict[str, Any]]:
        terms = self._query_terms(query)
        with self.connect() as conn:
            rows = self._search_rows(
                conn=conn,
                table="alarms",
                columns=["id", "device_id", "alarm_type", "severity", "status", "summary"],
                terms=terms,
                order_by="occurred_at DESC",
            )
        return [self._decode_json(row) for row in rows]

    def upsert_task(self, task: dict[str, Any]) -> None:
        now = utc_now()
        payload = {
            "id": task["id"],
            "thread_id": task["thread_id"],
            "title": task["title"],
            "status": task.get("status", "pending"),
            "priority": task.get("priority", "medium"),
            "details": task.get("details", ""),
            "created_at": task.get("created_at", now),
            "updated_at": now,
        }
        with self.connect() as conn:
            self._upsert(conn, "tasks", payload)

    def add_audit_event(self, thread_id: str, event_type: str, payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO audit_events(thread_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
                (thread_id, event_type, json.dumps(payload, ensure_ascii=False), utc_now()),
            )

    def add_review_request(
        self,
        thread_id: str,
        risk_level: str,
        reason: str,
        proposed_action: str,
    ) -> int:
        now = utc_now()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO review_requests(thread_id, risk_level, reason, proposed_action, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """,
                (thread_id, risk_level, reason, proposed_action, now, now),
            )
            return int(cursor.lastrowid)

    def complete_review(self, review_id: int, approved: bool) -> None:
        status = "approved" if approved else "rejected"
        with self.connect() as conn:
            conn.execute(
                "UPDATE review_requests SET status=?, updated_at=? WHERE id=?",
                (status, utc_now(), review_id),
            )

    @staticmethod
    def _upsert(conn: sqlite3.Connection, table: str, data: dict[str, Any]) -> None:
        columns = list(data)
        values = [json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value for value in data.values()]
        placeholders = ", ".join(["?"] * len(columns))
        update_columns = [column for column in columns if column != "id"]
        updates = ", ".join([f"{column}=excluded.{column}" for column in update_columns])
        sql = f"""
            INSERT INTO {table}({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(id) DO UPDATE SET {updates}
        """
        conn.execute(sql, values)

    @staticmethod
    def _decode_json(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        for key in ["metadata_json", "payload_json"]:
            if key in data and isinstance(data[key], str):
                try:
                    data[key] = json.loads(data[key])
                except json.JSONDecodeError:
                    pass
        return data

    @staticmethod
    def _query_terms(query: str) -> list[str]:
        terms = [query.strip()] if query.strip() else []
        terms.extend(match.group(0) for match in TOKEN_RE.finditer(query))
        terms.extend(char for char in query if "\u4e00" <= char <= "\u9fff")
        deduped: list[str] = []
        for term in terms:
            if term and term not in deduped:
                deduped.append(term)
        return deduped

    @staticmethod
    def _search_rows(
        conn: sqlite3.Connection,
        table: str,
        columns: list[str],
        terms: list[str],
        order_by: str,
    ) -> list[sqlite3.Row]:
        if not terms:
            return []
        clauses = []
        params = []
        for term in terms:
            for column in columns:
                clauses.append(f"{column} LIKE ?")
                params.append(f"%{term}%")
        sql = f"""
            SELECT * FROM {table}
            WHERE {" OR ".join(clauses)}
            ORDER BY {order_by}
        """
        return conn.execute(sql, params).fetchall()


def init_database(settings: Settings | None = None) -> Database:
    database = Database((settings or get_settings()).db_path)
    database.init_schema()
    database.seed_defaults()
    return database

