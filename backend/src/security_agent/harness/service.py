from security_agent.harness.context import ContextAssembler
from security_agent.harness.intent import IntentRouter
from security_agent.harness.persistence import ResponsePersister
from security_agent.harness.pipeline import RequestPipeline
from security_agent.harness.runtime import AgentRuntime
from security_agent.schemas import ChatRequest, ChatResponse


class SecurityAgentService:
    def __init__(
        self,
        *,
        request_pipeline: RequestPipeline,
        intent_router: IntentRouter,
        context_assembler: ContextAssembler,
        agent_runtime: AgentRuntime,
        response_persister: ResponsePersister,
    ) -> None:
        self._request_pipeline = request_pipeline
        self._intent_router = intent_router
        self._context_assembler = context_assembler
        self._agent_runtime = agent_runtime
        self._response_persister = response_persister

    async def chat(self, request: ChatRequest) -> ChatResponse:
        prepared = await self._request_pipeline.pre_process(request)
        routing = await self._intent_router.route(prepared)
        context = await self._context_assembler.build(prepared, routing)
        result = await self._agent_runtime.invoke(routing=routing, context=context)
        return await self._response_persister.persist(
            prepared=prepared,
            routing=routing,
            context=context,
            result=result,
        )

