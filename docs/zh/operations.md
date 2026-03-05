# 运行与配置

## 常用命令

安装：

```bash
uv sync
```

启动 API：

```bash
PYTHONPATH=src uv run uvicorn scriptwriter.gateway.app:app --reload
```

测试与静态检查：

```bash
uv run pytest -q
uv run --extra dev ruff check src tests
```

重建知识索引：

```bash
uv run python scripts/rebuild_knowledge_index.py \
  --user-id user_1 \
  --project-id project_alpha
```

## 环境变量

### 核心

- `OPENAI_API_KEY`
- `SCRIPTWRITER_DATABASE_URL`
- `SCRIPTWRITER_THREADS_DIR`（默认 `data/threads`）
- `SCRIPTWRITER_RAG_DATA_DIR`（默认 `data/rag`）
- `SCRIPTWRITER_MAX_UPLOAD_BYTES`（默认 `20971520`）

### 模型

- `SCRIPTWRITER_WRITER_MODEL`（默认 `gpt-4o`）
- `SCRIPTWRITER_CRITIC_MODEL`（默认 `gpt-4o-mini`）

### Embedding / 检索

- `SCRIPTWRITER_EMBEDDING_PROVIDER`（`auto`、`openai`、`mock`）
- `SCRIPTWRITER_EMBEDDING_MODEL`
- `SCRIPTWRITER_MILVUS_DB_PATH`（默认 `./data/milvus_demo.db`）

### MCP

- `SCRIPTWRITER_MCP_SERVERS_JSON`
- `SCRIPTWRITER_ENABLE_BRAVE_MCP`
- `BRAVE_API_KEY`

## State Store 选择

`state_store/factory.py` 的选择逻辑：

- 配置 `SCRIPTWRITER_DATABASE_URL` 且初始化成功：使用 PostgreSQL
- 否则：使用 InMemory

建议：

- 需要持久化的环境使用 PostgreSQL
- InMemory 只用于本地测试和演示

## 数据目录

- 线程运行数据：`data/threads/{thread_id}/...`
- RAG 元数据与原文：`data/rag/...`
- Milvus 本地文件：`data/milvus_demo.db`（默认）

`data/threads/` 属于运行时数据，不应提交到 Git。

## 当前运维缺口

当前尚未内建：

- 统一 request ID 链路追踪
- 指标导出（metrics）
- 认证后上下文自动注入

上线前建议补齐以上能力。
