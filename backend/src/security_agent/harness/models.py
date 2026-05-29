from pydantic import BaseModel, Field

from security_agent.schemas import (
    ChatRequest,
    IntentLabel,
    RouteLabel,
    TraceEvent,
)
from security_agent.stores.models import MessageRecord, SessionMemory, ThreadRecord


class PreparedRequest(BaseModel):
    request: ChatRequest
    thread: ThreadRecord
    user_message: MessageRecord
    trace: list[TraceEvent] = Field(default_factory=list)


class RoutingDecision(BaseModel):
    intent: IntentLabel
    route: RouteLabel
    target_agent: str
    reason: str


class RuntimeContext(BaseModel):
    thread_id: str
    user_id: str
    session_memory: SessionMemory
    recent_messages: list[MessageRecord] = Field(default_factory=list)
    system_context_block: str = ""
    trace: list[TraceEvent] = Field(default_factory=list)


class AgentRunResult(BaseModel):
    answer: str
    trace: list[TraceEvent] = Field(default_factory=list)
    evidence: list = Field(default_factory=list)
    tasks: list = Field(default_factory=list)
    needs_review: bool = False
    interrupted: bool = False
    review_requests: list = Field(default_factory=list)
