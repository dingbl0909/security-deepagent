from typing import Protocol

from security_agent.schemas import ReviewStatus, TaskStatus
from security_agent.stores.models import (
    AlarmRecord,
    DeviceRecord,
    MessageRecord,
    ReviewRecord,
    SessionMemory,
    TaskRecord,
    ThreadRecord,
    HandoffRecord,
)


class ThreadStore(Protocol):
    async def upsert_thread(
        self,
        *,
        user_id: str,
        thread_id: str | None = None,
        title: str | None = None,
    ) -> ThreadRecord: ...

    async def get_thread(self, thread_id: str) -> ThreadRecord | None: ...

    async def list_threads(self, *, user_id: str | None = None) -> list[ThreadRecord]: ...


class MessageStore(Protocol):
    async def add_message(
        self,
        *,
        thread_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> MessageRecord: ...

    async def list_messages(self, *, thread_id: str) -> list[MessageRecord]: ...


class TaskStore(Protocol):
    async def create_task(
        self,
        *,
        thread_id: str,
        title: str,
        description: str | None = None,
    ) -> TaskRecord: ...

    async def update_task_status(
        self,
        *,
        task_id: str,
        status: TaskStatus,
    ) -> TaskRecord: ...

    async def list_tasks(self, *, thread_id: str) -> list[TaskRecord]: ...


class ReviewStore(Protocol):
    async def create_review(
        self,
        *,
        thread_id: str,
        user_id: str,
        risk_level: str,
        reason: str,
        proposed_action: str,
        checkpoint_ref: str | None = None,
        resume_token_hash: str | None = None,
    ) -> ReviewRecord: ...

    async def decide_review(
        self,
        *,
        review_id: str,
        status: ReviewStatus,
        operator_id: str,
    ) -> ReviewRecord: ...

    async def mark_resumed(self, *, review_id: str) -> ReviewRecord: ...

    async def list_reviews(self, *, status: ReviewStatus | None = None) -> list[ReviewRecord]: ...

    async def get_review(self, review_id: str) -> ReviewRecord | None: ...

    async def finish_review(
        self,
        *,
        review_id: str,
        status: ReviewStatus,
    ) -> ReviewRecord: ...


class HandoffStore(Protocol):
    async def create_handoff(
        self,
        *,
        thread_id: str,
        from_agent: str,
        to_agent: str,
        task_brief: str,
        allowed_tools: list[str] | None = None,
    ) -> HandoffRecord: ...

    async def complete_handoff(
        self,
        *,
        handoff_id: str,
        status: str = "completed",
    ) -> HandoffRecord: ...

    async def list_handoffs(self, *, thread_id: str | None = None) -> list[HandoffRecord]: ...


class DeviceStore(Protocol):
    async def list_devices(self) -> list[DeviceRecord]: ...

    async def get_device(self, device_id: str) -> DeviceRecord | None: ...


class AlarmStore(Protocol):
    async def list_alarms(self) -> list[AlarmRecord]: ...


class ShortTermMemoryStore(Protocol):
    async def load(self, thread_id: str) -> SessionMemory: ...

    async def save(self, memory: SessionMemory) -> None: ...

    async def append_fact(self, thread_id: str, fact: str) -> SessionMemory: ...
