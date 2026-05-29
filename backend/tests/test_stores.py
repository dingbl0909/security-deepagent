import pytest

from security_agent.schemas import ReviewStatus, TaskStatus
from security_agent.stores.memory import InMemoryStores
from security_agent.stores.milvus.collections import (
    DEFAULT_COLLECTIONS,
    MilvusDependencyError,
    ensure_collections,
)
from security_agent.stores.postgres.schema import load_schema_sql
from security_agent.stores.redis.session import RedisSessionStore


def test_postgres_schema_contains_core_tables() -> None:
    sql = load_schema_sql()
    for table in [
        "threads",
        "messages",
        "tasks",
        "review_requests",
        "devices",
        "alarms",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql


@pytest.mark.asyncio
async def test_in_memory_thread_message_task_review_flow() -> None:
    store = InMemoryStores()
    thread = await store.upsert_thread(user_id="ops_001", title="北门摄像头")
    message = await store.add_message(
        thread_id=thread.thread_id,
        role="user",
        content="北门摄像头离线",
    )
    task = await store.create_task(thread_id=thread.thread_id, title="检查供电")
    updated = await store.update_task_status(
        task_id=task.task_id,
        status=TaskStatus.IN_PROGRESS,
    )
    review = await store.create_review(
        thread_id=thread.thread_id,
        user_id="ops_001",
        risk_level="high",
        reason="用户请求重启服务",
        proposed_action="重启北门流媒体服务",
        checkpoint_ref="checkpoint_1",
        resume_token_hash="token_hash",
    )
    decided = await store.decide_review(
        review_id=review.review_id,
        status=ReviewStatus.APPROVED,
        operator_id="lead_001",
    )
    resumed = await store.mark_resumed(review_id=review.review_id)
    finished = await store.finish_review(
        review_id=review.review_id,
        status=ReviewStatus.COMPLETED,
    )

    assert message.thread_id == thread.thread_id
    assert updated.status == TaskStatus.IN_PROGRESS
    assert decided.operator_id == "lead_001"
    assert resumed.resumed_at is not None
    assert finished.status == ReviewStatus.COMPLETED
    assert len(await store.list_messages(thread_id=thread.thread_id)) == 1
    assert len(await store.list_tasks(thread_id=thread.thread_id)) == 1
    assert len(await store.list_reviews(status=ReviewStatus.COMPLETED)) == 1


@pytest.mark.asyncio
async def test_in_memory_session_memory() -> None:
    store = InMemoryStores()
    memory = await store.append_fact("thread_1", "北门摄像头离线")
    assert memory.important_facts == ["北门摄像头离线"]
    loaded = await store.load("thread_1")
    assert loaded.important_facts == ["北门摄像头离线"]


@pytest.mark.asyncio
async def test_redis_session_store_with_fake_redis() -> None:
    redis = FakeRedis()
    store = RedisSessionStore(redis, ttl_seconds=60)
    memory = await store.append_fact("thread_1", "告警误报")
    loaded = await store.load("thread_1")

    assert memory.important_facts == ["告警误报"]
    assert loaded.important_facts == ["告警误报"]
    assert redis.expirations["agent:session:thread_1"] == 60


def test_milvus_collection_specs() -> None:
    assert [item.name for item in DEFAULT_COLLECTIONS] == [
        "security_knowledge",
        "agent_episodic_memory",
    ]


def test_milvus_missing_dependency_has_clear_error() -> None:
    with pytest.raises(MilvusDependencyError):
        ensure_collections("http://localhost:19530")


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.expirations: dict[str, int] = {}

    async def hgetall(self, key: str) -> dict[str, str]:
        return self.hashes.get(key, {})

    async def hset(self, key: str, mapping: dict[str, str]) -> None:
        self.hashes[key] = mapping

    async def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds
