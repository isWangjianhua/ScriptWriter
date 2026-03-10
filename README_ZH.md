# ScriptWriter

基于 FastAPI 的 project-scoped 剧本后端。

For English, see [README.md](README.md).

## 项目能力

- 管理 `bible -> outline -> draft` 的剧本工作流。
- 按项目维护产物版本与确认记录。
- 当前项目状态存放在进程内存中，便于本地迭代。
- 将项目知识入库到 PostgreSQL 元数据、OpenSearch 关键词索引和 Milvus 向量存储。
- 提供内置联网搜索和故事知识检索工具。

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
PYTHONPATH=src uv run uvicorn scriptwriter.api.app:app --reload
```

### 3. 运行质量检查

```bash
uv run --extra dev ruff check src tests
uv run pytest -q
```

## 主要接口

- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/chat`
- `POST /api/projects/{project_id}/confirm`
- `POST /api/projects/{project_id}/knowledge/upload`
- `GET /api/projects/{project_id}/versions`

请求与响应细节见 [API 参考](docs/zh/api-reference.md)。

## 运行说明

- 当前接口全部返回 JSON，没有流式 chat 或 run 恢复接口。
- 项目记录、版本和确认信息保存在进程内存里，服务重启后会清空。
- 知识库默认落在 `data/rag/`，向量数据写入 Milvus 本地数据库文件。
- `POST /api/projects/{project_id}/chat` 在项目不存在且请求里提供 `title` 时，会先创建项目再生成首个 bible。
- 知识检索现在要求启动时可用 `PostgreSQL + OpenSearch + Milvus`，建议从 `.env.example` 复制配置。
