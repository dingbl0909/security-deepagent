from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class IntentLabel(StrEnum):
    SECURITY_RESEARCH = "security_research"
    DEVICE_TROUBLESHOOT = "device_troubleshoot"
    ALARM_ANALYSIS = "alarm_analysis"
    OBJECT_ANALYSIS = "object_analysis"
    GENERAL = "general"


class RouteLabel(StrEnum):
    AGENT = "agent"
    VISION = "vision"
    REVIEW_RESUME = "review_resume"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESUMED = "resumed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    thread_id: str | None = None
    image_path: str | None = None
    image_url: str | None = None
    image_base64: str | None = None

    @model_validator(mode="after")
    def validate_image_inputs(self) -> "ChatRequest":
        image_inputs = [
            value
            for value in (self.image_path, self.image_url, self.image_base64)
            if value
        ]
        if len(image_inputs) > 1:
            raise ValueError(
                "only one of image_path, image_url, or image_base64 may be provided"
            )
        return self


class EvidenceItem(BaseModel):
    title: str
    source: str
    snippet: str
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceEvent(BaseModel):
    type: str
    summary: str
    agent: str | None = None
    name: str | None = None
    status: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskItem(BaseModel):
    task_id: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    description: str | None = None


class ReviewRequestItem(BaseModel):
    review_id: str
    risk_level: RiskLevel
    reason: str
    proposed_action: str
    status: ReviewStatus = ReviewStatus.PENDING
    resume_required: bool = True


class ReviewResumeResponse(BaseModel):
    review: ReviewRequestItem
    thread_id: str
    answer: str
    resumed: bool = True
    trace: list[TraceEvent] = Field(default_factory=list)


class ChatResponse(BaseModel):
    thread_id: str
    message_id: str
    answer: str
    intent: IntentLabel
    route: RouteLabel
    target_agent: str | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    trace: list[TraceEvent] = Field(default_factory=list)
    tasks: list[TaskItem] = Field(default_factory=list)
    needs_review: bool = False
    interrupted: bool = False
    review_requests: list[ReviewRequestItem] = Field(default_factory=list)


class ThreadSummary(BaseModel):
    thread_id: str
    user_id: str
    title: str | None = None
    updated_at: datetime


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "security-deepagent"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DependencyStatus(BaseModel):
    name: str
    configured: bool
    status: str
    detail: str | None = None


class ReadyResponse(BaseModel):
    status: str
    strict: bool
    dependencies: list[DependencyStatus]


class ErrorDetail(BaseModel):
    code: str
    message: str
    trace_id: str = Field(default_factory=lambda: uuid4().hex)


class ErrorResponse(BaseModel):
    error: ErrorDetail
