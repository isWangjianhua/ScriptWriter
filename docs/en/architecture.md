# Architecture Overview

## Runtime Topology

ScriptWriter currently runs as a single FastAPI process:

- Gateway: HTTP API + NDJSON streaming
- Orchestrator: synchronous `planner -> writer -> critic` flow
- Persistence: state store (PostgreSQL preferred, in-memory fallback)
- Knowledge: metadata + vector retrieval for story bible data

```mermaid
flowchart TB
    Client[Client / Frontend]

    subgraph API[FastAPI Gateway]
      ChatRouter["chat.py (/chat, /runs, /knowledge/ingest)"]
      UploadRouter["uploads.py (/upload, /list, /delete)"]
      ArtifactRouter["artifacts.py (/artifacts/<path>)"]
      PathGuard["paths.py (thread_id + path safety checks)"]
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

## Execution Flow

1. Client calls `POST /api/threads/{thread_id}/chat`.
2. Gateway validates `thread_id`, `user_id`, `project_id`.
3. Gateway builds `ScreenplayState` and executes orchestrator via `asyncio.to_thread(...)`.
4. Orchestrator creates/uses session, creates run, appends events + snapshots.
5. Planner/Writer/Critic produce deltas; orchestrator merges into state.
6. Gateway streams NDJSON events (`run_started`, `canvas_update`, `chat_chunk`, `critic_note`, `error`).

```mermaid
flowchart TD
    A["POST /api/threads/<thread_id>/chat"] --> B["Validate thread_id / user_id / project_id"]
    B --> C{"Has resume_run_id?"}
    C -- No --> D["Build initial ScreenplayState"]
    C -- Yes --> E["recover_run_state(thread_id, user_id, project_id)"]
    E --> F{"Scoped ownership check passed?"}
    F -- No --> X["Return 403/404"]
    F -- Yes --> G["Merge recovered state into inputs"]
    G --> H["asyncio.to_thread(run_lead_agent_flow)"]
    D --> H
    H --> I["planner -> writer -> critic"]
    I --> J["append event + save snapshot"]
    J --> K["Stream NDJSON: run_started/canvas_update/chat_chunk/critic_note"]
```

## Run Recovery Flow

```mermaid
flowchart TD
    A["GET /api/threads/<thread_id>/runs/<run_id>"] --> B["Validate thread_id"]
    B --> C["get_run(run_id) existence check"]
    C -->|Not found| N["404 run not found"]
    C -->|Found| D["get_run_scoped(run_id, thread_id, user_id, project_id)"]
    D -->|Scope mismatch| F["403 forbidden"]
    D -->|Scope valid| G["Load snapshot + events"]
    G --> H["Replay deltas to rebuild state"]
    H --> I["Return run/state/events/replayed_events"]
```

## Upload and Artifact Access Flow

```mermaid
flowchart TD
    A["POST /knowledge/upload"] --> B["safe_thread_id + filename normalization"]
    B --> C["Chunked read + SCRIPTWRITER_MAX_UPLOAD_BYTES"]
    C --> D["resolve_upload_path traversal guard"]
    D --> E["Write data/threads/<thread_id>/uploads"]
    E --> F["Extract text via markitdown"]
    F --> G["ingest_knowledge_document"]
    G --> H["Return virtual_path + artifact_url"]

    I["GET /artifacts/<path>"] --> J["resolve_thread_virtual_path"]
    J --> K{"Inside allowed virtual roots?"}
    K -- No --> L["400/403"]
    K -- Yes --> M["Read and return inline or download by mime"]
```

## Module Map

### Gateway

- `src/scriptwriter/gateway/app.py`: app composition
- `src/scriptwriter/gateway/paths.py`: thread/path safety utilities
- `src/scriptwriter/gateway/routers/chat.py`: chat, run recovery, knowledge ingest
- `src/scriptwriter/gateway/routers/uploads.py`: upload + list + delete
- `src/scriptwriter/gateway/routers/artifacts.py`: virtual-path artifact serving

### Agent Layer

- `src/scriptwriter/agents/thread_state.py`: canonical state schema
- `src/scriptwriter/agents/lead_agent/orchestrator.py`: orchestration + recovery
- `src/scriptwriter/agents/lead_agent/planner.py`
- `src/scriptwriter/agents/lead_agent/writer.py`
- `src/scriptwriter/agents/lead_agent/critic.py`
- `src/scriptwriter/agents/middlewares/`: prompt/state/tool integrity middlewares

### State Store

- `src/scriptwriter/state_store/base.py`: protocol + typed models
- `src/scriptwriter/state_store/factory.py`: backend selection
- `src/scriptwriter/state_store/in_memory.py`: test/dev fallback
- `src/scriptwriter/state_store/postgres.py`: durable backend

### Knowledge (RAG)

- `src/scriptwriter/rag/service.py`: ingest/search orchestration
- `src/scriptwriter/rag/metadata_store.py`: SQLite metadata index
- `src/scriptwriter/agents/memory/milvus_store.py`: vector store adapter

### MCP and Tools

- `src/scriptwriter/mcp/client.py`: MCP server config adapter
- `src/scriptwriter/mcp/tools.py`: cached MCP tool loader
- `src/scriptwriter/tools/builtins/`: story bible search/store, web search, skill read

## Data Boundaries

- Thread files: `${SCRIPTWRITER_THREADS_DIR}/{thread_id}/...`
- Virtual artifact paths: `/mnt/user-data/{uploads|outputs|workspace}/...`
- Knowledge metadata/source: `${SCRIPTWRITER_RAG_DATA_DIR}`
- State store data: PostgreSQL tables or process memory

## Compatibility Notes

- Public APIs are thread-scoped.
- Legacy non-thread-scoped endpoints are removed.
- `user_id` and `project_id` are mandatory for all write/recovery flows.
