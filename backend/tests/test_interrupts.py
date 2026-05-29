import pytest

from security_agent.harness.interrupts import InterruptManager, ReviewStateError
from security_agent.harness.risk import RiskGate
from security_agent.schemas import ReviewStatus
from security_agent.stores.memory import InMemoryStores


def test_risk_gate_detects_high_risk_keywords() -> None:
    decision = RiskGate().evaluate_text("请下发规则并重启北门服务")

    assert decision.requires_review is True
    assert decision.risk_level == "high"
    assert {"重启", "下发规则"}.issubset(set(decision.matched_keywords))


@pytest.mark.asyncio
async def test_interrupt_manager_pause_prints_review_required(capsys) -> None:
    store = InMemoryStores()
    manager = InterruptManager(store, memory_store=store)

    review = await manager.pause_for_review(
        thread_id="thread_1",
        user_id="ops_001",
        proposed_action="重启北门流媒体服务",
    )

    output = capsys.readouterr().out
    memory = await store.load("thread_1")
    assert "[REVIEW_REQUIRED]" in output
    assert f"review_id={review.review_id}" in output
    assert review.status == ReviewStatus.PENDING
    assert memory.active_review_id == review.review_id


@pytest.mark.asyncio
async def test_interrupt_manager_resume_approved_review_completes_flow() -> None:
    store = InMemoryStores()
    manager = InterruptManager(store, message_store=store, memory_store=store)
    review = await manager.pause_for_review(
        thread_id="thread_1",
        user_id="ops_001",
        proposed_action="重启北门流媒体服务",
    )
    await store.decide_review(
        review_id=review.review_id,
        status=ReviewStatus.APPROVED,
        operator_id="lead_001",
    )

    result = await manager.resume_after_review(review.review_id)
    messages = await store.list_messages(thread_id="thread_1")
    memory = await store.load("thread_1")

    assert result.review.status == ReviewStatus.COMPLETED
    assert "审批已通过" in result.answer
    assert result.trace[0].type == "review_resumed"
    assert messages[-1].metadata["resumed"] is True
    assert memory.active_review_id is None


@pytest.mark.asyncio
async def test_interrupt_manager_resume_rejected_review_cancels_flow() -> None:
    store = InMemoryStores()
    manager = InterruptManager(store)
    review = await manager.pause_for_review(
        thread_id="thread_1",
        user_id="ops_001",
        proposed_action="删除设备配置",
    )
    await store.decide_review(
        review_id=review.review_id,
        status=ReviewStatus.REJECTED,
        operator_id="lead_001",
    )

    result = await manager.resume_after_review(review.review_id)

    assert result.review.status == ReviewStatus.CANCELLED
    assert "审批已拒绝" in result.answer


@pytest.mark.asyncio
async def test_interrupt_manager_requires_decision_before_resume() -> None:
    store = InMemoryStores()
    manager = InterruptManager(store)
    review = await manager.pause_for_review(
        thread_id="thread_1",
        user_id="ops_001",
        proposed_action="升级核心设备",
    )

    with pytest.raises(ReviewStateError):
        await manager.resume_after_review(review.review_id)
