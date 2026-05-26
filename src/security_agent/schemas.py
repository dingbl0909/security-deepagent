from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    thread_id: str = Field(default="default-thread")
    user_id: str = Field(default="ops_001")
    image_path: str | None = None
    image_url: str | None = None
    image_base64: str | None = None


class Evidence(BaseModel):
    title: str
    source: str
    snippet: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    thread_id: str
    user_id: str
    react_trace: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    needs_review: bool = False
    review_id: int | None = None
    risk_level: str = "low"
    review_reason: str | None = None
    proposed_action: str | None = None
    risk_keywords: list[str] = Field(default_factory=list)
    intent: str | None = None


class ContinueReviewRequest(BaseModel):
    review_id: int
    approve: bool
    operator_id: str = "ops_001"


class ContinueReviewResponse(BaseModel):
    review_id: int
    status: str


class HealthResponse(BaseModel):
    status: str
    app: str
    llm_enabled: bool
    vision_enabled: bool = False

