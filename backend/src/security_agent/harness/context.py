from security_agent.harness.models import PreparedRequest, RoutingDecision, RuntimeContext
from security_agent.schemas import TraceEvent
from security_agent.stores.protocols import MessageStore, ShortTermMemoryStore


class ContextAssembler:
    def __init__(
        self,
        *,
        memory_store: ShortTermMemoryStore,
        message_store: MessageStore,
    ) -> None:
        self._memory_store = memory_store
        self._message_store = message_store

    async def build(
        self,
        prepared: PreparedRequest,
        routing: RoutingDecision,
    ) -> RuntimeContext:
        memory = await self._memory_store.load(prepared.thread.thread_id)
        recent_messages = await self._message_store.list_messages(
            thread_id=prepared.thread.thread_id,
        )
        system_context_block = (
            "## 会话上下文\n"
            f"- 当前意图：{routing.intent.value}\n"
            f"- 当前负责 Agent：{routing.target_agent}\n"
            f"- 会话摘要：{memory.recent_summary or '暂无'}\n"
        )
        trace = [
            TraceEvent(
                type="context_built",
                summary="Runtime context assembled.",
                agent="harness",
                metadata={
                    "thread_id": prepared.thread.thread_id,
                    "message_count": len(recent_messages),
                    "facts_count": len(memory.important_facts),
                },
            )
        ]
        return RuntimeContext(
            thread_id=prepared.thread.thread_id,
            user_id=prepared.request.user_id,
            session_memory=memory,
            recent_messages=recent_messages,
            system_context_block=system_context_block,
            trace=trace,
        )

