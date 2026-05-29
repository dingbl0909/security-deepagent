from pathlib import Path

import yaml

from security_agent.agents.models import AgentRuntimeConfig, ModelProfile, SubAgentSpec
from security_agent.tools.registry import ToolRegistry


class AgentConfigError(ValueError):
    pass


class SubAgentRegistry:
    def __init__(self, config: AgentRuntimeConfig) -> None:
        self._config = config

    @classmethod
    def from_yaml(cls, path: str | Path, tool_registry: ToolRegistry) -> "SubAgentRegistry":
        config_path = Path(path)
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        model_profiles = {
            name: ModelProfile(name=name, **payload)
            for name, payload in (raw.get("model_profiles") or {}).items()
        }
        agents = {
            payload["name"]: SubAgentSpec(**payload)
            for payload in (raw.get("agents") or [])
        }
        config = AgentRuntimeConfig(model_profiles=model_profiles, agents=agents)
        _validate(config, tool_registry)
        return cls(config)

    def get_agent(self, name: str) -> SubAgentSpec:
        return self._config.agents[name]

    def get_model_profile(self, agent_name: str) -> ModelProfile:
        agent = self.get_agent(agent_name)
        return self._config.model_profiles[agent.model_profile]

    def allowed_tools(self, agent_name: str) -> list[str]:
        return list(self.get_agent(agent_name).tools)

    def agent_names(self) -> list[str]:
        return list(self._config.agents)


def _validate(config: AgentRuntimeConfig, tool_registry: ToolRegistry) -> None:
    if not config.model_profiles:
        raise AgentConfigError("at least one model profile is required")
    if not config.agents:
        raise AgentConfigError("at least one agent is required")

    registered_tools = {spec.name: spec for spec in tool_registry.all()}
    for agent in config.agents.values():
        if agent.model_profile not in config.model_profiles:
            raise AgentConfigError(
                f"agent {agent.name} references unknown model_profile {agent.model_profile}"
            )
        missing_tools = set(agent.tools) - set(registered_tools)
        if missing_tools:
            raise AgentConfigError(
                f"agent {agent.name} references unknown tools: {sorted(missing_tools)}"
            )
        disallowed_tools = [
            tool_name
            for tool_name in agent.tools
            if agent.name not in registered_tools[tool_name].allowed_agents
        ]
        if disallowed_tools:
            raise AgentConfigError(
                f"agent {agent.name} is not allowed to use tools: {sorted(disallowed_tools)}"
            )
