from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha1

from security_agent.database import Database, utc_now


@dataclass(frozen=True)
class SecurityTask:
    id: str
    thread_id: str
    title: str
    status: str = "pending"
    priority: str = "medium"
    details: str = ""
    created_at: str = ""

    def to_record(self) -> dict[str, str]:
        record = asdict(self)
        record["created_at"] = self.created_at or utc_now()
        return record


DEFAULT_TROUBLESHOOTING_STEPS = [
    "确认设备供电、网线、交换机端口和指示灯状态。",
    "确认设备 IP、网关、DNS、NTP 时间和平台接入参数。",
    "检查平台侧心跳、GB28181/RTSP 注册状态和最近错误日志。",
    "检索相关 SOP，整理可能原因和验证命令。",
    "涉及重启服务、修改配置或升级规则前，提交人工确认。",
]


class TaskService:
    def __init__(self, database: Database | None = None):
        self.database = database or Database()

    def create_todos(self, thread_id: str, task: str) -> list[dict[str, str]]:
        tasks = []
        for index, step in enumerate(DEFAULT_TROUBLESHOOTING_STEPS, start=1):
            task_id = self._task_id(thread_id, step)
            security_task = SecurityTask(
                id=task_id,
                thread_id=thread_id,
                title=f"{index}. {step}",
                status="pending",
                priority="high" if index in {1, 5} else "medium",
                details=f"来源任务：{task}",
            )
            record = security_task.to_record()
            self.database.upsert_task(record)
            tasks.append(record)
        return tasks

    @staticmethod
    def _task_id(thread_id: str, title: str) -> str:
        digest = sha1(f"{thread_id}:{title}".encode("utf-8")).hexdigest()[:12]
        return f"task-{digest}"

