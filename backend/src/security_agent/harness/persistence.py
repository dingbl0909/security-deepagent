from security_agent.harness.models import AgentRunResult, PreparedRequest, RoutingDecision, RuntimeContext
from security_agent.schemas import ChatResponse, TraceEvent
from security_agent.stores.protocols import MessageStore, ShortTermMemoryStore


class ResponsePersister:
    def __init__(
        self,
        *,
        message_store: MessageStore,
        memory_store: ShortTermMemoryStore,
    ) -> None:
        self._message_store = message_store
        self._memory_store = memory_store

    async def persist(
        self,
        *,
        prepared: PreparedRequest,
        routing: RoutingDecision,
        context: RuntimeContext,
        result: AgentRunResult,
    ) -> ChatResponse:
        assistant_message = await self._message_store.add_message(
            thread_id=prepared.thread.thread_id,
            role="assistant",
            content=result.answer,
            metadata={
                "intent": routing.intent.value,
                "target_agent": routing.target_agent,
                "needs_review": result.needs_review,
                "interrupted": result.interrupted,
            },
        )
        memory = context.session_memory
        memory.last_intent = routing.intent.value
        memory.active_agent = routing.target_agent
        memory.active_review_id = (
            result.review_requests[0].review_id
            if result.review_requests
            else memory.active_review_id
        )
        await self._memory_store.save(memory)

        trace = [
            *prepared.trace,
            *context.trace,
            *result.trace,
            TraceEvent(
                type="assistant_response",
                summary="Assistant response persisted.",
                agent="harness",
                metadata={"message_id": assistant_message.message_id},
            ),
        ]
        return ChatResponse(
            thread_id=prepared.thread.thread_id,
            message_id=assistant_message.message_id,
            answer=result.answer,
            intent=routing.intent,
            route=routing.route,
            target_agent=routing.target_agent,
            evidence=result.evidence,
            trace=trace,
            tasks=result.tasks,
            needs_review=result.needs_review,
            interrupted=result.interrupted,
            review_requests=result.review_requests,
        )
