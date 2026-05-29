from fastapi import APIRouter
from security_agent.stores.factory import get_in_memory_stores

router = APIRouter(prefix="/alarms", tags=["alarms"])


@router.get("")
async def list_alarms() -> list[dict[str, str]]:
    store = get_in_memory_stores()
    alarms = await store.list_alarms()
    return [alarm.model_dump(mode="json") for alarm in alarms]
