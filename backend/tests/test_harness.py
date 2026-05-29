import pytest

from security_agent.harness.context import ContextAssembler
from security_agent.harness.intent import IntentRouter
from security_agent.harness.persistence import ResponsePersister
from security_agent.harness.pipeline import RequestPipeline
from security_agent.harness.runtime import AgentRuntime
from security_agent.harness.service import SecurityAgentService
from security_agent.schemas import ChatRequest, IntentLabel, RouteLabel
from security_agent.stores.memory import InMemoryStores


@pytest.mark.asyncio
async def test_intent_router_routes_device_alarm_knowledge_and_image() -> None:
    store = InMemoryStores()
    pipeline = RequestPipeline(store, store)
    router = IntentRouter()

    device_prepared = await pipeline.pre_process(
        ChatRequest(user_id="ops", message="北门摄像头离线")
    )
    alarm_prepared = await pipeline.pre_process(
        ChatRequest(user_id="ops", message="周界入侵告警是不是误报")
    )
    knowledge_prepared = await pipeline.pre_process(
        ChatRequest(user_id="ops", message="查询接入 SOP 文档")
    )
    image_prepared = await pipeline.pre_process(
        ChatRequest(user_id="ops", message="看图", image_url="https://example.com/a.jpg")
    )

    assert (await router.route(device_prepared)).intent == IntentLabel.DEVICE_TROUBLESHOOT
    assert (await router.route(alarm_prepared)).target_agent == "alarm-analyst"
    assert (await router.route(knowledge_prepared)).target_agent == "security-researcher"
    image_decision = await router.route(image_prepared)
    assert image_decision.intent == IntentLabel.OBJECT_ANALYSIS
    assert image_decision.route == RouteLabel.VISION


@pytest.mark.asyncio
async def test_security_agent_service_chat_persists_messages_and_memory() -> None:
    store = InMemoryStores()
    service = _build_service(store)

    response = await service.chat(
        ChatRequest(user_id="ops_001", message="北门摄像头离线了")
    )

    messages = await store.list_messages(thread_id=response.thread_id)
    memory = await store.load(response.thread_id)

    assert response.intent == IntentLabel.DEVICE_TROUBLESHOOT
    assert response.target_agent == "ops-troubleshooter"
    assert [message.role for message in messages] == ["user", "assistant"]
    assert memory.last_intent == IntentLabel.DEVICE_TROUBLESHOOT.value
    assert memory.active_agent == "ops-troubleshooter"
    assert [event.type for event in response.trace] == [
        "chat_received",
        "intent_routed",
        "context_built",
        "agent_runtime_stub",
        "assistant_response",
    ]


@pytest.mark.asyncio
async def test_security_agent_service_routes_image_to_object_analyst() -> None:
    service = _build_service(InMemoryStores())

    response = await service.chat(
        ChatRequest(
            user_id="ops_001",
            message="识别现场图片",
            image_url="https://example.com/a.jpg",
        )
    )

    assert response.route == RouteLabel.VISION
    assert response.intent == IntentLabel.OBJECT_ANALYSIS
    assert response.target_agent == "object-analyst"


def _build_service(store: InMemoryStores) -> SecurityAgentService:
    return SecurityAgentService(
        request_pipeline=RequestPipeline(store, store),
        intent_router=IntentRouter(),
        context_assembler=ContextAssembler(memory_store=store, message_store=store),
        agent_runtime=AgentRuntime(),
        response_persister=ResponsePersister(message_store=store, memory_store=store),
    )

