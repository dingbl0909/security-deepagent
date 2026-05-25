# Security DeepAgent Practice 基础设计文档

## 1. 项目定位

`security-deepagent-practice` 是一个面向安防业务场景的轻量化 DeepAgents 生产系统。它的目标是在本地工作站上完成部署、测试和演示，提供从用户请求、任务规划、知识检索、工具调用、人工确认、审计记录到 API 服务的完整闭环。

项目重点落地以下能力：

- 使用 `create_deep_agent` 构建主 Agent。
- 通过 Skills 管理可按需加载的业务能力说明。
- 通过 Sub-agents 拆分研究、排障、现场分析等子任务。
- 通过工具函数接入安防知识检索、告警查询、系统信息采集等能力。
- 通过沙箱后端限制 Agent 的文件和命令执行范围。
- 通过任务清单、审计日志、持久化记忆和人工确认机制提升可控性。
- 通过 FastAPI、CLI、配置文件和本地数据目录形成可部署服务。

## 2. 目标场景

首版项目围绕三个安防高频场景展开：

1. 设备接入与部署排障
   - 摄像头离线
   - 平台接入失败
   - 服务部署后接口异常

2. 布控告警与处置建议
   - 告警误报分析
   - 告警规则检查
   - 处置 SOP 检索

3. 现场抓拍与知识问答
   - 抓拍记录说明
   - 图片关联文档检索
   - 现场问题归因建议

系统默认使用本地可运行实现：文本知识库、SQLite 元数据、文件审计日志和轻量检索索引。GME / Milvus / Redis / MCP 作为增强适配层预留接口，但不作为本地部署的强依赖。

## 3. 总体架构

```text
security-deepagent-practice/
├── .env.example
├── README.md
├── config/
│   ├── subagents.yaml
│   └── settings.yaml
├── data/
│   ├── checkpoints/
│   ├── db/
│   ├── knowledge/
│   ├── logs/
│   ├── memory/
│   └── workspace/
├── docs/
│   └── design.md
├── scripts/
│   ├── init_db.py
│   └── run_cli.py
├── skills/
│   ├── research/
│   │   └── SKILL.md
│   └── system-info/
│       └── SKILL.md
└── src/
    └── security_agent/
        ├── __init__.py
        ├── agent.py
        ├── app.py
        ├── audit.py
        ├── backend.py
        ├── config.py
        ├── database.py
        ├── knowledge.py
        ├── llm.py
        ├── memory.py
        ├── prompts.py
        ├── schemas.py
        ├── subagents.py
        ├── tasks.py
        └── tools.py
```

## 4. 核心模块设计

### 4.1 Harness 层

`agent.py` 是项目的主入口，负责组合以下组件：

- LLM 模型
- 安防工具集
- Skills / Memory 文件
- Sub-agents 配置
- 沙箱 Backend
- Checkpointer
- 审计和会话持久化组件

主 Agent 不直接承载所有业务细节，而是负责理解用户目标、规划任务、选择工具或委派子 Agent。

### 4.2 LLM 接入

`llm.py` 使用 OpenAI 兼容接口，默认读取环境变量：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `SECURITY_AGENT_MODEL`

为了方便本地部署，LLM 创建逻辑需要保持简单，并允许对接本地 OpenAI 兼容模型服务，例如 Ollama、vLLM、LM Studio 或私有化 Qwen 服务。没有环境变量时，服务启动阶段应给出清晰错误。

### 4.3 工具层

`tools.py` 提供可本地运行的业务工具：

- `search_security_knowledge(query)`
  - 检索本地安防知识文档。
- `query_device_status(device_id_or_name)`
  - 查询 SQLite 中的摄像头或边缘设备状态。
- `query_alarm_events(query)`
  - 查询 SQLite 中的告警事件。
- `create_security_todos(task)`
  - 将复杂任务拆成可追踪清单。
- `request_human_review(reason, risk_level)`
  - 对高风险操作触发人工确认建议。

工具默认读写本地数据，可在不依赖外部服务的情况下完成端到端测试。后续如需接入真实平台，可通过适配器替换为真实 RAG、设备管理数据库、告警平台、工单系统或 MCP 工具。

### 4.4 知识检索层

`knowledge.py` 负责加载 `data/knowledge/` 下的 Markdown / JSON 文档，并提供轻量检索能力。

默认检索策略：

- 中文关键词匹配
- TF-IDF / BM25 风格的轻量得分排序
- 返回文档标题、片段、来源路径和置信度
- 将索引产物持久化到 `data/db/` 或 `data/knowledge/.index/`

增强检索策略：

- 可选接入本地 embedding 模型和 FAISS。
- 可选接入 Milvus 做 Dense / Sparse 混合检索。
- 可选接入多模态图文统一检索。
- 可选接入 RAGAS 评估闭环。

### 4.5 Skills

Skills 使用 Markdown 文件表达能力边界和使用说明，对齐 `rag_learning/deepagent/src/skills` 的风格。

首版包含：

- `skills/research/SKILL.md`
  - 用于安防资料调研、方案整理、排障报告生成。
- `skills/system-info/SKILL.md`
  - 用于采集环境信息、辅助部署排障。

后续可以增加：

- `skills/alarm-response/`
- `skills/device-access/`
- `skills/snapshot-analysis/`
- `skills/deployment-troubleshooting/`

### 4.6 Sub-agents

`config/subagents.yaml` 定义子 Agent。

首版建议包含：

- `security-researcher`
  - 负责资料检索、报告整理和方案比较。
- `ops-troubleshooter`
  - 负责设备接入、部署、服务异常排查。
- `alarm-analyst`
  - 负责告警误报、规则检查、处置建议。

`subagents.py` 负责读取 YAML，并将工具名称映射为真实工具对象。

所有子 Agent 都运行在同一套本地配置和沙箱边界内，避免不同子任务直接访问宿主机任意路径。

### 4.7 沙箱 Backend

`backend.py` 封装 DeepAgents Backend 创建逻辑。

首版优先使用：

- `FilesystemBackend(root_dir=..., virtual_mode=True)`

可选支持：

- `LocalShellBackend`
  - 仅允许在项目工作目录内执行命令。
  - 设置超时时间和输出大小限制。

设计原则：

- Agent 默认不能访问项目目录外部文件。
- 命令执行必须有超时。
- 高风险命令不在首版开放。
- 所有可写文件统一落在 `data/workspace/`、`data/logs/`、`data/memory/` 或 `data/db/`。

### 4.8 任务状态与审计

`tasks.py` 负责把复杂任务拆解为状态清单：

- `pending`
- `in_progress`
- `blocked`
- `completed`

`audit.py` 负责记录：

- 用户请求
- 工具调用摘要
- 人工确认原因
- 最终结论

日志保存到 `data/logs/`，结构化任务状态保存到 SQLite，便于展示可审计能力并支持服务重启后的查询。

### 4.9 记忆层

`memory.py` 首版使用 SQLite 和本地 JSON 文件实现短期记忆：

- thread_id
- user_id
- recent_summary
- important_facts

生产增强时可以替换为：

- Redis 短期会话
- 向量库长期记忆
- 工具调用日志归档

## 5. 运行链路

### 5.1 CLI 链路

```text
用户输入
  -> scripts/run_cli.py
  -> security_agent.agent.build_agent()
  -> 主 Agent 规划
  -> 调用工具 / 委派子 Agent
  -> 返回答案和证据
```

### 5.2 API 链路

```text
POST /chat
  -> app.py
  -> 构造 thread_id / user_id
  -> 调用 Agent
  -> 写入审计日志
  -> 返回 answer / evidence / needs_review
```

### 5.3 本地部署链路

```text
复制 .env.example 为 .env
  -> 安装 requirements.txt
  -> python scripts/init_db.py
  -> uvicorn security_agent.app:app --host 0.0.0.0 --port 8015
  -> 通过 /health 和 /chat 测试服务
```

## 6. 人工确认策略

以下情况应触发人工确认建议：

- 涉及重启服务、修改配置、升级规则等操作。
- 检索证据不足或置信度较低。
- 告警处置可能影响现场业务连续性。
- 用户要求生成可直接执行的高风险命令。

首版通过 `request_human_review` 工具返回结构化结果，并在 API 层标记 `needs_review=true`。高风险任务不会直接执行，只返回建议、风险原因和待确认动作。后续可以接入 LangGraph interrupt / resume 形成真正的暂停与恢复。

## 7. 本地生产版实现范围

本地生产版需要做到：

- 项目可以被 `pip install -r requirements.txt` 安装依赖。
- CLI 可以发起一次对话。
- FastAPI 可以启动 `/health`、`/chat`、`/threads/{thread_id}`、`/review/continue` 接口。
- 本地知识库检索可以返回证据。
- SQLite 可以保存设备、告警、任务、会话和审计摘要。
- 子 Agent 配置可以从 YAML 加载。
- Skills 文件和主系统提示词可以被 Agent 使用。
- 审计日志可以写入本地文件并关联 thread_id。
- 服务重启后仍能读取历史会话摘要和任务状态。
- 所有默认能力在单机环境内可启动、可测试、可替换。

本地生产版暂不内置：

- 分布式 Milvus 集群。
- 外部 Redis 集群。
- GPU 多模态模型推理服务。
- 真实 MCP 远端服务调用。
- 企业级 RBAC / SSO 权限系统。

这些能力以适配器接口保留，避免影响本地工作站部署。

## 8. 实现优先级

1. 补齐项目基础文件
   - `README.md`
   - `requirements.txt`
   - `.env.example`
   - `docs/design.md`

2. 实现本地持久化底座
   - `database.py`
   - `scripts/init_db.py`
   - SQLite schema
   - 样例设备、告警、知识数据

3. 实现核心可运行链路
   - `llm.py`
   - `tools.py`
   - `knowledge.py`
   - `agent.py`
   - `scripts/run_cli.py`

4. 补齐工程化能力
   - `subagents.py`
   - `backend.py`
   - `memory.py`
   - `audit.py`
   - `tasks.py`

5. 增加 API
   - `app.py`
   - `schemas.py`

6. 增加样例数据和 Skills
   - 安防知识文档
   - 子 Agent YAML
   - Skills Markdown

## 9. 验收标准

最小验收问题：

```text
仓库北门摄像头离线，帮我根据知识库排查原因，并给出下一步建议。
```

期望输出：

- 能识别这是设备接入 / 运维排障问题。
- 能检索到本地知识库中的相关 SOP。
- 能拆出排查步骤。
- 能提示高风险操作需要人工确认。
- 能在日志中记录本次任务摘要。
- 能在 SQLite 中保存 thread、task 和审计摘要。
- 能通过 FastAPI 在本地工作站完成一次完整请求。

