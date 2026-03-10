# 运行与配置

## 常用命令

安装：

```bash
uv sync
```

启动 API：

```bash
PYTHONPATH=src uv run uvicorn scriptwriter.api.app:app --reload
```

测试与静态检查：

```bash
uv run pytest -q
uv run --extra dev ruff check src tests
```

## 环境变量

### 知识库存储

- `SCRIPTWRITER_RAG_DATA_DIR`  
  SQLite 元数据与原文存储根目录，默认 `data/rag`
- `SCRIPTWRITER_MILVUS_DB_PATH`  
  Milvus 本地数据库路径，默认 `./data/milvus_demo.db`

### Embedding

- `OPENAI_API_KEY`
- `SCRIPTWRITER_EMBEDDING_PROVIDER`  
  支持 `auto`、`openai`、`mock`
- `SCRIPTWRITER_EMBEDDING_MODEL`  
  默认 OpenAI embedding 模型为 `text-embedding-3-small`

### MCP

- `SCRIPTWRITER_MCP_SERVERS_JSON`  
  MCP server 配置 JSON 对象
- `SCRIPTWRITER_ENABLE_BRAVE_MCP`  
  旧式 Brave MCP 快捷开关
- `BRAVE_API_KEY`

## 持久化模型

### 项目工作流状态

- 项目对象
- 产物版本
- 确认记录

这些都通过 `InMemoryProjectStore` 保存在进程内存，API 重启后会清空。

### 知识库数据

- 文档元数据：默认位于 `data/rag/metadata.db`
- 原文：默认位于 `data/rag/sources/`
- 向量数据：Milvus 本地数据库文件

知识库数据在进程重启后仍会保留。

## 运维说明

- 当前实现没有文档化的生产级项目状态持久化后端。
- 若 Milvus 不可用，入库仍会保留元数据和原文，但向量检索能力会退化或关闭。
- 若 OpenAI embedding 不可用，系统会自动回退到哈希 embedding。

## 数据目录

- 知识元数据与原文：`data/rag/...`
- Milvus 本地数据库：默认 `data/milvus_demo.db`

## 当前运维缺口

当前代码库尚未提供：

- 请求级 tracing
- 结构化 metrics 导出
- 基于认证身份的运行时上下文
- 持久化的项目工作流存储
