from __future__ import annotations

from security_agent.config import Settings, get_settings


def build_llm(settings: Settings | None = None):
    settings = settings or get_settings()
    if not settings.llm_enabled:
        return None
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required when SECURITY_AGENT_LLM_ENABLED=true")
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # pragma: no cover - dependency is declared in requirements.txt
        raise RuntimeError("langchain-openai is required when LLM mode is enabled") from exc

    return ChatOpenAI(
        model=settings.model_name,
        temperature=0.2,
        openai_api_key=settings.openai_api_key,
        openai_api_base=settings.openai_base_url,
    )

