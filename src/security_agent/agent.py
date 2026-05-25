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
            system_prompt=MAIN_SYSTEM_PROMPT,
        )

    def _chat_with_deep_agent(self, message: str, thread_id: str, user_id: str) -> ChatResponse:
        result = self.deep_agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": thread_id, "user_id": user_id}},
        )
        answer = self._extract_answer(result)
        evidence_hits = self.knowledge.search(message, self.settings.top_k)
        risk_level = self._risk_level(message, answer)
        review_id = None
        needs_review = risk_level in {"high", "critical"}
        if needs_review:
            review_id = self.database.add_review_request(
                thread_id=thread_id,
                risk_level=risk_level,
                reason="模型回复或用户请求涉及高风险运维动作。",
                proposed_action=message,
            )
        return ChatResponse(
            answer=answer,
            thread_id=thread_id,
            user_id=user_id,
            evidence=[Evidence(**hit.__dict__) for hit in evidence_hits],
            tasks=[],
            needs_review=needs_review,
            review_id=review_id,
            risk_level=risk_level,
        )

    def _chat_with_local_rules(self, message: str, thread_id: str, user_id: str) -> ChatResponse:
        hits = self.knowledge.search(message, self.settings.top_k)
        devices = self.database.search_devices(message)
        alarms = self.database.search_alarms(message)
        tasks = self.tasks.create_todos(thread_id=thread_id, task=message)
        risk_level = self._risk_level(message)
        needs_review = risk_level in {"high", "critical"}
        review_id = None
        if needs_review:
            review_id = self.database.add_review_request(
                thread_id=thread_id,
                risk_level=risk_level,
                reason="请求中包含可能影响业务连续性的高风险动作。",
                proposed_action=message,
            )
        answer = self._compose_local_answer(message, hits, devices, alarms, needs_review)
        return ChatResponse(
            answer=answer,
            thread_id=thread_id,
            user_id=user_id,
            evidence=[Evidence(**hit.__dict__) for hit in hits],
            tasks=tasks,
            needs_review=needs_review,
            review_id=review_id,
            risk_level=risk_level,
        )

    def _compose_local_answer(self, message: str, hits, devices, alarms, needs_review: bool) -> str:
        lines = [
            "已按本地生产链路完成初步分析。",
            "",
            "判断：这是一个安防运维/告警处置类问题，需要结合设备状态、告警事件和知识库 SOP 排查。",
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
                "evidence_count": len(response.evidence),
                "task_count": len(response.tasks),
            },
        )

    @staticmethod
    def _risk_level(*texts: str) -> str:
        merged = " ".join(texts)
        if any(keyword in merged for keyword in RISK_KEYWORDS):
            return "high"
        return "low"

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

