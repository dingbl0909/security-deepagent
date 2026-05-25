# Security DeepAgent Practice

面向安防场景的轻量化 DeepAgents 本地生产系统。项目默认使用本地 SQLite、Markdown 知识库、文件审计日志和 FastAPI，适合部署在个人工作站上完成端到端测试。

## 核心能力

- 安防知识库检索和证据返回
- 设备状态、告警事件、任务状态本地持久化
- DeepAgent 主代理和 YAML 子代理配置
- 高风险操作人工确认标记
- 会话记忆、审计日志和线程查询
- CLI 与 FastAPI 两种调用方式

## 快速开始

```bash
cd /home/blding/security-deepagent-practice
source /home/blding/grapgrag_env/bin/activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env
python scripts/init_db.py
uvicorn security_agent.app:app --host 0.0.0.0 --port 8015
```

如果没有可用的大模型服务，可以在 `.env` 中保持 `SECURITY_AGENT_LLM_ENABLED=false`，系统会使用本地规则链路完成测试。

## API 示例

```bash
curl -X POST http://127.0.0.1:8015/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "仓库北门摄像头离线，帮我根据知识库排查原因，并给出下一步建议。",
    "thread_id": "local-test-1",
    "user_id": "ops_001"
  }'
```

查看线程：

```bash
curl http://127.0.0.1:8015/threads/local-test-1
```

## CLI 示例

```bash
python scripts/run_cli.py "仓库北门摄像头离线，帮我排查"
```

## 目录说明

- `config/`：系统配置和子代理配置
- `data/knowledge/`：本地安防知识库
- `data/db/`：SQLite 数据库
- `data/logs/`：审计日志
- `data/memory/`：会话摘要和本地记忆
- `data/workspace/`：Agent 可写工作目录
- `src/security_agent/`：系统核心代码

