from dataclasses import dataclass

from security_agent.adapters.local import (
    LocalKnowledgeRetriever,
    LocalVisionGateway,
    StoreBackedAlarmGateway,
    StoreBackedDeviceGateway,
)
from security_agent.adapters.protocols import KnowledgeRetriever, VisionGateway
from security_agent.harness.interrupts import InterruptManager
from security_agent.schemas import ReviewStatus, RiskLevel, TaskStatus
from security_agent.stores.protocols import AlarmStore, DeviceStore, ReviewStore, TaskStore
from security_agent.tools.models import ToolContext, ToolName, ToolResult, ToolSpec
from security_agent.tools.registry import ToolRegistry


@dataclass
class ToolDependencies:
    task_store: TaskStore
    review_store: ReviewStore
    device_store: DeviceStore
    alarm_store: AlarmStore
    knowledge_retriever: KnowledgeRetriever
    vision_gateway: VisionGateway


def build_default_tool_registry(deps: ToolDependencies) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name=ToolName.SEARCH_SECURITY_KNOWLEDGE.value,
            description="检索安防 SOP 和知识库",
            risk_level=RiskLevel.LOW,
            allowed_agents={
                "main-agent",
                "security-researcher",
                "ops-troubleshooter",
                "alarm-analyst",
                "object-analyst",
            },
            handler=lambda context: search_security_knowledge(context, deps),
        )
    )
    registry.register(
        ToolSpec(
            name=ToolName.QUERY_DEVICE_STATUS.value,
            description="查询设备状态",
            risk_level=RiskLevel.LOW,
            allowed_agents={"ops-troubleshooter"},
            handler=lambda context: query_device_status(context, deps),
        )
    )
    registry.register(
        ToolSpec(
            name=ToolName.QUERY_ALARM_EVENTS.value,
            description="查询告警事件",
            risk_level=RiskLevel.LOW,
            allowed_agents={"alarm-analyst"},
            handler=lambda context: query_alarm_events(context, deps),
        )
    )
    registry.register(
        ToolSpec(
            name=ToolName.CREATE_SECURITY_TODOS.value,
            description="创建排查任务清单",
            risk_level=RiskLevel.MEDIUM,
            allowed_agents={"ops-troubleshooter", "alarm-analyst"},
            handler=lambda context: create_security_todos(context, deps),
        )
    )
    registry.register(
        ToolSpec(
            name=ToolName.UPDATE_TASK_STATUS.value,
            description="更新任务状态",
            risk_level=RiskLevel.MEDIUM,
            allowed_agents={"ops-troubleshooter", "alarm-analyst"},
            handler=lambda context: update_task_status(context, deps),
        )
    )
    registry.register(
        ToolSpec(
            name=ToolName.REQUEST_HUMAN_REVIEW.value,
            description="创建人工确认请求",
            risk_level=RiskLevel.HIGH,
            requires_review=True,
            allowed_agents={
                "main-agent",
                "security-researcher",
                "ops-troubleshooter",
                "alarm-analyst",
                "object-analyst",
            },
            handler=lambda context: request_human_review(context, deps),
        )
    )
    registry.register(
        ToolSpec(
            name=ToolName.ANALYZE_SECURITY_OBJECT.value,
            description="图片物品研判",
            risk_level=RiskLevel.MEDIUM,
            allowed_agents={"object-analyst"},
            handler=lambda context: analyze_security_object(context, deps),
        )
    )
    registry.register(
        ToolSpec(
            name=ToolName.ARCHIVE_EPISODE.value,
            description="归档长期经验",
            risk_level=RiskLevel.MEDIUM,
            allowed_agents={"ops-troubleshooter", "alarm-analyst"},
            handler=lambda context: archive_episode(context, deps),
        )
    )
    return registry


def build_local_tool_dependencies(stores) -> ToolDependencies:
    return ToolDependencies(
        task_store=stores,
        review_store=stores,
        device_store=stores,
        alarm_store=stores,
        knowledge_retriever=LocalKnowledgeRetriever(),
        vision_gateway=LocalVisionGateway(),
    )


async def search_security_knowledge(context: ToolContext, deps: ToolDependencies) -> ToolResult:
    hits = await deps.knowledge_retriever.search(context.message)
    evidence = [hit.model_dump() for hit in hits]
    return ToolResult(
        name=ToolName.SEARCH_SECURITY_KNOWLEDGE.value,
        summary=f"检索到 {len(evidence)} 条知识库证据。",
        evidence=evidence,
        data={"count": len(evidence)},
    )


async def query_device_status(context: ToolContext, deps: ToolDependencies) -> ToolResult:
    gateway = StoreBackedDeviceGateway(deps.device_store)
    devices = await gateway.query(context.message)
    summary = "未查询到匹配设备状态。" if not devices else f"查询到 {len(devices)} 条设备状态。"
    return ToolResult(
        name=ToolName.QUERY_DEVICE_STATUS.value,
        summary=summary,
        data={"devices": devices},
    )


async def query_alarm_events(context: ToolContext, deps: ToolDependencies) -> ToolResult:
    gateway = StoreBackedAlarmGateway(deps.alarm_store)
    alarms = await gateway.query(context.message)
    summary = "未查询到匹配告警事件。" if not alarms else f"查询到 {len(alarms)} 条告警事件。"
    return ToolResult(
        name=ToolName.QUERY_ALARM_EVENTS.value,
        summary=summary,
        data={"alarms": alarms},
    )


async def create_security_todos(context: ToolContext, deps: ToolDependencies) -> ToolResult:
    titles = _default_task_titles(context.message)
    tasks = [
        await deps.task_store.create_task(thread_id=context.thread_id, title=title)
        for title in titles
    ]
    return ToolResult(
        name=ToolName.CREATE_SECURITY_TODOS.value,
        summary=f"已创建 {len(tasks)} 个排查任务。",
        tasks=[
            {
                "task_id": task.task_id,
                "title": task.title,
                "status": task.status.value,
                "description": task.description,
            }
            for task in tasks
        ],
        data={"count": len(tasks)},
    )


async def update_task_status(context: ToolContext, deps: ToolDependencies) -> ToolResult:
    tasks = await deps.task_store.list_tasks(thread_id=context.thread_id)
    if not tasks:
        return ToolResult(
            name=ToolName.UPDATE_TASK_STATUS.value,
            summary="当前会话没有可更新任务。",
        )
    updated = await deps.task_store.update_task_status(
        task_id=tasks[0].task_id,
        status=TaskStatus.IN_PROGRESS,
    )
    return ToolResult(
        name=ToolName.UPDATE_TASK_STATUS.value,
        summary=f"任务已更新为 {updated.status.value}。",
        tasks=[
            {
                "task_id": updated.task_id,
                "title": updated.title,
                "status": updated.status.value,
            }
        ],
    )


async def request_human_review(context: ToolContext, deps: ToolDependencies) -> ToolResult:
    review = await InterruptManager(deps.review_store).pause_for_review(
        thread_id=context.thread_id,
        user_id=context.user_id,
        reason=None,
        proposed_action=context.message,
        checkpoint_ref=f"checkpoint:{context.thread_id}",
    )
    return ToolResult(
        name=ToolName.REQUEST_HUMAN_REVIEW.value,
        summary="已创建人工确认请求，等待审批。",
        review_requests=[
            {
                "review_id": review.review_id,
                "risk_level": review.risk_level.value,
                "reason": review.reason,
                "proposed_action": review.proposed_action,
                "status": ReviewStatus.PENDING.value,
                "resume_required": True,
            }
        ],
    )


async def analyze_security_object(context: ToolContext, deps: ToolDependencies) -> ToolResult:
    analysis = await deps.vision_gateway.analyze(
        image_path=context.image_path,
        image_url=context.image_url,
        image_base64=context.image_base64,
        prompt=context.message,
    )
    return ToolResult(
        name=ToolName.ANALYZE_SECURITY_OBJECT.value,
        summary=analysis.scene_summary,
        data=analysis.model_dump(),
    )


async def archive_episode(context: ToolContext, deps: ToolDependencies) -> ToolResult:
    return ToolResult(
        name=ToolName.ARCHIVE_EPISODE.value,
        summary="长期经验归档将在 Milvus episodic store 接入后启用。",
        data={"archived": False},
    )


def _default_task_titles(message: str) -> list[str]:
    if any(keyword in message for keyword in ["告警", "误报", "布控"]):
        return ["核对告警时间线", "检查告警规则阈值", "复核现场证据"]
    return ["检查设备供电", "检查网络连通性", "核对平台接入配置"]
