from fastapi import APIRouter, Response, status

from security_agent.config import get_settings
from security_agent.schemas import HealthResponse, ReadyResponse
from security_agent.services.readiness import build_readiness

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.get("/ready", response_model=ReadyResponse)
async def ready(response: Response) -> ReadyResponse:
    settings = get_settings()
    readiness = build_readiness(settings)
    if readiness.status != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return readiness
