import json

from redis.asyncio import Redis

from security_agent.stores.models import SessionMemory, utc_now


class RedisSessionStore:
    def __init__(
        self,
        redis: Redis,
        *,
        key_prefix: str = "agent:session:",
        ttl_seconds: int = 14 * 24 * 60 * 60,
    ) -> None:
        self._redis = redis
        self._key_prefix = key_prefix
        self._ttl_seconds = ttl_seconds

    async def load(self, thread_id: str) -> SessionMemory:
        raw = await self._redis.hgetall(self._key(thread_id))
        if not raw:
            return SessionMemory(thread_id=thread_id)
        data = _decode_hash(raw)
        return SessionMemory(
            thread_id=thread_id,
            recent_summary=data.get("recent_summary") or None,
            important_facts=json.loads(data.get("important_facts") or "[]"),
            last_intent=data.get("last_intent") or None,
            active_agent=data.get("active_agent") or "main",
            active_review_id=data.get("active_review_id") or None,
        )

    async def save(self, memory: SessionMemory) -> None:
        memory.updated_at = utc_now()
        await self._redis.hset(
            self._key(memory.thread_id),
            mapping={
                "recent_summary": memory.recent_summary or "",
                "important_facts": json.dumps(memory.important_facts, ensure_ascii=False),
                "last_intent": memory.last_intent or "",
                "active_agent": memory.active_agent,
                "active_review_id": memory.active_review_id or "",
                "updated_at": memory.updated_at.isoformat(),
            },
        )
        await self._redis.expire(self._key(memory.thread_id), self._ttl_seconds)

    async def append_fact(self, thread_id: str, fact: str) -> SessionMemory:
        memory = await self.load(thread_id)
        memory.important_facts.append(fact)
        await self.save(memory)
        return memory

    def _key(self, thread_id: str) -> str:
        return f"{self._key_prefix}{thread_id}"


def _decode_hash(raw: dict) -> dict[str, str]:
    decoded: dict[str, str] = {}
    for key, value in raw.items():
        text_key = key.decode() if isinstance(key, bytes) else str(key)
        text_value = value.decode() if isinstance(value, bytes) else str(value)
        decoded[text_key] = text_value
    return decoded

