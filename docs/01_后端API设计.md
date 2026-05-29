# 01 后端 API 设计

源头文档：`项目介绍.txt`

溯源段落：
- API 服务层：基于 FastAPI 提供 `/chat`、`/threads`、`/reviews`、`/devices`、`/alarms` 等接口，支持会话持久化、审核流转和业务数据查询。
- 前端交互层：根据 `/health` 动态展示当前 Agent 执行链路。

覆盖任务：
- T10 创建后端 Python 项目骨架
- T12 定义 Pydantic Schemas
- T13 实现 `/health` 和 `/ready`
- T64 实现 Review approve / reject / resume API

---

## 1. API 列表

| Method | Path | 说明 |
|--------|------|------|
| GET | `/health` | 进程存活检查 |
| GET | `/ready` | 依赖就绪检查 |
| POST | `/chat` | Agent 主入口 |
| GET | `/threads` | 会话列表 |
| GET | `/threads/{thread_id}` | 会话详情 |
| GET | `/reviews` | 审核列表 |
| POST | `/reviews/{review_id}/approve` | 审核通过 |
| POST | `/reviews/{review_id}/reject` | 审核拒绝 |
| POST | `/reviews/{review_id}/resume` | 从 checkpoint 恢复 |
| GET | `/devices` | 设备列表 |
| GET | `/devices/{device_id}` | 设备详情 |
| GET | `/alarms` | 告警列表 |

---

## 2. `/chat`

请求：

```json
{
  "thread_id": "optional",
  "user_id": "ops_001",
  "message": "北门摄像头离线了，帮我排查",
  "image_path": null,
  "image_url": null,
  "image_base64": null
}
```

响应：

```json
{
  "thread_id": "thread_x",
  "message_id": "msg_x",
  "answer": "...",
  "intent": "device_troubleshoot",
  "route": "agent",
  "target_agent": "ops-troubleshooter",
  "evidence": [],
  "trace": [],
  "tasks": [],
  "needs_review": false,
  "interrupted": false,
  "review_requests": []
}
```

高风险中断时：

```json
{
  "needs_review": true,
  "interrupted": true,
  "review_requests": [
    {
      "review_id": "rev_x",
      "risk_level": "high",
      "reason": "用户请求重启服务",
      "proposed_action": "重启北门流媒体服务",
      "resume_required": true
    }
  ]
}
```

---

## 3. Review API

审批通过：

```text
POST /reviews/{review_id}/approve
```

审批拒绝：

```text
POST /reviews/{review_id}/reject
```

恢复流程：

```text
POST /reviews/{review_id}/resume
```

设计约束：

- approve/reject 只记录人工决定。
- resume 负责消费 checkpoint 并继续 Agent 流程。
- 也可以在 approve 后自动调用 resume，但内部仍要保留可审计的 resume 阶段。
- resume_token 只能消费一次。

---

## 4. 错误模型

```json
{
  "error": {
    "code": "REVIEW_ALREADY_RESUMED",
    "message": "review has already been resumed",
    "trace_id": "trace_x"
  }
}
```

---

## 5. 验收

- `/chat` 能返回 answer/evidence/trace/tasks。
- `/chat` 高风险时返回 `interrupted=true`。
- Review API 能完成 approve/reject/resume。
- `/ready` 能检查 PostgreSQL、Redis、Milvus、LLM 网关。

---

## 6. 当前实现状态

- `/chat`、`/threads`、`/reviews`、`/devices`、`/alarms` 已有 FastAPI 路由骨架。
- `/reviews/{id}/approve` 和 `/reject` 已记录人工决定。
- `/reviews/{id}/resume` 已消费 approved/rejected 状态并返回 `ReviewResumeResponse`。
- 当前 `/resume` 仍是 checkpoint 占位恢复，真实 LangGraph 恢复在 T65 接入。
