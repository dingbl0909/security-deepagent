from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the backend service.

    The first implementation stage validates configuration shape only. Concrete
    database, Redis, Milvus, and model clients are introduced in later tasks.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Security DeepAgent"
    environment: Literal["local", "dev", "test", "prod"] = "local"
    log_level: str = "INFO"

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    milvus_uri: str | None = Field(default=None, alias="MILVUS_URI")

    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    security_agent_model: str | None = Field(
        default=None,
        alias="SECURITY_AGENT_MODEL",
    )

    readiness_strict: bool = Field(
        default=False,
        alias="SECURITY_AGENT_READINESS_STRICT",
        description="When true, /ready fails if required external URLs are absent.",
    )

    subagents_config: str = Field(
        default="config/agents.yaml",
        alias="SECURITY_AGENT_SUBAGENTS_CONFIG",
    )
    skills_dir: str = Field(default="skills", alias="SECURITY_AGENT_SKILLS_DIR")

    def missing_required_dependency_names(self) -> list[str]:
        required = {
            "DATABASE_URL": self.database_url,
            "REDIS_URL": self.redis_url,
            "MILVUS_URI": self.milvus_uri,
            "OPENAI_BASE_URL": self.openai_base_url,
            "OPENAI_API_KEY": self.openai_api_key,
            "SECURITY_AGENT_MODEL": self.security_agent_model,
        }
        return [name for name, value in required.items() if not value]


@lru_cache
def get_settings() -> Settings:
    return Settings()
