# 02 Harness 驾驭层设计

源头文档：`项目介绍.txt`

溯源段落：
- Harness 驾驭层统一上下文治理、工具编排与任务恢复。
- 将上下文治理、工具编排、会话持久化、审计日志、检查点恢复从业务逻辑中剥离。

覆盖任务：
- T30 SecurityAgentService
- T31 RequestPipeline
- T32 IntentRouter
- T33 ContextAssembler
- T34 ResponsePersister
- T35 TraceEvent

---

## 1. 生命周期

```text
ChatRequest
  → RequestPipeline.pre()
  → IntentRouter.route()
  → ContextAssembler.build()
  → AgentRuntime.invoke()
  → RiskGate / InterruptManager
  → ResponsePersister.post()
  → ChatResponse
```

---

## 2. 核心组件

| 组件 | 职责 |
|------|------|
| `SecurityAgentService` | 对 API 层暴露 chat、continue_review、get_thread |
| `RequestPipeline` | 建 thread、保存用户消息、写审计 |
| `IntentRouter` | 判断设备排障、告警分析、知识问答、图片研判 |
| `ContextAssembler` | 读取 Redis 记忆、Milvus 召回、最近消息 |
| `AgentRuntime` | 执行主 Agent 和 Sub-agent |
| `ResponsePersister` | 保存 assistant message、任务、工具轨迹、审计 |
| `InterruptManager` | 高风险中断和恢复 |

---

## 3. Intent 标签

| intent | target_agent |
|--------|--------------|
| `security_research` | `security-researcher` |
| `device_troubleshoot` | `ops-troubleshooter` |
| `alarm_analysis` | `alarm-analyst` |
| `object_analysis` | `object-analyst` |
| `general` | `main-agent` |

图片字段优先级最高，直接进入 `object_analysis`。

---

## 4. TraceEvent

```json
{
  "type": "tool_call",
  "agent": "ops-troubleshooter",
  "name": "query_device_status",
  "status": "success",
  "summary": "查询北门摄像头状态",
  "timestamp": "..."
}
```

事件类型：

- `intent_routed`
- `context_built`
- `handoff_started`
- `handoff_completed`
- `tool_call`
- `risk_detected`
- `agent_interrupted`
- `review_decided`
- `agent_resumed`
- `assistant_response`

---

## 5. 验收

- Harness 不直接依赖数据库 client，只依赖 Store 接口。
- LLM 不直连 DB。
- 高风险动作能进入 InterruptManager。
- 所有关键步骤有 trace 和 audit。

