from __future__ import annotations

import json
from typing import Any, Callable

from security_agent.database import Database
from security_agent.knowledge import KnowledgeBase
from security_agent.tasks import TaskService
from security_agent.vision import analyze_security_image

try:
    from langchain_core.tools import tool
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    def tool(name: str | None = None, parse_docstring: bool = False):
        def decorator(func: Callable):
            func.name = name or func.__name__
            return func
        return decorator


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


@tool("search_security_knowledge", parse_docstring=True)
def search_security_knowledge(query: str) -> str:
    """
    检索本地安防知识库，返回带来源和片段的证据。

    Args:
        query: 用户问题或检索关键词。
    """
    hits = KnowledgeBase().search(query)
    return _json([hit.__dict__ for hit in hits]) if hits else "未检索到相关知识。"


@tool("query_device_status", parse_docstring=True)
def query_device_status(device_id_or_name: str) -> str:
    """
    查询本地 SQLite 中的设备状态。

    Args:
        device_id_or_name: 设备 ID、名称、位置、IP 或状态关键词。
    """
    rows = Database().search_devices(device_id_or_name)
    return _json(rows) if rows else "未查询到匹配设备。"


@tool("query_alarm_events", parse_docstring=True)
def query_alarm_events(query: str) -> str:
    """
    查询本地 SQLite 中的告警事件。

    Args:
        query: 告警 ID、设备 ID、告警类型、状态、级别或关键词。
    """
    rows = Database().search_alarms(query)
    return _json(rows) if rows else "未查询到匹配告警。"


@tool("create_security_todos", parse_docstring=True)
def create_security_todos(task: str, thread_id: str = "default-thread") -> str:
    """
    将复杂安防任务拆解为可追踪的本地任务清单。

    Args:
        task: 用户提出的复杂任务。
        thread_id: 会话线程 ID。
    """
    todos = TaskService().create_todos(thread_id=thread_id, task=task)
    return _json(todos)


@tool("analyze_security_object", parse_docstring=True)
def analyze_security_object(
    question: str,
    image_path: str = "",
    image_url: str = "",
    image_base64: str = "",
) -> str:
    """
    调用多模态模型完成安防物品研判和图片识别。

    Args:
        question: 用户问题或研判要求。
        image_path: 工作目录内图片相对路径，例如 uploads/sample.jpg。
        image_url: 图片 URL 或 data URL。
        image_base64: base64 编码图片内容。
    """
    result = analyze_security_image(
        question,
        image_path=image_path or None,
        image_url=image_url or None,
        image_base64=image_base64 or None,
    )
    return _json(
        {
            "answer": result.answer,
            "model": result.model,
            "source": result.source,
        }
    )


@tool("request_human_review", parse_docstring=True)
def request_human_review(
    reason: str,
    proposed_action: str,
    risk_level: str = "high",
    thread_id: str = "default-thread",
) -> str:
    """
    为高风险动作创建人工确认请求。

    Args:
        reason: 需要人工确认的原因。
        proposed_action: 待确认动作。
        risk_level: 风险级别，建议使用 low、medium、high、critical。
        thread_id: 会话线程 ID。
    """
    review_id = Database().add_review_request(
        thread_id=thread_id,
        risk_level=risk_level,
        reason=reason,
        proposed_action=proposed_action,
    )
    return _json(
        {
            "review_id": review_id,
            "needs_review": True,
            "risk_level": risk_level,
            "reason": reason,
            "proposed_action": proposed_action,
        }
    )


SECURITY_TOOLS = [
    search_security_knowledge,
    query_device_status,
    query_alarm_events,
    create_security_todos,
    analyze_security_object,
    request_human_review,
]


def _tool_name(tool_obj: Any) -> str:
    name = getattr(tool_obj, "name", None)
    if name:
        return str(name)
    return str(getattr(tool_obj, "__name__"))


TOOL_REGISTRY = {_tool_name(tool_obj): tool_obj for tool_obj in SECURITY_TOOLS}

