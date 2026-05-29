from pathlib import Path
from functools import lru_cache

from security_agent.agents.registry import SubAgentRegistry
from security_agent.agents.skills import load_skills
from security_agent.config import get_settings
from security_agent.harness.context import ContextAssembler
from security_agent.harness.handoff import HandoffService
from security_agent.harness.intent import IntentRouter
from security_agent.harness.persistence import ResponsePersister
from security_agent.harness.pipeline import RequestPipeline
from security_agent.harness.runtime import AgentRuntime
from security_agent.harness.service import SecurityAgentService
from security_agent.stores.factory import get_in_memory_stores
from security_agent.tools.builtin import build_default_tool_registry, build_local_tool_dependencies


@lru_cache
def get_security_agent_service() -> SecurityAgentService:
    settings = get_settings()
    stores = get_in_memory_stores()
    tool_registry = build_default_tool_registry(build_local_tool_dependencies(stores))
    subagent_registry = SubAgentRegistry.from_yaml(settings.subagents_config, tool_registry)
    skills = load_skills(Path(settings.skills_dir))
    return SecurityAgentService(
        request_pipeline=RequestPipeline(stores, stores),
        intent_router=IntentRouter(),
        context_assembler=ContextAssembler(memory_store=stores, message_store=stores),
        agent_runtime=AgentRuntime(
            tool_registry,
            subagent_registry=subagent_registry,
            skills=skills,
            handoff_service=HandoffService(stores),
        ),
        response_persister=ResponsePersister(message_store=stores, memory_store=stores),
    )
