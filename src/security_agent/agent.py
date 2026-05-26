from __future__ import annotations

import json
from typing import Any

from security_agent.audit import AuditLogger
from security_agent.backend import build_backend
from security_agent.config import Settings, get_settings
from security_agent.database import Database, init_database
from security_agent.knowledge import KnowledgeBase
from security_agent.llm import build_llm
from security_agent.memory import MemoryStore
from security_agent.prompts import MAIN_SYSTEM_PROMPT
from security_agent.schemas import ChatResponse, Evidence
from security_agent.skills import load_skills, render_skills_prompt
from security_agent.subagents import load_subagents
from security_agent.tasks import TaskService
from security_agent.tools import SECURITY_TOOLS


RISK_KEYWORDS = ["重启", "删除", "修改配置", "升级", "执行命令", "停用", "清空", "下发规则"]


class SecurityAgentService:
    """Application service that keeps local production behavior available without an LLM."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.database = init_database(self.settings)
        self.knowledge = KnowledgeBase(self.settings.knowledge_dir)
        self.tasks = TaskService(self.database)
        self.audit = AuditLogger(self.database, self.settings.log_dir)
        self.memory = MemoryStore(self.database, self.settings.memory_dir)
        self.skills = load_skills(self.settings.skills_dir) if self.settings.skills_enabled else []
        self.deep_agent = self._try_build_deep_agent()

    def chat(self, message: str, thread_id: str, user_id: str) -> ChatResponse:
        self.database.upsert_thread(thread_id, user_id, title=message[:40])
        self.database.add_message(thread_id, "user", message)
        self.audit.record(thread_id, "user_message", {"user_id": user_id, "message": message})

        if self.deep_agent is not None:
            try:
                response = self._chat_with_deep_agent(message, thread_id, user_id)
                self._persist_response(response)
                return response
            except Exception as exc:
                self.audit.record(thread_id, "deep_agent_fallback", {"error": str(exc)})

        response = self._chat_with_local_rules(message, thread_id, user_id)
        self._persist_response(response)
        return response

    def continue_review(self, review_id: int, approve: bool, operator_id: str) -> dict[str, Any]:
        self.database.complete_review(review_id, approve)
        status = "approved" if approve else "rejected"
        return {"review_id": review_id, "status": status, "operator_id": operator_id}

    def get_thread(self, thread_id: str) -> dict[str, Any] | None:
        return self.database.get_thread(thread_id)

    def list_threads(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.database.list_threads(limit=limit)

    def list_reviews(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        return self.database.list_reviews(status=status, limit=limit)

    def list_devices(self, query: str = "") -> list[dict[str, Any]]:
        return self.database.list_devices(query=query)

    def list_alarms(self, query: str = "") -> list[dict[str, Any]]:
        return self.database.list_alarms(query=query)

    def _try_build_deep_agent(self):
        if not self.settings.llm_enabled:
            return None
        llm = build_llm(self.settings)
        if llm is None:
            return None
        try:
            from deepagents import create_deep_agent
            from langgraph.checkpoint.memory import InMemorySaver
        except ImportError:
            return None
        return create_deep_agent(
            model=llm,
            tools=SECURITY_TOOLS,
            checkpointer=InMemorySaver(),
            backend=build_backend(self.settings),
            subagents=load_subagents(self.settings.subagents_path),
            system_prompt=self._build_system_prompt(),
        )

    def _build_system_prompt(self) -> str:
        skills_prompt = render_skills_prompt(self.skills)
        if not skills_prompt:
            return MAIN_SYSTEM_PROMPT
        return f"{MAIN_SYSTEM_PROMPT.rstrip()}\n\n{skills_prompt}"

    def _chat_with_deep_agent(self, message: str, thread_id: str, user_id: str) -> ChatResponse:
        result = self.deep_agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": thread_id, "user_id": user_id}},
        )
        answer = self._extract_answer(result)
        evidence_hits = self.knowledge.search(message, self.settings.top_k)
        risk_level = self._risk_level(message, answer)
        review_id = None
        review_reason = None
        proposed_action = None
        risk_keywords: list[str] = []
        needs_review = risk_level in {"high", "critical"}
        if needs_review:
            review_reason, proposed_action, risk_keywords = self._build_review_context(message, answer)
            review_id = self.database.add_review_request(
                thread_id=thread_id,
                risk_level=risk_level,
                reason=review_reason,
                proposed_action=proposed_action,
            )
        return ChatResponse(
            answer=answer,
            thread_id=thread_id,
            user_id=user_id,
            react_trace=self._extract_deep_agent_trace(result, message, evidence_hits, needs_review),
            evidence=[Evidence(**hit.__dict__) for hit in evidence_hits],
            tasks=[],
            needs_review=needs_review,
            review_id=review_id,
            risk_level=risk_level,
            review_reason=review_reason,
            proposed_action=proposed_action,
            risk_keywords=risk_keywords,
        )

    def _chat_with_local_rules(self, message: str, thread_id: str, user_id: str) -> ChatResponse:
        hits = self.knowledge.search(message, self.settings.top_k)
        devices = self.database.search_devices(message)
        alarms = self.database.search_alarms(message)
        tasks = self.tasks.create_todos(thread_id=thread_id, task=message)
        risk_level = self._risk_level(message)
        needs_review = risk_level in {"high", "critical"}
        intent = self._infer_intent(message, devices, alarms, hits)
        react_trace = self._build_local_react_trace(
            intent=intent,
            hit_count=len(hits),
            device_count=len(devices),
            alarm_count=len(alarms),
            task_count=len(tasks),
            needs_review=needs_review,
        )
        review_id = None
        review_reason = None
        proposed_action = None
        risk_keywords: list[str] = []
        if needs_review:
            review_reason, proposed_action, risk_keywords = self._build_review_context(message)
            review_id = self.database.add_review_request(
                thread_id=thread_id,
                risk_level=risk_level,
                reason=review_reason,
                proposed_action=proposed_action,
            )
        answer = self._compose_local_answer(
            message=message,
            intent=intent,
            react_trace=react_trace,
            hits=hits,
            devices=devices,
            alarms=alarms,
            needs_review=needs_review,
        )
        return ChatResponse(
            answer=answer,
            thread_id=thread_id,
            user_id=user_id,
            react_trace=react_trace,
            evidence=[Evidence(**hit.__dict__) for hit in hits],
            tasks=tasks,
            needs_review=needs_review,
            review_id=review_id,
            risk_level=risk_level,
            review_reason=review_reason,
            proposed_action=proposed_action,
            risk_keywords=risk_keywords,
        )

    def _compose_local_answer(
        self,
        message: str,
        intent: str,
        react_trace: list[str],
        hits,
        devices,
        alarms,
        needs_review: bool,
    ) -> str:
        lines = [
            "已按本地生产链路完成初步分析。",
            "",
            f"判断：这是{intent}问题，需要结合设备状态、告警事件和知识库 SOP 排查。",
            "",
            "ReAct 执行过程：",
            *[f"- {step}" for step in react_trace],
        ]
        if devices:
            lines.append("")
            lines.append("相关设备：")
            for device in devices[:3]:
                lines.append(
                    f"- {device['name']}（{device['id']}）：状态 {device['status']}，位置 {device['location']}，IP {device.get('ip') or '未知'}。"
                )
        if alarms:
            lines.append("")
            lines.append("相关告警：")
            for alarm in alarms[:3]:
                lines.append(f"- {alarm['id']}：{alarm['severity']}，{alarm['summary']}")
        if hits:
            lines.append("")
            lines.append("知识库证据：")
            for hit in hits:
                lines.append(f"- {hit.title}（{hit.source}，score={hit.score}）：{hit.snippet}")
        lines.extend(
            [
                "",
                "建议下一步：",
                "1. 先检查设备供电、网络链路和交换机端口。",
                "2. 再核对设备 IP、平台接入参数、时间同步和心跳状态。",
                "3. 检查平台侧最近错误日志，确认是网络、鉴权、协议注册还是服务异常。",
                "4. 如果需要重启服务、修改配置或下发规则，先走人工确认。",
            ]
        )
        if needs_review:
            lines.append("")
            lines.append("风险提示：该请求涉及高风险动作，系统已创建人工确认请求，暂不直接执行。")
        return "\n".join(lines)

    def _persist_response(self, response: ChatResponse) -> None:
        self.database.add_message(response.thread_id, "assistant", response.answer)
        summary = response.answer[:500]
        self.memory.save(response.thread_id, summary)
        self.audit.record(
            response.thread_id,
            "assistant_response",
            {
                "needs_review": response.needs_review,
                "review_id": response.review_id,
                "risk_level": response.risk_level,
                "react_trace_count": len(response.react_trace),
                "evidence_count": len(response.evidence),
                "task_count": len(response.tasks),
            },
        )

    @staticmethod
    def _matched_risk_keywords(*texts: str) -> list[str]:
        merged = " ".join(texts)
        return [keyword for keyword in RISK_KEYWORDS if keyword in merged]

    @staticmethod
    def _build_review_context(message: str, answer: str = "") -> tuple[str, str, list[str]]:
        risk_keywords = SecurityAgentService._matched_risk_keywords(message, answer)
        proposed_action = message.strip() or "未提供明确动作描述。"
        if risk_keywords:
            reason = f"命中高风险关键词：{'、'.join(risk_keywords)}。"
        elif answer.strip():
            reason = "模型回复或用户请求涉及高风险运维动作。"
        else:
            reason = "请求中包含可能影响业务连续性的高风险动作。"
        return reason, proposed_action, risk_keywords

    @staticmethod
    def _risk_level(*texts: str) -> str:
        merged = " ".join(texts)
        if any(keyword in merged for keyword in RISK_KEYWORDS):
            return "high"
        return "low"

    @staticmethod
    def _infer_intent(message: str, devices: list[dict[str, Any]], alarms: list[dict[str, Any]], hits) -> str:
        if any(keyword in message for keyword in ["部署", "接口", "启动", "服务", "配置", ".env"]):
            return "私有化部署 / 服务异常排查"
        if devices or any(keyword in message for keyword in ["摄像头", "设备", "离线", "接入", "心跳", "RTSP", "GB28181"]):
            return "设备接入 / 摄像头离线排查"
        if alarms or any(keyword in message for keyword in ["告警", "误报", "布控", "越界", "入侵"]):
            return "布控告警处置 / 误报分析"
        if hits:
            return "本地知识库问答"
        return "通用安防咨询"

    @staticmethod
    def _build_local_react_trace(
        intent: str,
        hit_count: int,
        device_count: int,
        alarm_count: int,
        task_count: int,
        needs_review: bool,
    ) -> list[str]:
        trace = [
            f"识别：这是{intent}问题。",
            f"行动：调用 search_security_knowledge 检索本地知识库；观察：命中 {hit_count} 条证据。",
            f"行动：调用 query_device_status 查询设备状态；观察：命中 {device_count} 台设备。",
            f"行动：调用 query_alarm_events 查询告警事件；观察：命中 {alarm_count} 条告警。",
            f"行动：调用 create_security_todos 生成排查任务；观察：生成 {task_count} 个待办步骤。",
        ]
        if needs_review:
            trace.append("行动：调用 request_human_review 创建人工确认；观察：该请求被标记为高风险。")
        else:
            trace.append("判断：未命中高风险动作关键词，本轮不需要人工确认。")
        return trace

    @staticmethod
    def _extract_deep_agent_trace(result: Any, message: str, evidence_hits, needs_review: bool) -> list[str]:
        trace = ["识别：进入 DeepAgent + 大模型编排链路。"]
        if isinstance(result, dict):
            for item in result.get("messages", []):
                tool_calls = getattr(item, "tool_calls", None)
                if tool_calls:
                    for call in tool_calls:
                        name = call.get("name") if isinstance(call, dict) else getattr(call, "name", "unknown_tool")
                        args = call.get("args") if isinstance(call, dict) else getattr(call, "args", {})
                        trace.append(f"行动：DeepAgent 调用 {name} 工具，参数 {args}。")
                message_type = getattr(item, "type", "")
                tool_name = getattr(item, "name", None)
                content = getattr(item, "content", "")
                if message_type == "tool" or tool_name:
                    preview = str(content).replace("\n", " ")[:120]
                    trace.append(f"观察：工具 {tool_name or 'unknown_tool'} 返回 {preview}。")
        trace.append(f"行动：调用 search_security_knowledge 补充本地证据；观察：命中 {len(evidence_hits)} 条证据。")
        if needs_review:
            trace.append("判断：模型回复或用户请求涉及高风险动作，已创建人工确认请求。")
        return trace

    @staticmethod
    def _extract_answer(result: Any) -> str:
        if isinstance(result, dict) and "messages" in result and result["messages"]:
            message = result["messages"][-1]
            content = getattr(message, "content", None)
            if content:
                return str(content)
            if isinstance(message, dict):
                return str(message.get("content", ""))
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False, default=str)


def build_agent_service(settings: Settings | None = None) -> SecurityAgentService:
    return SecurityAgentService(settings)

