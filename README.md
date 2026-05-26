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

## 安防物品研判（图片识别）

启用多模态能力后，主 Agent 会先识别图片/物品研判意图，再委派 `object-analyst` 子 Agent 调用多模态 API：

```bash
SECURITY_AGENT_VISION_ENABLED=true
SECURITY_AGENT_VISION_MODEL=qwen-vl-plus
SECURITY_AGENT_VISION_API_KEY=your-api-key
SECURITY_AGENT_VISION_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

调用示例：

```bash
curl -X POST http://127.0.0.1:8015/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请识别这张抓拍图里的异常物品，并给出安防研判。",
    "thread_id": "vision-test-1",
    "user_id": "ops_001",
    "image_path": "uploads/sample.jpg"
  }'
```

图片文件需放在 `data/workspace/` 下，例如 `data/workspace/uploads/sample.jpg`。

## 前端工作台

项目包含一个 React + TypeScript + Vite 前端，用于产品化展示安防助手能力：

```bash
cd /home/blding/security-deepagent-practice/frontend
npm install
cp .env.example .env
npm run dev
```

默认前端地址为 `http://127.0.0.1:5173`，后端地址通过 `VITE_API_BASE_URL` 配置，默认指向 `http://127.0.0.1:8015`。

前端包含：

- 智能工作台：聊天、答案、证据、ReAct 轨迹、任务和风险展示。
- 图片上传：支持上传图片并调用后端 `image_base64` 完成安防物品研判。
- 业务概览：设备和告警概览。
- 历史会话：读取 `/threads` 和 `/threads/{thread_id}`。
- 人工确认：读取 `/reviews` 并调用 `/review/continue`。

## 沙箱配置

项目默认使用本地轻量沙箱：

```bash
SECURITY_AGENT_SANDBOX_PROVIDER=local
SECURITY_AGENT_ALLOW_SHELL=false
```

`local` provider 会把 Agent 可写目录限制在 `data/workspace/`。如需预留 OpenSandbox 部署，可以切换：

```bash
SECURITY_AGENT_SANDBOX_PROVIDER=opensandbox
SECURITY_AGENT_OPENSANDBOX_DOMAIN=http://your-opensandbox-host:8080
```

当前轻量版本只提供 OpenSandbox 接入点，真实接入时需要补充 OpenSandbox SDK、连接配置和 backend adapter。

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

