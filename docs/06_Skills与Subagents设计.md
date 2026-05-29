# 06 Skills 与 Sub-agents 设计

源头文档：`项目介绍.txt`

溯源段落：
- Skills 以 Markdown + YAML 管理并按需注入系统提示词。
- 通过 YAML 配置研究、排障、告警、物品研判等 Sub-agents。

覆盖任务：
- T52 Sub-agent 配置加载
- T53 Skill 扫描、frontmatter 解析、按需注入
- T83 object-analyst 链路

---

## 1. Sub-agent 列表

| Sub-agent | 职责 |
|-----------|------|
| `security-researcher` | 安防知识检索与 SOP 问答 |
| `ops-troubleshooter` | 设备接入、离线、部署排障 |
| `alarm-analyst` | 告警误报、规则分析、处置建议 |
| `object-analyst` | 图片物品研判 |

---

## 2. 配置结构

```yaml
agents:
  - name: ops-troubleshooter
    description: 设备接入、离线、部署排障
    model_profile: private-main
    tools:
      - query_device_status
      - search_security_knowledge
      - create_security_todos
      - request_human_review
```

---

## 3. Skill 文件

```text
skills/<name>/SKILL.md
```

frontmatter：

```yaml
---
name: ops-troubleshooter
description: 设备接入和离线排障
triggers:
  - 离线
  - 接入失败
---
```

---

## 4. 验收

- Skill 不新增工具，只影响提示词。
- Sub-agent 工具白名单来自配置。
- Sub-agent 模型来自 `model_profile`。
- 配置不存在的工具或模型时启动失败。

---

## 5. 当前实现状态

- `config/agents.yaml` 已定义 `main-agent`、`security-researcher`、`ops-troubleshooter`、`alarm-analyst`、`object-analyst`。
- `skills/*/SKILL.md` 已按 YAML frontmatter + Markdown 正文组织。
- `load_skills()`、`select_skills()`、`render_skills_prompt()` 已实现并有单元测试。
- `AgentRuntime` 已将命中的 skill 名称和注入提示长度写入 trace，后续接 LLM 时复用该 prompt。
