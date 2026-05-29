from typing import Protocol

from pydantic import BaseModel, Field

from security_agent.schemas import TraceEvent
from security_agent.stores.models import HandoffRecord


class HandoffPacket(BaseModel):
    thread_id: str
    from_agent: str = "main-agent"
    to_agent: str
    task_brief: str
    context_summary: str = ""
    allowed_tools: list[str] = Field(default_factory=list)


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

    async def complete_handoff(self, *, handoff_id: str, status: str = "completed") -> HandoffRecord: ...


class HandoffService:
    def __init__(self, store: HandoffStore | None = None) -> None:
        self._store = store

    async def create(
        self,
        packet: HandoffPacket,
    ) -> tuple[HandoffRecord | None, TraceEvent]:
        record = None
        if self._store:
            record = await self._store.create_handoff(
                thread_id=packet.thread_id,
                from_agent=packet.from_agent,
                to_agent=packet.to_agent,
                task_brief=packet.task_brief,
                allowed_tools=packet.allowed_tools,
            )
        return record, TraceEvent(
            type="agent_handoff",
            summary=f"{packet.from_agent} handed off task to {packet.to_agent}.",
            agent=packet.from_agent,
            name=packet.to_agent,
            status="created",
            metadata={
                "handoff_id": record.handoff_id if record else None,
                "from_agent": packet.from_agent,
                "to_agent": packet.to_agent,
                "allowed_tools": packet.allowed_tools,
                "context_summary": packet.context_summary,
            },
        )

    async def complete(self, handoff_id: str | None, *, status: str = "completed") -> None:
        if self._store and handoff_id:
            await self._store.complete_handoff(handoff_id=handoff_id, status=status)
