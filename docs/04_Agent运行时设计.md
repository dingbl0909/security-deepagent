# 04 Agent 运行时设计

源头文档：`项目介绍.txt`

溯源段落：
- 技术架构：项目基于 DeepAgents（LangChain + LangGraph）构建 Agent 运行时。
- Agent 驾驭层：主 Agent 负责意图识别与任务编排，按场景委派 security-researcher、ops-troubleshooter、alarm-analyst、object-analyst 等 Sub-agents。
- Human-in-the-loop 风险控制：审批通过后通过 LangGraph interrupt / resume 从 checkpoint 继续执行原流程。

覆盖任务：
- T50 接入 DeepAgents / LangGraph runtime
- T51 设计主 Agent prompt 和职责边界
- T54 实现 HandoffService 和 HandoffStore
- T55 接入 Redis checkpoint
- T65 实现 LangGraph interrupt / resume 与 Redis checkpoint 联动

---

## 1. 运行时目标

Agent Runtime 负责把 Harness 组装好的任务和上下文交给大模型执行，并确保：

- 主 Agent 只负责任务理解、规划和委派。
- Sub-agent 只处理各自场景。
- 每个 Sub-agent 只能访问白名单工具。
- 每个 Sub-agent 可绑定不同模型。
- 高风险工具调用必须 interrupt，审批后 resume。
- 所有 handoff、tool call、interrupt、resume 都可审计。

---

## 2. Agent 类型

| Agent | 职责 | 默认模型策略 |
|------|------|--------------|
| main-agent | 意图理解、任务规划、选择 Sub-agent | 私有化通用文本模型 |
| security-researcher | SOP 检索、知识问答、方案整理 | 长上下文私有模型 |
| ops-troubleshooter | 设备接入、离线、部署排障 | 私有化安全模型 |
| alarm-analyst | 告警误报、规则分析、处置建议 | 私有化安全模型 |
| object-analyst | 图片物品研判 | 私有化或公开 Vision 模型，按数据策略决定 |

---

## 3. 多模型支持

### 3.1 是否支持不同 Sub-agent 接不同模型

支持。每个 Sub-agent 通过 `model_profile` 绑定模型配置，可以接：

- 内网私有化 OpenAI-compatible 网关。
- vLLM / Ollama / LM Studio / 私有 Qwen 服务。
- 公开 API。
- 专用 Vision API。

### 3.2 模型配置

建议配置文件：

```yaml
model_profiles:
  private-main:
    provider: openai-compatible
    base_url: http://llm-gateway.internal/v1
    model: qwen-agent-main
    api_key_env: PRIVATE_LLM_API_KEY
    timeout_seconds: 60
    data_policy: internal_only

  private-long-context:
    provider: openai-compatible
    base_url: http://llm-gateway.internal/v1
    model: qwen-long-context
    api_key_env: PRIVATE_LLM_API_KEY
    timeout_seconds: 90
    data_policy: internal_only

  public-general:
    provider: openai-compatible
    base_url: https://api.public-provider.example/v1
    model: public-chat-model
    api_key_env: PUBLIC_LLM_API_KEY
    timeout_seconds: 60
    data_policy: sanitized_only

  public-vision:
    provider: openai-compatible
    base_url: https://api.public-provider.example/v1
    model: public-vision-model
    api_key_env: PUBLIC_VISION_API_KEY
    timeout_seconds: 90
    data_policy: image_review_required
```

Sub-agent 配置：

```yaml
agents:
  - name: security-researcher
    model_profile: private-long-context
    tools:
      - search_security_knowledge

  - name: ops-troubleshooter
    model_profile: private-main
    tools:
      - search_security_knowledge
      - query_device_status
      - create_security_todos
      - request_human_review

  - name: alarm-analyst
    model_profile: private-main
    tools:
      - search_security_knowledge
      - query_alarm_events
      - create_security_todos
      - request_human_review

  - name: object-analyst
    model_profile: public-vision
    tools:
      - analyze_security_object
      - search_security_knowledge
```

### 3.3 数据策略

| data_policy | 允许输入 | 禁止输入 |
|------------|----------|----------|
| `internal_only` | 内部 SOP、设备、告警、审计摘要 | 无特殊禁止，仍需脱敏密钥 |
| `sanitized_only` | 脱敏后的文本摘要 | 设备 IP、客户名、告警原文、内部 SOP 原文 |
| `image_review_required` | 已确认可外发的图片或脱敏图片 | 未授权现场图片、包含敏感区域的图片 |

Harness 必须在调用公开 API 前做数据策略校验。校验不通过时，应改用私有模型或返回需要人工确认。

---

## 4. Runtime 组件

```text
AgentRuntime
├── MainAgentRunner
├── SubAgentRunner
├── SubAgentRegistry
├── LLMGatewayFactory
├── HandoffService
├── CheckpointManager
└── InterruptManager
```

### 4.1 `LLMGatewayFactory`

职责：

- 根据 `model_profile` 创建模型客户端。
- 屏蔽私有模型和公开 API 的差异。
- 注入 timeout、retry、api key、base_url。
- 输出统一 `LLMGateway`。

接口：

```python
class LLMGatewayFactory:
    def create(self, profile_name: str) -> LLMGateway: ...
```

### 4.2 `SubAgentRegistry`

职责：

- 加载 Sub-agent 配置。
- 校验 agent name、tools、model_profile。
- 为 `SubAgentRunner` 提供 agent spec。

启动校验：

- 配置中的 `model_profile` 必须存在。
- 配置中的工具必须存在于 ToolRegistry。
- 公开 API profile 必须声明 data_policy。

### 4.3 `SubAgentRunner`

职责：

- 接收 HandoffPacket。
- 创建对应 LLM。
- 注入工具白名单。
- 执行任务。
- 返回 AgentRunResult。

### 4.4 `HandoffService`

职责：

- 主 Agent 到 Sub-agent 的唯一委派通道。
- 限制传递上下文，避免把全量会话直接交给 Sub-agent。
- 写 HandoffStore 和 trace。

### 4.5 `CheckpointManager`

职责：

- 使用 Redis 存储 LangGraph checkpoint。
- 以 `thread_id` 做 checkpoint namespace。
- 为 interrupt/resume 提供 checkpoint_ref。

### 4.6 `InterruptManager`

职责：

- 高风险工具节点触发 interrupt。
- 写 review_request。
- 输出终端 `[REVIEW_REQUIRED]`。
- 审批后调用 `Command(resume=...)`。

---

## 5. 执行链路

### 5.1 普通文本链路

```text
Harness RuntimeContext
  → MainAgentRunner(private-main)
  → handoff_to_agent(target_agent)
  → SubAgentRegistry 查 model_profile
  → LLMGatewayFactory 创建 LLM
  → SubAgentRunner 执行白名单工具
  → AgentRunResult
```

### 5.2 高风险中断链路

```text
Sub-agent 准备调用高风险工具
  → RiskGate 判断 high
  → InterruptManager.pause_for_review()
  → Redis checkpoint
  → PostgreSQL review_request pending
  → terminal [REVIEW_REQUIRED]
  → ChatResponse interrupted=true
  → approve/reject
  → InterruptManager.resume_after_review()
  → graph.invoke(Command(resume=...))
  → AgentRunResult
```

---

## 6. 审计字段

每次模型调用必须记录：

- agent_name
- model_profile
- provider
- model
- data_policy
- prompt_tokens / completion_tokens，若 provider 支持
- latency_ms

---

## 7. 当前实现状态

- 已实现 `config/agents.yaml`，每个 Sub-agent 通过 `model_profile` 绑定私有或公开模型配置。
- 已实现 `SubAgentRegistry` 启动校验：未知模型、未知工具、越权工具都会失败。
- 已实现 deterministic `AgentRuntime` 骨架：按路由选择工具链，并在 trace 中输出 `model_profile`、`data_policy`、skills 和 handoff 信息。
- 已实现 `HandoffService` 和内存 `HandoffStore` 骨架；PostgreSQL DAO 后续补齐。
- 尚未接入 DeepAgents / LangGraph，T50、T55、T65 仍为后续任务。
- status
- error_type

不能记录：

- API key。
- 完整敏感 prompt。
- 完整图片 base64。
- 未脱敏设备凭据。

---

## 7. 测试要求

- Sub-agent 使用自己的 `model_profile`。
- 配置不存在的 `model_profile` 启动失败。
- 公开 API profile 不能接收 `internal_only` 数据。
- 私有模型失败时按配置决定是否 fallback 到其他私有模型，不自动 fallback 到公开 API。
- 高风险工具调用能 interrupt。
- approve 后从 checkpoint resume。
- reject 后返回终止说明或替代建议。
