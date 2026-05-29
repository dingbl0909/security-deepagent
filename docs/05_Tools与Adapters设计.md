# 05 Tools 与 Adapters 设计

源头文档：`项目介绍.txt`

溯源段落：
- 工具调用采用白名单机制。
- 覆盖设备接入排障、布控告警分析、知识库问答、现场图片物品研判。

覆盖任务：
- T40 ToolRegistry
- T41 search_security_knowledge
- T42 query_device_status
- T43 query_alarm_events
- T44 create_security_todos / update_task_status
- T45 request_human_review
- T46 analyze_security_object
- T47 LLM / Embedding / Vision / ObjectStorage adapters

---

## 1. ToolRegistry

每个工具声明：

- name
- description
- input_schema
- output_schema
- risk_level
- requires_review
- allowed_agents

---

## 2. 首版工具

| 工具 | 职责 | 风险 |
|------|------|------|
| `search_security_knowledge` | SOP 检索 | low |
| `query_device_status` | 设备状态查询 | low |
| `query_alarm_events` | 告警查询 | low |
| `create_security_todos` | 创建任务清单 | medium |
| `update_task_status` | 更新任务状态 | medium |
| `request_human_review` | 创建审核并触发 interrupt | high |
| `analyze_security_object` | 图片研判 | medium |
| `archive_episode` | 归档长期经验 | medium |

---

## 3. Adapters

| Adapter | 作用 |
|---------|------|
| `LLMGateway` | 文本模型统一接口 |
| `EmbeddingGateway` | 向量化 |
| `KnowledgeRetriever` | 知识库检索 |
| `DeviceGateway` | 安防设备平台或 PG 镜像 |
| `AlarmGateway` | 告警平台或 PG 镜像 |
| `ObjectStorage` | 图片和附件 |
| `VisionGateway` | 多模态模型 |

---

## 4. 验收

- Sub-agent 只能拿到允许工具。
- 高风险工具必须进入人工确认。
- 工具结果结构化，可进入 evidence 和 trace。
- 公开模型 API 前必须经过数据策略检查。

