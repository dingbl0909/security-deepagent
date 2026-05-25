from __future__ import annotations

from fastapi import FastAPI, HTTPException

from security_agent.agent import build_agent_service
from security_agent.config import get_settings
from security_agent.schemas import (
    ChatRequest,
    ChatResponse,
    ContinueReviewRequest,
    ContinueReviewResponse,
    HealthResponse,
)


settings = get_settings()
service = build_agent_service(settings)

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name, llm_enabled=settings.llm_enabled)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return service.chat(
        message=request.message,
        thread_id=request.thread_id,
        user_id=request.user_id,
    )


@app.get("/threads/{thread_id}")
def get_thread(thread_id: str):
    thread = service.get_thread(thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="thread not found")
    return thread


@app.post("/review/continue", response_model=ContinueReviewResponse)
def continue_review(request: ContinueReviewRequest) -> ContinueReviewResponse:
    result = service.continue_review(
        review_id=request.review_id,
        approve=request.approve,
        operator_id=request.operator_id,
    )
    return ContinueReviewResponse(review_id=result["review_id"], status=result["status"])

