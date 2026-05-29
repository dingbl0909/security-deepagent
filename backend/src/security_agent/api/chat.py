from fastapi import APIRouter

from security_agent.harness.factory import get_security_agent_service
from security_agent.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    service = get_security_agent_service()
    return await service.chat(request)
