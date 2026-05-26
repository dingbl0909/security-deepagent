from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        llm_enabled=settings.llm_enabled,
        vision_enabled=settings.vision_enabled,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return service.chat(
        message=request.message,
        thread_id=request.thread_id,
        user_id=request.user_id,
        image_path=request.image_path,
        image_url=request.image_url,
        image_base64=request.image_base64,
    )


@app.get("/threads/{thread_id}")
def get_thread(thread_id: str):
    thread = service.get_thread(thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="thread not found")
    return thread


@app.get("/threads")
def list_threads(limit: int = 50):
    return {"threads": service.list_threads(limit=limit)}


@app.get("/reviews")
def list_reviews(status: str | None = "pending", limit: int = 50):
    return {"reviews": service.list_reviews(status=status, limit=limit)}


@app.get("/devices")
def list_devices(query: str = ""):
    return {"devices": service.list_devices(query=query)}


@app.get("/alarms")
def list_alarms(query: str = ""):
    return {"alarms": service.list_alarms(query=query)}


@app.post("/review/continue", response_model=ContinueReviewResponse)
def continue_review(request: ContinueReviewRequest) -> ContinueReviewResponse:
    result = service.continue_review(
        review_id=request.review_id,
        approve=request.approve,
        operator_id=request.operator_id,
    )
    return ContinueReviewResponse(review_id=result["review_id"], status=result["status"])

