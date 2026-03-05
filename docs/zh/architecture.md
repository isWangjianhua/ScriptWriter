# 架构总览

## 运行拓扑

ScriptWriter 目前是单进程 FastAPI 服务：

- Gateway：HTTP API + NDJSON 流输出
- Orchestrator：同步 `planner -> writer -> critic` 编排
- Persistence：状态存储（优先 PostgreSQL，回退 InMemory）
- Knowledge：故事知识的元数据与向量检索

```mermaid
flowchart TB
    Client[Client / Frontend]

    subgraph API[FastAPI Gateway]
      ChatRouter["chat.py (/chat, /runs, /knowledge/ingest)"]
      UploadRouter["uploads.py (/upload, /list, /delete)"]
      ArtifactRouter["artifacts.py (/artifacts/<path>)"]
      PathGuard["paths.py (thread_id + 路径安全校验)"]
    end

    subgraph Agent[Lead Agent Runtime]
      Orchestrator["orchestrator.py"]
      Planner["planner.py"]
      Writer["writer.py"]
      Critic["critic.py"]
      Mid["middlewares/*"]
    end

    subgraph Store[State Store]
      Factory["state_store/factory.py"]
      PG["postgres.py"]
      MEM["in_memory.py"]
    end

    subgraph Knowledge[RAG + Tools]
      RAG["rag/service.py"]
      Meta["rag/metadata_store.py"]
      Milvus["memory/milvus_store.py"]
      MCP["mcp/tools.py"]
      Builtins["tools/builtins/*"]
    end

    subgraph Files[Thread Filesystem]
      Threads["$SCRIPTWRITER_THREADS_DIR/<thread_id>/..."]
    end

    Client --> API
    ChatRouter --> PathGuard
    UploadRouter --> PathGuard
    ArtifactRouter --> PathGuard

    ChatRouter --> Orchestrator
    Orchestrator --> Planner --> Writer --> Critic
    Planner --> Mid
    Writer --> Mid
    Critic --> Mid

    Orchestrator --> Factory
    Factory --> PG
    Factory --> MEM

    ChatRouter --> RAG
    UploadRouter --> RAG
    RAG --> Meta
    RAG --> Milvus
    Writer --> MCP
    Writer --> Builtins

    UploadRouter --> Threads
    ArtifactRouter --> Threads
```

## 执行流程

1. 客户端请求 `POST /api/threads/{thread_id}/chat`。
2. Gateway 校验 `thread_id`、`user_id`、`project_id`。
3. Gateway 构造 `ScreenplayState`，并通过 `asyncio.to_thread(...)` 执行编排。
4. Orchestrator 创建/复用 session，创建 run，写入 event 与 snapshot。
5. Planner/Writer/Critic 返回 delta，编排器合并状态。
6. Gateway 以 NDJSON 持续返回 `run_started`、`canvas_update`、`chat_chunk`、`critic_note`、`error`。

```mermaid
flowchart TD
    A["POST /api/threads/<thread_id>/chat"] --> B["校验 thread_id / user_id / project_id"]
    B --> C{"是否包含 resume_run_id"}
    C -- 否 --> D["构建初始 ScreenplayState"]
    C -- 是 --> E["recover_run_state(thread_id, user_id, project_id)"]
    E --> F{"恢复是否通过归属校验"}
    F -- 否 --> X["返回 403/404"]
    F -- 是 --> G["合并历史 state 到输入"]
    G --> H["asyncio.to_thread(run_lead_agent_flow)"]
    D --> H
    H --> I["planner -> writer -> critic"]
    I --> J["append event + save snapshot"]
    J --> K["NDJSON streaming 返回 run_started/canvas_update/chat_chunk/critic_note"]
```

## 运行恢复链路

```mermaid
flowchart TD
    A["GET /api/threads/<thread_id>/runs/<run_id>"] --> B["校验 thread_id"]
    B --> C["get_run(run_id) 检查存在性"]
    C -->|不存在| N["404 run not found"]
    C -->|存在| D["get_run_scoped(run_id, thread_id, user_id, project_id)"]
    D -->|归属不匹配| F["403 forbidden"]
    D -->|通过| G["读取 snapshot + events"]
    G --> H["replay delta 恢复 state"]
    H --> I["返回 run/state/events/replayed_events"]
```

## 上传与产物访问链路

```mermaid
flowchart TD
    A["POST /knowledge/upload"] --> B["safe_thread_id + 文件名规范化"]
    B --> C["分块读取 + SCRIPTWRITER_MAX_UPLOAD_BYTES"]
    C --> D["resolve_upload_path 防 traversal"]
    D --> E["写入 data/threads/<thread_id>/uploads"]
    E --> F["markitdown 抽取文本"]
    F --> G["ingest_knowledge_document 入库"]
    G --> H["返回 virtual_path + artifact_url"]

    I["GET /artifacts/<path>"] --> J["resolve_thread_virtual_path"]
    J --> K{"路径是否在允许的虚拟目录内"}
    K -- 否 --> L["400/403"]
    K -- 是 --> M["读取文件并按 mime 返回 inline 或 download"]
```

## 模块分层

### Gateway

- `src/scriptwriter/gateway/app.py`：应用装配
- `src/scriptwriter/gateway/paths.py`：线程路径与安全校验
- `src/scriptwriter/gateway/routers/chat.py`：聊天、run 恢复、知识入库
- `src/scriptwriter/gateway/routers/uploads.py`：上传、列举、删除
- `src/scriptwriter/gateway/routers/artifacts.py`：虚拟路径文件访问

### Agent 层

- `src/scriptwriter/agents/thread_state.py`：状态结构
- `src/scriptwriter/agents/lead_agent/orchestrator.py`：编排与恢复
- `src/scriptwriter/agents/lead_agent/planner.py`
- `src/scriptwriter/agents/lead_agent/writer.py`
- `src/scriptwriter/agents/lead_agent/critic.py`
- `src/scriptwriter/agents/middlewares/`：上下文/提示/工具完整性中间件

### State Store

- `src/scriptwriter/state_store/base.py`：协议与类型
- `src/scriptwriter/state_store/factory.py`：后端选择
- `src/scriptwriter/state_store/in_memory.py`：本地回退
- `src/scriptwriter/state_store/postgres.py`：持久化后端

### Knowledge（RAG）

- `src/scriptwriter/rag/service.py`：入库与检索编排
- `src/scriptwriter/rag/metadata_store.py`：SQLite 元数据
- `src/scriptwriter/agents/memory/milvus_store.py`：向量存储适配

### MCP 与工具

- `src/scriptwriter/mcp/client.py`：MCP 配置解析
- `src/scriptwriter/mcp/tools.py`：MCP 工具缓存加载
- `src/scriptwriter/tools/builtins/`：知识检索/存储、联网搜索、技能读取

## 数据边界

- 线程文件：`${SCRIPTWRITER_THREADS_DIR}/{thread_id}/...`
- 虚拟路径：`/mnt/user-data/{uploads|outputs|workspace}/...`
- 知识库：`${SCRIPTWRITER_RAG_DATA_DIR}`
- 运行状态：PostgreSQL 或进程内存

## 兼容性说明

- 公共 API 已全部 thread-scoped。
- 旧的非 thread-scoped 接口已移除。
- `user_id` 与 `project_id` 现在都是必填。
