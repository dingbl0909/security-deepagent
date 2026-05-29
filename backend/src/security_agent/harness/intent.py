from security_agent.harness.models import PreparedRequest, RoutingDecision
from security_agent.schemas import IntentLabel, RouteLabel, TraceEvent


class IntentRouter:
    async def route(self, prepared: PreparedRequest) -> RoutingDecision:
        request = prepared.request
        message = request.message.lower()
        if request.image_path or request.image_url or request.image_base64:
            decision = RoutingDecision(
                intent=IntentLabel.OBJECT_ANALYSIS,
                route=RouteLabel.VISION,
                target_agent="object-analyst",
                reason="image input present",
            )
        elif _contains_any(message, ["告警", "误报", "布控", "入侵"]):
            decision = RoutingDecision(
                intent=IntentLabel.ALARM_ANALYSIS,
                route=RouteLabel.AGENT,
                target_agent="alarm-analyst",
                reason="alarm keywords matched",
            )
        elif _contains_any(message, ["sop", "知识", "规范", "方案", "文档"]):
            decision = RoutingDecision(
                intent=IntentLabel.SECURITY_RESEARCH,
                route=RouteLabel.AGENT,
                target_agent="security-researcher",
                reason="knowledge keywords matched",
            )
        elif _contains_any(message, ["离线", "接入", "摄像头", "部署", "设备"]):
            decision = RoutingDecision(
                intent=IntentLabel.DEVICE_TROUBLESHOOT,
                route=RouteLabel.AGENT,
                target_agent="ops-troubleshooter",
                reason="device troubleshooting keywords matched",
            )
        else:
            decision = RoutingDecision(
                intent=IntentLabel.GENERAL,
                route=RouteLabel.AGENT,
                target_agent="main-agent",
                reason="no specific routing rule matched",
            )

        prepared.trace.append(
            TraceEvent(
                type="intent_routed",
                summary=f"Routed request to {decision.target_agent}.",
                agent="harness",
                metadata=decision.model_dump(),
            )
        )
        return decision


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)
