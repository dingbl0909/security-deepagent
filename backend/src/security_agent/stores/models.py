from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from security_agent.schemas import ReviewStatus, RiskLevel, TaskStatus


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def utc_now() -> datetime:
    return datetime.now(UTC)


class ThreadRecord(BaseModel):
    thread_id: str = Field(default_factory=lambda: new_id("thread"))
    user_id: str
    title: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MessageRecord(BaseModel):
    message_id: str = Field(default_factory=lambda: new_id("msg"))
    thread_id: str
    role: str
    content: str
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict = Field(default_factory=dict)


class TaskRecord(BaseModel):
    task_id: str = Field(default_factory=lambda: new_id("task"))
    thread_id: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    description: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ReviewRecord(BaseModel):
    review_id: str = Field(default_factory=lambda: new_id("review"))
    thread_id: str
    user_id: str
    risk_level: RiskLevel
    reason: str
    proposed_action: str
    status: ReviewStatus = ReviewStatus.PENDING
    checkpoint_ref: str | None = None
    resume_token_hash: str | None = None
    operator_id: str | None = None
    decided_at: datetime | None = None
    resumed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class HandoffRecord(BaseModel):
    handoff_id: str = Field(default_factory=lambda: new_id("handoff"))
    thread_id: str
    from_agent: str
    to_agent: str
    task_brief: str
    status: str = "created"
    allowed_tools: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class DeviceRecord(BaseModel):
    device_id: str
    name: str
    status: str
    location: str | None = None
    metadata: dict = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=utc_now)


class AlarmRecord(BaseModel):
    alarm_id: str
    device_id: str | None = None
    alarm_type: str
    severity: str
    status: str
    description: str | None = None
    occurred_at: datetime = Field(default_factory=utc_now)
    metadata: dict = Field(default_factory=dict)


class SessionMemory(BaseModel):
    thread_id: str
    recent_summary: str | None = None
    important_facts: list[str] = Field(default_factory=list)
    last_intent: str | None = None
    active_agent: str = "main"
    active_review_id: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class MilvusCollectionSpec(BaseModel):
    name: str
    description: str
    vector_field: str = "embedding"
    dim: int = 1024
