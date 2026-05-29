from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from security_agent.schemas import RiskLevel


class ToolName(StrEnum):
    SEARCH_SECURITY_KNOWLEDGE = "search_security_knowledge"
    QUERY_DEVICE_STATUS = "query_device_status"
    QUERY_ALARM_EVENTS = "query_alarm_events"
    CREATE_SECURITY_TODOS = "create_security_todos"
    UPDATE_TASK_STATUS = "update_task_status"
    REQUEST_HUMAN_REVIEW = "request_human_review"
    ANALYZE_SECURITY_OBJECT = "analyze_security_object"
    ARCHIVE_EPISODE = "archive_episode"


class ToolResult(BaseModel):
    name: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    review_requests: list[dict[str, Any]] = Field(default_factory=list)


class ToolContext(BaseModel):
    thread_id: str
    user_id: str
    message: str
    image_path: str | None = None
    image_url: str | None = None
    image_base64: str | None = None


ToolHandler = Callable[[ToolContext], Awaitable[ToolResult]]


class ToolSpec(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    risk_level: RiskLevel
    requires_review: bool = False
    allowed_agents: set[str] = Field(default_factory=set)
    handler: ToolHandler = Field(exclude=True)
