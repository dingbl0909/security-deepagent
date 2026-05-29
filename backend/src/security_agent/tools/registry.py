from security_agent.tools.models import ToolSpec


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        return self._tools[name]

    def names_for_agent(self, agent_name: str) -> list[str]:
        return [
            name
            for name, spec in self._tools.items()
            if agent_name in spec.allowed_agents
        ]

    def for_agent(self, agent_name: str) -> list[ToolSpec]:
        return [
            spec
            for spec in self._tools.values()
            if agent_name in spec.allowed_agents
        ]

    def all(self) -> list[ToolSpec]:
        return list(self._tools.values())

