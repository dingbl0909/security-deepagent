from fastapi import APIRouter

from security_agent.schemas import ThreadSummary
from security_agent.stores.factory import get_in_memory_stores

router = APIRouter(prefix="/threads", tags=["threads"])


@router.get("", response_model=list[ThreadSummary])
async def list_threads(user_id: str | None = None) -> list[ThreadSummary]:
    store = get_in_memory_stores()
    threads = await store.list_threads(user_id=user_id)
    return [
        ThreadSummary(
            thread_id=thread.thread_id,
            user_id=thread.user_id,
            title=thread.title,
            updated_at=thread.updated_at,
        )
        for thread in threads
    ]
