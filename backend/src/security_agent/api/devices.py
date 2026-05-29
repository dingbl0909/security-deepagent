from fastapi import APIRouter
from fastapi import HTTPException, status

from security_agent.stores.factory import get_in_memory_stores

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("")
async def list_devices() -> list[dict[str, str]]:
    store = get_in_memory_stores()
    devices = await store.list_devices()
    return [device.model_dump(mode="json") for device in devices]


@router.get("/{device_id}")
async def get_device(device_id: str) -> dict:
    store = get_in_memory_stores()
    device = await store.get_device(device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device not found")
    return device.model_dump(mode="json")
