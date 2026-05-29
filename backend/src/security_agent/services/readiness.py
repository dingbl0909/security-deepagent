from collections.abc import Iterable

from security_agent.config import Settings
from security_agent.schemas import DependencyStatus, ReadyResponse


def build_readiness(settings: Settings) -> ReadyResponse:
    dependencies = list(_dependency_statuses(settings))
    has_missing = any(not item.configured for item in dependencies)
    status = "ready"
    if settings.readiness_strict and has_missing:
        status = "not_ready"
    return ReadyResponse(
        status=status,
        strict=settings.readiness_strict,
        dependencies=dependencies,
    )


def _dependency_statuses(settings: Settings) -> Iterable[DependencyStatus]:
    yield _configured("postgresql", settings.database_url)
    yield _configured("redis", settings.redis_url)
    yield _configured("milvus", settings.milvus_uri)
    yield _configured("llm_base_url", settings.openai_base_url)
    yield _configured("llm_api_key", settings.openai_api_key.get_secret_value() if settings.openai_api_key else None)
    yield _configured("llm_model", settings.security_agent_model)


def _configured(name: str, value: str | None) -> DependencyStatus:
    configured = bool(value)
    return DependencyStatus(
        name=name,
        configured=configured,
        status="configured" if configured else "missing",
    )

