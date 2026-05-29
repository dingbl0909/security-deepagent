import pytest

from security_agent.harness.handoff import HandoffPacket, HandoffService
from security_agent.stores.memory import InMemoryStores


@pytest.mark.asyncio
async def test_handoff_service_persists_and_completes_record() -> None:
    store = InMemoryStores()
    service = HandoffService(store)

    record, trace = await service.create(
        HandoffPacket(
            thread_id="thread_1",
            to_agent="ops-troubleshooter",
            task_brief="北门摄像头离线",
            allowed_tools=["query_device_status"],
        )
    )
    await service.complete(record.handoff_id)

    handoffs = await store.list_handoffs(thread_id="thread_1")
    assert len(handoffs) == 1
    assert handoffs[0].status == "completed"
    assert handoffs[0].allowed_tools == ["query_device_status"]
    assert trace.type == "agent_handoff"
    assert trace.metadata["handoff_id"] == record.handoff_id
