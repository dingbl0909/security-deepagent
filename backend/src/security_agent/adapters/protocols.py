from typing import Protocol

from pydantic import BaseModel, Field


class KnowledgeHit(BaseModel):
    title: str
    source: str
    snippet: str
    score: float = 0.0
    metadata: dict = Field(default_factory=dict)


class VisionAnalysis(BaseModel):
    scene_summary: str
    objects: list[str] = Field(default_factory=list)
    risk_level: str = "low"
    recommendation: str


class KnowledgeRetriever(Protocol):
    async def search(self, query: str, *, top_k: int = 5) -> list[KnowledgeHit]: ...


class VisionGateway(Protocol):
    async def analyze(
        self,
        *,
        image_path: str | None = None,
        image_url: str | None = None,
        image_base64: str | None = None,
        prompt: str,
    ) -> VisionAnalysis: ...

