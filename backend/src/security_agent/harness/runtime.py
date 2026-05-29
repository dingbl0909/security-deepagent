from security_agent.agents.models import ModelProfile
from security_agent.agents.registry import SubAgentRegistry
from security_agent.agents.skills import Skill, render_skills_prompt, select_skills
from security_agent.harness.handoff import HandoffPacket, HandoffService
from security_agent.harness.models import AgentRunResult, RoutingDecision, RuntimeContext
from security_agent.harness.risk import RiskGate
from security_agent.schemas import ReviewRequestItem, RiskLevel, TraceEvent
from security_agent.tools.models import ToolContext, ToolName, ToolResult
from security_agent.tools.registry import ToolRegistry


class AgentRuntime:
    def __init__(
        self,
        tool_registry: ToolRegistry | None = None,
        *,
        subagent_registry: SubAgentRegistry | None = None,
        skills: list[Skill] | None = None,
        handoff_service: HandoffService | None = None,
        risk_gate: RiskGate | None = None,
    ) -> None:
        self._tool_registry = tool_registry
        self._subagent_registry = subagent_registry
        self._skills = skills or []
        self._handoff_service = handoff_service
        self._risk_gate = risk_gate or RiskGate()

    async def invoke(
        self,
        *,
        routing: RoutingDecision,
        context: RuntimeContext,
    ) -> AgentRunResult:
        if not self._tool_registry:
            return AgentRunResult(
                answer=(
                    "Harness lifecycle is running. "
                    f"Request routed to {routing.target_agent}; concrete Agent execution is pending."
                ),
                trace=[
                    TraceEvent(
                        type="agent_runtime_stub",
                        summary="Agent runtime stub returned a structured response.",
                        agent=routing.target_agent,
                        metadata={
                            "intent": routing.intent.value,
                            "route": routing.route.value,
                            "context_thread_id": context.thread_id,
                        },
                    )
                ],
            )

        model_profile = self._model_profile_for(routing.target_agent)
        selected_skills = select_skills(self._skills, _latest_message(context))
        skills_prompt = render_skills_prompt(selected_skills)
        allowed_tool_names = self._allowed_tools(routing.target_agent)
        tool_names = _configured_tool_plan(
            _tool_plan(routing.target_agent, context, self._risk_gate),
            allowed_tool_names,
        )
        trace: list[TraceEvent] = [
            TraceEvent(
                type="model_profile_selected",
                summary=f"Selected model profile for {routing.target_agent}.",
                agent=routing.target_agent,
                name=model_profile.name if model_profile else None,
                status="configured" if model_profile else "missing",
                metadata=_model_profile_metadata(model_profile),
            )
        ]
        if selected_skills:
            trace.append(
                TraceEvent(
                    type="skills_selected",
                    summary=f"Selected {len(selected_skills)} skill(s).",
                    agent=routing.target_agent,
                    status="selected",
                    metadata={
                        "skills": [skill.name for skill in selected_skills],
                        "prompt_chars": len(skills_prompt),
                    },
                )
            )
        handoff_id: str | None = None
        if self._handoff_service and routing.target_agent != "main-agent":
            record, handoff_trace = await self._handoff_service.create(
                HandoffPacket(
                    thread_id=context.thread_id,
                    to_agent=routing.target_agent,
                    task_brief=_latest_message(context),
                    context_summary=context.system_context_block,
                    allowed_tools=allowed_tool_names,
                )
            )
            handoff_id = record.handoff_id if record else None
            trace.append(handoff_trace)

        tool_context = ToolContext(
            thread_id=context.thread_id,
            user_id=context.user_id,
            message=_latest_message(context),
            image_path=context.recent_messages[-1].metadata.get("image_path") if context.recent_messages else None,
            image_url=context.recent_messages[-1].metadata.get("image_url") if context.recent_messages else None,
            image_base64=context.recent_messages[-1].metadata.get("image_base64") if context.recent_messages else None,
        )

        results: list[ToolResult] = []
        for tool_name in tool_names:
            spec = self._tool_registry.get(tool_name)
            if routing.target_agent not in spec.allowed_agents:
                trace.append(
                    TraceEvent(
                        type="tool_blocked",
                        summary=f"Tool {tool_name} is not allowed for {routing.target_agent}.",
                        agent=routing.target_agent,
                        name=tool_name,
                        status="blocked",
                    )
                )
                continue
            result = await spec.handler(tool_context)
            results.append(result)
            trace.append(
                TraceEvent(
                    type="tool_call",
                    summary=result.summary,
                    agent=routing.target_agent,
                    name=tool_name,
                    status="success",
                    metadata={
                        "risk_level": spec.risk_level.value,
                        "requires_review": spec.requires_review,
                        "model_profile": model_profile.name if model_profile else None,
                        "data_policy": model_profile.data_policy.value if model_profile else None,
                        "handoff_id": handoff_id,
                    },
                )
            )

        if self._handoff_service:
            await self._handoff_service.complete(
                handoff_id,
                status="interrupted" if any(result.review_requests for result in results) else "completed",
            )

        return _build_result(routing.target_agent, results, trace)

    def _model_profile_for(self, agent_name: str) -> ModelProfile | None:
        if not self._subagent_registry:
            return None
        return self._subagent_registry.get_model_profile(agent_name)

    def _allowed_tools(self, agent_name: str) -> list[str]:
        if self._subagent_registry:
            return self._subagent_registry.allowed_tools(agent_name)
        return self._tool_registry.names_for_agent(agent_name) if self._tool_registry else []


def _tool_plan(target_agent: str, context: RuntimeContext, risk_gate: RiskGate) -> list[str]:
    message = _latest_message(context)
    if risk_gate.requires_review(message):
        return [ToolName.REQUEST_HUMAN_REVIEW.value]
    if target_agent == "ops-troubleshooter":
        return [
            ToolName.QUERY_DEVICE_STATUS.value,
            ToolName.SEARCH_SECURITY_KNOWLEDGE.value,
            ToolName.CREATE_SECURITY_TODOS.value,
        ]
    if target_agent == "alarm-analyst":
        return [
            ToolName.QUERY_ALARM_EVENTS.value,
            ToolName.SEARCH_SECURITY_KNOWLEDGE.value,
            ToolName.CREATE_SECURITY_TODOS.value,
        ]
    if target_agent == "security-researcher":
        return [ToolName.SEARCH_SECURITY_KNOWLEDGE.value]
    if target_agent == "object-analyst":
        return [
            ToolName.ANALYZE_SECURITY_OBJECT.value,
            ToolName.SEARCH_SECURITY_KNOWLEDGE.value,
        ]
    return [ToolName.SEARCH_SECURITY_KNOWLEDGE.value]


def _configured_tool_plan(planned_tools: list[str], allowed_tools: list[str]) -> list[str]:
    allowed = set(allowed_tools)
    return [tool_name for tool_name in planned_tools if tool_name in allowed]


def _build_result(target_agent: str, results: list[ToolResult], trace: list[TraceEvent]) -> AgentRunResult:
    evidence = [item for result in results for item in result.evidence]
    tasks = [item for result in results for item in result.tasks]
    review_requests = [
        ReviewRequestItem(**item)
        for result in results
        for item in result.review_requests
    ]
    interrupted = bool(review_requests)
    answer_lines = [f"{target_agent} 已完成受控工具链路。"]
    answer_lines.extend(f"- {result.summary}" for result in results)
    if review_requests:
        answer_lines.append("- 已暂停高风险动作，等待人工确认。")
    return AgentRunResult(
        answer="\n".join(answer_lines),
        trace=trace,
        evidence=evidence,
        tasks=tasks,
        needs_review=interrupted,
        interrupted=interrupted,
        review_requests=review_requests,
    )


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _latest_message(context: RuntimeContext) -> str:
    return context.recent_messages[-1].content if context.recent_messages else ""


def _model_profile_metadata(model_profile: ModelProfile | None) -> dict:
    if not model_profile:
        return {}
    return {
        "model_profile": model_profile.name,
        "provider": model_profile.provider,
        "base_url": model_profile.base_url,
        "model": model_profile.model,
        "data_policy": model_profile.data_policy.value,
        "timeout_seconds": model_profile.timeout_seconds,
    }
