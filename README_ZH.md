# ScriptWriter

基于 FastAPI 的线程隔离（thread-scoped）多智能体剧本后端。

For English, see [README.md](README.md).

## 项目能力

- 执行 `planner -> writer -> critic` 编排链路。
- 持久化 `session/run/events/snapshot`，支持运行恢复。
- 支持线程隔离上传与产物读取，并具备路径穿越防护。
- 支持基于 RAG 的知识入库/检索，以及可选 MCP 工具。

## 文档

- [文档入口](docs/README.md)
- [中文文档](docs/zh/README.md)
- [架构总览](docs/zh/architecture.md)
- [API 参考](docs/zh/api-reference.md)
- [运行与配置](docs/zh/operations.md)
- [开发指南](docs/zh/development.md)
- [安全模型](docs/zh/security-model.md)
- [历史设计/计划](docs/plans/)

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 启动 API

```bash
PYTHONPATH=src uv run uvicorn scriptwriter.gateway.app:app --reload
```

### 3. 运行质量检查

```bash
uv run --extra dev ruff check src tests
uv run pytest -q
```

## 主要接口

- `POST /api/threads/{thread_id}/chat`
- `GET /api/threads/{thread_id}/runs/{run_id}?user_id=...&project_id=...`
- `POST /api/threads/{thread_id}/knowledge/ingest`
- `POST /api/threads/{thread_id}/knowledge/upload`
- `GET /api/threads/{thread_id}/knowledge/upload/list`
- `DELETE /api/threads/{thread_id}/knowledge/upload/{filename}`
- `GET /api/threads/{thread_id}/artifacts/{path}`

请求与响应细节见 [API 参考](docs/zh/api-reference.md)。

## 运行说明

- `user_id` 和 `project_id` 为必填。
- `thread_id` 会按正则 `^[A-Za-z0-9_-]+$` 校验。
- `data/threads/` 是运行时数据，已加入 `.gitignore`。
