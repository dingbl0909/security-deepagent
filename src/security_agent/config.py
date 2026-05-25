from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env", override=False)


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _path_env(name: str, default: str) -> Path:
    value = os.getenv(name, default)
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


@dataclass(frozen=True)
class Settings:
    app_name: str
    host: str
    port: int
    llm_enabled: bool
    model_name: str
    openai_api_key: str | None
    openai_base_url: str | None
    db_path: Path
    knowledge_dir: Path
    log_dir: Path
    memory_dir: Path
    workspace_dir: Path
    subagents_path: Path
    settings_path: Path
    top_k: int

    def ensure_directories(self) -> None:
        for path in [
            self.db_path.parent,
            self.knowledge_dir,
            self.log_dir,
            self.memory_dir,
            self.workspace_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    _load_dotenv()
    settings = Settings(
        app_name="security-deepagent-practice",
        host=os.getenv("SECURITY_AGENT_HOST", "0.0.0.0"),
        port=_int_env("SECURITY_AGENT_PORT", 8015),
        llm_enabled=_bool_env("SECURITY_AGENT_LLM_ENABLED", False),
        model_name=os.getenv("SECURITY_AGENT_MODEL", "qwen-plus"),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_base_url=os.getenv("OPENAI_BASE_URL") or None,
        db_path=_path_env("SECURITY_AGENT_DB_PATH", "data/db/security_agent.sqlite3"),
        knowledge_dir=_path_env("SECURITY_AGENT_KNOWLEDGE_DIR", "data/knowledge"),
        log_dir=_path_env("SECURITY_AGENT_LOG_DIR", "data/logs"),
        memory_dir=_path_env("SECURITY_AGENT_MEMORY_DIR", "data/memory"),
        workspace_dir=_path_env("SECURITY_AGENT_WORKSPACE_DIR", "data/workspace"),
        subagents_path=_path_env("SECURITY_AGENT_SUBAGENTS_PATH", "config/subagents.yaml"),
        settings_path=_path_env("SECURITY_AGENT_SETTINGS_PATH", "config/settings.yaml"),
        top_k=_int_env("SECURITY_AGENT_TOP_K", 4),
    )
    settings.ensure_directories()
    return settings

