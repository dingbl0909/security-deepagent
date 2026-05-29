import pytest

from security_agent.harness.context import ContextAssembler
from security_agent.harness.handoff import HandoffService
from security_agent.harness.intent import IntentRouter
from security_agent.harness.persistence import ResponsePersister
from security_agent.harness.pipeline import RequestPipeline
from security_agent.harness.runtime import AgentRuntime
from security_agent.harness.service import SecurityAgentService
from security_agent.schemas import ChatRequest, IntentLabel
from security_agent.stores.memory import InMemoryStores
from security_agent.stores.models import AlarmRecord, DeviceRecord
from security_agent.tools.builtin import build_default_tool_registry, build_local_tool_dependencies
from security_agent.tools.models import ToolName
from security_agent.agents.registry import SubAgentRegistry
from security_agent.agents.skills import load_skills


@pytest.mark.asyncio
async def test_tool_registry_whitelists_by_agent() -> None:
    store = InMemoryStores()
    registry = build_default_tool_registry(build_local_tool_dependencies(store))

    ops_tools = set(registry.names_for_agent("ops-troubleshooter"))
    object_tools = set(registry.names_for_agent("object-analyst"))

    assert ToolName.QUERY_DEVICE_STATUS.value in ops_tools
    assert ToolName.QUERY_ALARM_EVENTS.value not in ops_tools
    assert ToolName.ANALYZE_SECURITY_OBJECT.value in object_tools


@pytest.mark.asyncio
async def test_ops_runtime_runs_device_knowledge_and_tasks() -> None:
    store = InMemoryStores()
    store.devices["cam-north"] = DeviceRecord(
        device_id="cam-north",
        name="北门摄像头",
        status="offline",
        location="北门",
    )
    service = _build_service(store)

    response = await service.chat(
        ChatRequest(user_id="ops_001", message="北门摄像头离线了")
    )

    assert response.intent == IntentLabel.DEVICE_TROUBLESHOOT
    assert response.evidence
    assert len(response.tasks) == 3
    assert any(event.name == ToolName.QUERY_DEVICE_STATUS.value for event in response.trace)
    assert "已完成受控工具链路" in response.answer


@pytest.mark.asyncio
async def test_configured_runtime_emits_model_skill_and_handoff_trace() -> None:
    store = InMemoryStores()
    service = _build_configured_service(store)

    response = await service.chat(
        ChatRequest(user_id="ops_001", message="北门摄像头离线了")
    )

    assert any(
        event.type == "model_profile_selected"
        and event.metadata["model_profile"] == "private-main"
        for event in response.trace
    )
    assert any(
        event.type == "skills_selected"
        and event.metadata["skills"] == ["ops-troubleshooter"]
        for event in response.trace
    )
    assert any(event.type == "agent_handoff" for event in response.trace)
    handoffs = await store.list_handoffs(thread_id=response.thread_id)
    assert handoffs[0].to_agent == "ops-troubleshooter"
    assert handoffs[0].status == "completed"


@pytest.mark.asyncio
async def test_alarm_runtime_runs_alarm_query_and_tasks() -> None:
    store = InMemoryStores()
    store.alarms["alarm-1"] = AlarmRecord(
        alarm_id="alarm-1",
        device_id="cam-north",
        alarm_type="周界入侵",
        severity="high",
        status="open",
        description="夜间周界入侵告警",
    )
    service = _build_service(store)

    response = await service.chat(
        ChatRequest(user_id="ops_001", message="周界入侵告警是不是误报")
    )

    assert response.target_agent == "alarm-analyst"
    assert len(response.tasks) == 3
    assert any(event.name == ToolName.QUERY_ALARM_EVENTS.value for event in response.trace)


@pytest.mark.asyncio
async def test_high_risk_message_creates_review_and_interrupts() -> None:
    service = _build_service(InMemoryStores())

    response = await service.chat(
        ChatRequest(user_id="ops_001", message="重启北门流媒体服务")
    )

    assert response.needs_review is True
    assert response.interrupted is True
    assert response.review_requests
    assert response.review_requests[0].risk_level == "high"
    assert any(event.name == ToolName.REQUEST_HUMAN_REVIEW.value for event in response.trace)


@pytest.mark.asyncio
async def test_object_runtime_runs_vision_tool() -> None:
    service = _build_service(InMemoryStores())

    response = await service.chat(
        ChatRequest(
            user_id="ops_001",
            message="识别现场图片",
            image_url="https://example.com/snapshot.jpg",
        )
    )

    assert response.target_agent == "object-analyst"
    assert any(event.name == ToolName.ANALYZE_SECURITY_OBJECT.value for event in response.trace)
    assert "已接收现场图片输入" in response.answer


def _build_service(store: InMemoryStores) -> SecurityAgentService:
    registry = build_default_tool_registry(build_local_tool_dependencies(store))
    return SecurityAgentService(
        request_pipeline=RequestPipeline(store, store),
        intent_router=IntentRouter(),
        context_assembler=ContextAssembler(memory_store=store, message_store=store),
        agent_runtime=AgentRuntime(registry),
        response_persister=ResponsePersister(message_store=store, memory_store=store),
    )


def _build_configured_service(store: InMemoryStores) -> SecurityAgentService:
    registry = build_default_tool_registry(build_local_tool_dependencies(store))
    return SecurityAgentService(
        request_pipeline=RequestPipeline(store, store),
        intent_router=IntentRouter(),
        context_assembler=ContextAssembler(memory_store=store, message_store=store),
        agent_runtime=AgentRuntime(
            registry,
            subagent_registry=SubAgentRegistry.from_yaml("config/agents.yaml", registry),
            skills=load_skills("skills"),
            handoff_service=HandoffService(store),
        ),
        response_persister=ResponsePersister(message_store=store, memory_store=store),
    )
