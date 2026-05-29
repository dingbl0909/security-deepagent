from pathlib import Path

import pytest

from security_agent.agents.registry import AgentConfigError, SubAgentRegistry
from security_agent.agents.skills import load_skills, render_skills_prompt, select_skills
from security_agent.stores.memory import InMemoryStores
from security_agent.tools.builtin import build_default_tool_registry, build_local_tool_dependencies
from security_agent.tools.models import ToolName


def test_subagent_registry_loads_agents_and_model_profiles() -> None:
    registry = _load_registry()

    assert set(registry.agent_names()) == {
        "main-agent",
        "security-researcher",
        "ops-troubleshooter",
        "alarm-analyst",
        "object-analyst",
    }
    assert registry.get_model_profile("object-analyst").data_policy == "image_review_required"
    assert ToolName.REQUEST_HUMAN_REVIEW.value in registry.allowed_tools("object-analyst")


def test_subagent_registry_rejects_unknown_tool(tmp_path: Path) -> None:
    path = tmp_path / "agents.yaml"
    path.write_text(
        """
model_profiles:
  private-main:
    provider: openai-compatible
    base_url: http://localhost/v1
    model: local-model
    api_key_env: PRIVATE_LLM_API_KEY
    data_policy: internal_only
agents:
  - name: main-agent
    description: invalid
    model_profile: private-main
    tools:
      - missing_tool
""",
        encoding="utf-8",
    )

    with pytest.raises(AgentConfigError, match="unknown tools"):
        SubAgentRegistry.from_yaml(path, _tool_registry())


def test_subagent_registry_rejects_unknown_model_profile(tmp_path: Path) -> None:
    path = tmp_path / "agents.yaml"
    path.write_text(
        """
model_profiles:
  private-main:
    provider: openai-compatible
    base_url: http://localhost/v1
    model: local-model
    api_key_env: PRIVATE_LLM_API_KEY
    data_policy: internal_only
agents:
  - name: main-agent
    description: invalid
    model_profile: missing-profile
    tools:
      - search_security_knowledge
""",
        encoding="utf-8",
    )

    with pytest.raises(AgentConfigError, match="unknown model_profile"):
        SubAgentRegistry.from_yaml(path, _tool_registry())


def test_subagent_registry_rejects_disallowed_tool(tmp_path: Path) -> None:
    path = tmp_path / "agents.yaml"
    path.write_text(
        """
model_profiles:
  private-main:
    provider: openai-compatible
    base_url: http://localhost/v1
    model: local-model
    api_key_env: PRIVATE_LLM_API_KEY
    data_policy: internal_only
agents:
  - name: security-researcher
    description: invalid
    model_profile: private-main
    tools:
      - query_device_status
""",
        encoding="utf-8",
    )

    with pytest.raises(AgentConfigError, match="not allowed"):
        SubAgentRegistry.from_yaml(path, _tool_registry())


def test_load_select_and_render_skills() -> None:
    skills = load_skills("skills")

    assert {skill.name for skill in skills} == {
        "security-researcher",
        "ops-troubleshooter",
        "alarm-analyst",
        "object-analyst",
    }

    selected = select_skills(skills, "北门摄像头离线")
    assert [skill.name for skill in selected] == ["ops-troubleshooter"]

    prompt = render_skills_prompt(selected)
    assert "ops-troubleshooter" in prompt
    assert "设备状态查询" in prompt


def _load_registry() -> SubAgentRegistry:
    return SubAgentRegistry.from_yaml("config/agents.yaml", _tool_registry())


def _tool_registry():
    return build_default_tool_registry(build_local_tool_dependencies(InMemoryStores()))
