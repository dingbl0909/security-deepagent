from enum import StrEnum

from pydantic import BaseModel, Field


class DataPolicy(StrEnum):
    INTERNAL_ONLY = "internal_only"
    SANITIZED_ONLY = "sanitized_only"
    IMAGE_REVIEW_REQUIRED = "image_review_required"


class ModelProfile(BaseModel):
    name: str
    provider: str
    base_url: str
    model: str
    api_key_env: str
    timeout_seconds: int = 60
    data_policy: DataPolicy


class SubAgentSpec(BaseModel):
    name: str
    description: str
    model_profile: str
    tools: list[str] = Field(default_factory=list)


class AgentRuntimeConfig(BaseModel):
    model_profiles: dict[str, ModelProfile]
    agents: dict[str, SubAgentSpec]

